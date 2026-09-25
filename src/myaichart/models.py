from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, ConfigDict, Field, model_validator


class CandleState(StrEnum):
    PENDING = "PENDING"
    LIVE = "LIVE"
    PROVISIONALLY_CLOSED = "PROVISIONALLY_CLOSED"
    FINAL = "FINAL"
    CORRECTED = "CORRECTED"
    RECOVERED = "RECOVERED"


class FeedStatus(StrEnum):
    CONNECTING = "CONNECTING"
    LIVE = "LIVE"
    DELAYED = "DELAYED"
    STALE = "STALE"
    RECONNECTING = "RECONNECTING"
    MARKET_CLOSED = "MARKET_CLOSED"
    HOLIDAY = "HOLIDAY"
    SOURCE_ERROR = "SOURCE_ERROR"


class BoundaryProfile(StrEnum):
    MYT_CALENDAR = "MYT_CALENDAR"
    SOURCE_SESSION = "SOURCE_SESSION"


class MarketState(StrEnum):
    OPEN = "OPEN"
    SCHEDULED_BREAK = "SCHEDULED_BREAK"
    WEEKEND = "WEEKEND"
    HOLIDAY = "HOLIDAY"
    EARLY_CLOSE = "EARLY_CLOSE"
    DATA_GAP = "DATA_GAP"
    SOURCE_OUTAGE = "SOURCE_OUTAGE"
    UNKNOWN = "UNKNOWN"


class NormalizedTick(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol: str
    source: str
    source_record_id: str
    source_timestamp_utc: datetime
    received_timestamp_utc: datetime
    bid: float
    ask: float
    bid_volume_best: float | None = None
    ask_volume_best: float | None = None
    sequence_id: str | None = None

    @model_validator(mode="after")
    def validate_quote(self):
        if self.source_timestamp_utc.tzinfo is None or self.received_timestamp_utc.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        if self.bid <= 0 or self.ask <= 0 or self.ask < self.bid:
            raise ValueError("invalid bid/ask quote")
        return self

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    @property
    def spread_price(self) -> float:
        return self.ask - self.bid


class Candle(BaseModel):
    model_config = ConfigDict(frozen=True)
    symbol: str
    timeframe: str
    boundary_profile: BoundaryProfile
    time_open_utc: datetime
    time_close_utc: datetime
    state: CandleState
    bid_open: float
    bid_high: float
    bid_low: float
    bid_close: float
    ask_open: float
    ask_high: float
    ask_low: float
    ask_close: float
    mid_open: float
    mid_high: float
    mid_low: float
    mid_close: float
    tick_count: int = Field(ge=1)
    quote_change_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_ohlc(self):
        triples = [
            (self.bid_open, self.bid_high, self.bid_low, self.bid_close),
            (self.ask_open, self.ask_high, self.ask_low, self.ask_close),
            (self.mid_open, self.mid_high, self.mid_low, self.mid_close),
        ]
        for o, h, l, c in triples:
            if l > o or l > c or h < o or h < c or h < l:
                raise ValueError("invalid OHLC")
        return self
