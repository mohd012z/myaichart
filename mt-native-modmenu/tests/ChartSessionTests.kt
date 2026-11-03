import mt.nativeaddon.*
fun main(){
 var s=ChartSession(-1,0,false,false,0,0,false)
 check(!s.mayDraw)
 s=ChartSessionReducer.apply(s,ChartSessionEvent.Bind(42))
 s=ChartSessionReducer.apply(s,ChartSessionEvent.TextureAvailable(1080,720))
 check(!s.mayDraw)
 s=ChartSessionReducer.apply(s,ChartSessionEvent.Calibrated);check(s.mayDraw)
 s=ChartSessionReducer.apply(s,ChartSessionEvent.Resize(720,1080));check(!s.mayDraw)
 s=ChartSessionReducer.apply(s,ChartSessionEvent.Calibrated);check(s.mayDraw)
 s=ChartSessionReducer.apply(s,ChartSessionEvent.Bind(43));check(!s.mayDraw)
 s=ChartSessionReducer.apply(s,ChartSessionEvent.TextureAvailable(720,1080))
 s=ChartSessionReducer.apply(s,ChartSessionEvent.Calibrated)
 s=ChartSessionReducer.apply(s,ChartSessionEvent.TextureDestroyed);check(!s.mayDraw)
 s=ChartSessionReducer.apply(s,ChartSessionEvent.Detached);check(!s.mayDraw)
 try{ChartSessionReducer.apply(s,ChartSessionEvent.TextureAvailable(0,10));error("invalid accepted")}catch(_:IllegalArgumentException){}
 println("PASS: chart session lifecycle")
}