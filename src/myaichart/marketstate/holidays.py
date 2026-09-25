from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class HolidayReference:
    date: date
    name: str
    jurisdiction: str
    expected_state: str
    source: str
