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


def test_build_effect_dataset_returns_persistable_rows_without_future_leakage():
    from myaichart.events.effects import build_effect_dataset
    e=event(); cs=candles()
    rows=build_effect_dataset([e],cs,as_of=e.scheduled_time_utc)
    assert len(rows)==1
    assert rows[0].event_id=='e1'
    assert rows[0].t_plus_5_return is None


def test_cli_effects_build_writes_file_from_stored_event_and_m1_candle(tmp_path):
    from myaichart.cli import main
    from myaichart.events.storage import EventStore
    from myaichart.data.candles import CandleStore
    from myaichart.models import Candle, CandleState, BoundaryProfile
    e=event()
    EventStore(tmp_path).write([e])
    t=e.scheduled_time_utc
    c=Candle(symbol='XAUUSD',timeframe='M1',boundary_profile=BoundaryProfile.MYT_CALENDAR,
        time_open_utc=t,time_close_utc=t+timedelta(minutes=1),state=CandleState.FINAL,
        bid_open=100,bid_high=100,bid_low=100,bid_close=100,
        ask_open=100.2,ask_high=100.2,ask_low=100.2,ask_close=100.2,
        mid_open=100.1,mid_high=100.1,mid_low=100.1,mid_close=100.1,
        tick_count=1,quote_change_count=0)
    CandleStore(tmp_path).write('XAUUSD','M1',[c])
    assert main(['--data-dir',str(tmp_path),'effects','build','XAUUSD']) == 0
    assert (tmp_path/'effects'/'news_effects.jsonl').exists()


def test_event_baseline_uses_last_closed_candle_not_event_minute_future_close():
    from myaichart.events.effects import build_event_features
    e=event()
    class ClosedCandle:
        def __init__(self,open_time,close_time,close):
            self.time_open_utc=open_time
            self.time_close_utc=close_time
            self.mid_close=close
    t=e.scheduled_time_utc
    cs=[
        ClosedCandle(t-timedelta(minutes=1),t,100.0),
        ClosedCandle(t,t+timedelta(minutes=1),120.0),
    ]
    row=build_event_features(e,cs,as_of=t+timedelta(minutes=1))
    assert row.t_plus_1_return == 0.2
