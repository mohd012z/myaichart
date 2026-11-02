import mt.nativeaddon.*
fun main(){
 val s=ZoneSelectionPolicy.create(" eurusd ",ZoneTimeframe.M15,999)
 check(s.symbol=="EURUSD"&&s.maxVisible==100)
 check(ZoneSelectionPolicy.create("XAUUSD",ZoneTimeframe.H1,-2).maxVisible==1)
 var rejected=false
 try{ZoneSelectionPolicy.create("INVALID SYMBOL",ZoneTimeframe.M1,5)}catch(_:IllegalStateException){rejected=true}
 check(rejected){"Invalid symbols must be rejected"}
 check(ZoneSelectionPolicy.visible(emptyList(),s).isEmpty())
 println("PASS: validated symbol, timeframe and bounded visible zone count")
}
