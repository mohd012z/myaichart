from __future__ import annotations

from pathlib import Path
from .models import EconomicEvent


class EventStore:
    def __init__(self, root):
        self.root=Path(root)

    @property
    def path(self):
        return self.root/'events'/'events_master.jsonl'

    def write(self, events):
        events=sorted(list(events),key=lambda e:(e.scheduled_time_utc,e.source,e.event_id))
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open('w',encoding='utf-8') as fh:
            for event in events:
                fh.write(_dump(event)+'\n')
        return self.path

    def read(self):
        if not self.path.exists():
            return
        import json
        from datetime import datetime
        for line in self.path.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            row=json.loads(line)
            source_time=datetime.fromisoformat(row['scheduled_time_source'])
            yield EconomicEvent.from_source_time(
                event_id=row['event_id'],family=row['family'],name=row['name'],source=row['source'],
                source_time=source_time,source_url=row.get('source_url'),reference_period=row.get('reference_period'),
                actual=row.get('actual'),forecast=row.get('forecast'),forecast_source=row.get('forecast_source'),
                previous=row.get('previous'),revised_previous=row.get('revised_previous'),revision_no=row.get('revision_no',0),
                verification_state=row.get('verification_state','SCHEDULED'))


def _dump(event: EconomicEvent) -> str:
    import json
    return json.dumps({
        'event_id':event.event_id,'family':event.family,'name':event.name,'source':event.source,
        'scheduled_time_source':event.scheduled_time_source.isoformat(),
        'scheduled_time_utc':event.scheduled_time_utc.isoformat(),
        'scheduled_time_myt':event.scheduled_time_myt.isoformat(),
        'source_timezone':event.source_timezone,'source_url':event.source_url,'reference_period':event.reference_period,
        'actual':event.actual,'forecast':event.forecast,'forecast_source':event.forecast_source,
        'previous':event.previous,'revised_previous':event.revised_previous,'revision_no':event.revision_no,
        'verification_state':event.verification_state,
    },separators=(',',':'))
