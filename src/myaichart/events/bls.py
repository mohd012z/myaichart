from .models import EconomicEvent

def parse_events(records):
    return [r if isinstance(r,EconomicEvent) else EconomicEvent.from_source_time(**r) for r in records]
