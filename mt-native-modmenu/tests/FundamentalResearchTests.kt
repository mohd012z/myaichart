import mt.nativeaddon.*
fun main(){
 val now=1000000000L
 fun e(text:String,url:String="https://centralbank.example/statement",published:Long=now-1000)=PolicyEvidence(url,"Central bank",published,now,text)
 check(FundamentalResearch.classify(listOf(e("inflation remains elevated")),now).tone==PolicyTone.HAWKISH)
 check(FundamentalResearch.classify(listOf(e("rate cuts")),now).tone==PolicyTone.DOVISH)
 check(FundamentalResearch.classify(listOf(e("rate cuts and restrictive policy")),now).tone==PolicyTone.MIXED)
 check(FundamentalResearch.classify(listOf(e("rate cuts",published=now-900000000)),now).tone==PolicyTone.INSUFFICIENT)
 check(FundamentalResearch.classify(emptyList(),now).tone==PolicyTone.INSUFFICIENT)
 println("PASS: hawkish, dovish, mixed, stale, missing evidence")
}