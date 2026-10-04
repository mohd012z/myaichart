"""Provider health + authority engine (canonical-market hub core).

This is the part that is correct regardless of *which* providers are later
wired in. It assigns a role per provider (AUTHORITY / VALIDATOR / REFERENCE /
FALLBACK), scores freshness/latency, measures cross-provider divergence on a
common instrument, and raises a PROVIDER_CONFLICT freeze when a validator
disagrees with authority beyond tolerance.

Design rule (matches Anam's spec + the helix invariant): authority is ONE
provider; others *verify*, they never blend into the candle. On authority
outage a FALLBACK is promoted — and the promotion is recorded, not silent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional

from myaichart.market.tick import InstrumentRole


class HealthState(StrEnum):
    LIVE = "LIVE"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    OUTAGE = "OUTAGE"
    CONFLICT = "CONFLICT"   # provider-level: it is the one diverging
    UNSUPPORTED = "UNSUPPORTED"


class HubState(StrEnum):
    HEALTHY = "HEALTHY"
    PROVIDER_CONFLICT = "PROVIDER_CONFLICT"
    PROVIDER_SWITCH = "PROVIDER_SWITCH"
    NO_AUTHORITY = "NO_AUTHORITY"


@dataclass
class ProviderHealth:
    provider: str
    symbol: str
    role: InstrumentRole
    state: HealthState = HealthState.UNSUPPORTED
    last_ts: Optional[datetime] = None
    last_mid: Optional[float] = None
    median_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    gap_count: int = 0
    _lat: list = field(default_factory=list, repr=False)

    def observe(self, mid: float, ts: datetime, *, latency_ms: float, gap: bool = False) -> None:
        self.last_ts = ts.astimezone(timezone.utc)
        self.last_mid = mid
        self._lat.append(latency_ms)
        self._lat.sort()
        n = len(self._lat)
        self.median_latency_ms = self._lat[n // 2]
        self.p95_latency_ms = self._lat[min(n - 1, int(n * 0.95))]
        if gap:
            self.gap_count += 1
        self.state = HealthState.LIVE

    def age_ms(self, now: datetime) -> Optional[float]:
        if self.last_ts is None:
            return None
        return (now.astimezone(timezone.utc) - self.last_ts).total_seconds() * 1000.0


@dataclass
class Divergence:
    authority: str
    provider: str
    authority_mid: float
    provider_mid: float
    abs_diff: float
    rel_diff: float   # provider - authority, in price units / authority
    within_tolerance: bool


class HealthEngine:
    """Tracks per-provider health and cross-provider divergence.

    ``tolerance_abs`` / ``tolerance_rel`` bound how far a validator may drift
    from authority before the hub freezes (PROVIDER_CONFLICT). For a spot
    instrument with tight inter-provider spreads these stay small; the
    operator chooses them per instrument.
    """

    def __init__(self, symbol: str, *, tolerance_abs: float = 0.5, tolerance_rel: float = 0.0002, stale_after_ms: float = 30000.0):
        self.symbol = symbol
        self.tolerance_abs = tolerance_abs
        self.tolerance_rel = tolerance_rel
        self.stale_after_ms = stale_after_ms
        self.providers: dict[str, ProviderHealth] = {}
        self.state = HubState.NO_AUTHORITY
        self.authority: Optional[str] = None
        self._divergence: dict[str, Divergence] = {}
        self._switch_log: list[dict] = []
        self._freshest: Optional[datetime] = None

    def register(self, provider: str, role: InstrumentRole) -> ProviderHealth:
        if provider not in self.providers:
            self.providers[provider] = ProviderHealth(provider, self.symbol, role)
        else:
            self.providers[provider].role = role
        if role == InstrumentRole.AUTHORITY:
            self._set_authority(provider)
        return self.providers[provider]

    def _set_authority(self, provider: str) -> None:
        if self.authority != provider:
            prev = self.authority
            self.authority = provider
            if prev is not None:
                # a genuine handoff (first authority registration is not a switch)
                self._switch_log.append({
                    "at": datetime.now(timezone.utc).isoformat(),
                    "from": prev,
                    "to": provider,
                })
            self.state = HubState.PROVIDER_SWITCH if prev is not None else HubState.HEALTHY

    def observe(self, provider: str, mid: float, ts: datetime, *, latency_ms: float, gap: bool = False) -> None:
        ph = self.providers.get(provider)
        if ph is None:
            raise KeyError(f"provider {provider!r} not registered")
        ph.observe(mid, ts, latency_ms=latency_ms, gap=gap)
        ts_utc = ts.astimezone(timezone.utc)
        if self._freshest is None or ts_utc > self._freshest:
            self._freshest = ts_utc
        # mark stale relative to the freshest tick seen (replay-safe: not wall clock)
        self._mark_stale()
        self._recompute_divergence()

    def _mark_stale(self) -> None:
        if self._freshest is None:
            return
        for ph in self.providers.values():
            if ph.last_ts is None:
                continue
            age = (self._freshest - ph.last_ts).total_seconds() * 1000.0
            if ph.state == HealthState.LIVE:
                if age > self.stale_after_ms:
                    ph.state = HealthState.STALE
                elif ph.gap_count:
                    ph.state = HealthState.DEGRADED

    def _recompute_divergence(self) -> None:
        if self.authority is None:
            return
        auth = self.providers[self.authority]
        if auth.last_mid is None:
            return
        self._divergence.clear()
        conflict = False
        for prov, ph in self.providers.items():
            if prov == self.authority or ph.last_mid is None or ph.role not in (
                InstrumentRole.VALIDATOR, InstrumentRole.FALLBACK
            ):
                continue
            rel = (ph.last_mid - auth.last_mid) / auth.last_mid
            within = abs(ph.last_mid - auth.last_mid) <= self.tolerance_abs and abs(rel) <= self.tolerance_rel
            if not within:
                conflict = True
                ph.state = HealthState.CONFLICT
            self._divergence[prov] = Divergence(
                authority=self.authority,
                provider=prov,
                authority_mid=auth.last_mid,
                provider_mid=ph.last_mid,
                abs_diff=abs(ph.last_mid - auth.last_mid),
                rel_diff=rel,
                within_tolerance=within,
            )
        if conflict:
            self.state = HubState.PROVIDER_CONFLICT
        elif self.state == HubState.PROVIDER_CONFLICT:
            # conflict cleared
            self.state = HubState.HEALTHY

    def divergence(self, provider: str) -> Optional[Divergence]:
        return self._divergence.get(provider)

    def report(self) -> dict:
        return {
            "symbol": self.symbol,
            "hub_state": self.state.value,
            "authority": self.authority,
            "tolerance_abs": self.tolerance_abs,
            "tolerance_rel": self.tolerance_rel,
            "providers": {
                p: {
                    "role": ph.role.value,
                    "state": ph.state.value,
                    "last_mid": ph.last_mid,
                    "median_latency_ms": round(ph.median_latency_ms, 2),
                    "p95_latency_ms": round(ph.p95_latency_ms, 2),
                    "gap_count": ph.gap_count,
                }
                for p, ph in self.providers.items()
            },
            "divergence": {
                p: {
                    "abs_diff": round(d.abs_diff, 6),
                    "rel_diff": round(d.rel_diff, 6),
                    "within_tolerance": d.within_tolerance,
                }
                for p, d in self._divergence.items()
            },
            "switch_log": self._switch_log,
        }
