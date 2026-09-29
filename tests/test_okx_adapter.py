"""Tests for the OKX public adapter (PR #4 FeedAdapter spine).

Hermetic: fake WS + fake REST, no network. One optional live capture
(skipped when the sandbox has no egress to OKX) proves the real socket
against the real feed.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest

from myaichart.live.okx_public import OkxPublicAdapter
from myaichart.market.normalize import normalize_tick
from myaichart.market.tick import MarketTick, SourceClass

UTC = timezone.utc
T0 = datetime(2026, 9, 29, 3, 0, 0, tzinfo=UTC)


def _okx_reachable(timeout: float = 6.0) -> bool:
    """Cheap preflight for the live-capture test (datacenter egress is the
    gate — see the 2026-09-28 feed benchmark)."""
    try:
        import websockets

        async def _probe():
            async with websockets.connect("wss://ws.okx.com:8443/ws/v5/public",
                                          open_timeout=timeout):
                return True
        return asyncio.run(_probe())
    except Exception:
        return False


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


class FakeWS:
    """Scripted websocket: a list of frames to serve, then EOF/exception."""

    def __init__(self, frames: list[str], *, drop_after: int | None = None):
        self._frames = list(frames)
        self._i = 0
        self.sent: list[str] = []
        self._drop_after = drop_after

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def send(self, msg):
        self.sent.append(msg)

    async def recv(self):
        if self._drop_after is not None and self._i >= self._drop_after:
            raise ConnectionError("simulated drop")
        if self._i >= len(self._frames):
            raise StopAsyncIteration
        f = self._frames[self._i]
        self._i += 1
        return f


def _ticker_frame(native: str, ts_ms: int, last: str = "100.5",
                  bid: str = "100.4", ask: str = "100.6") -> str:
    return json.dumps({"arg": {"channel": "tickers", "instId": native},
                       "data": [{"instId": native, "last": last, "bidPx": bid,
                                 "askPx": ask, "ts": str(ts_ms)}]})


def _ack_frame() -> str:
    return json.dumps({"event": "subscribe", "arg": {"channel": "tickers"}})


def _pong() -> str:
    return "pong"


# --------------------------------------------------------------------- #
# symbol_map
# --------------------------------------------------------------------- #
def test_symbol_map_covers_crypto_not_gold():
    a = OkxPublicAdapter()
    assert a.symbol_map("BTCUSDT") == "BTC-USDT"
    assert a.symbol_map("ETHUSDT") == "ETH-USDT"
    assert a.symbol_map("XAUUSD") is None  # gold is broker-sourced, not OKX


# --------------------------------------------------------------------- #
# stream parsing (hermetic)
# --------------------------------------------------------------------- #
async def test_stream_yields_raw_market_ticks():
    frames = [_ack_frame(),
              _ticker_frame("BTC-USDT", _ms(T0)),
              _pong(),
              _ticker_frame("BTC-USDT", _ms(T0 + timedelta(seconds=1)), last="101.0",
                            bid="100.9", ask="101.1")]
    a = OkxPublicAdapter(ws_factory=lambda: FakeWS(frames))
    got = []
    async for t in a.stream(["BTCUSDT", "XAUUSD"]):
        got.append(t)
        if len(got) >= 2:
            break
    assert len(got) == 2
    assert isinstance(got[0], MarketTick)
    assert got[0].symbol == "BTCUSDT"          # canonical, not provider-native
    assert got[0].provider_symbol == "BTC-USDT"
    assert got[0].provider == "OKX"
    assert got[0].source_class == SourceClass.EXCHANGE
    assert got[0].bid == 100.4 and got[0].ask == 100.6 and got[0].last == 100.5
    assert got[0].ts_exchange == T0
    assert got[1].last == 101.0
    assert got[0].raw["instId"] == "BTC-USDT"


async def test_stream_skips_null_subscribe_snapshot():
    # OKX's first tickers frame is all "-" until the first real quote.
    frames = [_ack_frame(),
              _ticker_frame("BTC-USDT", _ms(T0), last="-", bid="-", ask="-"),
              _ticker_frame("BTC-USDT", _ms(T0 + timedelta(seconds=2)), last="100.0",
                            bid="99.9", ask="100.1")]
    a = OkxPublicAdapter(ws_factory=lambda: FakeWS(frames))
    got = []
    async for t in a.stream(["BTCUSDT"]):
        got.append(t)
        if len(got) >= 1:
            break
    assert len(got) == 1
    assert got[0].last == 100.0  # the snapshot produced NOTHING
    assert got[0].ts_exchange == T0 + timedelta(seconds=2)


async def test_stream_unmapped_symbol_yields_nothing():
    frames = [_ack_frame(), _ticker_frame("BTC-USDT", _ms(T0))]
    a = OkxPublicAdapter(ws_factory=lambda: FakeWS(frames))
    got = [t async for t in a.stream(["XAUUSD"])]
    assert got == []


async def test_stream_reconnects_after_drop():
    # first connection drops after the first tick; second serves a new tick
    class TwoPhase:
        def __init__(self):
            self.calls = 0
        def __call__(self):
            self.calls += 1
            # first connection: serve ack + one tick, then drop (after 2 frames)
            if self.calls == 1:
                return FakeWS([_ack_frame(), _ticker_frame("BTC-USDT", _ms(T0))],
                               drop_after=2)
            return FakeWS([_ack_frame(),
                            _ticker_frame("BTC-USDT", _ms(T0 + timedelta(seconds=5)),
                                          last="102.0", bid="101.9", ask="102.1")])
    factory = TwoPhase()
    a = OkxPublicAdapter(ws_factory=factory, max_reconnects=3)
    got = []
    async for t in a.stream(["BTCUSDT"]):
        got.append(t)
        if len(got) >= 2:
            break
    assert len(got) == 2
    assert got[1].last == 102.0
    assert factory.calls == 2


# --------------------------------------------------------------------- #
# backfill (hermetic REST)
# --------------------------------------------------------------------- #
def _candle_row(ts: datetime, o: float, h: float, c: float, l: float,
                confirm: str = "1") -> list[str]:
    return [str(_ms(ts)), f"{o}", f"{h}", f"{c}", f"{l}", "1.5", "100", "150", confirm]


def test_backfill_returns_candle_summary_ticks_for_window():
    rows = [_candle_row(T0 + timedelta(minutes=i), 100 + i, 101 + i, 100.5 + i, 99 + i)
            for i in range(3)]
    http = lambda url, params: {"code": "0", "data": rows}  # noqa: E731
    a = OkxPublicAdapter(http_get=http)
    ticks = a.backfill("BTCUSDT", T0, T0 + timedelta(minutes=3))
    assert len(ticks) == 3
    assert ticks[0].ts_exchange == T0
    # candle summary: bid==ask==close, OHLC preserved + labeled
    assert ticks[0].bid == ticks[0].ask == 100.5
    assert ticks[0].raw["candle-summary"] is True
    assert ticks[0].raw["ohlc"] == {"o": 100.0, "h": 101.0, "c": 100.5, "l": 99.0}
    assert [t.ts_exchange for t in ticks] == sorted(t.ts_exchange for t in ticks)


def test_backfill_excludes_open_bars_and_out_of_window():
    rows = [_candle_row(T0, 100, 101, 100.5, 99, confirm="0"),            # OPEN bar
            _candle_row(T0 + timedelta(minutes=1), 100, 101, 100.5, 99),  # in window
            _candle_row(T0 + timedelta(minutes=5), 100, 101, 100.5, 99)]  # out of window
    http = lambda url, params: {"data": rows}  # noqa: E731
    a = OkxPublicAdapter(http_get=http)
    ticks = a.backfill("BTCUSDT", T0, T0 + timedelta(minutes=2))
    assert len(ticks) == 1
    assert ticks[0].ts_exchange == T0 + timedelta(minutes=1)


def test_backfill_empty_for_unmapped_or_bad_window():
    a = OkxPublicAdapter(http_get=lambda u, p: {"data": []})
    assert a.backfill("XAUUSD", T0, T0 + timedelta(minutes=1)) == []
    assert a.backfill("BTCUSDT", T0, T0) == []  # end <= start
    # REST failure -> no fabrication
    def boom(u, p):
        raise RuntimeError("network down")
    assert OkxPublicAdapter(http_get=boom).backfill("BTCUSDT", T0, T0 + timedelta(minutes=1)) == []


# --------------------------------------------------------------------- #
# normalize integration: adapter output -> NormalizedTick (quality envelope)
# --------------------------------------------------------------------- #
async def test_adapter_tick_normalizes_with_quality_envelope():
    frames = [_ack_frame(), _ticker_frame("BTC-USDT", _ms(T0))]
    a = OkxPublicAdapter(ws_factory=lambda: FakeWS(frames))
    first = None
    async for t in a.stream(["BTCUSDT"]):
        first = t
        break
    assert first is not None
    n = normalize_tick(first)
    assert n.symbol == "BTCUSDT"
    assert n.source == "OKX"
    assert n.bid == 100.4 and n.ask == 100.6
    assert n.source_class == "EXCHANGE"
    assert n.spread_price_tag == "bid-ask"   # real two-sided quote, not last-only
    assert n.latency_ms is not None and n.latency_ms >= -5000  # sane, not garbage
    assert n.is_out_of_order in (True, False)


def test_candle_summary_normalizes_as_last_only():
    rows = [_candle_row(T0, 100, 101, 100.5, 99)]
    a = OkxPublicAdapter(http_get=lambda u, p: {"data": rows})  # noqa: E731
    tick = a.backfill("BTCUSDT", T0, T0 + timedelta(minutes=1))[0]
    n = normalize_tick(tick)
    assert n.bid == n.ask == 100.5
    assert n.spread_price_tag == "bid-ask"  # bid==ask is the honest summary quote


# --------------------------------------------------------------------- #
# live capture (network-gated; skipped in egress-restricted sandboxes)
# --------------------------------------------------------------------- #
@pytest.mark.skipif(
    not _okx_reachable(),
    reason="OKX public WS not reachable from this egress (see 09-28 feed bench)",
)
async def test_live_okx_capture_one_tick():
    a = OkxPublicAdapter()
    got = None
    async for t in a.stream(["BTCUSDT"]):
        got = t
        break
    assert got is not None
    assert got.last and got.last > 0
    n = normalize_tick(got)
    assert n.bid > 0 and n.ask >= n.bid
