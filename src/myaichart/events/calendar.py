def sync_events(*sources):
    by_id={}
    for source in sources:
        for event in source:
            by_id[event.event_id]=event
    return sorted(by_id.values(),key=lambda e:e.scheduled_time_utc)
