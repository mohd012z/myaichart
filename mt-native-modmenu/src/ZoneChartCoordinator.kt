package mt.nativeaddon

/**
 * Read-only host adapter for a separately owned chart ViewGroup.
 * Call on the Android UI thread after the host provides calibrated viewport and timestamped candles.
 * No MT5 process access, order placement, or untrusted screen scraping.
 */
class ZoneChartCoordinator(private val overlay:SupplyDemandOverlayView) {
 private var current:ZoneSelection?=null
 private var revision:Long=0
 private var lastRenderedClose:Long=-1
 fun select(selection:ZoneSelection):Long {
  check(android.os.Looper.myLooper()==android.os.Looper.getMainLooper()){"UI thread required"}
  current=selection
  revision++
  lastRenderedClose=-1
  overlay.update(emptyList())
  return revision
 }
 fun submit(
  requestRevision:Long,
  selection:ZoneSelection,
  candles:List<Candle>,
  viewport:ChartViewport,
  asOfMs:Long
 ):Boolean {
  check(android.os.Looper.myLooper()==android.os.Looper.getMainLooper()){"UI thread required"}
  if(requestRevision!=revision||selection!=current)return false
  val closed=ClosedBarAlignment.filter(candles,selection.timeframe,asOfMs)
  val latest=closed.lastOrNull()?.timeMillis?:-1
  if(latest<lastRenderedClose)return false
  val key=ZoneKey(selection.symbol,selection.timeframe.name)
  val rectangles=ZoneResearchPipeline.render(selection,mapOf(key to (selection.timeframe to candles)),asOfMs,viewport)
  if(requestRevision!=revision)return false
  lastRenderedClose=latest
  overlay.update(rectangles)
  return true
 }
 fun clear(){
  check(android.os.Looper.myLooper()==android.os.Looper.getMainLooper()){"UI thread required"}
  revision++
  current=null
  lastRenderedClose=-1
  overlay.update(emptyList())
 }
}
