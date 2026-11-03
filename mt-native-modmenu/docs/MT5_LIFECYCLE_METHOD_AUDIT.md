# MT5 500.6260 chart lifecycle DEX audit

Read-only inspection of the user-supplied APK's `classes.dex` method tables (not an Android runtime trace).

**ChartSurface** extends `android.view.TextureView`. Defined methods include:
`onAttachedToWindow`, `onDetachedFromWindow`,
`onSurfaceTextureAvailable`, `onSurfaceTextureDestroyed`,
`onSurfaceTextureSizeChanged`, `onSurfaceTextureUpdated`,
`onWindowVisibilityChanged`, `getChartId`, `setChartId`,
`onChartIdChanged`, `onTerminalLoad`, `onTerminalUnload`.

**ChartsMdiGroup** extends `android.view.ViewGroup`. Defined methods include:
`onMeasure`, `onLayout`, `dispatchDraw`,
`setOnChartViewCreatedListener`, `setSelectedChart`,
`setChartLayoutMode`, `getActualMode`.

**ChartRenderer** extends `java.lang.Object`; method names include
`setAlphabet`, `setBanner`, `setDarkMode`, `setDensity`,
`createAlphabet`, `createBitmap`, `getPaint`.

These are **DEX method names**, not validated method signatures, invocation order, callbacks or safe injection points.
A separate lifecycle reducer was implemented and locally tested for attachment, texture availability, resize, destruction and detachment. It is NOT connected to the MT5 application.

## Android compilation verification
Repository CI #135 passed Python/JS tests; source-smoke skipped. No Android SDK `android.jar` exists in the current local container. The branch contains an Android compile workflow, but the GitHub connector's commit-workflow endpoint only exposes PR-triggered runs and has not provided a verified Android compile job. Do not claim Android compilation passed.

## Release gates
- Runtime chart parent hierarchy: **UNKNOWN**
- Overlay pixel calibration: **UNKNOWN**
- Real chart OHLC adapter: **NOT IMPLEMENTED**
- Android source compilation: **UNVERIFIED**
- Modified MT5 APK: **NOT BUILT**
- Signed and installed MT5 APK: **NOT VERIFIED**
