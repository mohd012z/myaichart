package mt.nativeaddon

import java.net.HttpURLConnection
import java.net.URL

/** One-shot, user-initiated read-only fetch. Never follows redirects or stores credentials. */
data class FetchedSource(val url:String,val retrievedAtMs:Long,val body:String,val contentType:String)
object ResearchSourceFetcher {
 fun fetch(url:String,nowMs:Long,maxBytes:Int=131072):FetchedSource {
  check(android.os.Looper.myLooper()!=android.os.Looper.getMainLooper()){"Network fetch must not run on Android UI thread"}
  require(maxBytes in 1024..262144)
  val candidate=ResearchDocument(url,"official source",nowMs,nowMs,"pending","unclassified")
  require(ResearchEvidenceGate.validate(listOf(candidate),nowMs).accepted.size==1){"URL not approved"}
  val connection=(URL(url).openConnection() as HttpURLConnection)
  try {
   connection.instanceFollowRedirects=false
   connection.connectTimeout=6000
   connection.readTimeout=6000
   connection.requestMethod="GET"
   connection.setRequestProperty("Accept","text/plain, text/html, application/xml, text/xml")
   require(connection.responseCode==200){"Unexpected HTTP status"}
   val contentType=connection.contentType?.substringBefore(';')?.lowercase() ?: ""
   require(contentType in setOf("text/plain","text/html","application/xml","text/xml")){"Unsupported content type"}
   require(connection.contentLengthLong in -1L..maxBytes.toLong()){"Document too large"}
   val bytes=connection.inputStream.use { stream ->
    val output=java.io.ByteArrayOutputStream()
    val buffer=ByteArray(4096)
    while(true){
     val count=stream.read(buffer)
     if(count<0)break
     require(output.size()+count<=maxBytes){"Document too large"}
     output.write(buffer,0,count)
    }
    output.toByteArray()
   }
   val text=bytes.toString(Charsets.UTF_8)
   require(text.isNotBlank())
   return FetchedSource(url,nowMs,text,contentType)
  } finally { connection.disconnect() }
 }
}
