package mt.nativeaddon

data class ZoneKey(val symbol:String,val timeframe:String)
data class ZoneSnapshot(val key:ZoneKey,val lastClosedAtMs:Long,val zones:List<EvaluatedZone>)
class ZoneCache {
 private val entries=mutableMapOf<ZoneKey,ZoneSnapshot>()
 fun get(key:ZoneKey,lastClosedAtMs:Long):ZoneSnapshot?=entries[key]?.takeIf{it.lastClosedAtMs==lastClosedAtMs}
 fun put(snapshot:ZoneSnapshot){require(snapshot.key.symbol.isNotBlank()&&snapshot.key.timeframe.isNotBlank());entries[snapshot.key]=snapshot.copy(zones=snapshot.zones.toList())}
 fun invalidate(key:ZoneKey){entries.remove(key)}
 fun clear(){entries.clear()}
}
object MultiTimeframeZones {
 /** Input consists of completed candles only; each timeframe is analyzed independently. */
 fun analyze(closedByTimeframe:Map<ZoneKey,List<Candle>>,asOfMs:Long,config:ZoneConfig=ZoneConfig()):Map<ZoneKey,List<EvaluatedZone>> {
  return closedByTimeframe.mapValues{(_,candles)->
   require(candles.all{it.timeMillis<=asOfMs}){"Future or unfinished candles must be excluded"}
   SupplyDemand.detect(candles,config).map{zone->
    val result=ZoneLifecycle.evaluate(zone,candles,asOfMs)
    result.copy(pattern=ZoneLifecycle.classify(zone,candles))
   }
  }
 }
}
