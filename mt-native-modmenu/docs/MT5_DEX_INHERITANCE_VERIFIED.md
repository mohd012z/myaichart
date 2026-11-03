# MT5 build 500.6260 DEX class-definition audit

Read-only inspection of user-supplied APK `MetaTrader 5_500.6260.apk` and its `classes.dex` using the DEX header string_ids/type_ids/class_defs tables. APK binaries are not committed.

DEX size: 7,766,512 bytes. Class definitions: 8,616. Type IDs: 10,530.

| DEX class descriptor | superclass (from class_def_item.superclass_idx) |
|---|---|
| Lnet/metaquotes/metatrader5/ui/charts/ChartSurface; | Landroid/view/TextureView; |
| Lnet/metaquotes/metatrader5/terminal/ChartRenderer; | Ljava/lang/Object; |
| Lnet/metaquotes/metatrader5/ui/charts/ChartsMdiGroup; | Landroid/view/ViewGroup; |
| Lnet/metaquotes/metatrader5/ui/charts/ChartsFragment; | Lcn; |

**Correction:** The verified `ChartSurface` superclass is `TextureView`, not `SurfaceView`. A separate `SurfaceView` type reference in DEX does not imply chart rendering uses it.

**Not yet verified:** view IDs, chart hierarchy, TextureView surface lifecycle, chart coordinate transforms, chart history feed, host instrumentation, Android SDK compilation, APK packaging and installability.

**Safe next experiment:** instrument a test-only, authorized Android environment to inspect the actual chart parent and texture bounds. Require validated viewport snapshots before drawing; never assume that the DEX class name alone is a safe injection target.
