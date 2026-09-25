from datetime import datetime, timedelta, timezone
import asyncio
import lzma
import struct

import httpx
import pytest

from myaichart.models import NormalizedTick
from myaichart.data.dukascopy import collect_range, CollectionStats


def tick(rid, second):
    ts=datetime(2026,9,25,8,0,second,tzinfo=timezone.utc)
    return NormalizedTick(symbol='XAUUSD',source='fixture',source_record_id=rid,
        source_timestamp_utc=ts,received_timestamp_utc=ts,bid=3762.5,ask=3762.6)


def bi5_payload(*, offsets_ms):
    rows=[]
    for i, ms in enumerate(offsets_ms):
        ask_i=3_762_600 + i
        bid_i=3_762_500 + i
        rows.append(struct.pack('>IIIff', ms, ask_i, bid_i, 10.0 + i, 12.0 + i))
    return lzma.compress(b''.join(rows), format=lzma.FORMAT_ALONE)


@pytest.mark.asyncio
async def test_collect_range_streams_chunks_to_store_without_accumulating_all_ticks():
    class Provider:
        async def iter_hour_chunks(self, symbol, start_utc, end_utc):
            yield [tick('a',1), tick('b',2)]
            yield [tick('c',3)]
    class Store:
        def __init__(self): self.chunks=[]
        def append_chunk(self, ticks): self.chunks.append(list(ticks))
    store=Store()
    start=datetime(2026,9,25,8,0,0,tzinfo=timezone.utc)
    end=datetime(2026,9,25,9,0,0,tzinfo=timezone.utc)
    stats=await collect_range(Provider(),store,'XAUUSD',start,end)
    assert isinstance(stats, CollectionStats)
    assert stats.tick_count == 3
    assert stats.chunk_count == 2
    assert len(store.chunks) == 2


@pytest.mark.asyncio
async def test_provider_fetches_hour_chunks_with_bounded_concurrency_and_order():
    from myaichart.data.dukascopy import DukascopyHistoricalProvider

    class Provider(DukascopyHistoricalProvider):
        def __init__(self):
            super().__init__(concurrency=4)
            self.active=0
            self.max_active=0
        async def _fetch_hour(self, symbol, hour_utc, client=None):
            self.active += 1
            self.max_active=max(self.max_active,self.active)
            await asyncio.sleep(0.01)
            sec=int((hour_utc.hour % 24))
            ts=hour_utc
            result=[NormalizedTick(symbol='XAUUSD',source='fixture',source_record_id=f'h{hour_utc.hour}',
                source_timestamp_utc=ts,received_timestamp_utc=ts,bid=3700+sec,ask=3700.1+sec)]
            self.active -= 1
            return result

    provider=Provider()
    start=datetime(2026,9,25,0,0,tzinfo=timezone.utc)
    end=start+timedelta(hours=7)
    chunks=[]
    async for chunk in provider.iter_hour_chunks('XAUUSD',start,end):
        chunks.append(chunk)
    assert provider.max_active > 1
    assert provider.max_active <= 4
    times=[c[0].source_timestamp_utc for c in chunks]
    assert times == sorted(times)


@pytest.mark.asyncio
async def test_429_retry_honors_retry_after(monkeypatch):
    from myaichart.data.dukascopy import DukascopyHistoricalProvider

    requests=[]
    payload=bi5_payload(offsets_ms=[1_000])

    async def fake_sleep(delay):
        sleeps.append(delay)

    def handler(request):
        requests.append(str(request.url))
        if len(requests) == 1:
            return httpx.Response(429, headers={'Retry-After': '2'}, request=request)
        return httpx.Response(200, content=payload, request=request)

    sleeps=[]
    monkeypatch.setattr('myaichart.data.dukascopy.asyncio.sleep', fake_sleep)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider=DukascopyHistoricalProvider(client=client, attempts=3, concurrency=1)
        hour=datetime(2026,9,23,12,0,tzinfo=timezone.utc)
        ticks=await provider._fetch_hour('XAUUSD', hour)

    assert len(ticks) == 1
    assert len(requests) == 2
    assert sleeps == [2.0]


@pytest.mark.asyncio
async def test_current_daily_bucket_is_used_and_split_back_to_hour_chunks():
    from myaichart.data.dukascopy import DukascopyHistoricalProvider

    requested_paths=[]
    # Two ticks inside 12:00 UTC, expressed as milliseconds since day start.
    payload=bi5_payload(offsets_ms=[12*60*60*1000 + 1_000, 12*60*60*1000 + 30_000])

    def handler(request):
        requested_paths.append(request.url.path)
        if request.url.path.endswith('/23_ticks.bi5'):
            return httpx.Response(200, content=payload, request=request)
        return httpx.Response(404, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        provider=DukascopyHistoricalProvider(client=client, attempts=1, concurrency=1)
        start=datetime(2026,9,23,12,0,0,tzinfo=timezone.utc)
        end=datetime(2026,9,23,12,59,59,tzinfo=timezone.utc)
        chunks=[]
        async for chunk in provider.iter_hour_chunks('XAUUSD', start, end):
            chunks.append(chunk)

    assert any(path.endswith('/2026/08/23_ticks.bi5') for path in requested_paths)
    assert len(chunks) == 1
    assert len(chunks[0]) == 2
    assert all(start <= t.source_timestamp_utc <= end for t in chunks[0])
