package mt.nativeaddon

data class LanguageFinding(val tone: PolicyTone, val hawkish: Int, val dovish: Int, val excludedNegations: Int)
object PolicyLanguage {
 private val hawkish = listOf("higher for longer", "inflation remains elevated", "restrictive policy", "further tightening", "raise interest rates", "upside inflation risks")
 private val dovish = listOf("rate cuts", "lower interest rates", "easing monetary policy", "downside growth risks", "disinflation progress", "policy accommodation")
 private val negation = Regex("\\b(?:no|not|never|without|unlikely|rejects?|denies?)\\b", RegexOption.IGNORE_CASE)
 fun inspect(text: String): LanguageFinding {
  require(text.length <= 100000)
  var h = 0; var d = 0; var excluded = 0
  val sentences = text.split(Regex("[.!?;\\n]+"))
  for (sentence in sentences) {
   val matches = hawkish.map { it to true } + dovish.map { it to false }
   for ((phrase, isHawkish) in matches) {
    var from = 0
    while (true) {
     val at = sentence.indexOf(phrase, from, ignoreCase = true)
     if (at < 0) break
     val context = sentence.substring(maxOf(0, at - 40), at)
     if (negation.containsMatchIn(context)) excluded++
     else if (isHawkish) h++ else d++
     from = at + phrase.length
    }
   }
  }
  return LanguageFinding(when {h>0&&d>0->PolicyTone.MIXED;h>0->PolicyTone.HAWKISH;d>0->PolicyTone.DOVISH;else->PolicyTone.INSUFFICIENT},h,d,excluded)
 }
}
