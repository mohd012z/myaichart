# myaichart RC1 Verification

Date: 2026-09-25  
Branch: `feature/realtime-xauusd`  
Scope: research-only XAUUSD market evidence, realtime/replay candles, Chart.js workbench, event/news-effect context, and BABYLON P1/P2 shadow analysis. No automatic trading or broker order execution.

## Fresh verification evidence

### Python tests — GitHub Actions

Command:

```bash
pytest -q
```

Observed on commit `6788a465cf0aa7c40f1582d4eaf49d07d38fe3ff`:

```text
68 passed, 1 warning in 0.79s
```

The warning is a Starlette/FastAPI TestClient deprecation warning and did not fail the suite.

### Frontend contract — GitHub Actions

Command:

```bash
node tests/web/test_frontend_contract.mjs
```

Observed result: exit code 0.

### Editable installation — GitHub Actions

Command:

```bash
pip install -e '.[test,parquet]'
```

Observed result: package build/install succeeded on Python 3.12, including `pyarrow` Parquet support.

### CLI / compile verification

The local RC verification established that `myaichart --help` and `python -m compileall -q src` exit successfully. The current GitHub CI independently verifies install, Python tests, and the Node frontend contract.

## Real-source smoke test — PASSED

GitHub Actions run `36144081466`, job `source-smoke`, fetched a bounded real Dukascopy XAUUSD interval requested as Malaysia time:

```text
2026-09-23 20:00:00 MYT -> 20:59:59 MYT
```

which normalized to:

```text
2026-09-23 12:00:00 UTC -> 12:59:59 UTC
```

Observed collection result:

```json
{"ticks": 14412, "chunks": 1, "start_utc": "2026-09-23T12:00:00+00:00", "end_utc": "2026-09-23T12:59:59+00:00"}
```

Integrity verification:

```text
raw_tick_count    14412
unique_tick_count 14412
duplicate_count   0
data_gap_count    0
missing_hour_count 0
first_tick_utc    2026-09-23T12:00:00.095000+00:00
last_tick_utc     2026-09-23T12:59:58.837000+00:00
```

A SHA-256 checksum manifest was generated for the raw Parquet partition and metadata files.

The same real tick sample was then aggregated successfully:

```text
M1 candles 60
M5 candles 12
```

Both `Verify real ticks` and `Verify processed candles` completed successfully in GitHub Actions.

## Dukascopy rate-limit hardening

An earlier source-smoke run exposed HTTP 429 throttling. The collector was changed under regression tests to:

- use the current daily BI5 bucket path for six-month collection instead of issuing one HTTP request per hour;
- split accepted daily ticks back into chronological hourly chunks internally;
- default to conservative request concurrency;
- honor numeric `Retry-After` on HTTP 429;
- use capped exponential backoff for retryable 429/5xx/transport failures;
- keep the legacy hourly fetch helper for compatibility/diagnostics.

This reduces a six-month collection from roughly 4,300 hourly requests to roughly 180 daily requests before retries.

## Metadata regression fixed

The first successful real fetch exposed a separate metadata bug: `write_metadata()` referenced `payloads['integrity']` although the stored key was `integrity.json`. A RED regression test reproduced the exact `KeyError`; the writer now builds `checksums.json` directly from the computed integrity payload. The final source-smoke passed after this fix.

## Storage behavior

`RawTickStore` supports:

- Parquet when the optional `parquet` extra is installed;
- append-only JSONL fallback when Parquet support is unavailable.

GitHub Actions uses the Parquet path. The normalized tick API, source identity, timestamps, and evidence semantics are identical across storage backends.

## Core verified contracts

- UTC canonical timestamps and MYT (`Asia/Kuala_Lumpur`, UTC+8) display conversion.
- M1/M5/M15/M30/H1/H4/D1/W1/MN1 bucket rules with MYT calendar and source-session profiles.
- Equal-time distinct source ticks are retained; source-identity duplicates are rejected.
- No tick produces no synthetic candle.
- Realtime bid/ask/mid OHLC is generated only from accepted ticks.
- Late ticks can amend provisional candles during the grace window; post-finalization correction is versioned.
- Overlapping reconnect/backfill data are deterministically deduplicated.
- Replay uses the same normalized tick/candle path as live input.
- Spread, top-of-book liquidity/activity, volatility, and Bollinger calculations are separated semantically.
- BLS official-calendar events normalize Eastern Time to UTC and MYT; missing forecasts remain null; revisions retain history.
- Event-effect baselines use only candles closed at or before the target time; pre-event features do not expose future post-event outcomes.
- P2 shadow BLOCK/ALLOW annotations do not remove or mutate P1 control trades.
- FastAPI exposes health/timeframe and WebSocket contracts.
- Chart.js frontend keeps backend tick processing separate from repaint throttling.
- MT5 bridge adapter accepts normalized incoming ticks but contains no broker order execution.

## Known limitations

- The bounded real-source smoke passed, but the full six-calendar-month XAUUSD dataset has **not yet been collected**. Do not treat the one-hour smoke sample as a six-month backtest dataset.
- The packaged `DukascopyLiveAdapter` is only an adapter boundary; a live JForex connection is not embedded.
- The MT5 bridge is an incoming-tick adapter contract, not an embedded MetaTrader terminal connector.
- Broker-specific contract size, commissions, slippage, and execution are not treated as authoritative unless supplied by the broker/test environment.
- Consensus forecasts remain optional and are not synthesized.
- The smoke workflow did not print first/last bid/ask prices in its log, so this report does not invent them.

## GitHub verification

Latest verified implementation commit before this documentation update:

```text
6788a465cf0aa7c40f1582d4eaf49d07d38fe3ff
```

GitHub Actions run:

```text
36144081466
```

Results:

```text
test job          SUCCESS
pytest             68 passed
frontend contract  SUCCESS
source-smoke       SUCCESS
real ticks         14,412
M1 candles         60
M5 candles         12
duplicates         0
data gaps           0
```

## Next dataset gate

1. Run the `Collect XAUUSD` workflow for a larger bounded period (for example one trading day or one week) to validate sustained source behavior and artifact size.
2. Verify tick/candle counts, data gaps, spread/liquidity distributions, checksums, event alignment, and storage size.
3. Only after that gate is clean, run the full six-calendar-month collection as a GitHub Actions artifact rather than committing raw tick blobs to normal Git history.
4. Use the resulting six-month evidence dataset for the BABYLON backtest/replay comparison; keep live execution disabled.
