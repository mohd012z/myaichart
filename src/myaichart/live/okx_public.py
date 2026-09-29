"""OKX public WebSocket/REST adapter (PR #4 FeedAdapter spine).

First end-to-end live path for the Market Hub: anonymous, no account, no
key — the only exchange the 2026-09-28 egress benchmark proved reachable
from the cluster box (``wss://ws.okx.com:8443/ws/v5/public``).

Honesty rules, same as the rest of the hub:
- ``stream`` yields *raw* :class:`MarketTick` from the ``tickers`` channel
  (best bid/ask + last). The subscribe snapshot (all-``"-"`` fields) is
  skipped, never faked.
- ``backfill`` uses public 1m candles. OKX has no public tick-history API,
  so a gap is recovered as **candle-summary ticks** (``bid=ask=close``,
  raw carries the OHLC + ``"candle-summary": True``) — the engine rebuilds
  M1 from them, and the label is preserved so consumers never mistake them
  for ticks. No window → no fabrication.
- XAUUSD is deliberately *not* in the symbol map: gold is broker-sourced
  (Fatah's decision); this adapter covers the crypto instruments only, and
  the spine is provider-agnostic, so the broker adapter slots in beside it.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Callable, Optional

from myaichart.market.adapter_base import FeedAdapter
from myaichart.market.tick import MarketTick, SourceClass

WS_URL = "wss://ws.okx.com:8443/ws/v5/public"
REST_BASE = "https://www.okx.com"
PING_EVERY_S = 20.0  # OKX drops idle public sockets at ~30s
RECONNECT_BACKOFF = (1.0, 2.0, 5.0, 10.0)

# canonical hub symbol -> OKX native instId
_SYMBOL_MAP = {
    "BTCUSDT": "BTC-USDT",
    "ETHUSDT": "ETH-USDT",
    "SOLUSDT": "SOL-USDT",
    "XRPUSDT": "XRP-USDT",
}

Bar = dict[str, Any]  # {"ts","o","h","c","l","vol","confirm"}


class OkxPublicAdapter(FeedAdapter):
    provider = "OKX"
    source_class = SourceClass.EXCHANGE

    def __init__(self, *, ws_factory: Optional[Callable] = None,
                 http_get: Optional[Callable[[str, dict], Any]] = None,
                 ping_every_s: float = PING_EVERY_S,
                 max_reconnects: int = 8):
        """``ws_factory()`` must return an async context manager yielding an
        object with ``send(str)``/``recv() -> str``. Defaults to the real
        ``websockets.connect(WS_URL)``. ``http_get(url, params) -> json``
        defaults to a sync ``httpx.get``. Both are injectable for tests."""
        self._ws_factory = ws_factory or self._default_ws_factory
        self._http_get = http_get or self._default_http_get
        self._ping_every_s = ping_every_s
        self._max_reconnects = max_reconnects
        self._closed = False

    # ------------------------------------------------------------------ #
    # FeedAdapter contract
    # ------------------------------------------------------------------ #
    def symbol_map(self, canonical: str) -> Optional[str]:
        return _SYMBOL_MAP.get(canonical)

    async def stream(self, canonical_symbols: list[str]) -> AsyncIterator[MarketTick]:
        natives = []
        canon_of: dict[str, str] = {}
        for c in canonical_symbols:
            n = self.symbol_map(c)
            if n is None:
                continue
            natives.append(n)
            canon_of[n] = c
        if not natives:
            return

        attempt = 0
        while not self._closed and attempt <= self._max_reconnects:
            try:
                async with self._ws_factory() as ws:
                    await ws.send(json.dumps({
                        "op": "subscribe",
                        "args": [{"channel": "tickers", "instId": n} for n in natives],
                    }))
                    attempt = 0  # a healthy session resets backoff
                    async for raw in self._messages(ws):
                        for tick in self._parse(raw, canon_of):
                            yield tick
            except asyncio.CancelledError:
                raise
            except Exception:
                attempt += 1
                if attempt > self._max_reconnects:
                    raise
                await asyncio.sleep(RECONNECT_BACKOFF[min(attempt, len(RECONNECT_BACKOFF)) - 1])
            if self._closed:
                return

    def backfill(self, canonical: str, start: datetime, end: datetime) -> list[MarketTick]:
        native = self.symbol_map(canonical)
        if native is None:
            return []
        s, e = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
        if e <= s:
            return []
        try:
            data = self._http_get(f"{REST_BASE}/api/v5/market/candles",
                                  {"instId": native, "bar": "1m", "limit": "300"})
            rows: list[list[str]] = data.get("data", []) if isinstance(data, dict) else []
        except Exception:
            return []  # no window -> no fabrication
        out: list[MarketTick] = []
        for row in rows:
            if len(row) < 9:
                continue
            ts = datetime.fromtimestamp(int(row[0]) / 1000, tz=timezone.utc)
            if not (s <= ts < e):
                continue
            if row[8] != "1":  # only CLOSED bars are authority
                continue
            out.append(self._candle_summary_tick(canonical, native, ts, row))
        return sorted(out, key=lambda t: t.ts_exchange)

    def close(self) -> None:
        self._closed = True

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #
    @staticmethod
    def _default_ws_factory():
        import websockets
        return websockets.connect(WS_URL, open_timeout=10, max_size=2 ** 20)

    @staticmethod
    def _default_http_get(url: str, params: dict) -> Any:
        import httpx
        r = httpx.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    async def _messages(self, ws):
        """recv() loop with a background keepalive ping (OKX needs 'ping'
        text every <30s; replies 'pong' as a plain string)."""
        stop = asyncio.Event()

        async def _pinger():
            while not stop.is_set():
                try:
                    await asyncio.wait_for(stop.wait(), timeout=self._ping_every_s)
                except asyncio.TimeoutError:
                    if not stop.is_set():
                        await ws.send("ping")

        pinger = asyncio.create_task(_pinger())
        try:
            while True:
                msg = await ws.recv()
                if isinstance(msg, (bytes, bytearray)):
                    continue
                if msg in ("pong", "ping"):
                    continue
                yield msg
        finally:
            stop.set()
            pinger.cancel()

    @staticmethod
    def _parse(raw: str, canon_of: dict[str, str]) -> list[MarketTick]:
        try:
            msg = json.loads(raw)
        except (ValueError, TypeError):
            return []
        if msg.get("event") in ("subscribe", "error") or "data" not in msg:
            return []
        arg = msg.get("arg") or {}
        if arg.get("channel") != "tickers":
            return []
        out = []
        for d in msg["data"]:
            native = d.get("instId")
            canonical = canon_of.get(native)
            if canonical is None:
                continue
            last = _num(d.get("last"))
            bid = _num(d.get("bidPx"))
            ask = _num(d.get("askPx"))
            ts_ms = d.get("ts")
            if last is None and bid is None and ask is None:
                continue  # subscribe snapshot: all "-" — skip, never fake
            if not ts_ms:
                continue
            out.append(MarketTick(
                symbol=canonical,
                provider="OKX",
                provider_symbol=native,
                source_class=SourceClass.EXCHANGE,
                ts_exchange=datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc),
                ts_received=datetime.now(timezone.utc),
                bid=bid, ask=ask, last=last,
                raw=d,
            ))
        return out

    @staticmethod
    def _candle_summary_tick(canonical: str, native: str, ts: datetime, row: list[str]) -> MarketTick:
        o, h, c, l = _num(row[1]), _num(row[2]), _num(row[3]), _num(row[4])
        vol = _num(row[5])
        close = c if c is not None else (h if h is not None else l)
        assert close is not None  # row[2]/row[3] both "-" is not a real bar
        return MarketTick(
            symbol=canonical,
            provider="OKX",
            provider_symbol=native,
            source_class=SourceClass.EXCHANGE,
            ts_exchange=ts,
            ts_received=datetime.now(timezone.utc),
            bid=close, ask=close, last=close,
            raw={"instId": native, "ohlc": {"o": o, "h": h, "c": c, "l": l},
                 "vol": vol, "candle-summary": True},
        )


def _num(v: Any) -> Optional[float]:
    if v is None or v == "-" or v == "":
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # NaN guard
