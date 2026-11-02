import mt.nativeaddon.*
import kotlin.math.abs
fun eq(a:Double,b:Double)=check(abs(a-b)<1e-9){"$a != $b"}
fun main(){
 val a=(1..60).map{it.toDouble()}
 val s=Indicators.sma(a,5);check(s.take(4).all{it==null});eq(s[4]!!,3.0)
 val w=Indicators.lwma(a,3);eq(w[2]!!,14.0/6.0)
 val e=Indicators.ema(a,5);eq(e[4]!!,3.0);eq(e[5]!!,4.0)
 val b=Indicators.bands(List(20){10.0});eq(b[19]!!.upper,10.0);eq(b[19]!!.lower,10.0)
 val candles=(0 until 60).map{Candle(it.toLong()*60000,10.0,12.0,8.0,10.0)}
 val out=Indicators.bbma(candles);check(out.size==60);check(out[18].bands==null);check(out[19].bands!=null);check(out[48].ema50==null);eq(out[49].ema50!!,10.0)
 val fib=Fibonacci.levels(100.0,200.0);eq(fib.first().price,200.0);eq(fib[4].price,138.2)
 try{Indicators.bbma(candles.reversed());error("unsorted candles accepted")}catch(_:IllegalArgumentException){}
 println("PASS: SMA LWMA EMA BBANDS BBMA warmup Fibonacci ordering validation")
}