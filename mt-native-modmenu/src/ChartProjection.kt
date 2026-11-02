package mt.nativeaddon
data class ChartViewport(val leftPx:Float,val topPx:Float,val widthPx:Float,val heightPx:Float,val firstTimeMs:Long,val lastTimeMs:Long,val minimumPrice:Double,val maximumPrice:Double){
 init{require(leftPx.isFinite()&&topPx.isFinite()&&widthPx.isFinite()&&heightPx.isFinite());require(widthPx>0f&&heightPx>0f&&firstTimeMs>=0&&lastTimeMs>firstTimeMs);require(minimumPrice.isFinite()&&maximumPrice.isFinite()&&maximumPrice>minimumPrice)}
}
data class ChartPoint(val x:Float,val y:Float)
object ChartProjection{
 fun project(v:ChartViewport,time:Long,price:Double):ChartPoint?{
  if(!price.isFinite()||time<v.firstTimeMs||time>v.lastTimeMs||price<v.minimumPrice||price>v.maximumPrice)return null
  val x=(time-v.firstTimeMs).toDouble()/(v.lastTimeMs-v.firstTimeMs).toDouble()
  val y=(v.maximumPrice-price)/(v.maximumPrice-v.minimumPrice)
  return ChartPoint((v.leftPx+v.widthPx*x).toFloat(),(v.topPx+v.heightPx*y).toFloat())
 }
}