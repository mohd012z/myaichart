import mt.nativeaddon.*
fun main(){
 fun c(t:Long,o:Double,h:Double,l:Double,cl:Double)=Candle(t,o,h,l,cl)
 val m=60000L
 val candles=listOf(c(0,10.0,10.3,9.8,10.1),c(m,10.1,10.4,9.9,10.0),c(2*m,10.0,10.2,9.8,10.1),c(3*m,10.1,12.5,10.0,12.0))
 val key=ZoneKey("EURUSD","M1")
 val selection=ZoneSelection("EURUSD",ZoneTimeframe.M1,1)
 val viewport=ChartViewport(0f,0f,800f,500f,0,5*m,8.0,14.0)
 val series=mapOf(key to (ZoneTimeframe.M1 to candles))
 check(ZoneResearchPipeline.render(selection,series,3*m,viewport).isEmpty())
 check(ZoneResearchPipeline.render(selection,series,4*m,viewport).size==1)
 check(ZoneResearchPipeline.render(selection.copy(symbol="GBPUSD"),series,4*m,viewport).isEmpty())
 try {ZoneResearchPipeline.render(selection,mapOf(key to (ZoneTimeframe.H1 to candles)),4*m,viewport);throw AssertionError("Expected mismatch")}catch(_:IllegalArgumentException){}
 println("PASS: closed bar cutoff, selected symbol, bounded zones, timeframe mismatch")
}
