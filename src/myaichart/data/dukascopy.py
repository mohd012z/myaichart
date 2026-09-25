from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import lzma
import struct
from dataclasses import dataclass
import httpx

from myaichart.models import NormalizedTick

URL = 'https://datafeed.dukascopy.com/datafeed/{symbol}/{year:04d}/{month0:02d}/{day:02d}/{hour:02d}h_ticks.bi5'
PRICE_SCALES = {'XAUUSD': 1000, 'XAGUSD': 1000}


def decode_bi5_ticks(payload: bytes, base_hour_utc: datetime, *, symbol='XAUUSD', price_scale: int | None = None, received_utc: datetime | None = None):
    if base_hour_utc.tzinfo is None:
        raise ValueError('base hour must be timezone-aware')
    raw = lzma.decompress(payload, format=lzma.FORMAT_ALONE)
    if len(raw) % 20:
        raise ValueError('bi5 payload length is not a multiple of 20 bytes')
    scale = price_scale or PRICE_SCALES.get(symbol, 100000)
    received = received_utc or datetime.now(timezone.utc)
    out: list[NormalizedTick] = []
    for idx in range(0, len(raw), 20):
        ms, ask_i, bid_i, ask_vol, bid_vol = struct.unpack('>IIIff', raw[idx:idx+20])
        ts = base_hour_utc.astimezone(timezone.utc) + timedelta(milliseconds=ms)
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
    def __init__(self, *, client: httpx.AsyncClient | None = None, attempts: int = 3, concurrency: int = 8):
        self._client = client
        self.attempts = attempts
        self.concurrency = max(1, int(concurrency))

    async def _fetch_hour(self, symbol: str, hour_utc: datetime, client: httpx.AsyncClient | None = None):
        url = URL.format(symbol=symbol, year=hour_utc.year, month0=hour_utc.month - 1, day=hour_utc.day, hour=hour_utc.hour)
        owns = client is None and self._client is None
        client = client or self._client or httpx.AsyncClient(timeout=30)
        try:
            for attempt in range(self.attempts):
                try:
                    response = await client.get(url)
                    if response.status_code in (404, 204) or not response.content:
                        return []
                    response.raise_for_status()
                    return decode_bi5_ticks(response.content, hour_utc, symbol=symbol)
                except (httpx.HTTPError, lzma.LZMAError):
                    if attempt + 1 >= self.attempts:
                        raise
                    await asyncio.sleep(min(2 ** attempt, 4))
        finally:
            if owns:
                await client.aclose()

    async def _iter_hour_chunks_with_client(self, client, symbol: str, start_utc: datetime, end_utc: datetime):
        hours=[]
        cur = start_utc.replace(minute=0, second=0, microsecond=0)
        end_hour = end_utc.replace(minute=0, second=0, microsecond=0)
        while cur <= end_hour:
            hours.append(cur)
            cur += timedelta(hours=1)
        for pos in range(0, len(hours), self.concurrency):
            batch=hours[pos:pos+self.concurrency]
            results=await asyncio.gather(*(self._fetch_hour(symbol, hour, client) for hour in batch))
            for ticks in results:
                filtered = [t for t in ticks if start_utc <= t.source_timestamp_utc <= end_utc]
                if filtered:
                    yield filtered

    async def iter_hour_chunks(self, symbol: str, start_utc: datetime, end_utc: datetime):
        start_utc = start_utc.astimezone(timezone.utc)
        end_utc = end_utc.astimezone(timezone.utc)
        if self._client is not None:
            async for chunk in self._iter_hour_chunks_with_client(self._client, symbol, start_utc, end_utc):
                yield chunk
            return
        async with httpx.AsyncClient(timeout=30) as client:
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
