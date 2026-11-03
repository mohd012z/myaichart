import mt.nativeaddon.*
fun main(){
 fun c(t:Long,o:Double,h:Double,l:Double,cl:Double)=Candle(t,o,h,l,cl)
 val candles=listOf(c(1000,10.0,10.3,9.8,10.1),c(1100,10.1,10.4,9.9,10.0),c(1200,10.0,10.2,9.8,10.1),c(1300,10.1,12.5,10.0,12.0))
 val zone=SupplyDemand.detect(candles).single()
 check(ZoneLifecycle.evaluate(zone,candles,1300).status==ZoneStatus.FRESH)
 check(ZoneLifecycle.evaluate(zone,candles+c(1400,12.0,12.2,10.1,11.0),1400).status==ZoneStatus.TESTED)
 check(ZoneLifecycle.evaluate(zone,candles+c(1400,12.0,12.2,9.0,9.5),1400).status==ZoneStatus.INVALIDATED)
 val v=ChartViewport(0f,0f,1000f,500f,1000,2000,8.0,14.0)
 check(ZoneProjection.rectangles(listOf(ZoneLifecycle.evaluate(zone,candles,1300)),v,1200).isEmpty())
 val rect=ZoneProjection.rectangles(listOf(ZoneLifecycle.evaluate(zone,candles,1300)),v,1300).single()
 check(rect.left>=0f&&rect.right<=1000f&&rect.top<rect.bottom)
 check(ZoneProjection.rectangles(listOf(ZoneLifecycle.evaluate(zone,candles,1300)),v.copy(minimumPrice=15.0,maximumPrice=20.0),1300).isEmpty())
 println("PASS: lifecycle, confirmation cutoff, viewport clipping")
}
