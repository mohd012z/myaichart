import mt.nativeaddon.*
fun main(){
 val now=2000000000L
 fun doc(url:String="https://www.federalreserve.gov/newsevents/pressreleases/test.htm",age:Long=1000)=ResearchDocument(url,"Federal Reserve",now-age,now,"Inflation risks remain elevated","statement")
 check(ResearchEvidenceGate.validate(listOf(doc()),now).accepted.size==1)
 check(ResearchEvidenceGate.validate(listOf(doc("https://federalreserve.gov.evil.example/x")),now).accepted.isEmpty())
 check(ResearchEvidenceGate.validate(listOf(doc("http://www.federalreserve.gov/x")),now).accepted.isEmpty())
 check(ResearchEvidenceGate.validate(listOf(doc(age=40L*86400000)),now).accepted.isEmpty())
 check(ResearchEvidenceGate.validate(listOf(doc(),doc()),now).rejected==1)
 println("PASS official-domain boundary, HTTPS, stale rejection, duplicate rejection")
}
