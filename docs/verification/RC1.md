# myaichart RC1 Verification

Date: 2026-09-25  
Branch: `feature/realtime-xauusd`  
Scope: research-only XAUUSD market evidence, realtime/replay candles, Chart.js workbench, event/news-effect context, and BABYLON P1/P2 shadow analysis. No automatic trading or broker order execution.

## Fresh verification evidence

### Python tests

Command:

```bash
pytest -q
```

Observed result before this report was written:

```text
49 passed in 0.29s
```

### Frontend contract

Command:

```bash
node tests/web/test_frontend_contract.mjs
```

Observed result: exit code 0.

### Editable installation

Command:

```bash
python -m pip install -e '.[test]' --no-build-isolation
```

Observed result: `Successfully installed myaichart-0.1.0`.

`--no-build-isolation` is used in this execution environment because it has no outbound package installation access and already provides setuptools. The package itself uses the standard `setuptools.build_meta` backend.

### CLI

Command:

```bash
myaichart --help
```

Observed command groups:

```text
collect, verify, aggregate, events, effects, serve, live, replay
```

### Compile verification

Command:

```bash
python -m compileall -q src
```

Observed result: exit code 0.

## Source smoke test

Attempted one historical Dukascopy XAUUSD hour:

```text
2026-09-23 12:00:00 UTC -> 12:59:59 UTC
```

Observed result:

```text
SOURCE_SMOKE_BLOCKED ConnectError [Errno -3] Temporary failure in name resolution
```

Therefore this environment did not fabricate a tick count or performance result. The downloader/BI5 parser is covered with deterministic binary fixtures, while a real-source smoke run must be repeated in an internet-enabled environment, preferably GitHub Actions.

## Offline storage ruling

`pyarrow` could not be downloaded in this environment. `RawTickStore` therefore supports:

- Parquet when the optional `parquet` extra is installed;
- append-only JSONL fallback when Parquet support is unavailable.

The normalized tick API, source identity, timestamps, and evidence semantics are unchanged.

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
- Economic-event times normalize to UTC and MYT; revisions retain history.
- Pre-event features do not expose future post-event outcomes.
- P2 shadow BLOCK/ALLOW annotations do not remove or mutate P1 control trades.
- FastAPI exposes health/timeframe and WebSocket contracts.
- Chart.js frontend keeps backend tick processing separate from repaint throttling.
- MT5 bridge adapter accepts real normalized incoming ticks but contains no broker order execution.

## Known limitations

- No real six-month XAUUSD download was completed inside this offline runtime.
- The packaged `DukascopyLiveAdapter` is only an adapter boundary; a live JForex connection is not embedded.
- The MT5 bridge is an incoming-tick adapter contract, not an embedded MetaTrader terminal connector.
- Broker-specific contract size, commissions, slippage, and execution are not treated as authoritative unless supplied by the broker/test environment.
- Consensus forecasts remain optional and are not synthesized.
- Parquet is optional in the local offline build; GitHub Actions installs the `parquet` extra.

## Next verification in GitHub Actions

1. Run CI on `feature/realtime-xauusd` and confirm the Python + frontend suites in GitHub's environment.
2. Run the `Collect XAUUSD` workflow with a small historical interval first.
3. Validate first/last bid/ask, tick count, data gaps, M1/M5 candle counts, and checksums.
4. Only after the smoke run is valid, request the six-month dataset artifact.
