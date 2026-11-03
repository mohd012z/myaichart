# MT5 500.6260 DEX method prototypes — evidence

Read-only parsed from uploaded APK `classes.dex`, using `method_ids`, `proto_ids` and `type_list` tables. These are exact DEX descriptors, **not** proof of call sites or execution order.

| Owner | Method | DEX signature |
|---|---|---|
| ChartSurface | getChartId | `()I` |
| ChartSurface | setChartId | `(I)V` |
| ChartSurface | onChartIdChanged | `(II)V` |
| ChartSurface | onAttachedToWindow | `()V` |
| ChartSurface | onDetachedFromWindow | `()V` |
| ChartSurface | onSurfaceTextureAvailable | `(Landroid/graphics/SurfaceTexture;II)V` |
| ChartSurface | onSurfaceTextureDestroyed | `(Landroid/graphics/SurfaceTexture;)Z` |
| ChartSurface | onSurfaceTextureSizeChanged | `(Landroid/graphics/SurfaceTexture;II)V` |
| ChartSurface | onSurfaceTextureUpdated | `(Landroid/graphics/SurfaceTexture;)V` |
| ChartSurface | onTerminalLoad | `()V` |
| ChartSurface | onTerminalUnload | `()V` |
| ChartsMdiGroup | onLayout | `(ZIIII)V` |
| ChartsMdiGroup | onMeasure | `(II)V` |
| ChartsMdiGroup | setOnChartViewCreatedListener | `(Lu23;)V` |
| ChartsMdiGroup | setSelectedChart | `(I)V` |

**Important:** `Lu23;` is an obfuscated listener type. Its method definition and actual callback invocation are not established here. `ChartSurface` is a `TextureView`; modifying or replacing its existing `SurfaceTextureListener` risks interfering with MT5's rendering. Use an independently hosted overlay only after observing actual runtime view hierarchy and coordinates.

## Build evidence

Repository CI run #140 completed successfully, but the dedicated Android SDK compile job has **not** been independently verified. Green Python/JS tests do not demonstrate that `BbmaOverlayView.kt` or `ModeMenuPanel.kt` compiles.

## Remaining falsification checks

1. Decode `Lu23;` callback method signatures and inspect actual `invoke-*` call sites using a complete DEX instruction decoder.
2. Confirm `ChartSurface` is instantiated and attached beneath `ChartsMdiGroup` at runtime.
3. Calibrate chart price/time-to-pixel transform, then test chart pan, zoom and rotation.
4. Verify Android compile workflow and capture job logs; repair confirmed errors only.
5. Do not claim modified APK or installability before build/sign/install evidence.
