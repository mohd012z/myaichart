package mt.nativeaddon

/** Prevents rendering with calibration from a previous chart or texture generation. */
data class ViewportLease(val chartId: Int, val generation: Long, val viewport: ChartViewport) {
    init { require(chartId >= 0 && generation >= 0) }
}
object ViewportLeaseGate {
    fun isCurrent(session: ChartSession, lease: ViewportLease?): Boolean =
        lease != null && session.mayDraw && session.chartId == lease.chartId &&
        session.generation == lease.generation &&
        lease.viewport.widthPx <= session.width.toFloat() &&
        lease.viewport.heightPx <= session.height.toFloat() &&
        lease.viewport.leftPx >= 0f && lease.viewport.topPx >= 0f &&
        lease.viewport.leftPx + lease.viewport.widthPx <= session.width.toFloat() &&
        lease.viewport.topPx + lease.viewport.heightPx <= session.height.toFloat()
}