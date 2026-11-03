package mt.nativeaddon

/** Source-attributed, closed-bar-only CSV export. Does not access MT5 private storage. */
data class HistoricalCandleRow(
    val symbol: String,
    val timeframe: ZoneTimeframe,
    val openTimeMs: Long,
    val open: Double,
    val high: Double,
    val low: Double,
    val close: Double,
    val source: String
) {
    init {
        require(SymbolCatalog.normalize(symbol) == symbol)
        require(openTimeMs >= 0)
        require(source.isNotBlank())
        require(listOf(open,high,low,close).all { it.isFinite() })
        require(high >= maxOf(open,close,low) && low <= minOf(open,close,high))
    }
}
object HistoricalCandleCsv {
    private fun escape(value:String):String = "\"" + value.replace("\"","\"\"") + "\""
    private fun field(value:Double):String = java.lang.Double.toString(value)
    fun export(rows:List<HistoricalCandleRow>, asOfMs:Long, maxRows:Int=100000):String {
        require(asOfMs >= 0 && maxRows in 1..1000000 && rows.size <= maxRows)
        val seen=HashSet<String>()
        val out=StringBuilder("symbol,timeframe,open_time_ms,close_time_ms,open,high,low,close,source\n")
        for(row in rows) {
            val closeTime=Math.addExact(row.openTimeMs,row.timeframe.durationMs)
            require(closeTime <= asOfMs) { "Open or future candle rejected" }
            val key="${row.symbol}|${row.timeframe.name}|${row.openTimeMs}|${row.source}"
            require(seen.add(key)) { "Duplicate candle rejected" }
            out.append(escape(row.symbol)).append(',').append(escape(row.timeframe.name)).append(',')
                .append(row.openTimeMs).append(',').append(closeTime).append(',')
                .append(field(row.open)).append(',').append(field(row.high)).append(',')
                .append(field(row.low)).append(',').append(field(row.close)).append(',')
                .append(escape(row.source)).append('\n')
        }
        return out.toString()
    }
}
