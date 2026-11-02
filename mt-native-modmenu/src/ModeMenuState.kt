package mt.nativeaddon
data class ModeMenuState(val visible:Boolean=false,val enabled:Boolean=true,val showBands:Boolean=true,val showEma50:Boolean=true,val showLwma5:Boolean=true,val showLwma10:Boolean=true,val closedOnly:Boolean=true)
object ModeMenuReducer {
 enum class Action { TOGGLE_MENU,TOGGLE_OVERLAY,TOGGLE_BANDS,TOGGLE_EMA50,TOGGLE_LWMA5,TOGGLE_LWMA10 }
 fun apply(s:ModeMenuState,a:Action):ModeMenuState=when(a){
 Action.TOGGLE_MENU->s.copy(visible=!s.visible)
 Action.TOGGLE_OVERLAY->s.copy(enabled=!s.enabled)
 Action.TOGGLE_BANDS->s.copy(showBands=!s.showBands)
 Action.TOGGLE_EMA50->s.copy(showEma50=!s.showEma50)
 Action.TOGGLE_LWMA5->s.copy(showLwma5=!s.showLwma5)
 Action.TOGGLE_LWMA10->s.copy(showLwma10=!s.showLwma10)
 }
}