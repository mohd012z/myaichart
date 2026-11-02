package mt.nativeaddon

import kotlin.math.max
import kotlin.math.min

data class MenuPosition(val x: Float, val y: Float)
object MenuPlacement {
 fun clamp(x: Float, y: Float, menuWidth: Int, menuHeight: Int, hostWidth: Int, hostHeight: Int): MenuPosition {
  require(menuWidth >= 0 && menuHeight >= 0 && hostWidth >= 0 && hostHeight >= 0)
  val maxX=max(0,hostWidth-menuWidth).toFloat()
  val maxY=max(0,hostHeight-menuHeight).toFloat()
  return MenuPosition(if(x.isFinite()) min(max(0f,x),maxX) else 0f,if(y.isFinite()) min(max(0f,y),maxY) else 0f)
 }
 fun default(menuWidth:Int,menuHeight:Int,hostWidth:Int,hostHeight:Int,margin:Int):MenuPosition =
  clamp((hostWidth-menuWidth-margin).toFloat(),margin.toFloat(),menuWidth,menuHeight,hostWidth,hostHeight)
}
