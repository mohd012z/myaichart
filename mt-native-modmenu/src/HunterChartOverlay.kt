package mt.nativeaddon
import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.view.View
/** Research-only chart overlay. Must attach to a verified MT5 chart host. */
class HunterChartOverlay(context:Context):View(context){
 data class Marker(val timestampMs:Long,val price:Double,val label:String,val bullish:Boolean)
 private val paint=Paint(Paint.ANTI_ALIAS_FLAG).apply{textSize=28f;strokeWidth=2f}
 private var viewport:ChartViewport?=null
 private var markers:List<Marker> = emptyList()
 fun updateViewport(value:ChartViewport?){viewport=value;invalidate()}
 fun updateMarkers(value:List<Marker>){markers=value.takeLast(200).filter{it.label.length in 1..32&&it.price.isFinite()};invalidate()}
 override fun onDraw(canvas:Canvas){
  super.onDraw(canvas)
  val v=viewport?:return
  for(m in markers){
   val p=ChartProjection.project(v,m.timestampMs,m.price)?:continue
   paint.color=if(m.bullish)Color.rgb(34,197,94) else Color.rgb(239,68,68)
   canvas.drawCircle(p.x,p.y,6f,paint)
   canvas.drawText(m.label,p.x+8f,p.y-8f,paint)
  }
 }
}