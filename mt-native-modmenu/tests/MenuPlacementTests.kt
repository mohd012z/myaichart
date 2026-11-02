import mt.nativeaddon.*
fun main(){
 check(MenuPlacement.clamp(-100f,999f,200,300,600,800)==MenuPosition(0f,500f))
 check(MenuPlacement.clamp(500f,500f,700,900,600,800)==MenuPosition(0f,0f))
 check(MenuPlacement.default(200,300,600,800,16)==MenuPosition(384f,16f))
 check(MenuPlacement.clamp(Float.NaN,Float.POSITIVE_INFINITY,200,200,600,800)==MenuPosition(0f,0f))
 println("PASS responsive placement, oversize, invalid offsets")
}