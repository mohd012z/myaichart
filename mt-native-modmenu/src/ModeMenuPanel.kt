package mt.nativeaddon

import android.content.Context
import android.graphics.Color
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup
import android.view.ViewConfiguration
import android.widget.Button
import android.widget.CheckBox
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.SeekBar

/** Host-owned floating controls. Parent must be an independently verified chart ViewGroup. */
class ModeMenuPanel(context: Context, private val overlay: BbmaOverlayView, private val onScreenshotRequested: (() -> Unit)? = null): FrameLayout(context) {
 private val preferences=context.getSharedPreferences("mt_bbma_mode_menu",Context.MODE_PRIVATE)
 private var state=ModeMenuState(visible=preferences.getBoolean("expanded",false))
 private val density=resources.displayMetrics.density
 private fun dp(value:Int)=(value*density+0.5f).toInt()
 private val floating=LinearLayout(context).apply {
  orientation=LinearLayout.VERTICAL
  setBackgroundColor(Color.argb(240,20,25,35))
  elevation=dp(8).toFloat()
 }
 private val options=LinearLayout(context).apply {
  orientation=LinearLayout.VERTICAL
  setPadding(dp(12),dp(4),dp(12),dp(10))
 }
 private val optionScroll=ScrollView(context).apply { isFillViewport=false; addView(options) }
 private var overlaySettings=OverlaySettings(
  enabled=OverlayLayer.values().filter{preferences.getBoolean("layer_"+it.name,it==OverlayLayer.BBMA_DASHBOARD)}.toSet(),
  opacity=preferences.getInt("opacity",90).coerceIn(10,100),
  scalePercent=preferences.getInt("scale",100).coerceIn(50,200))
 private val layerChecks=mutableMapOf<OverlayLayer,CheckBox>()
 private var userMoved=false
 private var savedX=0f
 private var savedY=0f
 private var downRawX=0f
 private var downRawY=0f
 private var startX=0f
 private var startY=0f
 private var dragging=false
 private val touchSlop=ViewConfiguration.get(context).scaledTouchSlop
 private var restored=false
 private val header=Button(context).apply {
  text="☰ BBMA · Drag"
  setAllCaps(false)
  setOnTouchListener { _:View,event:MotionEvent ->
   when(event.actionMasked) {
    MotionEvent.ACTION_DOWN -> {
     downRawX=event.rawX;downRawY=event.rawY;startX=floating.x;startY=floating.y;dragging=false
     true
    }
    MotionEvent.ACTION_MOVE -> {
     val dx=event.rawX-downRawX;val dy=event.rawY-downRawY
     if(!dragging && (kotlin.math.abs(dx)>touchSlop||kotlin.math.abs(dy)>touchSlop))dragging=true
     if(dragging)moveTo(startX+dx,startY+dy)
     true
    }
    MotionEvent.ACTION_UP -> {
     if(dragging){userMoved=true;savePosition()} else performClick()
     dragging=false
     true
    }
    MotionEvent.ACTION_CANCEL -> {dragging=false;true}
    else -> false
   }
  }
  setOnClickListener { dispatch(ModeMenuReducer.Action.TOGGLE_MENU) }
 }
 init {
  clipChildren=false
  floating.addView(header,LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(48)))
  val definitions=listOf(
   "Enable BBMA" to ModeMenuReducer.Action.TOGGLE_OVERLAY,
   "Bollinger Bands" to ModeMenuReducer.Action.TOGGLE_BANDS,
   "EMA 50" to ModeMenuReducer.Action.TOGGLE_EMA50,
   "LWMA 5 High/Low" to ModeMenuReducer.Action.TOGGLE_LWMA5,
   "LWMA 10 High/Low" to ModeMenuReducer.Action.TOGGLE_LWMA10
  )
  definitions.forEach { (label,action) ->
   val cb=CheckBox(context).apply {
    text=label;setTextColor(Color.WHITE);minHeight=dp(44)
    setOnClickListener { dispatch(action) }
   }
   options.addView(cb,LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT))
  }
  OverlayLayer.values().forEach { layer ->
   val check=CheckBox(context).apply {
    text=layer.name.replace('_',' ').lowercase().replaceFirstChar{it.uppercase()}
    setTextColor(Color.WHITE);minHeight=dp(44)
    isChecked=layer in overlaySettings.enabled
    setOnClickListener {
     overlaySettings=overlaySettings.toggle(layer)
     preferences.edit().putBoolean("layer_"+layer.name,layer in overlaySettings.enabled).apply()
     updateOverlayAppearance()
    }
   }
   layerChecks[layer]=check
   options.addView(check,LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(48)))
  }
  fun addSlider(title:String,min:Int,max:Int,current:Int,onValue:(Int)->Unit){
   val label=android.widget.TextView(context).apply{text=title;setTextColor(Color.WHITE);setPadding(dp(8),dp(4),0,0)}
   options.addView(label)
   options.addView(SeekBar(context).apply{
    this.max=max-min;progress=current-min
    contentDescription=title
    setOnSeekBarChangeListener(object:SeekBar.OnSeekBarChangeListener{
     override fun onProgressChanged(seek:SeekBar?,progress:Int,fromUser:Boolean){if(fromUser)onValue(progress+min)}
     override fun onStartTrackingTouch(seek:SeekBar?){}
     override fun onStopTrackingTouch(seek:SeekBar?){}
    })
   },LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(48)))
  }
  addSlider("Overlay opacity",10,100,overlaySettings.opacity){
   overlaySettings=overlaySettings.adjust(opacity=it)
   preferences.edit().putInt("opacity",overlaySettings.opacity).apply()
   updateOverlayAppearance()
  }
  addSlider("Menu size",50,200,overlaySettings.scalePercent){
   overlaySettings=overlaySettings.adjust(scalePercent=it)
   preferences.edit().putInt("scale",overlaySettings.scalePercent).apply()
   floating.post{reposition()}
  }
  val screenshot=Button(context).apply {
   text="Screenshot · Review"
   setAllCaps(false)
   contentDescription="Request screenshot with consent"
   isEnabled=onScreenshotRequested!=null
   setOnClickListener { onScreenshotRequested?.invoke() }
  }
  options.addView(screenshot,LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(48)))
  val research=Button(context).apply {
   text="Fundamental · Global sources"
   setAllCaps(false)
   contentDescription="Open public central bank research sources"
   setOnClickListener {
    val uri=android.net.Uri.parse("https://www.bis.org/cbanks.htm")
    val intent=android.content.Intent(android.content.Intent.ACTION_VIEW,uri)
    try { context.startActivity(intent.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK)) }
    catch (_:android.content.ActivityNotFoundException) { isEnabled=false }
   }
  }
  options.addView(research,LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,dp(48)))
  floating.addView(optionScroll,LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,ViewGroup.LayoutParams.WRAP_CONTENT))
  addView(floating,LayoutParams(dp(240),ViewGroup.LayoutParams.WRAP_CONTENT,Gravity.TOP or Gravity.START))
  refresh()
  updateOverlayAppearance()
  addOnLayoutChangeListener { _,_,_,_,_,_,_,_,_ -> reposition() }
 }
 private fun updateOverlayAppearance(){
  floating.alpha=overlaySettings.opacity/100f
  layerChecks.forEach{(layer,check)->check.isChecked=layer in overlaySettings.enabled}
  // Non-BBMA layers require their own validated renderer; toggles only store visibility intent.
 }
 private fun moveTo(x:Float,y:Float) {
  val p=ResponsiveMenu.place(MenuBounds(width,height),MenuBounds(floating.width,floating.height),x,y)
  savedX=p.x;savedY=p.y;floating.x=p.x;floating.y=p.y
 }
 private fun savePosition(){
  val saved=ResponsiveMenu.save(MenuBounds(width,height),MenuGeometry(floating.x,floating.y,floating.width,floating.height),state.visible)
  preferences.edit().putFloat("x",saved.xFraction).putFloat("y",saved.yFraction).putBoolean("expanded",state.visible).apply()
 }
 private fun reposition(){
  if(width<=0||height<=0)return
  val desiredWidth=ResponsiveMenu.size(MenuBounds(width,height),dp(240)*overlaySettings.scalePercent/100,height,dp(8)).width
  val params=floating.layoutParams
  if(params.width!=desiredWidth){params.width=desiredWidth;floating.layoutParams=params;floating.post{reposition()};return}
  val maximumHeight=(height-dp(16)).coerceAtLeast(0)
  val availableOptionsHeight=(maximumHeight-dp(48)).coerceAtLeast(0)
  // Cap content to viewport; do not force short menus to cover the chart.
  optionScroll.measure(
   View.MeasureSpec.makeMeasureSpec(desiredWidth,View.MeasureSpec.EXACTLY),
   View.MeasureSpec.makeMeasureSpec(0,View.MeasureSpec.UNSPECIFIED))
  val naturalHeight=options.measuredHeight.coerceAtLeast(0)
  val targetHeight=if(state.visible) minOf(naturalHeight,availableOptionsHeight) else 0
  if(optionScroll.layoutParams.height!=targetHeight) optionScroll.layoutParams=optionScroll.layoutParams.apply{height=targetHeight}
  if(!restored){
   restored=true
   val saved=MenuSavedState(preferences.getFloat("x",1f),preferences.getFloat("y",0f),state.visible)
   val p=ResponsiveMenu.restore(MenuBounds(width,height),MenuBounds(floating.width,floating.height),saved)
   moveTo(p.x,p.y)
  } else moveTo(savedX,savedY)
 }
 private fun dispatch(action:ModeMenuReducer.Action){
  state=ModeMenuReducer.apply(state,action);refresh()
  preferences.edit().putBoolean("expanded",state.visible).apply()
  floating.post { reposition() }
 }
 private fun refresh(){
  optionScroll.visibility=if(state.visible) VISIBLE else GONE
  header.contentDescription=if(state.visible)"BBMA options expanded. Drag to move" else "BBMA options collapsed. Drag to move"
  val selected=buildSet {
   if(state.enabled){
    if(state.showBands){add(BbmaOverlayView.Line.BB_UPPER);add(BbmaOverlayView.Line.BB_MIDDLE);add(BbmaOverlayView.Line.BB_LOWER)}
    if(state.showEma50)add(BbmaOverlayView.Line.EMA50)
    if(state.showLwma5){add(BbmaOverlayView.Line.LWMA5_HIGH);add(BbmaOverlayView.Line.LWMA5_LOW)}
    if(state.showLwma10){add(BbmaOverlayView.Line.LWMA10_HIGH);add(BbmaOverlayView.Line.LWMA10_LOW)}
   }
  }
  overlay.setVisibleLines(selected)
  listOf(state.enabled,state.showBands,state.showEma50,state.showLwma5,state.showLwma10).forEachIndexed { index,value -> (options.getChildAt(index) as CheckBox).isChecked=value }
 }
}
