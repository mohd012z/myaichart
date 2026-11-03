# MT5 build 500.6260: chart integration evidence

Source: user-provided MetaTrader 5_500.6260.apk, inspected read-only.
The APK contains one classes.dex and ARM native libraries including libcommon.so.

Verified DEX type descriptors:
- Lnet/metaquotes/metatrader5/ui/charts/ChartSurface;
- Lnet/metaquotes/metatrader5/terminal/ChartRenderer;
- Lnet/metaquotes/metatrader5/ui/charts/ChartsFragment;
- Lnet/metaquotes/metatrader5/ui/charts/ChartsMdiGroup;
- Lnet/metaquotes/metatrader5/Chart;
- Landroid/view/SurfaceView;

These are type references, NOT verified View inheritance, host IDs, methods, hook points, renderer transforms or supported plugin APIs.

Integration acceptance gates:
1. Decompile or inspect class definitions and inheritance with independently validated DEX tooling.
2. Inspect layout inflation and chart lifecycle, verify actual ViewGroup host.
3. Instrument chart time/price pixel mapping and test pan, zoom, rotation and timeframe switches.
4. Confirm overlay draw order and touches with SurfaceView or native rendering.
5. Reject stale and unverified host snapshots; never fabricate OHLC prices.
6. Build against Android SDK, test Android 9+, sign a distinct debug package and install on a test device.
7. Do not redistribute original proprietary APK or publish signing secrets.
No original APK or .so binaries are committed.
