"""Raw provider tick (market.tick.v1) and the provider source taxonomy.

A ``MarketTick`` is what a provider adapter emits *before* normalization:
provider-shaped, unvalidated, carrying provider identity and timing. The
Market Hub turns it into ``myaichart.models.NormalizedTick`` (quality-tagged)
inside ``normalize.py``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Optional


class SourceClass(StrEnum):
    """How a provider's price is produced — drives role assignment + trust.

    BROKER = real broker quote (CFD/spot feed). Exchange-adjacent but
    provider-specific.
    EXCHANGE = anonymous public exchange feed (Binance/OKX/Bybit).
    AGGREGATOR = third-party rollup (Twelve Data, Finnhub).
    REFERENCE = cheap/slow spot reference (gold-api class).
    FUTURES_PROXY = a futures contract used as a *proxy* for spot (e.g.
    COMEX GC for XAUUSD) — MUST stay labeled, never blended into spot.
    """
    BROKER = "BROKER"
    EXCHANGE = "EXCHANGE"
    AGGREGATOR = "AGGREGATOR"
    REFERENCE = "REFERENCE"
    FUTURES_PROXY = "FUTURES_PROXY"


class InstrumentRole(StrEnum):
    """Role a provider is allowed to play for a given instrument.

    AUTHORITY = the single source of candle truth for this instrument.
    VALIDATOR = cross-checks AUTHORITY (divergence / stale detection).
    REFERENCE = slow spot reference, never drives candles.
    FALLBACK = becomes temporary AUTHORITY on AUTHORITY outage (audited).
    """
    AUTHORITY = "AUTHORITY"
    VALIDATOR = "VALIDATOR"
    REFERENCE = "REFERENCE"
    FALLBACK = "FALLBACK"


@dataclass(frozen=True)
class MarketTick:
    """Provider-shaped raw tick. No quote validation here — that is
    ``normalize.py``'s job, so an adapter never silently 'fixes' data."""
    symbol: str                      # canonical hub symbol, e.g. "XAUUSD"
    provider: str                    # e.g. "BINANCE", "CTRADER"
    provider_symbol: str             # provider-native, e.g. "PAXGUSDT"
    source_class: SourceClass
    ts_exchange: datetime            # provider timestamp (UTC, aware)
    ts_received: datetime            # when the hub received it (UTC, aware)
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    sequence: Optional[int] = None   # provider sequence if the feed has one
    raw: dict = field(default_factory=dict)   # full raw payload, provenance

    def best_price(self) -> Optional[float]:
        """Mid when both sides present, else last, else whichever side."""
        if self.bid is not None and self.ask is not None:
            return (self.bid + self.ask) / 2.0
        if self.last is not None:
            return self.last
        return self.bid if self.bid is not None else self.ask


__all__ = ["MarketTick", "SourceClass", "InstrumentRole"]
