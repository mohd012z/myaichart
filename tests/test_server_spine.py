"""Tests for the unified-chart data spine (PR #5).

Covers: /api/candles from a real store, /api/health/providers shape,
/api/sessions first-candle zones, and LiveHub backfill + broadcast +
unregister (contract-preserving: no-data path still yields the testing
message so existing dashboard/tests keep working).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, time as _time, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from myaichart.data.candles import CandleStore
from myaichart.models import Candle, CandleState
from myaichart.server.app import create_app
from myaichart.server.live_hub import LiveHub, candle_update_message, candle_to_chart
from myaichart.server.sessions import _latest_open_utc, session_zones
from myaichart.server.websocket import testing_message as _testing_message
from zoneinfo import ZoneInfo


from myaichart.models import BoundaryProfile
from datetime import timedelta


def _candle(open_utc, *, state=CandleState.LIVE, open_=3820.0, high=3824.0, low=3818.0, close=3823.0,
            timeframe="M1"):
    return Candle(
        symbol="XAUUSD", timeframe=timeframe,
        boundary_profile=BoundaryProfile.MYT_CALENDAR,
        time_open_utc=open_utc, time_close_utc=open_utc + timedelta(minutes=1),
        state=state,
        bid_open=open_ - 0.1, bid_high=high - 0.1, bid_low=low - 0.1, bid_close=close - 0.1,
        ask_open=open_ + 0.1, ask_high=high + 0.1, ask_low=low + 0.1, ask_close=close + 0.1,
        mid_open=open_, mid_high=high, mid_low=low, mid_close=close,
        tick_count=10, quote_change_count=9,
    )


UTC = timezone.utc


def test_api_candles_reads_store(tmp_path):
    store = CandleStore(tmp_path)
    base = datetime(2026, 9, 29, 1, 0, tzinfo=UTC)
    candles = [_candle(base) for _ in range(3)]
    store.write("XAUUSD", "M1", candles)
    app = create_app(data_dir=tmp_path)
    with TestClient(app) as c:
        r = c.get("/api/candles", params={"symbol": "XAUUSD", "timeframe": "M1", "side": "mid"})
        assert r.status_code == 200
        body = r.json()
        assert body["timeframe"] == "M1"
        assert len(body["candles"]) == 3
        first = body["candles"][0]
        assert first["close"] == candles[0].mid_close
        assert first["source"] == CandleState.LIVE.value


def test_api_candles_empty_when_no_store():
    app = create_app()  # no data_dir -> stub
    with TestClient(app) as c:
        r = c.get("/api/candles", params={"timeframe": "M5"})
        assert r.json()["candles"] == []


def test_api_health_providers_no_engine_shape():
    app = create_app()
    with TestClient(app) as c:
        r = c.get("/api/health/providers")
        assert r.status_code == 200
        body = r.json()
        assert body["hub_state"] == "NO_AUTHORITY"
        assert body["authority"] is None
        assert "providers" in body and "switch_log" in body


def test_api_sessions_first_candle_zone(tmp_path):
    store = CandleStore(tmp_path)
    # Tokyo opens 09:00 JST = 00:00 UTC. Place M1 candles around 00:05 UTC.
    t0 = datetime(2026, 9, 29, 0, 5, tzinfo=UTC)
    candles = [
        _candle(t0, open_=3820, high=3825, low=3819, close=3824),
        _candle(datetime(2026, 9, 29, 0, 6, tzinfo=UTC), open_=3824, high=3826, low=3823, close=3825),
    ]
    store.write("XAUUSD", "M1", candles)
    app = create_app(data_dir=tmp_path)
    with TestClient(app) as c:
        r = c.get("/api/sessions")
        assert r.status_code == 200
        zones = {z["name"]: z for z in r.json()["zones"]}
        assert "TOKYO" in zones
        tz = zones["TOKYO"]
        assert tz["high"] == 3825  # first candle at/after Tokyo open
        assert tz["low"] == 3819
        assert tz["source"] == "FIRST_CANDLE"


def test_latest_open_utc_picks_most_recent_past_open():
    now = datetime(2026, 9, 29, 8, 0, tzinfo=UTC)  # 17:00 JST
    open_utc = _latest_open_utc(now, _time(9, 0), ZoneInfo("Asia/Tokyo"))
    # Tokyo 09:00 JST = 00:00 UTC today
    assert open_utc == datetime(2026, 9, 29, 0, 0, tzinfo=UTC)


def test_latest_open_utc_when_local_date_ahead_of_utc_date():
    # Regression: at 16:00Z the UTC date is 09-29 but Tokyo local is already
    # 09-30 01:00. The most recent Tokyo open is TODAY's (09-29 00:00Z), not
    # tonight's (09-30 00:00Z) — the old offset walk (0,-1,-2) produced all
    # future candidates and fell back to tonight's open.
    now = datetime(2026, 9, 29, 16, 0, tzinfo=UTC)  # 09-30 01:00 JST
    open_utc = _latest_open_utc(now, _time(9, 0), ZoneInfo("Asia/Tokyo"))
    assert open_utc == datetime(2026, 9, 29, 0, 0, tzinfo=UTC)
    # US at 16:00Z is 12:00 EDT on 09-29 (after its 09:30 open) -> the most
    # recent US open is TODAY's 13:30Z. (Contrast: before 13:30Z it would be
    # 09-28's — see test_latest_open_utc_picks_most_recent_past_open.)
    us_open = _latest_open_utc(now, _time(9, 30), ZoneInfo("America/New_York"))
    assert us_open == datetime(2026, 9, 29, 13, 30, tzinfo=UTC)
    # and a time BEFORE the US open: 12:00Z = 08:00 EDT, before 09:30 -> last
    # open is 09-28.
    us_before = _latest_open_utc(datetime(2026, 9, 29, 12, 0, tzinfo=UTC),
                                 _time(9, 30), ZoneInfo("America/New_York"))
    assert us_before == datetime(2026, 9, 28, 13, 30, tzinfo=UTC)


def test_session_zones_empty_without_candles():
    assert session_zones([], datetime(2026, 9, 29, 8, 0, tzinfo=UTC)) == []


# ---- LiveHub behaviour -------------------------------------------------

class _FakeWS:
    def __init__(self):
        self.sent = []

    async def send_json(self, msg):
        self.sent.append(msg)


async def test_live_hub_broadcast_and_unregister():
    hub = LiveHub()
    ws = _FakeWS()
    await hub.register(ws)
    c = _candle(datetime(2026, 9, 29, 1, 0, tzinfo=UTC))
    n = await hub.publish(c)
    assert n == 1
    # client got the no-data stub (contract candle_update) then the live update;
    # distinguish by mid close: the stub is the fixed 10.1 test candle.
    assert ws.sent[0]["type"] == "candle_update"
    assert ws.sent[0]["mid"]["c"] == 10.1
    assert ws.sent[1]["type"] == "candle_update"
    assert ws.sent[1]["mid"]["c"] == c.mid_close
    await hub.unregister(ws)
    assert hub.client_count == 0


async def test_live_hub_no_data_contract_preserved():
    """With no store and no backfill, a client still gets the testing message
    (the exact shape existing tests/dashboard rely on)."""
    hub = LiveHub()
    ws = _FakeWS()
    await hub.register(ws)
    await hub.unregister(ws)
    assert ws.sent[0] == _testing_message()


def test_candle_to_chart_shape():
    c = _candle(datetime(2026, 9, 29, 1, 0, tzinfo=UTC))
    row = candle_to_chart(c, "mid")
    assert set(row) >= {"time", "open", "high", "low", "close", "volume", "source"}
    assert row["time"] == int(c.time_open_utc.timestamp())


def test_candle_update_message_shape():
    c = _candle(datetime(2026, 9, 29, 1, 0, tzinfo=UTC))
    m = candle_update_message(c, "XAUUSD")
    assert m["type"] == "candle_update"
    assert m["symbol"] == "XAUUSD"
    assert m["state"] == CandleState.LIVE.value
    for k in ("bid", "ask", "mid", "spread"):
        assert k in m
