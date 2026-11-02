package mt.nativeaddon

/** Host-independent guard; does not attach to MetaTrader's private views. */
data class ChartSession(val chartId:Int,val generation:Long,val attached:Boolean,val textureAvailable:Boolean,val width:Int,val height:Int,val viewportCalibrated:Boolean) {
 val mayDraw:Boolean get()=chartId>=0&&attached&&textureAvailable&&width>0&&height>0&&viewportCalibrated
}
sealed class ChartSessionEvent {
 data class Bind(val chartId:Int):ChartSessionEvent()
 data class TextureAvailable(val width:Int,val height:Int):ChartSessionEvent()
 data class Resize(val width:Int,val height:Int):ChartSessionEvent()
 data object Calibrated:ChartSessionEvent()
 data object TextureDestroyed:ChartSessionEvent()
 data object Detached:ChartSessionEvent()
}
object ChartSessionReducer {
 fun apply(s:ChartSession,event:ChartSessionEvent):ChartSession=when(event){
  is ChartSessionEvent.Bind->{require(event.chartId>=0);ChartSession(event.chartId,s.generation+1,true,false,0,0,false)}
  is ChartSessionEvent.TextureAvailable->{require(event.width>0&&event.height>0);s.copy(textureAvailable=s.attached,width=event.width,height=event.height,viewportCalibrated=false,generation=s.generation+1)}
  is ChartSessionEvent.Resize->{require(event.width>0&&event.height>0);s.copy(width=event.width,height=event.height,viewportCalibrated=false,generation=s.generation+1)}
  ChartSessionEvent.Calibrated->s.copy(viewportCalibrated=s.attached&&s.textureAvailable)
  ChartSessionEvent.TextureDestroyed->s.copy(textureAvailable=false,viewportCalibrated=false,width=0,height=0,generation=s.generation+1)
  ChartSessionEvent.Detached->s.copy(attached=false,textureAvailable=false,viewportCalibrated=false,width=0,height=0,generation=s.generation+1)
 }
}