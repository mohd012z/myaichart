package mt.nativeaddon

/** Research evidence is not a live quote, policy decision, or trading instruction. */
data class ResearchDocument(val url:String,val publisher:String,val publishedAtMs:Long,val fetchedAtMs:Long,val text:String,val category:String)
data class ResearchBatch(val accepted:List<ResearchDocument>,val rejected:Int,val reasons:List<String>)
object ResearchEvidenceGate {
 private val domains=setOf("federalreserve.gov","ecb.europa.eu","bankofengland.co.uk","boj.or.jp","rba.gov.au","rbnz.govt.nz","bankofcanada.ca","snb.ch","bnm.gov.my","bis.org")
 fun validate(items:List<ResearchDocument>,nowMs:Long,maxAgeMs:Long=30L*86400000):ResearchBatch {
  require(nowMs>=0&&maxAgeMs>0)
  val seen=mutableSetOf<String>();val accepted=mutableListOf<ResearchDocument>();val reasons=mutableListOf<String>()
  for(item in items){
   val uri=runCatching{java.net.URI(item.url)}.getOrNull()
   val host=uri?.host?.lowercase()?.removeSuffix(".") ?: ""
   val approved=uri?.scheme?.lowercase()=="https"&&uri.userInfo==null&&uri.port==-1&&domains.any{host==it||host.endsWith(".$it")}
   val valid=approved&&item.publisher.isNotBlank()&&item.text.isNotBlank()&&item.text.length<=100000&&item.publishedAtMs in 1..nowMs&&item.fetchedAtMs in item.publishedAtMs..nowMs&&nowMs-item.publishedAtMs<=maxAgeMs
   if(!valid){reasons.add("Rejected unsupported, missing, future or stale evidence");continue}
   if(!seen.add(item.url)){reasons.add("Rejected duplicate URL");continue}
   accepted.add(item)
  }
  return ResearchBatch(accepted,items.size-accepted.size,reasons)
 }
}
