import mt.nativeaddon.*
import kotlin.math.abs
fun near(a:Float,b:Float)=check(abs(a-b)<0.001f)
fun main(){
 val v=ChartViewport(10f,20f,200f,100f,1000,3000,100.0,200.0)
 val a=ChartProjection.project(v,1000,200.0)!!;near(a.x,10f);near(a.y,20f)
 val b=ChartProjection.project(v,2000,150.0)!!;near(b.x,110f);near(b.y,70f)
 val c=ChartProjection.project(v,3000,100.0)!!;near(c.x,210f);near(c.y,120f)
 check(ChartProjection.project(v,999,150.0)==null)
 check(ChartProjection.project(v,2000,201.0)==null)
 check(ChartProjection.project(v,2000,Double.NaN)==null)
 try{ChartViewport(0f,0f,0f,100f,1,2,1.0,2.0);error("accepted")}catch(_:IllegalArgumentException){}
 println("PASS: MT5 chart projection tests")
}