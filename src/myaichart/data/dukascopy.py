from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import lzma
import struct
from dataclasses import dataclass

import httpx

from myaichart.models import NormalizedTick

# Current Dukascopy export buckets one tick file per day.  Keep the legacy
# hourly URL for compatibility helpers, but six-month collection uses DAILY_URL
# to drastically reduce request pressure and 429 exposure.
DAILY_URL = 'https://datafeed.dukascopy.com/datafeed/{symbol}/{year:04d}/{month0:02d}/{day:02d}_ticks.bi5'
HOURLY_URL = 'https://datafeed.dukascopy.com/datafeed/{symbol}/{year:04d}/{month0:02d}/{day:02d}/{hour:02d}h_ticks.bi5'
PRICE_SCALES = {'XAUUSD': 1000, 'XAGUSD': 1000}
DEFAULT_HEADERS = {
    'User-Agent': 'myaichart/0.1 research-data-collector',
    'Accept': 'application/octet-stream,*/*;q=0.8',
}


def decode_bi5_ticks(payload: bytes, base_utc: datetime, *, symbol='XAUUSD', price_scale: int | None = None, received_utc: datetime | None = None):
    if base_utc.tzinfo is None:
        raise ValueError('base time must be timezone-aware')
    raw = lzma.decompress(payload, format=lzma.FORMAT_ALONE)
    if len(raw) % 20:
        raise ValueError('bi5 payload length is not a multiple of 20 bytes')
    scale = price_scale or PRICE_SCALES.get(symbol, 100000)
    received = received_utc or datetime.now(timezone.utc)
    base = base_utc.astimezone(timezone.utc)
    out: list[NormalizedTick] = []
    for idx in range(0, len(raw), 20):
        ms, ask_i, bid_i, ask_vol, bid_vol = struct.unpack('>IIIff', raw[idx:idx+20])
        ts = base + timedelta(milliseconds=ms)
        row_index = idx // 20
        rid = f'{int(ts.timestamp()*1000)}-{row_index}-{ask_i}-{bid_i}'
        out.append(NormalizedTick(
            symbol=symbol,
            source='dukascopy',
            source_record_id=rid,
            source_timestamp_utc=ts,
            received_timestamp_utc=received,
            bid=bid_i / scale,
            ask=ask_i / scale,
            bid_volume_best=float(bid_vol),
            ask_volume_best=float(ask_vol),
            sequence_id=str(row_index),
        ))
    return out


@dataclass(frozen=True)
class CollectionStats:
    tick_count: int
    chunk_count: int
    first_tick_utc: datetime | None
    last_tick_utc: datetime | None


class DukascopyHistoricalProvider:
    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        attempts: int = 8,
        concurrency: int = 1,
        max_backoff_seconds: float = 60.0,
    ):
        self._client = client
        self.attempts = max(1, int(attempts))
        self.concurrency = max(1, int(concurrency))
        self.max_backoff_seconds = max(0.0, float(max_backoff_seconds))

    def _retry_delay(self, response: httpx.Response | None, attempt: int) -> float:
        if response is not None:
            value = response.headers.get('Retry-After')
            if value:
                try:
                    return min(max(float(value), 0.0), self.max_backoff_seconds)
                except ValueError:
                    pass
        return min(float(2 ** attempt), self.max_backoff_seconds)

    async def _request_with_retry(self, url: str, client: httpx.AsyncClient) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self.attempts):
            response: httpx.Response | None = None
            try:
                response = await client.get(url, headers=DEFAULT_HEADERS)
                if response.status_code in (404, 204):
                    return response
                if response.status_code == 429 or 500 <= response.status_code < 600:
                    if attempt + 1 >= self.attempts:
                        response.raise_for_status()
                    await asyncio.sleep(self._retry_delay(response, attempt))
                    continue
                response.raise_for_status()
                return response
            except httpx.TransportError as exc:
                last_error = exc
                if attempt + 1 >= self.attempts:
                    raise
                await asyncio.sleep(self._retry_delay(response, attempt))
        if last_error is not None:
            raise last_error
        raise RuntimeError('request retry loop exhausted')

    async def _fetch_hour(self, symbol: str, hour_utc: datetime, client: httpx.AsyncClient | None = None):
        """Legacy hourly fetch helper retained for compatibility and diagnostics."""
        hour_utc = hour_utc.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
        url = HOURLY_URL.format(
            symbol=symbol,
            year=hour_utc.year,
            month0=hour_utc.month - 1,
            day=hour_utc.day,
            hour=hour_utc.hour,
        )
        owns = client is None and self._client is None
        client = client or self._client or httpx.AsyncClient(timeout=30)
        try:
            response = await self._request_with_retry(url, client)
            if response.status_code in (404, 204) or not response.content:
                return []
            try:
                return decode_bi5_ticks(response.content, hour_utc, symbol=symbol)
            except lzma.LZMAError:
                raise
        finally:
            if owns:
                await client.aclose()

    async def _fetch_day(self, symbol: str, day_utc: datetime, client: httpx.AsyncClient | None = None):
        day_utc = day_utc.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        url = DAILY_URL.format(
            symbol=symbol,
            year=day_utc.year,
            month0=day_utc.month - 1,
            day=day_utc.day,
        )
        owns = client is None and self._client is None
        client = client or self._client or httpx.AsyncClient(timeout=60)
        try:
            response = await self._request_with_retry(url, client)
            if response.status_code in (404, 204) or not response.content:
                return []
            return decode_bi5_ticks(response.content, day_utc, symbol=symbol)
        finally:
            if owns:
                await client.aclose()

    async def _iter_hour_chunks_with_client(self, client, symbol: str, start_utc: datetime, end_utc: datetime):
        days=[]
        cur = start_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        end_day = end_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        while cur <= end_day:
            days.append(cur)
            cur += timedelta(days=1)

        # Daily files reduce a six-month run from roughly 4,300 HTTP requests
        # to roughly 180.  Default concurrency is intentionally conservative.
        for pos in range(0, len(days), self.concurrency):
            batch=days[pos:pos+self.concurrency]
            results=await asyncio.gather(*(self._fetch_day(symbol, day, client) for day in batch))
            for ticks in results:
                by_hour: dict[datetime, list[NormalizedTick]] = {}
                for t in ticks:
                    if not (start_utc <= t.source_timestamp_utc <= end_utc):
                        continue
                    hour=t.source_timestamp_utc.replace(minute=0, second=0, microsecond=0)
                    by_hour.setdefault(hour, []).append(t)
                for hour in sorted(by_hour):
                    yield sorted(by_hour[hour], key=lambda t: (t.source_timestamp_utc, t.source_record_id))

    async def iter_hour_chunks(self, symbol: str, start_utc: datetime, end_utc: datetime):
        start_utc = start_utc.astimezone(timezone.utc)
        end_utc = end_utc.astimezone(timezone.utc)
        if end_utc < start_utc:
            raise ValueError('end_utc must be >= start_utc')
        if self._client is not None:
            async for chunk in self._iter_hour_chunks_with_client(self._client, symbol, start_utc, end_utc):
                yield chunk
            return
        async with httpx.AsyncClient(timeout=60) as client:
            async for chunk in self._iter_hour_chunks_with_client(client, symbol, start_utc, end_utc):
                yield chunk

    async def fetch_ticks(self, symbol: str, start_utc: datetime, end_utc: datetime):
        # Compatibility helper for bounded windows. Six-month collection uses
        # iter_hour_chunks() via collect_range() and never accumulates all ticks.
        out: list[NormalizedTick] = []
        async for chunk in self.iter_hour_chunks(symbol, start_utc, end_utc):
            out.extend(chunk)
        return out


async def collect_range(provider, store, symbol: str, start_utc: datetime, end_utc: datetime) -> CollectionStats:
    tick_count = 0
    chunk_count = 0
    first_tick_utc = None
    last_tick_utc = None
    if hasattr(provider, 'iter_hour_chunks'):
        async for chunk in provider.iter_hour_chunks(symbol, start_utc, end_utc):
            if not chunk:
                continue
            store.append_chunk(chunk)
            chunk_count += 1
            tick_count += len(chunk)
            if first_tick_utc is None or chunk[0].source_timestamp_utc < first_tick_utc:
                first_tick_utc = chunk[0].source_timestamp_utc
            if last_tick_utc is None or chunk[-1].source_timestamp_utc > last_tick_utc:
                last_tick_utc = chunk[-1].source_timestamp_utc
    else:
        chunk = await provider.fetch_ticks(symbol, start_utc, end_utc)
        if chunk:
            store.append_chunk(chunk)
            chunk_count = 1
            tick_count = len(chunk)
            first_tick_utc = min(t.source_timestamp_utc for t in chunk)
            last_tick_utc = max(t.source_timestamp_utc for t in chunk)
    return CollectionStats(tick_count, chunk_count, first_tick_utc, last_tick_utc)
