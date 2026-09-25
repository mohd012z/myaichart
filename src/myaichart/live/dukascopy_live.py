from __future__ import annotations

class DukascopyLiveAdapter:
    """Adapter boundary for a future JForex/live reference bridge.

    Live network credentials/transport are deliberately not embedded in the
    package. Integrations should emit the same normalized tick contract.
    """
    async def stream(self):
        if False:
            yield None
        return

    async def backfill(self, start_utc, end_utc):
        return []
