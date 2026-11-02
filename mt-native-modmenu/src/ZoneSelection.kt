package mt.nativeaddon

data class ZoneSelection(val symbol:String,val timeframe:ZoneTimeframe,val maxVisible:Int=12) {
 init { require(SymbolCatalog.normalize(symbol)==symbol);require(maxVisible in 1..100) }
}
object ZoneSelectionPolicy {
 fun create(symbol:String,timeframe:ZoneTimeframe,maxVisible:Int):ZoneSelection {
  val normalized=SymbolCatalog.normalize(symbol)?:error("Invalid research symbol")
  return ZoneSelection(normalized,timeframe,maxVisible.coerceIn(1,100))
 }
 fun visible(zones:List<EvaluatedZone>,selection:ZoneSelection):List<EvaluatedZone> =
  zones.asSequence().filter{it.status!=ZoneStatus.INVALIDATED}
   .sortedWith(compareByDescending<EvaluatedZone>{it.zone.confirmedAtMs}.thenByDescending{it.zone.formedAtMs})
   .take(selection.maxVisible).toList()
}
