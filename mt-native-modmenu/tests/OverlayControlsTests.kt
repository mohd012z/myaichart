import mt.nativeaddon.*
fun main(){
 val initial=OverlaySettings()
 check(OverlayLayer.NEWS !in initial.enabled)
 val news=initial.toggle(OverlayLayer.NEWS)
 check(OverlayLayer.NEWS in news.enabled)
 check(news.toggle(OverlayLayer.NEWS)==initial)
 check(news.toggle(OverlayLayer.FIBONACCI).enabled.containsAll(setOf(OverlayLayer.NEWS,OverlayLayer.FIBONACCI)))
 val clamped=news.adjust(opacity=200,scalePercent=10,xFraction=-5f,yFraction=3f)
 check(clamped.opacity==100&&clamped.scalePercent==50&&clamped.xFraction==0f&&clamped.yFraction==1f)
 check(initial.enabled==setOf(OverlayLayer.BBMA_DASHBOARD))
 println("PASS: independent toggles, reset, bounds, defaults")
}
