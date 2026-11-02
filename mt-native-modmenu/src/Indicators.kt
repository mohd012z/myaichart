package mt.nativeaddon

import kotlin.math.sqrt

data class Candle(val timeMillis: Long, val open: Double, val high: Double, val low: Double, val close: Double) {
    init {
        require(timeMillis >= 0 && listOf(open, high, low, close).all { it.isFinite() })
        require(high >= maxOf(open, close, low) && low <= minOf(open, close, high))
    }
}
data class Bands(val middle: Double, val upper: Double, val lower: Double)
data class BbmaPoint(val timeMillis: Long, val bands: Bands?, val ema50: Double?, val lwma5High: Double?, val lwma5Low: Double?, val lwma10High: Double?, val lwma10Low: Double)
object Indicators {
    fun sma(a: List<Double>, period: Int): List<Double?> {
        require(period > 0)
        val out = MutableList<Double?>(a.size) { null }
        var sum = 0.0
        for (i in a.indices) {
            require(a[i].isFinite())
            sum += a[i]
            if (i >= period) sum -= a[i-period]
            if (i >= period-1) out[i] = sum/period
        }
        return out
    }
    fun ema(a: List<Double>, period: Int): List<Double?> {
        require(period > 0 && a.all { it.isFinite() })
        val out = MutableList<Double?>(a.size) { null }
        if (a.size < period) return out
        val alpha = 2.0/(period+1)
        var prev = a.take(period).average()
        out[period-1] = prev
        for (i in period until a.size) {
            prev = alpha*a[i]+(1-alpha)*prev
            out[i] = prev
        }
        return out
    }
    fun lwma(a: List<Double>, period: Int): List<Double?> {
        require(period > 0 && a.all { it.isFinite() })
        val out = MutableList<Double?>(a.size) { null }
        val denom = period*(period+1)/2.0
        for (i in period-1 until a.size) {
            var sum = 0.0
            for (k in 0 until period) sum += a[i-period+1+k]*(k+1)
            out[i] = sum/denom
        }
        return out
    }
    fun bands(a: List<Double>, period: Int=20, deviation: Double=2.0): List<Bands?> {
        require(period > 0 && deviation.isFinite() && deviation >= 0)
        val mid = sma(a,period)
        return a.indices.map { i ->
            if (i < period-1) null else {
                val mean = mid[i]!!
                var ss = 0.0
                for (j in i-period+1..i) ss += (a[j]-mean)*(a[j]-mean)
                val sd = sqrt(ss/period)
                Bands(mean,mean+deviation*sd,mean-deviation*sd)
            }
        }
    }
    fun bbma(candles: List<Candle>): List<BbmaPoint> {
        require(candles.zipWithNext().all { (a,b) -> a.timeMillis < b.timeMillis })
        val close = candles.map { it.close }
        val high = candles.map { it.high }
        val low = candles.map { it.low }
        val bb = bands(close)
        val ema = ema(close,50)
        val h5 = lwma(high,5)
        val l5 = lwma(low,5)
        val h10 = lwma(high,10)
        val l10 = lwma(low,10)
        return candles.indices.map { i -> BbmaPoint(candles[i].timeMillis,bb[i],ema[i],h5[i],l5[i],h10[i],l10[i]) }
    }
}
data class FibonacciLevel(val ratio: Double, val price: Double)
object Fibonacci {
    val ratios = listOf(0.0,0.236,0.382,0.5,0.618,0.786,1.0,1.272,1.618)
    fun levels(startPrice: Double,endPrice: Double): List<FibonacciLevel> {
        require(startPrice.isFinite() && endPrice.isFinite())
        return ratios.map { FibonacciLevel(it,endPrice+(startPrice-endPrice)*it) }
    }
}