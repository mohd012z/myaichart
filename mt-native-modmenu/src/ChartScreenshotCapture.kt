package mt.nativeaddon

import android.graphics.Bitmap
import android.graphics.SurfaceTexture
import android.view.TextureView

/** Capture only an explicitly selected, visible chart TextureView after user consent. */
object ChartScreenshotCapture {
 fun capture(view:TextureView, consent:Boolean, maxPixels:Long=4096L*4096L):Result<Bitmap> = runCatching {
  require(consent){"User consent is required"}
  require(view.isAttachedToWindow&&view.isAvailable){"Texture is unavailable"}
  require(view.width>0&&view.height>0&&view.width.toLong()*view.height.toLong()<=maxPixels){"Invalid or oversized screenshot"}
  view.getBitmap(view.width,view.height) ?: error("Texture capture returned null")
 }
}
