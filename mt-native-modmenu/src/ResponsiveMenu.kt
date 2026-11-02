package mt.nativeaddon

import kotlin.math.max
import kotlin.math.min

/** Density-independent, host-relative menu geometry. No Android dependency. */
data class MenuBounds(val width:Int,val height:Int)
data class MenuGeometry(val x:Float,val y:Float,val width:Int,val height:Int)
data class MenuSavedState(val xFraction:Float,val yFraction:Float,val expanded:Boolean)
object ResponsiveMenu {
 fun size(host:MenuBounds, preferredWidth:Int, preferredHeight:Int, margin:Int):MenuBounds {
  require(host.width>=0&&host.height>=0&&preferredWidth>=0&&preferredHeight>=0&&margin>=0)
  return MenuBounds(min(preferredWidth,max(0,host.width-2*margin)),min(preferredHeight,max(0,host.height-2*margin)))
 }
 fun place(host:MenuBounds,menu:MenuBounds,x:Float,y:Float):MenuGeometry {
  require(host.width>=0&&host.height>=0&&menu.width>=0&&menu.height>=0)
  val w=min(host.width,menu.width);val h=min(host.height,menu.height)
  return MenuGeometry((if(x.isFinite()) x else 0f).coerceIn(0f,(host.width-w).toFloat()),(if(y.isFinite()) y else 0f).coerceIn(0f,(host.height-h).toFloat()),w,h)
 }
 fun save(host:MenuBounds,menu:MenuGeometry,expanded:Boolean):MenuSavedState {
  val xDen=max(1,host.width-menu.width).toFloat();val yDen=max(1,host.height-menu.height).toFloat()
  return MenuSavedState((menu.x/xDen).coerceIn(0f,1f),(menu.y/yDen).coerceIn(0f,1f),expanded)
 }
 fun restore(host:MenuBounds,menu:MenuBounds,saved:MenuSavedState):MenuGeometry {
  val x=(host.width-menu.width).coerceAtLeast(0)*(if(saved.xFraction.isFinite())saved.xFraction.coerceIn(0f,1f) else 0f)
  val y=(host.height-menu.height).coerceAtLeast(0)*(if(saved.yFraction.isFinite())saved.yFraction.coerceIn(0f,1f) else 0f)
  return place(host,menu,x,y)
 }
 fun snap(host:MenuBounds,menu:MenuGeometry):MenuGeometry {
  val right=(host.width-menu.width).coerceAtLeast(0).toFloat()
  return place(host,MenuBounds(menu.width,menu.height),if(menu.x<=right/2)0f else right,menu.y)
 }
}
