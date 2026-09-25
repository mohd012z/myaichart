from dataclasses import dataclass
from datetime import datetime
from myaichart.models import Candle


@dataclass(frozen=True)
class CandleRevision:
    candle_key: str
    corrected_at_utc: datetime
    reason: str
    old: Candle
    new: Candle
