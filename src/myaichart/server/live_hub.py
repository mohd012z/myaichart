"""Live broadcast hub for /ws/live.

Fans out real candle_update messages to all connected clients. On connect a
client receives the backfill (last N candles of the active timeframe) first,
so a new client is never blank — then the live stream. When no real data is
configured (testing / empty store) it falls back to the contract stub message
from websocket.py, so the dashboard keeps working pre-data.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from myaichart.models import Candle
from myaichart.server.websocket import testing_message

MYT_MS = 8 * 3600 * 1000


def candle_to_chart(c: Candle, side: str = "mid") -> dict:
    """Canonical Candle -> Lightweight Charts candle row (UTC epoch seconds)."""
    g = {
        "open": c.mid_open, "high": c.mid_high, "low": c.mid_low, "close": c.mid_close,
    } if side == "mid" else (
        {
            "open": c.bid_open, "high": c.bid_high, "low": c.bid_low, "close": c.bid_close,
        } if side == "bid" else
        {
            "open": c.ask_open, "high": c.ask_high, "low": c.ask_low, "close": c.ask_close,
        }
    )
    return {
        "time": int(c.time_open_utc.timestamp()),
        **g,
        "volume": c.tick_count,
        "source": c.state.value,
    }


def _ohlc_side(c: Candle, side: str) -> dict:
    return {"o": getattr(c, f"{side}_open"), "h": getattr(c, f"{side}_high"),
            "l": getattr(c, f"{side}_low"), "c": getattr(c, f"{side}_close")}


def candle_update_message(c: Candle, symbol: str, side: str = "mid") -> dict:
    """The /ws/live candle_update shape (matches the contract the UI/tests expect)."""
    bid, ask = _ohlc_side(c, "bid"), _ohlc_side(c, "ask")
    return {
        "type": "candle_update",
        "symbol": symbol,
        "timeframe": c.timeframe,
        "state": c.state.value,
        "bucket_start_utc": c.time_open_utc.isoformat().replace("+00:00", "Z"),
        "bucket_start_myt": (c.time_open_utc + timedelta(milliseconds=MYT_MS)).isoformat(),
        "bid": bid,
        "ask": ask,
        "mid": _ohlc_side(c, "mid"),
        "spread": {"last": c.ask_close - c.bid_close, "mean": c.ask_close - c.bid_close,
                   "max": c.ask_close - c.bid_close},
        "tick_count": c.tick_count,
    }


class LiveHub:
    def __init__(self, *, backfill_fn=None, default_symbol: str = "XAUUSD",
                 default_tf: str = "M5", no_data_message=None):
        self._clients: set = set()
        self._backfill_fn = backfill_fn  # async () -> dict[tf, list[Candle]]
        self.default_symbol = default_symbol
        self.default_tf = default_tf
        self._no_data_message = no_data_message or testing_message()
        self._last_update: Candle | None = None
        self._lock = asyncio.Lock()

    async def register(self, ws) -> None:
        async with self._lock:
            self._clients.add(ws)
        try:
            backfill = await self._backfill() if self._backfill_fn else None
            if backfill:
                # real history available -> send it (no misleading stub first)
                await ws.send_json({"type": "backfill", "data": backfill})
            elif self._last_update is not None:
                # no history configured but a candle is forming -> send it
                await ws.send_json(candle_update_message(self._last_update, self.default_symbol))
            else:
                # no data at all -> the contract stub keeps the dashboard working
                await ws.send_json(self._no_data_message)
        except Exception:
            async with self._lock:
                self._clients.discard(ws)

    async def unregister(self, ws) -> None:
        async with self._lock:
            self._clients.discard(ws)

    async def _backfill(self) -> dict | None:
        try:
            data = await self._backfill_fn()
            if not data:
                return None
            out = {}
            for tf, candles in data.items():
                out[tf] = [candle_to_chart(c) for c in candles[-500:]]
            return out or None
        except Exception:
            return None

    async def publish(self, candle: Candle) -> int:
        """Broadcast a candle update; returns number of clients delivered to."""
        self._last_update = candle
        msg = candle_update_message(candle, self.default_symbol)
        dead = []
        async with self._lock:
            clients = list(self._clients)
        for ws in clients:
            try:
                await ws.send_json(msg)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._clients.discard(ws)
        return len(clients) - len(dead)

    @property
    def client_count(self) -> int:
        return len(self._clients)
