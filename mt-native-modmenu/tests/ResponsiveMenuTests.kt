import mt.nativeaddon.*
fun main(){
 val tiny=MenuBounds(160,200)
 check(ResponsiveMenu.size(tiny,240,400,8)==MenuBounds(144,184))
 val a=ResponsiveMenu.place(tiny,MenuBounds(144,184),999f,-5f)
 check(a.x==16f&&a.y==0f)
 val saved=ResponsiveMenu.save(tiny,a,true)
 check(saved.expanded)
 val rotated=ResponsiveMenu.restore(MenuBounds(500,300),MenuBounds(144,184),saved)
 check(rotated.x==356f&&rotated.y==0f)
 check(ResponsiveMenu.snap(tiny,a).x==16f)
 check(ResponsiveMenu.place(tiny,MenuBounds(999,999),Float.NaN,Float.POSITIVE_INFINITY)==MenuGeometry(0f,0f,160,200))
 println("PASS: narrow screen, clamp, fractional restore, snap, non-finite coordinates")
}