# MT4/MT5 Native ModeMenu Research

Source-only prototype for Android-native BBMA/Fibonacci, quote/spread/news and research strategy modules. **Not a modified MetaTrader APK; no live broker execution.**

## Planned modules
- Android ModeMenuView (not yet injected into MT4/MT5)
- BBMA Bollinger/EMA/LWMA and Fibonacci calculations
- Closed-bar research signals, simulated strategy evaluation
- Quote collector, CSV, spread and calendar event filters

## Verification gates
Identify chart container, validate OHLC provider and coordinate transformations, compile Android, test UI, sign isolated APK and run device tests.

No original proprietary APK, credentials, signing keys or Cloudflare deployment. Keep `main` unchanged.
