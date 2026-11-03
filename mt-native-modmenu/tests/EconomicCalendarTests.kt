import mt.nativeaddon.*
fun main(){
 val viewport=ChartViewport(0f,0f,1000f,600f,1000L,2000L,1.0,2.0)
 val events=listOf(
  EconomicEvent("1","USD","US CPI",1500L,EventImpact.HIGH,"https://www.forexfactory.com/calendar",""),
  EconomicEvent("2","JPY","BoJ",1500L,EventImpact.HIGH,"https://www.forexfactory.com/calendar",""),
  EconomicEvent("3","USD","Tentative",null,EventImpact.UNKNOWN,"https://www.forexfactory.com/calendar","Tentative"),
  EconomicEvent("4","USD","Out of range",3000L,EventImpact.LOW,"https://www.forexfactory.com/calendar",""))
 check(EconomicCalendar.visible(events,viewport,"EURUSD").map{it.id}==listOf("1"))
 check(EconomicCalendar.visible(events,viewport,"USDJPY").size==2)
 check(SymbolCatalog.options(listOf("eurusd","EURUSD","XAUUSD")).size==2)
 check(SymbolCatalog.normalize("bad symbol")==null)
 println("PASS symbol matching, marker projection, tentative exclusion, viewport bounds")
}
