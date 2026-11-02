import mt.nativeaddon.*
fun main(){
 fun c(t:Long,o:Double,h:Double,l:Double,cl:Double)=Candle(t,o,h,l,cl)
 val m=60000L
 val candles=listOf(c(0,10.0,10.3,9.8,10.1),c(m,10.1,10.4,9.9,10.0),c(2*m,10.0,10.2,9.8,10.1),c(3*m,10.1,12.5,10.0,12.0))
 check(ClosedBarAlignment.filter(candles,ZoneTimeframe.M1,3*m).size==3)
 check(ClosedBarAlignment.filter(candles,ZoneTimeframe.M1,4*m).size==4)
 val key=ZoneKey("EURUSD","M1")
 check(AlignedMultiTimeframeZones.analyze(mapOf(key to (ZoneTimeframe.M1 to candles)),3*m).getValue(key).isEmpty())
 check(AlignedMultiTimeframeZones.analyze(mapOf(key to (ZoneTimeframe.M1 to candles)),4*m).getValue(key).size==1)
 val h1=ZoneKey("EURUSD","H1")
 check(AlignedMultiTimeframeZones.analyze(mapOf(h1 to (ZoneTimeframe.H1 to candles)),4*m).getValue(h1).isEmpty())
 try {
  AlignedMultiTimeframeZones.analyze(mapOf(ZoneKey("EURUSD","H1") to (ZoneTimeframe.M1 to candles)),4*m)
  error("Expected timeframe-key mismatch rejection")
 } catch(_:IllegalArgumentException) {}
 println("PASS: open-time semantics, strict bar closure, cross-timeframe alignment, no-lookahead")
}
