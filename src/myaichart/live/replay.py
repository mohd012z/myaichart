from __future__ import annotations

import asyncio
from datetime import datetime

class ReplayAdapter:
    def __init__(self,ticks,*,speed=1.0):
        if speed not in {0.5,1,2,5,10,50}:
            raise ValueError('unsupported replay speed')
        self.ticks=sorted(list(ticks),key=lambda t:(t.source_timestamp_utc,t.source,t.source_record_id))
        self.speed=float(speed)
        self.paused=False
        self._cursor=0

    async def stream(self):
        previous=None
        while self._cursor<len(self.ticks):
            while self.paused:
                await asyncio.sleep(0.01)
            tick=self.ticks[self._cursor]
            self._cursor+=1
            if previous is not None and self.speed<50:
                delay=max(0,(tick.source_timestamp_utc-previous.source_timestamp_utc).total_seconds()/self.speed)
                if delay:
                    await asyncio.sleep(min(delay,0.05))
            previous=tick
            yield tick

    async def backfill(self,start_utc,end_utc):
        return [t for t in self.ticks if start_utc<=t.source_timestamp_utc<=end_utc]

    def pause(self): self.paused=True
    def resume(self): self.paused=False
    def jump(self, target_utc: datetime):
        for i,t in enumerate(self.ticks):
            if t.source_timestamp_utc>=target_utc:
                self._cursor=i; return
        self._cursor=len(self.ticks)
