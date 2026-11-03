package mt.nativeaddon

data class TextureHostState(val attached: Boolean = false, val textureReady: Boolean = false, val width: Int = 0, val height: Int = 0, val generation: Long = 0) {
    val canRender: Boolean get() = attached && textureReady && width > 0 && height > 0
}
sealed class TextureEvent {
    data object Attached: TextureEvent()
    data object Detached: TextureEvent()
    data class Available(val width: Int, val height: Int): TextureEvent()
    data class Resized(val width: Int, val height: Int): TextureEvent()
    data object Destroyed: TextureEvent()
}
object TextureLifecycle {
    fun reduce(s: TextureHostState, event: TextureEvent): TextureHostState = when(event) {
        TextureEvent.Attached -> s.copy(attached = true)
        TextureEvent.Detached -> s.copy(attached = false, textureReady = false, width = 0, height = 0, generation = s.generation + 1)
        is TextureEvent.Available -> {
            require(event.width > 0 && event.height > 0)
            s.copy(textureReady = true, width = event.width, height = event.height, generation = s.generation + 1)
        }
        is TextureEvent.Resized -> {
            require(event.width > 0 && event.height > 0)
            if (!s.textureReady) s else s.copy(width = event.width, height = event.height, generation = s.generation + 1)
        }
        TextureEvent.Destroyed -> s.copy(textureReady = false, width = 0, height = 0, generation = s.generation + 1)
    }
}