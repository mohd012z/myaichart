from __future__ import annotations
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

@dataclass(frozen=True)
class EventFeatures:
    event_id: str
    t_minus_60_return: float | None = None
    t_minus_30_return: float | None = None
    t_minus_15_return: float | None = None
    t_minus_5_return: float | None = None
    t_plus_1_return: float | None = None
    t_plus_5_return: float | None = None
    t_plus_15_return: float | None = None
    t_plus_30_return: float | None = None
    t_plus_60_return: float | None = None


def _price_at(candles, target):
    before=[c for c in candles if c.time_open_utc<=target]
    if not before: return None
    return max(before,key=lambda c:c.time_open_utc).mid_close


def _ret(p0,p1):
    if p0 is None or p1 is None or p0==0: return None
    return (p1-p0)/p0


def build_event_features(event,candles,*,as_of):
    t=event.scheduled_time_utc
    p0=_price_at(candles,t)
    vals={}
    for mins,name in [(-60,'t_minus_60_return'),(-30,'t_minus_30_return'),(-15,'t_minus_15_return'),(-5,'t_minus_5_return'),
                      (1,'t_plus_1_return'),(5,'t_plus_5_return'),(15,'t_plus_15_return'),(30,'t_plus_30_return'),(60,'t_plus_60_return')]:
        target=t+timedelta(minutes=mins)
        if mins>0 and as_of<target:
            vals[name]=None
        else:
            vals[name]=_ret(p0,_price_at(candles,target)) if mins>0 else _ret(_price_at(candles,target),p0)
    return EventFeatures(event_id=event.event_id,**vals)


def surprise_raw(actual,forecast):
    if actual is None or forecast is None: return None
    return float(Decimal(str(actual)) - Decimal(str(forecast)))


def select_controls(event,candidates,max_controls=5):
    wd=event.scheduled_time_myt.weekday(); minute=event.scheduled_time_myt.hour*60+event.scheduled_time_myt.minute
    eligible=[c for c in candidates if c.get('weekday')==wd and not c.get('has_equivalent_event',False)]
    eligible.sort(key=lambda c:abs(c.get('minute_of_day',minute)-minute))
    return eligible[:max_controls]
