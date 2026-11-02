package mt.nativeaddon

data class ZoneRectangle(val left:Float,val top:Float,val right:Float,val bottom:Float,val kind:ZoneKind,val status:ZoneStatus)
object ZoneProjection {
 /** Clips confirmed zones to a calibrated viewport; does not guess future price/time coordinates. */
 fun rectangles(zones:List<EvaluatedZone>,v:ChartViewport,asOfMs:Long):List<ZoneRectangle> {
  val visibleEnd=minOf(asOfMs,v.lastTimeMs)
  if(visibleEnd<v.firstTimeMs)return emptyList()
  return zones.mapNotNull{z->
   if(z.zone.confirmedAtMs>asOfMs||z.zone.formedAtMs>visibleEnd)return@mapNotNull null
   val leftTime=maxOf(z.zone.formedAtMs,v.firstTimeMs)
   val low=maxOf(z.zone.low,v.minimumPrice)
   val high=minOf(z.zone.high,v.maximumPrice)
   if(low>=high)return@mapNotNull null
   val top=ChartProjection.project(v,leftTime,high)?:return@mapNotNull null
   val bottom=ChartProjection.project(v,visibleEnd,low)?:return@mapNotNull null
   ZoneRectangle(top.x,top.y,bottom.x,bottom.y,z.zone.kind,z.status)
  }
 }
}
