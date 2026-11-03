import mt.nativeaddon.*
fun main(){
 fun c(t:Long,o:Double,h:Double,l:Double,cl:Double)=Candle(t,o,h,l,cl)
 val candles=listOf(c(1000,10.0,10.3,9.8,10.1),c(1100,10.1,10.4,9.9,10.0),c(1200,10.0,10.2,9.8,10.1),c(1300,10.1,12.5,10.0,12.0))
 val key=ZoneKey("EURUSD","M15")
 val results=MultiTimeframeZones.analyze(mapOf(key to candles),1300)
 check(results[key]?.size==1)
 val cache=ZoneCache()
 cache.put(ZoneSnapshot(key,1300,results.getValue(key)))
 check(cache.get(key,1300)!=null)
 check(cache.get(key,1400)==null)
 cache.invalidate(key)
 check(cache.get(key,1300)==null)
 try {MultiTimeframeZones.analyze(mapOf(key to candles),1200);throw AssertionError("Expected future-candle rejection")}catch(_:IllegalArgumentException){}
 println("PASS: timeframe isolation, cache invalidation, future-candle rejection")
}
