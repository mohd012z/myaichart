"""Tests for the live-feed seam (PR #8): LivePipeline -> LiveHub -> /ws/live.

The documented next step from PR #7 ("publisher hook composes with PR #5
LiveHub.publish") — verified end-to-end here with a fake adapter, the real
CandleEngine, the real LiveHub, and the real FastAPI lifespan: ticks from
the feed must arrive at a connected WebSocket client as candle_update
messages, backfill must use the pipeline's symbol, health must show the
provider, and the server must stay up when the feed ends/crashes.
"""
from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from myaichart.candles.engine import CandleEngine
from myaichart.data.candles import CandleStore
from myaichart.live.pipeline import LivePipeline
from myaichart.market.tick import MarketTick, SourceClass
from myaichart.models import BoundaryProfile, Candle, CandleState
from myaichart.server.app import create_app

UTC = timezone.utc
T0 = datetime(2026, 9, 29, 4, 0, 0, tzinfo=UTC)
SYM = "BTCUSDT"


def _mt(price: float, ts: datetime) -> MarketTick:
    return MarketTick(symbol=SYM, provider="FAKE", provider_symbol="BTC-USDT",
                      source_class=SourceClass.EXCHANGE, ts_exchange=ts,
                      ts_received=datetime.now(UTC),
                      bid=price, ask=price + 0.1, last=price)


def _candle(open_utc, *, price=100.0, timeframe="M1", symbol=SYM):
    return Candle(
        symbol=symbol, timeframe=timeframe,
        boundary_profile=BoundaryProfile.MYT_CALENDAR,
        time_open_utc=open_utc, time_close_utc=open_utc + timedelta(minutes=1),
        state=CandleState.LIVE,
        bid_open=price - 0.1, bid_high=price + 1, bid_low=price - 1, bid_close=price,
        ask_open=price + 0.1, ask_high=price + 1.1, ask_low=price - 0.9, ask_close=price + 0.1,
        mid_open=price, mid_high=price + 0.5, mid_low=price - 0.5, mid_close=price,
        tick_count=10, quote_change_count=9,
    )


class _FeedAdapter:
    """Yields its ticks then exhausts. ``gate`` (threading.Event) — when set,
    the stream waits for it before the FIRST tick: this makes the test
    deterministic (the client must be registered before any candle_update is
    published, or the publish goes to zero clients and the message is lost —
    which is also why the hub keeps _last_update as a connect fallback).
    ``exhausted`` is set once the stream generator is fully consumed, so a
    test can deterministically wait for feed completion without sleep-polling.
    """
    provider = "FAKE"
    source_class = SourceClass.EXCHANGE

    def __init__(self, ticks, gate=None, pace_s=0.02):
        self._ticks = list(ticks)
        self.gate = gate
        self.pace_s = pace_s
        self.closed = False
        self.streamed = 0
        self.exhausted = threading.Event()

    async def stream(self, symbols):
        try:
            if self.gate is not None:
                await asyncio.to_thread(self.gate.wait)
            for mt in self._ticks:
                yield mt
                self.streamed += 1
                await asyncio.sleep(self.pace_s)
        finally:
            self.exhausted.set()

    async def fetch_candles(self, start, end):
        return []

    def close(self):
        self.closed = True


def _make_pipeline(n_ticks=12, prices=None, gate=None):
    prices = prices or [100.0 + i * 0.5 for i in range(n_ticks)]
    ticks = [_mt(p, T0 + timedelta(seconds=i * 10)) for i, p in enumerate(prices)]
    adapter = _FeedAdapter(ticks, gate=gate)
    engine = CandleEngine(["M1", "M5"], BoundaryProfile.MYT_CALENDAR)
    return LivePipeline(adapter, engine, symbol=SYM), adapter, prices


def _wait_ws_updates(ws, count=1, timeout_msgs=40):
    """Collect real-feed candle_update messages (skipping the contract stub —
    the fixed 10.1 test candle from testing_message, see test_server_spine —
    and any backfill) until `count`."""
    got = []
    for _ in range(timeout_msgs):
        msg = ws.receive_json()
        if msg.get("type") != "candle_update":
            continue
        if msg.get("mid", {}).get("c") == 10.1:  # the no-data contract stub
            continue
        got.append(msg)
        if len(got) == count:
            return got
    return got


def test_pipeline_ticks_reach_ws_live():
    # 12 ticks @ 10s spacing over 110s -> candles in the 04:00 and 04:01 M1
    # buckets (+ matching M5 bucket). Gate the feed until the WS client is
    # registered so no candle_update is published to zero clients.
    gate = threading.Event()
    pipe, adapter, prices = _make_pipeline(gate=gate)
    app = create_app(live_pipeline=pipe)
    with TestClient(app) as c:
        with c.websocket_connect("/ws/live") as ws:
            # the no-data contract stub arrives at register time
            assert ws.receive_json()["type"] == "candle_update"
            gate.set()  # release the feed: client is registered
            updates = _wait_ws_updates(ws, count=2)
            assert updates, "no candle_update arrived from the live feed"
            # every update carries the pipeline's symbol
            assert all(u["symbol"] == SYM for u in updates)
            # first tick (04:00:00Z, bid 100.0/ask 100.1) -> mid 100.05, both
            # active timeframes (M1 + M5) publish for that candle.
            assert all(u["mid"]["c"] == 100.05 for u in updates)
            assert all(u["bucket_start_utc"] == "2026-09-29T04:00:00Z" for u in updates)
            assert {u["timeframe"] for u in updates} == {"M1", "M5"}
            # Wait for the feed to FULLY DRAIN before asserting. The
            # consumer reaches status "ENDED" only after it breaks on the
            # stream's _END marker — i.e. after all ticks are processed and
            # published. (The generator finishing is not enough: it feeds a
            # queue the consumer may still be draining.) Closing the
            # TestClient context below shuts the server down and stops the
            # feed by design, so this must be observed while the socket is open.
            import time as _time
            _t0 = _time.time()
            while pipe.status not in ("ENDED", "STOPPED") and _time.time() - _t0 < 15:
                _time.sleep(0.02)
        # feed ran to exhaustion through the lifespan
        assert pipe.stats.ticks_in >= len(prices) - 1
        assert pipe.stats.candles_published >= 2
        assert pipe.status in ("ENDED", "STOPPED")
        assert adapter.closed is True
        # stats + health surfaces reflect the pipeline
        st = c.get("/api/live/status").json()
        assert st["configured"] is True and st["symbol"] == SYM
        assert st["ticks_in"] >= len(prices) - 1
        hp = c.get("/api/health/providers").json()
        assert hp["authority"] == "FAKE"
        assert hp["providers"]["FAKE"]["state"] == "LIVE"
        assert hp["hub_state"] == "HEALTHY"


def test_backfill_uses_pipeline_symbol(tmp_path):
    """Store rows for the PIPELINE's symbol (not XAUUSD) must backfill."""
    store = CandleStore(tmp_path)
    store.write(SYM, "M1", [_candle(T0, price=99.0)])
    pipe, adapter, _ = _make_pipeline(n_ticks=4)
    app = create_app(live_pipeline=pipe, data_dir=tmp_path)
    with TestClient(app) as c:
        with c.websocket_connect("/ws/live") as ws:
            first = ws.receive_json()
            assert first["type"] == "backfill"
            assert first["data"]["M1"][0]["close"] == 99.0


def test_no_pipeline_keeps_existing_contract():
    """Without a pipeline: /api/live/status unconfigured, health NO_AUTHORITY,
    WS still gets the testing-message stub (existing dashboard contract)."""
    app = create_app()
    with TestClient(app) as c:
        assert c.get("/api/live/status").json() == {"configured": False}
        hp = c.get("/api/health/providers").json()
        assert hp["hub_state"] == "NO_AUTHORITY"
        with c.websocket_connect("/ws/live") as ws:
            assert ws.receive_json()["type"] == "candle_update"  # the 10.1 stub


class _CrashAdapter(_FeedAdapter):
    async def stream(self, symbols):
        yield _mt(100.0, T0)
        await asyncio.sleep(self.pace_s)
        raise RuntimeError("feed exploded")


def test_feed_crash_does_not_take_server_down():
    ticks = [_mt(100.0 + i * 0.5, T0 + timedelta(seconds=i * 10)) for i in range(3)]
    adapter = _CrashAdapter(ticks)
    pipe = LivePipeline(adapter, CandleEngine(["M1"], BoundaryProfile.MYT_CALENDAR), symbol=SYM)
    app = create_app(live_pipeline=pipe)
    with TestClient(app) as c:
        # lifespan must complete cleanly even though the feed raised
        assert c.get("/api/health").json() == {"ok": True}
        st = c.get("/api/live/status").json()
        assert st["configured"] is True
        # at least the pre-crash tick was seen
        assert st["ticks_in"] >= 1
