from datetime import datetime, timezone
import pytest
from myaichart.models import NormalizedTick
from myaichart.live.supervisor import merge_backfill, FeedSupervisor


def tick(rid, sec):
    ts=datetime(2026,9,25,7,40,sec,tzinfo=timezone.utc)
    return NormalizedTick(symbol='XAUUSD',source='s',source_record_id=rid,source_timestamp_utc=ts,received_timestamp_utc=ts,bid=10+sec/100,ask=10.2+sec/100)


def test_overlap_backfill_deduplicates_by_source_identity():
    existing=[tick('a',1),tick('b',2)]
    overlapping=[tick('b',2),tick('c',3)]
    merged=merge_backfill(existing,overlapping)
    ids=[(t.source,t.source_record_id) for t in merged]
    assert len(ids)==len(set(ids))
    assert [t.source_record_id for t in merged]==['a','b','c']


@pytest.mark.asyncio
async def test_missing_interval_without_backfill_is_preserved_as_data_gap():
    class FakeAdapter:
        async def backfill(self,start_utc,end_utc): return []
    sup=FeedSupervisor(adapter=FakeAdapter(),store=None,candle_engine=None)
    start=datetime(2026,9,25,7,40,tzinfo=timezone.utc)
    end=datetime(2026,9,25,7,45,tzinfo=timezone.utc)
    await sup.handle_disconnect(start_utc=start,end_utc=end)
    assert sup.outages[-1].final_state=='DATA_GAP'
