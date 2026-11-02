package mt.nativeaddon

import java.time.Instant

enum class EventImpact { HIGH, MEDIUM, LOW, NON_ECONOMIC, UNKNOWN }
data class EconomicEvent(val id:String,val currency:String,val title:String,val epochMs:Long?,val impact:EventImpact,val sourceUrl:String,val timeLabel:String)
data class EventMarker(val id:String,val x:Float,val impact:EventImpact,val title:String)
object EconomicCalendar {
 private val currencies=setOf("USD","EUR","GBP","JPY","AUD","NZD","CAD","CHF","CNY","MYR")
 fun visible(events:List<EconomicEvent>,viewport:ChartViewport,symbol:String):List<EventMarker> {
  val relevant=SymbolCatalog.currencies(symbol)
  return events.asSequence().filter { it.currency in currencies && it.currency in relevant && it.epochMs!=null && it.sourceUrl.startsWith("https://") }
   .mapNotNull { event ->
    val time=event.epochMs!!
    val point=ChartProjection.project(viewport,time,viewport.minimumPrice+(viewport.maximumPrice-viewport.minimumPrice)/2)
    if(point==null)null else EventMarker(event.id,point.x,event.impact,event.title)
   }.sortedBy{it.x}.toList()
 }
}
