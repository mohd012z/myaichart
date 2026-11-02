package mt.nativeaddon

data class ResearchSymbol(val code:String,val description:String)
object SymbolCatalog {
 private val valid=Regex("[A-Z0-9._-]{3,24}")
 fun normalize(raw:String):String? {
  val code=raw.trim().uppercase()
  return code.takeIf {valid.matches(it)}
 }
 fun currencies(raw:String):Set<String> {
  val code=normalize(raw) ?: return emptySet()
  val known=listOf("USD","EUR","GBP","JPY","AUD","NZD","CAD","CHF","CNY","MYR")
  val matches=known.filter{code.contains(it)}.toMutableSet()
  if(code.startsWith("XAU")||code.startsWith("XAG")||code.startsWith("BTC")||code.startsWith("ETH"))matches.add("USD")
  return matches
 }
 fun options(codes:List<String>):List<ResearchSymbol> = codes.mapNotNull{normalize(it)}.distinct().sorted().map{ResearchSymbol(it,it)}
}
