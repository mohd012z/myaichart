package mt.nativeaddon

/** Pure research pipeline. The host must supply authenticated, timestamped candles and a calibrated viewport. */
object ZoneResearchPipeline {
 fun render(
  selection:ZoneSelection,
  series:Map<ZoneKey,Pair<ZoneTimeframe,List<Candle>>>,
  asOfMs:Long,
  viewport:ChartViewport,
  config:ZoneConfig=ZoneConfig()
 ):List<ZoneRectangle> {
  val key=ZoneKey(selection.symbol,selection.timeframe.name)
  val input=series[key] ?: return emptyList()
  require(input.first==selection.timeframe){"Timeframe mismatch"}
  val evaluated=AlignedMultiTimeframeZones.analyze(mapOf(key to input),asOfMs,config).getValue(key)
  return ZoneProjection.rectangles(ZoneSelectionPolicy.visible(evaluated,selection),viewport,asOfMs)
 }
}
