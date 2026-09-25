from typing import Protocol


class HistoricalProvider(Protocol):
    async def fetch_ticks(self, symbol: str, start_utc, end_utc): ...
