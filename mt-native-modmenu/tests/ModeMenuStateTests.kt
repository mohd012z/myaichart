import mt.nativeaddon.*
fun main(){
 val s=ModeMenuState()
 check(!s.visible && s.closedOnly && s.enabled)
 val a=ModeMenuReducer.apply(s,ModeMenuReducer.Action.TOGGLE_MENU)
 check(a.visible && !s.visible)
 val b=ModeMenuReducer.apply(a,ModeMenuReducer.Action.TOGGLE_BANDS)
 check(!b.showBands && b.showEma50)
 check(ModeMenuReducer.apply(b,ModeMenuReducer.Action.TOGGLE_BANDS).showBands)
 val c=ModeMenuReducer.apply(b,ModeMenuReducer.Action.TOGGLE_OVERLAY)
 check(!c.enabled && c.closedOnly)
 println("PASS: ModeMenu immutable reducer tests")
}