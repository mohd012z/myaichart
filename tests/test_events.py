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


def test_bls_ics_parser_normalizes_official_release_time_to_utc_and_myt():
    from myaichart.events.bls import parse_ics
    ics='''BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:empsit-20261002\nDTSTART;TZID=America/New_York:20261002T083000\nSUMMARY:Employment Situation\nURL:https://www.bls.gov/news.release/empsit.toc.htm\nEND:VEVENT\nEND:VCALENDAR\n'''
    events=parse_ics(ics)
    assert len(events)==1
    e=events[0]
    assert e.source=='BLS'
    assert e.family=='EMPLOYMENT_SITUATION'
    assert e.scheduled_time_utc.isoformat()=='2026-10-02T12:30:00+00:00'
    assert e.scheduled_time_myt.isoformat()=='2026-10-02T20:30:00+08:00'
    assert e.forecast is None


def test_event_store_roundtrip_preserves_null_forecast(tmp_path):
    from myaichart.events.storage import EventStore
    source=datetime(2026,10,2,8,30,tzinfo=ZoneInfo('America/New_York'))
    e=EconomicEvent.from_source_time(event_id='x',family='CPI',name='CPI',source='BLS',source_time=source)
    store=EventStore(tmp_path)
    path=store.write([e])
    assert path.exists()
    got=list(store.read())
    assert got[0].event_id=='x'
    assert got[0].forecast is None


def test_bls_ics_fallback_id_is_stable_sha_not_process_hash():
    import hashlib
    from myaichart.events.bls import parse_ics
    ics='''BEGIN:VCALENDAR\nBEGIN:VEVENT\nDTSTART;TZID=America/New_York:20261013T083000\nSUMMARY:Consumer Price Index\nEND:VEVENT\nEND:VCALENDAR\n'''
    event=parse_ics(ics)[0]
    expected=hashlib.sha256(f"{event.scheduled_time_source.isoformat()}|Consumer Price Index".encode()).hexdigest()[:20]
    assert event.event_id == f'bls-{expected}'
