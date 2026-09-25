from datetime import datetime, timezone
import pytest
from myaichart.models import NormalizedTick
from myaichart.data.dukascopy import collect_range, CollectionStats


def tick(rid, second):
    ts=datetime(2026,9,25,8,0,second,tzinfo=timezone.utc)
    return NormalizedTick(symbol='XAUUSD',source='fixture',source_record_id=rid,
        source_timestamp_utc=ts,received_timestamp_utc=ts,bid=3762.5,ask=3762.6)


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
    import asyncio
    from datetime import timedelta
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
