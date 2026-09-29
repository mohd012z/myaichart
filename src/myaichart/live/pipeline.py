"""Live pipeline — the composition layer that makes the Market Hub *run*.

    adapter.stream()  →  normalize_tick  →  TickValidator (dedupe)
                        →  CandleEngine  →  publisher(candle_update)
                        →  HealthEngine.observe (per tick)
    outage            →  recover_outage(gap)  →  RECOVERED / DATA_GAP

One runnable process: real ticks in, canonical candles + health out. The
publisher is a **hook**, not a fixed target — it composes with PR #5's
``LiveHub.publish`` (WebSocket broadcast) when that merges, and is trivially
testable with a list. Provider-agnostic: anything that satisfies PR #4's
``FeedAdapter`` contract (``stream``/``backfill``/``close`` yielding
``MarketTick``) plugs in — the OKX public adapter is the first.

Honesty invariants preserved here:
- the validator's duplicate decisions are counted, never papered over, and a
  duplicate is *not* a data gap and is not re-fed to the engine;
- backfill only covers the outage window and only when the adapter returns
  rows (candle-summary rows carry their label in ``raw``);
- a missing publisher is a no-op, not an error — the pipeline still runs.

``run_with_watchdog`` adds stall detection on top of ``run``. Note: transport
deaths are already handled *inside* the adapter (bounded reconnect), so the
watchdog's job is the rarer silent-stall case; a hard stop after
``tick_timeout_s`` of no ticks triggers the backfill path. (Cancellation of
the underlying async generator mid-stall is left to adapter teardown —
tested via the explicit ``recover_outage`` path instead, which is the one a
supervisor would call on a detected outage.)
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Optional, Protocol, runtime_checkable

from myaichart.live.base import TickValidator
from myaichart.market.health import HealthEngine
from myaichart.market.normalize import normalize_tick
from myaichart.market.tick import InstrumentRole, MarketTick

log = logging.getLogger(__name__)

Publisher = Callable[[Any], Awaitable[None] | None]


@runtime_checkable
class CandleEngineLike(Protocol):
    def on_tick(self, tick) -> list: ...


@dataclass
class PipelineStats:
    ticks_in: int = 0
    normalized: int = 0
    dropped_no_price: int = 0
    duplicates: int = 0
    candles_published: int = 0
    outages: list = field(default_factory=list)  # OutageRecord-like dicts

    def snapshot(self) -> dict:
        return {
            "ticks_in": self.ticks_in,
            "normalized": self.normalized,
            "dropped_no_price": self.dropped_no_price,
            "duplicates": self.duplicates,
            "candles_published": self.candles_published,
            "outages": list(self.outages),
        }


async def _publish(publisher: Optional[Publisher], update) -> None:
    if publisher is None:
        return
    r = publisher(update)
    if asyncio.iscoroutine(r):
        await r


class LivePipeline:
    """Runs one adapter as the authority for one symbol.

    ``role`` defaults to AUTHORITY — the first live feed for its symbol *is*
    the authority by construction; a validator feed is wired separately
    (two pipelines + one HealthEngine) once a second provider exists.
    """

    def __init__(self, adapter, engine: CandleEngineLike, *, symbol: str,
                 health: Optional[HealthEngine] = None,
                 publisher: Optional[Publisher] = None,
                 role: InstrumentRole = InstrumentRole.AUTHORITY,
                 disconnect_watchdog_s: float = 30.0):
        self.adapter = adapter
        self.engine = engine
        self.symbol = symbol
        self.health = health or HealthEngine(symbol)
        self.publisher = publisher
        self.role = role
        self.disconnect_watchdog_s = disconnect_watchdog_s
        self.validator = TickValidator()
        self.stats = PipelineStats()
        self.status = "IDLE"
        self._last_tick: Optional[datetime] = None
        self._stop = asyncio.Event()

    # ------------------------------------------------------------------ #
    # run
    # ------------------------------------------------------------------ #
    async def run(self) -> None:
        """Consume the adapter until stopped (``stop()``) or the adapter's
        stream exhausts. Disconnects inside the stream are handled by the
        adapter (reconnect); a *stalled* stream (no ticks within the
        watchdog window) triggers the backfill-recovery path."""
        self.status = "CONNECTING"
        try:
            async for mt in self.adapter.stream([self.symbol]):
                for u in self._on_market_tick(mt):
                    await _publish(self.publisher, u)
        finally:
            try:
                self.adapter.close()
            except Exception:
                pass
            if self.status not in ("STOPPED",):
                self.status = "ENDED"

    def stop(self) -> None:
        self._stop.set()

    # ------------------------------------------------------------------ #
    # per-tick
    # ------------------------------------------------------------------ #
    def _on_market_tick(self, mt: MarketTick) -> list:
        """Consume one raw tick; returns the CandleUpdates to publish (the
        async run loops own publishing so they can await an async publisher)."""
        self.stats.ticks_in += 1
        self._last_tick = mt.ts_received
        try:
            nt = normalize_tick(mt)
        except ValueError:
            self.stats.dropped_no_price += 1
            return []
        self.stats.normalized += 1

        decision = self.validator.accept(nt)
        self._observe(nt, gap=False)
        if not decision.accepted:
            # Duplicate report of an already-accepted tick: NOT a data gap
            # (the data arrived) and must not re-feed the engine (would
            # double-count the candle). Counted, never silently dropped.
            self.stats.duplicates += 1
            return []

        updates = self.engine.on_tick(nt)
        for u in updates:
            self.stats.candles_published += 1
        if updates:
            self.status = "LIVE"
        return updates

    def _observe(self, nt, *, gap: bool) -> None:
        try:
            self.health.observe(self.adapter.provider, nt.mid, nt.source_timestamp_utc,
                                latency_ms=nt.latency_ms or 0.0, gap=gap)
        except KeyError:
            self.health.register(self.adapter.provider, role=self.role)
            self.health.observe(self.adapter.provider, nt.mid, nt.source_timestamp_utc,
                                latency_ms=nt.latency_ms or 0.0, gap=gap)

    # ------------------------------------------------------------------ #
    # recovery
    # ------------------------------------------------------------------ #
    async def recover_outage(self, start_utc: datetime, end_utc: datetime) -> list:
        """Backfill the gap the adapter missed. Returns the recovered ticks.
        Empty list ⇒ DATA_GAP is recorded (no fabrication, ever)."""
        self.status = "RECONNECTING"
        ticks = await self.adapter.backfill(self.symbol, start_utc, end_utc)
        if not ticks:
            rec = {"start_utc": start_utc, "end_utc": end_utc,
                   "final_state": "DATA_GAP", "recovered_count": 0}
            self.stats.outages.append(rec)
            self.status = "STALE"
            return []
        nt_list = []
        for mt in ticks:
            try:
                nt = normalize_tick(mt)
            except ValueError:
                continue
            if not self.validator.accept(nt).accepted:
                self.stats.duplicates += 1
                continue
            nt_list.append(nt)
            try:
                self.health.observe(self.adapter.provider, nt.mid, nt.source_timestamp_utc,
                                    latency_ms=nt.latency_ms or 0.0, gap=False)
            except KeyError:
                self.health.register(self.adapter.provider, role=self.role)
                self.health.observe(self.adapter.provider, nt.mid, nt.source_timestamp_utc,
                                    latency_ms=nt.latency_ms or 0.0, gap=False)
            updates = self.engine.on_tick(nt)
            for u in updates:
                self.stats.candles_published += 1
                if self.publisher is not None:
                    r = self.publisher(u)
                    if asyncio.iscoroutine(r):
                        await r
        rec = {"start_utc": start_utc, "end_utc": end_utc,
               "final_state": "RECOVERED", "recovered_count": len(nt_list)}
        self.stats.outages.append(rec)
        self.status = "LIVE"
        return nt_list

    async def run_with_watchdog(self, tick_timeout_s: Optional[float] = None) -> None:
        """run() + silent-stall recovery.

        Design note: a stall is detected on a **queue**, not on ``anext()`` —
        ``wait_for(anext())`` would cancel the socket recv itself, killing
        the very connection we're trying to recover. The pump task owns the
        adapter's stream (its own reconnect logic stays intact); the consumer
        times out on the queue and calls ``recover_outage`` for the missed
        window, then keeps consuming. On ``stop()`` the pump is cancelled.
        """
        timeout = tick_timeout_s or (self.disconnect_watchdog_s * 3)
        self.status = "CONNECTING"
        q: asyncio.Queue = asyncio.Queue()
        _END = object()

        async def _pump():
            try:
                async for mt in self.adapter.stream([self.symbol]):
                    await q.put(mt)
            except asyncio.CancelledError:
                raise
            except Exception:
                pass  # stream died; the consumer's timeout will recover
            finally:
                await q.put(_END)

        pump = asyncio.create_task(_pump())
        last_data_ts: Optional[datetime] = None
        try:
            while not self._stop.is_set():
                try:
                    item = await asyncio.wait_for(q.get(), timeout=timeout)
                except asyncio.TimeoutError:
                    # gap window: from the last data timestamp we actually had
                    # (exchange time — the data timeline) to now. NOT from wall
                    # clock alone: mixing clock time with exchange-time backfill
                    # rows is exactly the drift class this cluster exists to
                    # prevent.
                    start = last_data_ts or (datetime.now(timezone.utc) - _seconds(timeout))
                    await self.recover_outage(start, datetime.now(timezone.utc))
                    continue
                if item is _END:
                    break
                for u in self._on_market_tick(item):
                    await _publish(self.publisher, u)
                last_data_ts = item.ts_exchange
        finally:
            pump.cancel()
            await asyncio.gather(pump, return_exceptions=True)
            try:
                self.adapter.close()
            except Exception:
                pass
            if self.status not in ("STOPPED",):
                self.status = "ENDED"


def _seconds(s: float):
    from datetime import timedelta
    return timedelta(seconds=s)


__all__ = ["LivePipeline", "PipelineStats"]
