package mt.nativeaddon

/** Evidence-only fundamental analysis; no trade execution and no invented live feed. */
enum class PolicyTone { HAWKISH, DOVISH, MIXED, NEUTRAL, INSUFFICIENT }
data class PolicyEvidence(val sourceUrl:String,val publisher:String,val publishedAtMs:Long,val observedAtMs:Long,val text:String)
data class ToneResult(val tone:PolicyTone,val hawkishHits:Int,val dovishHits:Int,val sourceCount:Int,val warnings:List<String>)
object FundamentalResearch {
 private val hawkish=listOf("higher for longer","inflation remains elevated","restrictive policy","further tightening","raise interest rates","upside inflation risks")
 private val dovish=listOf("rate cuts","lower interest rates","easing monetary policy","downside growth risks","disinflation progress","policy accommodation")
 fun classify(items:List<PolicyEvidence>,nowMs:Long,maxAgeMs:Long=7L*24*60*60*1000):ToneResult {
  require(nowMs>=0&&maxAgeMs>0)
  val warnings=mutableListOf<String>()
  val eligible=items.filter {
   val valid=it.sourceUrl.startsWith("https://")&&it.publisher.isNotBlank()&&it.publishedAtMs in 1..nowMs&&it.observedAtMs in it.publishedAtMs..nowMs&&nowMs-it.publishedAtMs<=maxAgeMs&&it.text.isNotBlank()
   if(!valid)warnings.add("Excluded invalid or stale evidence")
   valid
  }.distinctBy{it.sourceUrl}
  val h=eligible.sumOf { e->termCount(e.text,hawkish) }
  val d=eligible.sumOf { e->termCount(e.text,dovish) }
  val tone=when {eligible.isEmpty()->PolicyTone.INSUFFICIENT;h>0&&d>0->PolicyTone.MIXED;h>0->PolicyTone.HAWKISH;d>0->PolicyTone.DOVISH;else->PolicyTone.NEUTRAL}
  return ToneResult(tone,h,d,eligible.size,warnings)
 }
 private fun termCount(text:String,terms:List<String>):Int=terms.count { text.contains(it,ignoreCase=true) }
}