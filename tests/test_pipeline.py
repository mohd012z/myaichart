"""Tests for the live pipeline (adapter → normalize → dedupe → engine → publish
+ outage backfill recovery). Hermetic: fake adapter/engine/publisher, no
network. One network-gated live end-to-end (OKX) test, skipped when egress
can't reach the feed.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from myaichart.candles.engine import CandleEngine, CandleUpdate
from myaichart.live.pipeline import LivePipeline
from myaichart.market.health import HealthEngine
from myaichart.market.normalize import normalize_tick
from myaichart.market.tick import InstrumentRole, MarketTick, SourceClass

UTC = timezone.utc
T0 = datetime(2026, 9, 29, 4, 0, 0, tzinfo=UTC)


def _okx_reachable(timeout: float = 6.0) -> bool:
    """Cheap preflight for the live end-to-end test (datacenter egress is
    the gate — see the 2026-09-28 feed benchmark)."""
    try:
        import websockets

        async def _probe():
            async with websockets.connect("wss://ws.okx.com:8443/ws/v5/public",
                                          open_timeout=timeout):
                return True
        return asyncio.run(_probe())
    except Exception:
        return False


def _mt(price: float, ts: datetime, *, provider: str = "FAKE", sym: str = "BTC-USDT",
        canonical: str = "BTCUSDT", bid=None, ask=None) -> MarketTick:
    b, a = (bid, ask) if bid is not None else (price, price)
    return MarketTick(symbol=canonical, provider=provider, provider_symbol=sym,
                      source_class=SourceClass.EXCHANGE, ts_exchange=ts,
                      ts_received=datetime.now(timezone.utc),
                      bid=b, ask=a, last=price)


def _candle_update(candle, tf: str = "M1", kind: str = "FORMING") -> CandleUpdate:
    return CandleUpdate(timeframe=tf, candle=candle, kind=kind)


class FakeCandle:
    """Just enough of a Candle for the pipeline's bookkeeping."""
    def __init__(self, ts):
        self.time_open_utc = ts
        self.timeframe = "M1"
        self.state = type("S", (), {"value": "LIVE"})()
        self.mid_open = self.mid_high = self.mid_low = self.mid_close = 100.0
        self.tick_count = 1


class FakeEngine:
    """on_tick that forms one candle per distinct minute, like the real one."""
    def __init__(self):
        self.seen_minutes = set()
    def on_tick(self, nt):
        minute = nt.source_timestamp_utc.replace(second=0, microsecond=0)
        updates = []
        if minute not in self.seen_minutes:
            self.seen_minutes.add(minute)
            updates.append(_candle_update(FakeCandle(minute)))
        return updates


class FakeAdapter:
    provider = "FAKE"
    source_class = SourceClass.EXCHANGE

    def __init__(self, ticks: list, backfill_ticks: list | None = None):
        self._ticks = ticks
        self._backfill = backfill_ticks or []
        self.closed = False
        self.stream_calls = 0
    def symbol_map(self, canonical):
        return "BTC-USDT" if canonical == "BTCUSDT" else None
    async def stream(self, canonical_symbols):
        self.stream_calls += 1
        for t in self._ticks:
            yield t
    async def backfill(self, canonical, start, end):
        return [t for t in self._backfill if start <= t.ts_exchange <= end]
    def close(self):
        self.closed = True


# --------------------------------------------------------------------- #
async def test_pipeline_ticks_to_candles_to_publisher():
    ticks = [_mt(100.0 + i * 0.1, T0 + timedelta(seconds=i * 5)) for i in range(12)]  # 60s
    adapter = FakeAdapter(ticks)
    engine = FakeEngine()
    health = HealthEngine("BTCUSDT")
    health.register("FAKE", role=InstrumentRole.AUTHORITY)
    published = []
    pipe = LivePipeline(adapter, engine, symbol="BTCUSDT", health=health,
                        publisher=lambda u: published.append(u))
    await pipe.run()
    assert pipe.status == "ENDED"
    assert adapter.closed
    assert pipe.stats.ticks_in == 12
    assert pipe.stats.normalized == 12
    assert pipe.stats.candles_published >= 1
    assert len(published) == pipe.stats.candles_published
    rep = health.report()
    assert rep["authority"] == "FAKE"
    assert rep["providers"]["FAKE"]["state"] == "LIVE"


async def test_pipeline_dedupes_duplicate_source_ids():
    # same exchange ts + same provider twice (ticker re-report) -> one engine feed
    t1 = _mt(100.0, T0)
    t2 = _mt(100.0, T0)  # identical ts -> same source_record_id
    adapter = FakeAdapter([t1, t2])
    engine = FakeEngine()
    pipe = LivePipeline(adapter, engine, symbol="BTCUSDT", health=HealthEngine("BTCUSDT"))
    await pipe.run()
    assert pipe.stats.ticks_in == 2
    assert pipe.stats.duplicates == 1
    # engine saw exactly one distinct minute
    assert len(engine.seen_minutes) == 1


async def test_pipeline_no_price_dropped_counted():
    adapter = FakeAdapter([_mt(0.0, T0, bid=None, ask=None)])  # last-only via bid/ask=None? see below
    # construct a truly price-less tick
    bad = MarketTick(symbol="BTCUSDT", provider="FAKE", provider_symbol="BTC-USDT",
                     source_class=SourceClass.EXCHANGE, ts_exchange=T0,
                     ts_received=datetime.now(timezone.utc), bid=None, ask=None, last=None)
    adapter = FakeAdapter([bad])
    engine = FakeEngine()
    pipe = LivePipeline(adapter, engine, symbol="BTCUSDT", health=HealthEngine("BTCUSDT"))
    await pipe.run()
    assert pipe.stats.dropped_no_price == 1
    assert pipe.stats.normalized == 0
    assert pipe.stats.candles_published == 0


async def test_pipeline_auto_registers_unregistered_provider():
    ticks = [_mt(100.0, T0)]
    pipe = LivePipeline(FakeAdapter(ticks), FakeEngine(), symbol="BTCUSDT",
                        health=HealthEngine("BTCUSDT"))  # FAKE not pre-registered
    await pipe.run()
    rep = pipe.health.report()
    assert "FAKE" in rep["providers"]
    assert rep["providers"]["FAKE"]["role"] == "AUTHORITY"


# --------------------------------------------------------------------- #
# outage recovery
# --------------------------------------------------------------------- #
async def test_recover_outage_recovers_gap():
    live = [_mt(100.0, T0)]
    gap = [_mt(101.0, T0 + timedelta(minutes=1)), _mt(102.0, T0 + timedelta(minutes=2))]
    adapter = FakeAdapter(live, backfill_ticks=gap)
    engine = FakeEngine()
    pipe = LivePipeline(adapter, engine, symbol="BTCUSDT", health=HealthEngine("BTCUSDT"))
    recovered = await pipe.recover_outage(T0 + timedelta(minutes=1), T0 + timedelta(minutes=3))
    assert len(recovered) == 2
    rec = pipe.stats.outages[-1]
    assert rec["final_state"] == "RECOVERED" and rec["recovered_count"] == 2
    assert pipe.status == "LIVE"


async def test_recover_outage_data_gap_when_no_backfill():
    adapter = FakeAdapter([_mt(100.0, T0)], backfill_ticks=[])
    pipe = LivePipeline(adapter, FakeEngine(), symbol="BTCUSDT", health=HealthEngine("BTCUSDT"))
    recovered = await pipe.recover_outage(T0 + timedelta(minutes=1), T0 + timedelta(minutes=2))
    assert recovered == []
    rec = pipe.stats.outages[-1]
    assert rec["final_state"] == "DATA_GAP" and rec["recovered_count"] == 0
    assert pipe.status == "STALE"


# --------------------------------------------------------------------- #
async def test_watchdog_recovers_on_stall_then_resumes():
    # pump stays alive through the stall (queue-based watchdog never cancels
    # the recv): tick@now → stall → backfill recovery of the gap → next tick
    import time as _time
    t_wall = datetime.now(timezone.utc)
    t_first, t_second = t_wall, t_wall + timedelta(seconds=1.5)

    class StallAdapter(FakeAdapter):
        async def stream(self, canonical_symbols):
            self.stream_calls += 1
            yield _mt(100.0, t_first)
            await asyncio.sleep(1.0)  # silent stall — watchdog fires at 0.2s
            yield _mt(101.0, t_second)
    adapter = StallAdapter([_mt(100.0, t_first)],
                           # inside the first watchdog window (~[t_wall, t_wall+0.2s])
                           backfill_ticks=[_mt(100.5, t_wall + timedelta(milliseconds=50)),
                                           _mt(100.6, t_wall + timedelta(milliseconds=100))])
    engine = FakeEngine()
    pipe = LivePipeline(adapter, engine, symbol="BTCUSDT", health=HealthEngine("BTCUSDT"),
                        disconnect_watchdog_s=0.05)
    task = asyncio.create_task(pipe.run_with_watchdog(tick_timeout_s=0.2))
    for _ in range(100):  # until the second live tick arrives
        await asyncio.sleep(0.05)
        if pipe.stats.ticks_in >= 2:
            break
    await asyncio.wait_for(task, timeout=5)
    recovered = [r for r in pipe.stats.outages if r["final_state"] == "RECOVERED"]
    assert recovered, f"expected a RECOVERED outage, got {pipe.stats.outages}"
    assert recovered[0]["recovered_count"] == 2
    assert pipe.stats.ticks_in == 2      # live ticks on both sides of the stall
    assert adapter.stream_calls == 1     # stream survived the stall (no restart)
    assert pipe.status == "ENDED"


# --------------------------------------------------------------------- #
# live end-to-end (network-gated)
# --------------------------------------------------------------------- #
@pytest.mark.skipif(
    not _okx_reachable(),
    reason="OKX public WS not reachable from this egress (09-28 feed bench)",
)
async def test_live_okx_end_to_end_pipeline():
    from myaichart.live.okx_public import OkxPublicAdapter
    from myaichart.models import BoundaryProfile
    engine = CandleEngine(["M1", "M5"], BoundaryProfile.MYT_CALENDAR)
    health = HealthEngine("BTCUSDT")
    health.register("OKX", role=InstrumentRole.AUTHORITY)
    published = []
    pipe = LivePipeline(OkxPublicAdapter(), engine, symbol="BTCUSDT", health=health,
                        publisher=lambda u: published.append(u))
    task = asyncio.create_task(pipe.run())
    # wait for at least one published candle (bounded)
    for _ in range(50):
        await asyncio.sleep(0.2)
        if pipe.stats.candles_published >= 1 and pipe.stats.ticks_in >= 3:
            break
    pipe.stop()
    try:
        await asyncio.wait_for(task, timeout=5)
    except asyncio.TimeoutError:
        task.cancel()
    assert pipe.stats.ticks_in >= 3, f"expected >=3 live ticks, got {pipe.stats.ticks_in}"
    assert pipe.stats.candles_published >= 1
    rep = health.report()
    assert rep["providers"]["OKX"]["state"] == "LIVE"
    assert len(published) >= 1
