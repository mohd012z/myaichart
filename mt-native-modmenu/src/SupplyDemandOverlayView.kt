package mt.nativeaddon

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.view.View

/** Independent chart overlay view; requires a verified host and viewport. */
class SupplyDemandOverlayView(context:Context):View(context) {
 private var zones:List<ZoneRectangle> = emptyList()
 private var enabled=true
 private var opacity=60
 fun update(zones:List<ZoneRectangle>){this.zones=zones.toList();invalidate()}
 fun setZoneVisible(value:Boolean){enabled=value;invalidate()}
 fun setZoneOpacity(percent:Int){opacity=percent.coerceIn(10,100);invalidate()}
 private val fill=Paint(Paint.ANTI_ALIAS_FLAG).apply{style=Paint.Style.FILL}
 private val stroke=Paint(Paint.ANTI_ALIAS_FLAG).apply{style=Paint.Style.STROKE;strokeWidth=2f}
 override fun onDraw(canvas:Canvas){
  super.onDraw(canvas)
  if(!enabled)return
  for(zone in zones){
   val rgb=if(zone.kind==ZoneKind.DEMAND)0x28A56C else 0xCF4C56
   val alpha=(255*opacity/100f).toInt().coerceIn(0,255)
   fill.color=android.graphics.Color.argb(alpha/3,(rgb shr 16)and 255,(rgb shr 8)and 255,rgb and 255)
   stroke.color=android.graphics.Color.argb(alpha,(rgb shr 16)and 255,(rgb shr 8)and 255,rgb and 255)
   if(zone.status==ZoneStatus.INVALIDATED)continue
   canvas.drawRect(zone.left,zone.top,zone.right,zone.bottom,fill)
   canvas.drawRect(zone.left,zone.top,zone.right,zone.bottom,stroke)
  }
 }
}
