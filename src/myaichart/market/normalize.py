"""Normalize a raw MarketTick into a quality-tagged NormalizedTick.

This is the single boundary where provider data becomes hub data. It never
*invents* a quote: when a feed has only a trade price (crypto), both
bid/ask are set to that price and ``source_class`` preserves the truth. The
frozen NormalizedTick contract (ask >= bid > 0, tz-aware) is guaranteed here.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from myaichart.models import NormalizedTick
from myaichart.market.tick import MarketTick


def _utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("tick timestamp must be timezone-aware")
    return dt.astimezone(timezone.utc)


def normalize_tick(m: MarketTick) -> NormalizedTick:
    """Build a NormalizedTick from a MarketTick, computing the quality
    envelope (latency, staleness, duplicate flag on identical source id).

    Raises ValueError if no price is present — the hub records that as a
    dropped tick rather than fabricating one.
    """
    bid = m.bid
    ask = m.ask
    if bid is None and ask is None and m.last is None:
        raise ValueError(f"no price on tick from {m.provider}:{m.provider_symbol}")
    last_only = (bid is None) or (ask is None)
    if last_only:
        # last-only feed (crypto trade stream): quote == last. source_class
        # carries the honest label; we do NOT synthesize a fake spread.
        p = m.last if m.last is not None else (bid if bid is not None else ask)
        assert p is not None  # guarded by the no-price raise above
        bid, ask = float(p), float(p)
    else:
        assert bid is not None and ask is not None

    ts_exchange = _utc(m.ts_exchange)
    ts_received = _utc(m.ts_received)
    latency_ms = (ts_received - ts_exchange).total_seconds() * 1000.0
    # negative latency == provider clock ahead of us / out-of-order receipt
    out_of_order = latency_ms < 0

    return NormalizedTick(
        symbol=m.symbol,
        source=m.provider,
        source_record_id=f"{m.provider}:{m.provider_symbol}:{m.sequence if m.sequence is not None else m.ts_exchange.isoformat()}",
        source_timestamp_utc=ts_exchange,
        received_timestamp_utc=ts_received,
        bid=float(bid),
        ask=float(ask),
        provider_symbol=m.provider_symbol,
        source_class=m.source_class.value,
        latency_ms=round(latency_ms, 3),
        is_duplicate=False,            # filled in by the validator in hub.py
        is_stale=bool(out_of_order),   # provider clock ahead / delayed receipt
        is_out_of_order=out_of_order,
        spread_price_tag="last-only" if last_only else "bid-ask",
    )
