import mt.nativeaddon.*
fun main(){
 fun c(t:Long,o:Double,h:Double,l:Double,cl:Double)=Candle(t,o,h,l,cl)
 val demand=listOf(c(1,10.0,10.3,9.8,10.1),c(2,10.1,10.4,9.9,10.0),c(3,10.0,10.2,9.8,10.1),c(4,10.1,12.5,10.0,12.0))
 val zones=SupplyDemand.detect(demand)
 check(zones.size==1&&zones[0].kind==ZoneKind.DEMAND)
 check(zones[0].confirmedAtMs==4L)
 check(SupplyDemand.detect(demand.take(3)).isEmpty())
 check(SupplyDemand.unmitigated(zones,demand).size==1)
 check(SupplyDemand.unmitigated(zones,demand+c(5,12.0,12.1,10.0,10.5)).isEmpty())
 val supply=listOf(c(1,10.0,10.3,9.8,10.1),c(2,10.1,10.4,9.9,10.0),c(3,10.0,10.2,9.8,10.1),c(4,10.0,10.1,7.0,7.5))
 check(SupplyDemand.detect(supply).single().kind==ZoneKind.SUPPLY)
 println("PASS demand/supply confirmation, closed bar, mitigation")
}
