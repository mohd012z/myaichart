package mt.nativeaddon
import android.content.Context
import android.graphics.Color
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.CheckBox
import android.widget.FrameLayout
import android.widget.LinearLayout
/** Host-owned panel; attach only after validating chart host. */
class ModeMenuPanel(context:Context,private val overlay:BbmaOverlayView):FrameLayout(context){
 private var state=ModeMenuState()
 private val panel=LinearLayout(context).apply{
  orientation=LinearLayout.VERTICAL
  setBackgroundColor(Color.argb(235,20,25,35))
  setPadding(16,12,16,12)
 }
 init{
  val toggle=Button(context).apply{text="BBMA";setOnClickListener{dispatch(ModeMenuReducer.Action.TOGGLE_MENU)}}
  addView(toggle,LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,ViewGroup.LayoutParams.WRAP_CONTENT,Gravity.TOP or Gravity.END))
  val options=listOf(
   "Enable BBMA" to ModeMenuReducer.Action.TOGGLE_OVERLAY,
   "Bollinger Bands" to ModeMenuReducer.Action.TOGGLE_BANDS,
   "EMA 50" to ModeMenuReducer.Action.TOGGLE_EMA50,
   "LWMA 5 High/Low" to ModeMenuReducer.Action.TOGGLE_LWMA5,
   "LWMA 10 High/Low" to ModeMenuReducer.Action.TOGGLE_LWMA10
  )
  options.forEach{(label,action)->
   val cb=CheckBox(context).apply{text=label;setTextColor(Color.WHITE);setOnClickListener{dispatch(action)}}
   panel.addView(cb)
  }
  addView(panel,LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT,ViewGroup.LayoutParams.WRAP_CONTENT,Gravity.TOP or Gravity.START))
  refresh()
 }
 private fun dispatch(a:ModeMenuReducer.Action){state=ModeMenuReducer.apply(state,a);refresh()}
 private fun refresh(){
  panel.visibility=if(state.visible) VISIBLE else GONE
  val selected=buildSet{
   if(state.enabled){
    if(state.showBands){add(BbmaOverlayView.Line.BB_UPPER);add(BbmaOverlayView.Line.BB_MIDDLE);add(BbmaOverlayView.Line.BB_LOWER)}
    if(state.showEma50)add(BbmaOverlayView.Line.EMA50)
    if(state.showLwma5){add(BbmaOverlayView.Line.LWMA5_HIGH);add(BbmaOverlayView.Line.LWMA5_LOW)}
    if(state.showLwma10){add(BbmaOverlayView.Line.LWMA10_HIGH);add(BbmaOverlayView.Line.LWMA10_LOW)}
   }
  }
  overlay.setVisibleLines(selected)
  listOf(state.enabled,state.showBands,state.showEma50,state.showLwma5,state.showLwma10).forEachIndexed{index,value->(panel.getChildAt(index) as CheckBox).isChecked=value}
 }
}