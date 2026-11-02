import mt.nativeaddon.*
fun main(){
 val v=ChartViewport(0f,0f,320f,200f,1000,100000,90.0,110.0)
 val s=HostSnapshot("XAUUSD",15,v,90000,100000,100000,true)
 check(ChartHostGate.validate(s,100010) is HostStatus.Ready)
 check(ChartHostGate.validate(s.copy(coordinateSpaceVerified=false),100010) is HostStatus.Rejected)
 check(ChartHostGate.validate(s,150001) is HostStatus.Rejected)
 check(ChartHostGate.validate(s.copy(feedAsOfMs=150011),100010) is HostStatus.Rejected)
 check(ChartHostGate.validate(s.copy(symbol="../x"),100010) is HostStatus.Rejected)
 check(ChartHostGate.validate(s.copy(timeframeMinutes=13),100010) is HostStatus.Rejected)
 check(ChartHostGate.validate(s.copy(closedCandleTimeMs=100001),100010) is HostStatus.Rejected)
 check(ChartHostGate.validate(null,100010) is HostStatus.Rejected)
 println("PASS: verified host, stale data, future data, invalid symbol/TF, unverified viewport")
}