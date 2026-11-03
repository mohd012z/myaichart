package mt.nativeaddon
import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.view.View

/** Research-only BBMA curves; attach only to a verified chart host. */
class BbmaOverlayView(context:Context):View(context) {
 enum class Line { BB_UPPER,BB_MIDDLE,BB_LOWER,EMA50,LWMA5_HIGH,LWMA5_LOW,LWMA10_HIGH,LWMA10_LOW }
 private var viewport:ChartViewport?=null
 private var points:List<BbmaPoint> = emptyList()
 private var enabled:Set<Line> = Line.entries.toSet()
 private val paint=Paint(Paint.ANTI_ALIAS_FLAG).apply{style=Paint.Style.STROKE;strokeWidth=2.5f}
 init { isClickable=false;isFocusable=false }
 fun setViewport(value:ChartViewport?){viewport=value;invalidate()}
 fun setCandles(closedCandles:List<Candle>){
  require(closedCandles.size<=20000)
  points=Indicators.bbma(closedCandles);invalidate()
 }
 fun setVisibleLines(lines:Set<Line>){enabled=lines.toSet();invalidate()}
 override fun onDraw(canvas:Canvas){
  super.onDraw(canvas)
  val v=viewport?:return
  val save=canvas.save()
  canvas.clipRect(v.leftPx,v.topPx,v.leftPx+v.widthPx,v.topPx+v.heightPx)
  for(line in enabled){
   paint.color=when(line){
    Line.BB_UPPER,Line.BB_LOWER->Color.rgb(59,130,246)
    Line.BB_MIDDLE->Color.rgb(148,163,184)
    Line.EMA50->Color.rgb(250,204,21)
    Line.LWMA5_HIGH,Line.LWMA5_LOW->Color.rgb(34,197,94)
    Line.LWMA10_HIGH,Line.LWMA10_LOW->Color.rgb(239,68,68)
   }
   val path=Path()
   var started=false
   for(p in points){
    val price=when(line){
     Line.BB_UPPER->p.bands?.upper
     Line.BB_MIDDLE->p.bands?.middle
     Line.BB_LOWER->p.bands?.lower
     Line.EMA50->p.ema50
     Line.LWMA5_HIGH->p.lwma5High
     Line.LWMA5_LOW->p.lwma5Low
     Line.LWMA10_HIGH->p.lwma10High
     Line.LWMA10_LOW->p.lwma10Low
    }
    val xy=price?.let{ChartProjection.project(v,p.timeMillis,it)}
    if(xy==null){started=false;continue}
    if(!started){path.moveTo(xy.x,xy.y);started=true}else path.lineTo(xy.x,xy.y)
   }
   canvas.drawPath(path,paint)
  }
  canvas.restoreToCount(save)
 }
}