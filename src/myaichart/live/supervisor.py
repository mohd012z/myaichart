from dataclasses import dataclass
from myaichart.models import FeedStatus


def merge_backfill(existing,backfill):
    by_id={(t.source,t.source_record_id):t for t in existing}
    for t in backfill:
        by_id[(t.source,t.source_record_id)]=t
    return sorted(by_id.values(),key=lambda t:(t.source_timestamp_utc,t.source,t.source_record_id))


@dataclass(frozen=True)
class OutageRecord:
    start_utc: object
    end_utc: object
    final_state: str
    recovered_count: int=0


class FeedSupervisor:
    def __init__(self,adapter,store,candle_engine):
        self.adapter=adapter; self.store=store; self.candle_engine=candle_engine
        self.status=FeedStatus.CONNECTING
        self.outages=[]

    async def handle_disconnect(self,*,start_utc,end_utc):
        self.status=FeedStatus.RECONNECTING
        ticks=await self.adapter.backfill(start_utc,end_utc)
        if not ticks:
            self.outages.append(OutageRecord(start_utc,end_utc,'DATA_GAP',0))
            self.status=FeedStatus.STALE
            return []
        if self.store is not None:
            self.store.append_chunk(ticks)
        if self.candle_engine is not None:
            for tick in ticks:
                try:
                    self.candle_engine.apply_authorized_correction(tick,reason='BACKFILL')
                except KeyError:
                    self.candle_engine.on_tick(tick)
        self.outages.append(OutageRecord(start_utc,end_utc,'RECOVERED',len(ticks)))
        self.status=FeedStatus.LIVE
        return ticks
