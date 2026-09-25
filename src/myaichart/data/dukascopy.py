from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import lzma
import struct
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


class DukascopyHistoricalProvider:
    def __init__(self, *, client: httpx.AsyncClient | None = None, attempts: int = 3):
        self._client = client
        self.attempts = attempts

    async def _fetch_hour(self, symbol: str, hour_utc: datetime):
        url = URL.format(symbol=symbol, year=hour_utc.year, month0=hour_utc.month - 1, day=hour_utc.day, hour=hour_utc.hour)
        owns = self._client is None
        client = self._client or httpx.AsyncClient(timeout=30)
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

    async def fetch_ticks(self, symbol: str, start_utc: datetime, end_utc: datetime):
        cur = start_utc.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
        end_hour = end_utc.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
        ticks: list[NormalizedTick] = []
        while cur <= end_hour:
            ticks.extend(await self._fetch_hour(symbol, cur))
            cur += timedelta(hours=1)
        return [tick for tick in ticks if start_utc <= tick.source_timestamp_utc <= end_utc]


async def collect_range(provider, store, symbol: str, start_utc: datetime, end_utc: datetime):
    ticks = await provider.fetch_ticks(symbol, start_utc, end_utc)
    store.append_chunk(ticks)
    return ticks
