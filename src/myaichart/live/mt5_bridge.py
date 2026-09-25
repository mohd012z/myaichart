from __future__ import annotations

import asyncio
from myaichart.models import NormalizedTick

_SENTINEL = object()


class MT5BridgeAdapter:
    """In-process bridge contract for MT5/broker tick producers.

    An external MT5 bridge can push normalized ticks into this adapter. The
    research package never creates broker orders.
    """
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._history: list[NormalizedTick] = []

    async def push(self, tick: NormalizedTick) -> None:
        self._history.append(tick)
        await self._queue.put(tick)

    async def close(self) -> None:
        await self._queue.put(_SENTINEL)

    async def stream(self):
        while True:
            item = await self._queue.get()
            if item is _SENTINEL:
                break
            yield item

    async def backfill(self, start_utc, end_utc):
        return [t for t in self._history if start_utc <= t.source_timestamp_utc <= end_utc]
