# myaichart

`myaichart` is a research-first XAUUSD evidence collector, realtime/replay candle engine, Chart.js workbench, and BABYLON P1/P2 analysis toolkit. It does **not** place broker orders.

## Install

```bash
python -m pip install -e '.[test]'
```

Optional Parquet storage:

```bash
python -m pip install -e '.[parquet]'
```

## Malaysia-time workflow

Canonical storage is UTC. The primary display timezone is `Asia/Kuala_Lumpur` (MYT, UTC+8).

```bash
myaichart collect XAUUSD --months 6
myaichart verify XAUUSD
myaichart aggregate XAUUSD --timeframes M1 M5 M15 M30 H1 H4 D1 W1 MN1
myaichart serve XAUUSD --timezone Asia/Kuala_Lumpur
```

Historical raw ticks are excluded from normal git history. The manual GitHub workflow supports an exact MYT smoke range or six calendar months, and raw ticks are an opt-in artifact. The workbench supports MID/BID/ASK candlesticks, realtime/replay messages, spread/volatility/liquidity context, BLS official-calendar metadata, and research-only BABYLON overlays.

## Realtime sources

The common feed contract accepts normalized XAUUSD bid/ask ticks. `ReplayAdapter` is included for deterministic replay. Broker/live adapters must supply real ticks; no tick means no fabricated OHLC movement.

## Verification

See `docs/verification/RC1.md` for the release-candidate evidence and current environment limitations.
