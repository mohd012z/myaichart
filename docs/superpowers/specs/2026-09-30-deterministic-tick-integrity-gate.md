# Deterministic Tick Integrity Gate Specification

## Goal
Introduce a deterministic streaming integrity boundary between market-data adapters and `CandleEngine` without changing the engine's existing `NormalizedTick`/UTC-datetime contract. The gate must establish canonical event-time ordering, preserve point-in-time knowledge, emit auditable integrity/control decisions, and support identical live/replay semantics.

## Existing contracts to preserve
- `NormalizedTick` is the frozen Pydantic domain model in `src/myaichart/models.py` with symbol/source/source_record_id, timezone-aware source/received UTC timestamps, bid/ask, optional volumes, and optional sequence_id.
- `CandleEngine.on_tick(tick)` consumes `NormalizedTick` and emits `list[CandleUpdate]`.
- `CandleEngine.advance_clock(now)` consumes timezone-aware `datetime`.
- Candle lifecycle remains LIVE -> PROVISIONALLY_CLOSED -> FINAL, with explicit CORRECTED/RECOVERED states and authorized revision handling.
- Existing dataset-level `data/integrity.py` remains responsible for stored-dataset verification; streaming integrity is a separate subsystem.

## Core invariant
For identical ordered input observations, configuration, engine version, and initial state, the system must produce identical ordered ticks, candles, signals, decisions, and evidence.

## Temporal model
Every observation has two distinct times:
- Event time: provider/source timestamp; determines market-time ordering and candle bucket membership.
- Knowledge time: receive/availability timestamp; determines when the system could have known the observation.

Streaming integrity may use integer nanoseconds internally. Conversion back to timezone-aware UTC `datetime` occurs at the existing CandleEngine boundary without changing CandleEngine's public signature.

`allowed_lateness` and `CandleEngine.grace_seconds` are independent configuration concepts:
- allowed_lateness: reordering/watermark policy before aggregation.
- grace_seconds: post-boundary candle amendment/finalization policy.

## Watermark and deterministic ordering
Maintain a bounded reorder buffer. For each accepted structurally valid observation:
1. Update `max_event_time_seen`.
2. Compute `watermark = max_event_time_seen - allowed_lateness_ns`.
3. Hold observations newer than the watermark.
4. Release observations at/before the watermark in deterministic canonical order.
5. An observation arriving behind an already advanced watermark is classified as late and follows the explicit late/revision policy rather than silently rewriting history.

Canonical tie-breaking must not depend on Python insertion order. Ordering key is:
1. source/event timestamp,
2. provider sequence when the source guarantees a sequence domain,
3. stable source record identity,
4. receive/knowledge timestamp only as a documented fallback.

Providers without sequence numbers bypass sequence continuity validation. A sequence-domain change or explicit reconnect resets sequence tracking. A sequence gap is a control anomaly, not proof that the observed tick itself is corrupt.

## Integrity dispositions
Streaming decisions use these dispositions:
- ACCEPT
- ACCEPT_FLAGGED
- HOLD
- QUARANTINE
- REJECT_INVALID

Every decision is auditable and includes deterministic event identity, reason codes, event time, knowledge time, and current watermark.

Structural invalidity (for example crossed market `bid > ask`, malformed timestamps, or irreconcilable identity conflicts) may be rejected/quarantined according to policy. Zero spread (`bid == ask`) is valid. Statistical price anomalies are flagged rather than automatically deleted so macro-event moves remain observable.

## Duplicate identity
Duplicate handling is based on stable source identity when available. Content-derived fallback identity must be deterministic and documented. Duplicate disposition must be reproducible across replay runs.

## Sequence gaps and recovery
A sequence discontinuity emits a control event describing expected and observed sequence values. The observed later tick is not automatically quarantined. Recovery/backfill is owned by a separate RecoveryCoordinator; the integrity gate detects and reports but does not call provider APIs.

Recovered observations must re-enter through the normal Adapter -> Normalizer -> Integrity path. They must never be injected directly into candles.

## Feed health
Feed staleness is evaluated against market/session state. Silence during an ACTIVE market may become STALE after the configured timeout. Silence during SCHEDULED_BREAK, WEEKEND, HOLIDAY, or other explicitly closed states is expected dormancy and must not generate false stale alarms.

## Clock propagation
The gate exposes clock advancement independently from tick arrival and forwards semantic UTC clock advancement to CandleEngine. Replay may use a discrete-event scheduler; it does not need fixed-frequency pulses when no observable transition can occur. It must reproduce candle boundaries, grace expiries, macro availability times, strategy timers, session transitions, and recovery deadlines.

## Audit/control outputs
The streaming layer emits machine-verifiable structures, not natural-language decisions:
- IntegrityDecision
- SequenceGapEvent
- FeedStateEvent
- late/quarantine/rejection records

The EvidenceLedger records these structures. Presentation/LLM layers remain strictly downstream.

## Test-first acceptance matrix
Before the gate is connected to CandleEngine, tests must pin:
1. exact timestamp ordering,
2. bounded reordering: 100,102,101 -> 100,101,102 when all are admissible,
3. deterministic equal-timestamp tie-breaking,
4. beyond-watermark late disposition,
5. deterministic duplicate identity handling,
6. sequence 100 -> 102 emits a gap without falsely corrupting 102,
7. sequence-domain/reconnect reset,
8. provider with no sequence numbers,
9. `bid > ask` invalidity,
10. `bid == ask` acceptance,
11. active-market silence -> STALE,
12. scheduled-break/weekend silence -> not STALE,
13. UTC clock propagation into CandleEngine closure lifecycle,
14. repeated replay produces byte-identical ordered decision/control/tick streams.

Integration tests then extend this to D1-D6:
- D1 deterministic repeated replay,
- D2 restart/checkpoint equivalence,
- D3 point-in-time isolation,
- D4 live/replay and streamed/chunked convergence,
- D5 provenance traceability,
- D6 Babylon signal/evidence reproducibility.

## Non-goals for this phase
- No provider-specific WebSocket implementation.
- No REST backfill implementation inside the gate.
- No GUI/SSE/WebSocket gateway implementation.
- No change to Babylon trading/analysis semantics.
- No silent statistical spike filtering.

## Architectural boundary
`Adapter -> Normalizer -> TickIntegrityGate -> deterministic reorder/watermark -> CandleEngine -> Canonical State`

Side control plane:
`TickIntegrityGate -> anomaly/gap event -> RecoveryCoordinator -> Adapter -> Normalizer -> TickIntegrityGate`

This phase is successful only when the streaming gate's behavior is pinned by failing-then-passing tests and existing candle/replay tests remain compatible.