package mt.nativeaddon

enum class OverlayLayer { NEWS, BBMA_DASHBOARD, FIBONACCI, BANDS, EMA50, LWMA, SUPPLY_DEMAND, TRENDLINES }
data class OverlaySettings(val enabled:Set<OverlayLayer> = setOf(OverlayLayer.BBMA_DASHBOARD), val opacity:Int=90, val scalePercent:Int=100, val xFraction:Float=0.05f, val yFraction:Float=0.10f) {
 init { require(opacity in 10..100 && scalePercent in 50..200 && xFraction in 0f..1f && yFraction in 0f..1f) }
 fun toggle(layer:OverlayLayer)=copy(enabled=if(layer in enabled)enabled-layer else enabled+layer)
 fun adjust(opacity:Int=this.opacity,scalePercent:Int=this.scalePercent,xFraction:Float=this.xFraction,yFraction:Float=this.yFraction)=copy(opacity=opacity.coerceIn(10,100),scalePercent=scalePercent.coerceIn(50,200),xFraction=xFraction.coerceIn(0f,1f),yFraction=yFraction.coerceIn(0f,1f))
}
