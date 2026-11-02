package mt.nativeaddon

/** Explicit timeframe duration; all timestamps in UTC milliseconds. */
enum class ZoneTimeframe(val durationMs:Long) {
 M1(60000),M5(300000),M15(900000),M30(1800000),H1(3600000),H4(14400000),D1(86400000)
}
data class TimedCandle(val openTimeMs:Long,val candle:Candle)
object ClosedBarAlignment {
 /** Candle.timeMillis denotes OPEN time. A bar is usable only when its entire duration has elapsed. */
 fun filter(candles:List<Candle>,timeframe:ZoneTimeframe,asOfMs:Long):List<Candle> {
  require(asOfMs>=0)
  require(candles.zipWithNext().all{(a,b)->a.timeMillis<b.timeMillis}){"Candles must be ordered and unique"}
  return candles.filter { it.timeMillis<=asOfMs && timeframe.durationMs<=asOfMs-it.timeMillis }
 }
}
object AlignedMultiTimeframeZones {
 fun analyze(series:Map<ZoneKey,Pair<ZoneTimeframe,List<Candle>>>,asOfMs:Long,config:ZoneConfig=ZoneConfig()):Map<ZoneKey,List<EvaluatedZone>> {
  val aligned=series.mapValues{(_,pair)->ClosedBarAlignment.filter(pair.second,pair.first,asOfMs)}
  return MultiTimeframeZones.analyze(aligned,asOfMs,config)
 }
}
