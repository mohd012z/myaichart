from pydantic import BaseModel

class OHLC(BaseModel):
    o: float; h: float; l: float; c: float

class SpreadMsg(BaseModel):
    last: float; mean: float; max: float

class CandleUpdateMessage(BaseModel):
    type: str='candle_update'
    symbol: str
    timeframe: str
    state: str
    bucket_start_utc: str
    bucket_start_myt: str
    bid: OHLC
    ask: OHLC
    mid: OHLC
    spread: SpreadMsg
    tick_count: int
