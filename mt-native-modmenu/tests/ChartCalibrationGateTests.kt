import mt.nativeaddon.*

fun main() {
 val viewport=ChartViewport(0f,0f,800f,500f,0,600000,1.0,2.0)
 val calibration=ChartCalibration("EURUSD",ZoneTimeframe.M1,viewport,10000,7)
 val good=ChartObservation("EURUSD",ZoneTimeframe.M1,10000,7)
 check(ChartCalibrationGate.check(calibration,good,11000) is CalibrationDecision.Ready)
 fun rejected(obs:ChartObservation,now:Long,expected:String) {
  val result=ChartCalibrationGate.check(calibration,obs,now)
  check(result is CalibrationDecision.Rejected && result.reason==expected) { "Unexpected: $result" }
 }
 rejected(good.copy(symbol="GBPUSD"),11000,"CHART_IDENTITY_CHANGED")
 rejected(good.copy(timeframe=ZoneTimeframe.H1),11000,"CHART_IDENTITY_CHANGED")
 rejected(good.copy(revision=8),11000,"VIEWPORT_CHANGED")
 rejected(good.copy(capturedAtMs=10001),11000,"CAPTURE_CHANGED")
 rejected(good,9000,"FUTURE_CAPTURE")
 rejected(good,14001,"STALE_CAPTURE")
 check(ChartCalibrationGate.check(null,good,11000) is CalibrationDecision.Rejected)
 try { ChartCalibration("invalid symbol",ZoneTimeframe.M1,viewport,10000,7);throw AssertionError("Accepted invalid symbol") }
 catch (_:IllegalArgumentException) {}
 println("PASS: calibration identity, viewport revision, capture freshness, fail-closed drawing")
}
