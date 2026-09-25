from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import AsyncIterator, Protocol
from myaichart.models import NormalizedTick


class FeedAdapter(Protocol):
    async def stream(self) -> AsyncIterator[NormalizedTick]: ...
    async def backfill(self, start_utc: datetime, end_utc: datetime) -> list[NormalizedTick]: ...


@dataclass(frozen=True)
class TickDecision:
    accepted: bool
    reason: str


class TickValidator:
    def __init__(self):
        self._seen: set[tuple[str, str]] = set()
        self.accepted_count = 0
        self.duplicate_count = 0

    def accept(self, tick: NormalizedTick) -> TickDecision:
        identity = (tick.source, tick.source_record_id)
        if identity in self._seen:
            self.duplicate_count += 1
            return TickDecision(False, 'DUPLICATE_SOURCE_ID')
        self._seen.add(identity)
        self.accepted_count += 1
        return TickDecision(True, 'ACCEPTED')
