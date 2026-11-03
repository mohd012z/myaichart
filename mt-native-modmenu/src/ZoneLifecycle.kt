package mt.nativeaddon

enum class ZoneStatus { FRESH, TESTED, INVALIDATED }
enum class ZonePattern { RBR, DBD, RBD, DBR, UNKNOWN }
data class EvaluatedZone(val zone:PriceZone,val status:ZoneStatus,val touches:Int,val pattern:ZonePattern)
object ZoneLifecycle {
 fun evaluate(zone:PriceZone,candles:List<Candle>,asOfMs:Long):EvaluatedZone {
  require(asOfMs>=zone.confirmedAtMs)
  require(candles.zipWithNext().all{(a,b)->a.timeMillis<b.timeMillis})
  var touches=0;var invalidated=false;var wasInside=false
  for(c in candles) {
   if(c.timeMillis<=zone.confirmedAtMs||c.timeMillis>asOfMs)continue
   val inside=c.low<=zone.high&&c.high>=zone.low
   if(inside&&!wasInside)touches++
   wasInside=inside
   if(zone.kind==ZoneKind.DEMAND&&c.close<zone.low)invalidated=true
   if(zone.kind==ZoneKind.SUPPLY&&c.close>zone.high)invalidated=true
  }
  val status=when{invalidated->ZoneStatus.INVALIDATED;touches>0->ZoneStatus.TESTED;else->ZoneStatus.FRESH}
  return EvaluatedZone(zone,status,touches,ZonePattern.UNKNOWN)
 }
 fun classify(zone:PriceZone,candles:List<Candle>):ZonePattern {
  if(zone.baseStartIndex<=0||zone.impulseIndex !in candles.indices)return ZonePattern.UNKNOWN
  val prior=candles[zone.baseStartIndex-1]
  val priorUp=prior.close>prior.open
  return when {
   priorUp&&zone.kind==ZoneKind.DEMAND->ZonePattern.RBR
   !priorUp&&zone.kind==ZoneKind.SUPPLY->ZonePattern.DBD
   priorUp&&zone.kind==ZoneKind.SUPPLY->ZonePattern.RBD
   else->ZonePattern.DBR
  }
 }
}
