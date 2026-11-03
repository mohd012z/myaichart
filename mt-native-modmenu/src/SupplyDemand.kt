package mt.nativeaddon

enum class ZoneKind { DEMAND, SUPPLY }
data class PriceZone(val kind:ZoneKind,val low:Double,val high:Double,val formedAtMs:Long,val confirmedAtMs:Long,val impulseIndex:Int,val baseStartIndex:Int,val baseEndIndex:Int)
data class ZoneConfig(val baseBars:Int=3,val impulseMultiplier:Double=1.5,val minImpulseBody:Double=0.0) {
 init { require(baseBars in 1..10 && impulseMultiplier>0 && impulseMultiplier.isFinite() && minImpulseBody>=0 && minImpulseBody.isFinite()) }
}
object SupplyDemand {
 /** Closed candles only; base + impulse confirmation. No lookahead beyond confirmation bar. */
 fun detect(candles:List<Candle>,config:ZoneConfig=ZoneConfig()):List<PriceZone> {
  if(candles.size<=config.baseBars)return emptyList()
  require(candles.zipWithNext().all{(a,b)->a.timeMillis<b.timeMillis})
  val out=mutableListOf<PriceZone>()
  for(i in config.baseBars until candles.size){
   val base=candles.subList(i-config.baseBars,i)
   val impulse=candles[i]
   val meanBody=base.map{kotlin.math.abs(it.close-it.open)}.average()
   val body=kotlin.math.abs(impulse.close-impulse.open)
   val threshold=maxOf(config.minImpulseBody,meanBody*config.impulseMultiplier)
   if(body<=threshold||body==0.0)continue
   val low=base.minOf{it.low}
   val high=base.maxOf{it.high}
   val kind=when{
    impulse.close>impulse.open && impulse.close>high->ZoneKind.DEMAND
    impulse.close<impulse.open && impulse.close<low->ZoneKind.SUPPLY
    else->null
   }?:continue
   out.add(PriceZone(kind,low,high,base.first().timeMillis,impulse.timeMillis,i,i-config.baseBars,i-1))
  }
  return out
 }
 fun unmitigated(zones:List<PriceZone>,candles:List<Candle>):List<PriceZone> =
  zones.filter{z->candles.none{it.timeMillis>z.confirmedAtMs && it.low<=z.high && it.high>=z.low}}
}
