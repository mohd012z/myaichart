import mt.nativeaddon.*
fun main() {
 var s=ChartSession(-1,0,false,false,0,0,false)
 s=ChartSessionReducer.apply(s,ChartSessionEvent.Bind(7))
 s=ChartSessionReducer.apply(s,ChartSessionEvent.TextureAvailable(1080,720))
 s=ChartSessionReducer.apply(s,ChartSessionEvent.Calibrated)
 val v=ChartViewport(0f,0f,1080f,720f,1000,2000,90.0,110.0)
 val lease=ViewportLease(7,s.generation,v)
 check(ViewportLeaseGate.isCurrent(s,lease))
 check(!ViewportLeaseGate.isCurrent(s,lease.copy(chartId=8)))
 check(!ViewportLeaseGate.isCurrent(s,lease.copy(generation=s.generation-1)))
 check(!ViewportLeaseGate.isCurrent(s,lease.copy(viewport=v.copy(leftPx=1f))))
 s=ChartSessionReducer.apply(s,ChartSessionEvent.Resize(720,1080))
 check(!ViewportLeaseGate.isCurrent(s,lease))
 s=ChartSessionReducer.apply(s,ChartSessionEvent.Calibrated)
 check(!ViewportLeaseGate.isCurrent(s,lease))
 println("PASS viewport lease: chart, generation, bounds, resize")
}