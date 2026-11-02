package mt.nativeaddon

/** Captures the complete supplied candle series, not hidden candles from an MT5 chart. */
data class CandleSnapshot(val symbol:String,val timeframe:String,val candles:List<Candle>,val firstTimeMs:Long,val lastTimeMs:Long)
object CandleCapture {
 fun snapshot(symbol:String,timeframe:String,candles:List<Candle>,limit:Int=100000):CandleSnapshot {
  val normalized=SymbolCatalog.normalize(symbol)?:error("Invalid symbol")
  require(timeframe.isNotBlank()&&timeframe.length<=16)
  require(candles.isNotEmpty()&&candles.size<=limit)
  // This validates ordering without assuming the MT5 renderer exposes OHLC history.
  val times=candles.map{it.time}
  require(times.zipWithNext().all{(a,b)->a<b}){"Candles must be strictly increasing"}
  return CandleSnapshot(normalized,timeframe,candles.toList(),times.first(),times.last())
 }
}
