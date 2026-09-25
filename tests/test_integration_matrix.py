from datetime import datetime, timedelta, timezone
import asyncio
from fastapi.testclient import TestClient

from myaichart.models import NormalizedTick, BoundaryProfile
from myaichart.candles.engine import CandleEngine
from myaichart.candles.aggregate import aggregate_candles
from myaichart.live.mt5_bridge import MT5BridgeAdapter
from myaichart.live.replay import ReplayAdapter
from myaichart.server.app import create_app
from myaichart.babylon.backtest import BacktestEngine
from myaichart.events.models import EconomicEvent
from myaichart.events.effects import build_event_features


def t(rid, minute, sec, bid, ask):
    ts=datetime(2026,9,25,7,minute,sec,tzinfo=timezone.utc)
    return NormalizedTick(symbol='XAUUSD',source='mt5-fixture',source_record_id=rid,source_timestamp_utc=ts,received_timestamp_utc=ts,bid=bid,ask=ask)


def test_mt5_bridge_drives_real_candle_without_synthetic_ticks():
    async def run():
        adapter=MT5BridgeAdapter()
        await adapter.push(t('1',40,1,10,10.2))
        await adapter.push(t('2',40,2,10.5,10.7))
        await adapter.close()
        engine=CandleEngine(['M5'],BoundaryProfile.MYT_CALENDAR)
        async for tick in adapter.stream(): engine.on_tick(tick)
        c=engine.current('M5')
        assert c.tick_count==2 and c.bid_high==10.5
    asyncio.run(run())


def test_live_and_replay_same_ticks_same_current_candle():
    seq=[t('1',40,1,10,10.2),t('2',40,2,10.5,10.7)]
    live=CandleEngine(['M5'],BoundaryProfile.MYT_CALENDAR)
    for tick in seq: live.on_tick(tick)
    async def replayed():
        e=CandleEngine(['M5'],BoundaryProfile.MYT_CALENDAR)
        async for tick in ReplayAdapter(seq,speed=50).stream(): e.on_tick(tick)
        return e
    rep=asyncio.run(replayed())
    assert rep.current('M5')==live.current('M5')


def test_p2_shadow_does_not_mutate_p1_control():
    raw=[{'id':'s1','pnl':1.0}]
    result=BacktestEngine().run(raw,p2_shadow=True,context_by_id={'s1':{'valid':False}})
    assert result.p1_control_trades==raw
    assert result.p2_shadow_decisions[0]['decision']=='BLOCK'


def test_news_features_are_no_lookahead_at_event_time():
    event=EconomicEvent.from_source_time(event_id='e',family='CPI',name='CPI',source='BLS',source_time=datetime(2026,9,25,12,30,tzinfo=timezone.utc))
    class C:
        def __init__(self,tm,p): self.time_open_utc=tm; self.mid_close=p
    cs=[C(datetime(2026,9,25,12,29,tzinfo=timezone.utc),100),C(datetime(2026,9,25,12,30,tzinfo=timezone.utc),101),C(datetime(2026,9,25,12,35,tzinfo=timezone.utc),110)]
    row=build_event_features(event,cs,as_of=event.scheduled_time_utc)
    assert row.t_plus_5_return is None


def test_static_workbench_is_served():
    client=TestClient(create_app(testing=True))
    response=client.get('/web/index.html')
    assert response.status_code==200
    assert 'myaichart' in response.text
