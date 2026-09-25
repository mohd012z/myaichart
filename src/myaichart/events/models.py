from __future__ import annotations
from datetime import datetime
from dataclasses import dataclass, field, replace
from zoneinfo import ZoneInfo
from myaichart.timeutil import to_utc, to_myt


@dataclass(frozen=True)
class EventRevision:
    observed_at_utc: datetime
    old_previous: float | None
    new_previous: float | None
    revision_no: int


@dataclass(frozen=True)
class EconomicEvent:
    event_id: str
    family: str
    name: str
    source: str
    scheduled_time_source: datetime
    scheduled_time_utc: datetime
    scheduled_time_myt: datetime
    source_timezone: str
    source_url: str | None = None
    reference_period: str | None = None
    actual: float | None = None
    forecast: float | None = None
    forecast_source: str | None = None
    forecast_observed_at_utc: datetime | None = None
    previous: float | None = None
    revised_previous: float | None = None
    revision_no: int = 0
    verification_state: str = 'SCHEDULED'
    revisions: tuple[EventRevision, ...] = field(default_factory=tuple)

    @classmethod
    def from_source_time(cls, *, event_id, family, name, source, source_time, source_url=None, **kwargs):
        if source_time.tzinfo is None:
            raise ValueError('event source time must be timezone-aware')
        tzname=getattr(source_time.tzinfo,'key',str(source_time.tzinfo))
        return cls(event_id=event_id,family=family,name=name,source=source,
                   scheduled_time_source=source_time,scheduled_time_utc=to_utc(source_time),
                   scheduled_time_myt=to_myt(source_time),source_timezone=tzname,source_url=source_url,**kwargs)

    def with_revision(self, *, revised_previous, observed_at_utc):
        rev=EventRevision(observed_at_utc=to_utc(observed_at_utc),old_previous=self.previous if self.revised_previous is None else self.revised_previous,
                          new_previous=revised_previous,revision_no=self.revision_no+1)
        return replace(self,revised_previous=revised_previous,revision_no=self.revision_no+1,revisions=self.revisions+(rev,))
