from datetime import datetime
from zoneinfo import ZoneInfo
from myaichart.events.models import EconomicEvent, EventRevision


def test_new_york_release_is_normalized_to_utc_and_myt():
    source=datetime(2026,7,10,8,30,tzinfo=ZoneInfo('America/New_York'))
    e=EconomicEvent.from_source_time(event_id='cpi-2026-07',family='CPI',name='CPI',source='BLS',source_time=source)
    assert e.scheduled_time_myt.tzinfo.key=='Asia/Kuala_Lumpur'
    assert e.scheduled_time_utc.utcoffset().total_seconds()==0
    assert e.scheduled_time_myt.hour==20


def test_revision_preserves_original_previous_value():
    source=datetime(2026,7,10,8,30,tzinfo=ZoneInfo('America/New_York'))
    e=EconomicEvent.from_source_time(event_id='x',family='CPI',name='CPI',source='BLS',source_time=source,previous=2.1)
    e2=e.with_revision(revised_previous=2.0, observed_at_utc=e.scheduled_time_utc)
    assert e2.revisions[0].old_previous==2.1
    assert e2.revised_previous==2.0
