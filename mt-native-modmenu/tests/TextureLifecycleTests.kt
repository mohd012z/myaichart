import mt.nativeaddon.*
fun main() {
 var s = TextureHostState()
 check(!s.canRender)
 s = TextureLifecycle.reduce(s, TextureEvent.Attached)
 check(!s.canRender)
 s = TextureLifecycle.reduce(s, TextureEvent.Available(1080, 600))
 check(s.canRender && s.generation == 1L)
 s = TextureLifecycle.reduce(s, TextureEvent.Resized(600, 1080))
 check(s.canRender && s.width == 600 && s.generation == 2L)
 s = TextureLifecycle.reduce(s, TextureEvent.Destroyed)
 check(!s.canRender && s.generation == 3L)
 s = TextureLifecycle.reduce(s, TextureEvent.Detached)
 check(!s.canRender && s.generation == 4L)
 try { TextureLifecycle.reduce(s, TextureEvent.Available(0, 100)); error("zero-size texture accepted") } catch (_: IllegalArgumentException) {}
 println("PASS: texture attach, availability, resize, destroy, detach, zero dimensions")
}