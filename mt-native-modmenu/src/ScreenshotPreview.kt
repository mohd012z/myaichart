package mt.nativeaddon

import android.app.AlertDialog
import android.content.Context
import android.graphics.Bitmap
import android.widget.ImageView

/** Ephemeral local preview; user chooses whether to discard the bitmap. No network or storage. */
object ScreenshotPreview {
 fun show(context:Context,bitmap:Bitmap,onDismiss:()->Unit={}){
  val image=ImageView(context).apply{
   setImageBitmap(bitmap)
   adjustViewBounds=true
   scaleType=ImageView.ScaleType.FIT_CENTER
   contentDescription="Captured chart screenshot preview"
  }
  AlertDialog.Builder(context)
   .setTitle("Chart screenshot · Local preview")
   .setMessage("Preview only. The image has not been uploaded or saved.")
   .setView(image)
   .setPositiveButton("Close"){_,_->}
   .setOnDismissListener{image.setImageDrawable(null);onDismiss()}
   .show()
 }
}
