import mt.nativeaddon.*
fun main() {
 check(PolicyLanguage.inspect("Inflation remains elevated.").tone==PolicyTone.HAWKISH)
 check(PolicyLanguage.inspect("Rate cuts are possible.").tone==PolicyTone.DOVISH)
 check(PolicyLanguage.inspect("Rate cuts and restrictive policy.").tone==PolicyTone.MIXED)
 check(PolicyLanguage.inspect("No rate cuts.").tone==PolicyTone.INSUFFICIENT)
 check(PolicyLanguage.inspect("Not further tightening.").excludedNegations==1)
 check(PolicyLanguage.inspect("No rate cuts. Inflation remains elevated.").tone==PolicyTone.HAWKISH)
 println("PASS: hawkish, dovish, mixed, negation, sentence isolation")
}