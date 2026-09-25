from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from myaichart.events.models import EconomicEvent
from myaichart.events.effects import build_event_features, select_controls, surprise_raw

@dataclass
class C:
    time_open_utc: datetime
    mid_open: float
    mid_high: float
    mid_low: float
    mid_close: float


def event():
    t=datetime(2026,9,25,12,30,tzinfo=timezone.utc)
    return EconomicEvent.from_source_time(event_id='e1',family='CPI',name='CPI',source='BLS',source_time=t,actual=2.4,forecast=2.3)


def candles():
    t=datetime(2026,9,25,12,0,tzinfo=timezone.utc)
    return [C(t+timedelta(minutes=i),100+i*.1,100+i*.1+.05,100+i*.1-.05,100+i*.1+.02) for i in range(100)]


def test_pre_event_features_do_not_include_post_event_values():
    e=event(); row=build_event_features(e,candles(),as_of=e.scheduled_time_utc)
    assert row.t_plus_5_return is None
    assert row.t_plus_60_return is None


def test_post_event_window_populates_only_elapsed_horizons():
    e=event(); row=build_event_features(e,candles(),as_of=e.scheduled_time_utc+timedelta(minutes=6))
    assert row.t_plus_5_return is not None
    assert row.t_plus_60_return is None


def test_surprise_requires_forecast():
    assert surprise_raw(2.4,2.3)==0.1
    assert surprise_raw(2.4,None) is None


def test_controls_match_weekday_and_exclude_equivalent_event():
    e=event()
    candidates=[{'weekday':e.scheduled_time_myt.weekday(),'minute_of_day':e.scheduled_time_myt.hour*60+e.scheduled_time_myt.minute,'has_equivalent_event':False,'id':'ok'},
                {'weekday':e.scheduled_time_myt.weekday(),'minute_of_day':0,'has_equivalent_event':True,'id':'bad'}]
    controls=select_controls(e,candidates,max_controls=5)
    assert [c['id'] for c in controls]==['ok']
