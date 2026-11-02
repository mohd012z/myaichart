package mt.nativeaddon

/** Integration boundary: no MT5 class or chart surface is assumed. */
data class HostSnapshot(
    val symbol: String,
    val timeframeMinutes: Int,
    val viewport: ChartViewport,
    val closedCandleTimeMs: Long,
    val observedAtMs: Long,
    val feedAsOfMs: Long,
    val coordinateSpaceVerified: Boolean
)
sealed class HostStatus {
    data class Ready(val snapshot: HostSnapshot): HostStatus()
    data class Rejected(val reason: String): HostStatus()
}
object ChartHostGate {
    fun validate(snapshot: HostSnapshot?, nowMs: Long, maxAgeMs: Long = 30_000L): HostStatus {
        if (snapshot == null) return HostStatus.Rejected("No chart host snapshot")
        if (!snapshot.coordinateSpaceVerified) return HostStatus.Rejected("Chart coordinate space not verified")
        if (snapshot.symbol.isBlank() || snapshot.symbol.length > 32 || !snapshot.symbol.all { it.isLetterOrDigit() || it in "._-" }) return HostStatus.Rejected("Invalid symbol")
        if (snapshot.timeframeMinutes !in setOf(1,2,3,4,5,6,10,12,15,20,30,60,120,180,240,360,480,720,1440,10080,43200)) return HostStatus.Rejected("Unsupported timeframe")
        if (nowMs < 0 || maxAgeMs <= 0 || snapshot.observedAtMs > nowMs || snapshot.feedAsOfMs > nowMs || snapshot.closedCandleTimeMs > nowMs) return HostStatus.Rejected("Future timestamp")
        if (nowMs - snapshot.observedAtMs > maxAgeMs || nowMs - snapshot.feedAsOfMs > maxAgeMs) return HostStatus.Rejected("Stale host or market data")
        if (snapshot.closedCandleTimeMs > snapshot.viewport.lastTimeMs) return HostStatus.Rejected("Closed candle outside viewport")
        return HostStatus.Ready(snapshot)
    }
}