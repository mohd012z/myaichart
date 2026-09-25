from dataclasses import dataclass

@dataclass(frozen=True)
class IntervalState:
    observed_market_state: str
    reference_market_state: str | None
    reason: str


def classify_interval(*,ticks_present: bool,reference_state: str|None,outage: bool,weekend: bool):
    if ticks_present:
        return IntervalState('OPEN',reference_state,'OBSERVED_TICKS')
    if weekend:
        return IntervalState('WEEKEND',reference_state,'WEEKEND_NO_TICKS')
    if outage:
        return IntervalState('SOURCE_OUTAGE',reference_state,'KNOWN_SOURCE_OUTAGE')
    if reference_state in {'HOLIDAY','EARLY_CLOSE','SCHEDULED_BREAK'}:
        return IntervalState(reference_state,reference_state,'REFERENCE_SUPPORTED_NO_TICKS')
    return IntervalState('DATA_GAP',reference_state,'UNEXPLAINED_NO_TICKS')
