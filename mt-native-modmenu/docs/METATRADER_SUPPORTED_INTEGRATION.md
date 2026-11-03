# Safe MT5 integration decision

MetaTrader 5 Android documents built-in indicators and graphical chart tools, not an API for installing third-party MQL5 indicators inside the Android app. Do not modify MetaQuotes DEX, signatures, integrity checks or anti-tamper logic to hide a patch.
- Native Android option: standalone read-only companion dashboard showing authorized/imported OHLC and economic events, with its own independent overlays and symbol selector.
- MT5 desktop option: documented MQL5 custom indicator and graphical objects, installed through MetaEditor. This is a separate deliverable from the Android APK.
- Research toggles: NEWS, BBMA_DASHBOARD, FIBONACCI, BANDS, EMA50, LWMA, SUPPLY_DEMAND, TRENDLINES. All independent, opacity 10–100%, scale 50–200%, normalized position.
- Do not claim overlays are installed in MetaTrader Android until an authorized extension point is documented and verified.
- No broker order APIs, no bypass of app integrity, no billing.
