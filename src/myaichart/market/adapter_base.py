"""Provider adapter base class.

An adapter knows ONE provider. Its contract:
  - ``provider`` / ``default_symbol`` / ``source_class`` identify it.
  - ``async stream(symbols)`` yields raw ``MarketTick`` (no normalization,
    no validation — the hub does that).
  - ``async backfill(symbol, start, end)`` returns raw ticks for gap recovery.
  - ``async close()`` releases the transport.

Adapters never place orders and never mutate candles. They are deliberately
thin so any provider can be added without touching the hub.
"""
from __future__ import annotations

import abc
from datetime import datetime
from typing import AsyncIterator, Optional

from myaichart.market.tick import MarketTick, SourceClass


class FeedAdapter(abc.ABC):
    provider: str = "base"
    source_class: SourceClass = SourceClass.AGGREGATOR

    @abc.abstractmethod
    def symbol_map(self, canonical: str) -> Optional[str]:
        """Map a hub symbol to this provider's native symbol, or None if the
        provider doesn't cover it. e.g. XAUUSD -> None on Binance."""

    @abc.abstractmethod
    def stream(self, canonical_symbols: list[str]) -> AsyncIterator[MarketTick]:
        ...

    @abc.abstractmethod
    def backfill(self, canonical: str, start: datetime, end: datetime) -> list[MarketTick]:
        ...

    def close(self) -> None:  # sync ok; adapters with async teardown override
        return None
