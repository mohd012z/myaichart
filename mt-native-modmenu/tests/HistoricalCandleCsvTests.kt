import mt.nativeaddon.*
fun main() {
 val row=HistoricalCandleRow("EURUSD",ZoneTimeframe.M1,0,1.0,1.2,0.9,1.1,"broker-feed")
 val csv=HistoricalCandleCsv.export(listOf(row),60000)
 check(csv.contains("\"EURUSD\",\"M1\",0,60000,1.0,1.2,0.9,1.1,\"broker-feed\""))
 fun rejected(block:()->Unit) {
  var threw=false
  try {block()} catch(_:IllegalArgumentException) {threw=true}
  check(threw) { "Expected invalid input rejection" }
 }
 rejected { HistoricalCandleCsv.export(listOf(row),59999) }
 rejected { HistoricalCandleCsv.export(listOf(row,row),60000) }
 rejected { HistoricalCandleCsv.export(listOf(row),60000,0) }
 rejected { HistoricalCandleRow("EURUSD",ZoneTimeframe.M1,0,1.0,0.8,0.9,1.1,"broker") }
 rejected { HistoricalCandleRow("INVALID SYMBOL",ZoneTimeframe.M1,0,1.0,1.2,0.9,1.1,"broker") }
 val quoted=row.copy(source="feed,\"alpha\"")
 check(HistoricalCandleCsv.export(listOf(quoted),60000).contains("\"feed,\"\"alpha\"\"\""))
 println("PASS: closed-bar CSV, source escaping, duplicate and invalid-price rejection")
}
