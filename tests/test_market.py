"""Market hub core tests — hermetic, no network.

Covers the durable provider-agnostic contract: NormalizedTick quality
envelope, MarketTick normalization (incl. last-only feeds), and the
health/authority/divergence engine.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from myaichart.models import NormalizedTick
from myaichart.market.tick import MarketTick, SourceClass, InstrumentRole
from myaichart.market.normalize import normalize_tick
from myaichart.market.health import HealthEngine, HealthState, HubState


T0 = datetime(2026, 9, 29, 4, 0, 0, tzinfo=timezone.utc)


def _tick(
    symbol: str = "BTCUSDT",
    provider: str = "BINANCE",
    provider_symbol: str = "BTCUSDT",
    source_class: SourceClass = SourceClass.EXCHANGE,
    ts_exchange: datetime = T0,
    ts_received: datetime = T0,
    bid: float | None = 100.0,
    ask: float | None = 100.1,
    last: float | None = 100.05,
    sequence: int | None = None,
) -> MarketTick:
    return MarketTick(
        symbol=symbol, provider=provider, provider_symbol=provider_symbol,
        source_class=source_class, ts_exchange=ts_exchange, ts_received=ts_received,
        bid=bid, ask=ask, last=last, sequence=sequence,
    )


# ---------- NormalizedTick quality envelope ----------

def test_normalized_tick_carries_quality_envelope():
    t = normalize_tick(_tick())
    assert t.provider_symbol == "BTCUSDT"
    assert t.source_class == "EXCHANGE"
    assert t.spread_price_tag == "bid-ask"
    assert t.is_duplicate is False
    assert t.latency_ms == 0.0


def test_normalized_tick_requires_aware_timestamps():
    naive = _tick(ts_exchange=datetime(2026, 9, 29, 4, 0, 0), ts_received=T0)
    with pytest.raises(ValueError):
        normalize_tick(naive)


def test_no_price_raises():
    with pytest.raises(ValueError):
        normalize_tick(_tick(bid=None, ask=None, last=None))


# ---------- last-only feeds (crypto) ----------

def test_last_only_feed_sets_quote_to_last():
    t = normalize_tick(_tick(bid=None, ask=None, last=99.5))
    assert t.bid == 99.5 and t.ask == 99.5
    assert t.spread_price_tag == "last-only"


def test_out_of_order_when_received_before_exchange():
    # provider clock ahead of the hub -> negative latency -> flagged
    t = normalize_tick(_tick(ts_received=T0 - timedelta(seconds=1)))
    assert t.is_out_of_order is True
    assert t.is_stale is True
    assert t.latency_ms is not None and t.latency_ms < 0


# ---------- health / authority / divergence ----------

def test_authority_plus_validator_healthy_within_tolerance():
    eng = HealthEngine("XAUUSD", tolerance_abs=0.5, tolerance_rel=0.0002)
    eng.register("cTrader", InstrumentRole.AUTHORITY)
    eng.register("OANDA", InstrumentRole.VALIDATOR)
    eng.observe("cTrader", 3821.25, T0, latency_ms=60)
    eng.observe("OANDA", 3821.29, T0, latency_ms=70)
    rep = eng.report()
    assert rep["hub_state"] == "HEALTHY"
    assert rep["authority"] == "cTrader"
    assert rep["divergence"]["OANDA"]["within_tolerance"] is True


def test_divergence_beyond_tolerance_freezes_hub():
    eng = HealthEngine("XAUUSD", tolerance_abs=0.5, tolerance_rel=0.0002)
    eng.register("cTrader", InstrumentRole.AUTHORITY)
    eng.register("OANDA", InstrumentRole.VALIDATOR)
    eng.observe("cTrader", 3821.25, T0, latency_ms=60)
    eng.observe("OANDA", 3826.0, T0, latency_ms=70)  # +4.75, way out
    rep = eng.report()
    assert rep["hub_state"] == "PROVIDER_CONFLICT"
    assert rep["divergence"]["OANDA"]["within_tolerance"] is False
    assert rep["providers"]["OANDA"]["state"] == "CONFLICT"


def test_conflict_clears_when_divergence_recovers():
    eng = HealthEngine("XAUUSD", tolerance_abs=0.5, tolerance_rel=0.0002)
    eng.register("cTrader", InstrumentRole.AUTHORITY)
    eng.register("OANDA", InstrumentRole.VALIDATOR)
    eng.observe("cTrader", 3821.25, T0, latency_ms=60)
    eng.observe("OANDA", 3826.0, T0, latency_ms=70)
    assert eng.state == HubState.PROVIDER_CONFLICT
    # OANDA comes back into line
    eng.observe("OANDA", 3821.3, T0 + timedelta(milliseconds=10), latency_ms=70)
    assert eng.state == HubState.HEALTHY


def test_authority_switch_is_logged_not_silent():
    eng = HealthEngine("XAUUSD")
    eng.register("cTrader", InstrumentRole.AUTHORITY)
    eng.register("Capital", InstrumentRole.FALLBACK)
    # promote fallback to authority
    eng.register("Capital", InstrumentRole.AUTHORITY)
    rep = eng.report()
    assert rep["authority"] == "Capital"
    assert rep["switch_log"][-1]["from"] == "cTrader"
    assert rep["switch_log"][-1]["to"] == "Capital"
    assert rep["hub_state"] == "PROVIDER_SWITCH"


def test_report_shape_roundtrip():
    eng = HealthEngine("XAUUSD", tolerance_abs=0.5, tolerance_rel=0.0002)
    eng.register("cTrader", InstrumentRole.AUTHORITY)
    eng.register("Twelve", InstrumentRole.REFERENCE)
    eng.observe("cTrader", 3821.25, T0, latency_ms=60)
    rep = eng.report()
    assert rep["symbol"] == "XAUUSD"
    assert "cTrader" in rep["providers"]
    assert "Twelve" in rep["providers"]
    assert rep["providers"]["cTrader"]["state"] == "LIVE"
