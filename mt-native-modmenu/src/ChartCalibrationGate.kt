package mt.nativeaddon

/**
 * User-confirmed chart calibration. A screenshot is not a market-data source.
 * Coordinates are usable only while the captured MT5 chart identity and viewport
 * revision still match; callers must invalidate on pan, zoom or rotation.
 */
data class ChartCalibration(
    val symbol: String,
    val timeframe: ZoneTimeframe,
    val viewport: ChartViewport,
    val capturedAtMs: Long,
    val revision: Long
) {
    init {
        require(symbol.isNotBlank() && symbol == SymbolCatalog.normalize(symbol))
        require(capturedAtMs >= 0 && revision >= 0)
    }
}

data class ChartObservation(
    val symbol: String,
    val timeframe: ZoneTimeframe,
    val capturedAtMs: Long,
    val revision: Long
)

sealed class CalibrationDecision {
    data class Ready(val viewport: ChartViewport) : CalibrationDecision()
    data class Rejected(val reason: String) : CalibrationDecision()
}

object ChartCalibrationGate {
    /** Fail closed: stale screenshots or mismatched symbol/TF must never draw zones. */
    fun check(
        calibration: ChartCalibration?,
        observation: ChartObservation,
        nowMs: Long,
        maxAgeMs: Long = 3000L
    ): CalibrationDecision {
        require(nowMs >= 0 && maxAgeMs > 0)
        if (calibration == null) return CalibrationDecision.Rejected("NO_CALIBRATION")
        if (observation.symbol != calibration.symbol || observation.timeframe != calibration.timeframe)
            return CalibrationDecision.Rejected("CHART_IDENTITY_CHANGED")
        if (observation.revision != calibration.revision)
            return CalibrationDecision.Rejected("VIEWPORT_CHANGED")
        if (observation.capturedAtMs != calibration.capturedAtMs)
            return CalibrationDecision.Rejected("CAPTURE_CHANGED")
        if (calibration.capturedAtMs > nowMs)
            return CalibrationDecision.Rejected("FUTURE_CAPTURE")
        if (nowMs - calibration.capturedAtMs > maxAgeMs)
            return CalibrationDecision.Rejected("STALE_CAPTURE")
        return CalibrationDecision.Ready(calibration.viewport)
    }
}
