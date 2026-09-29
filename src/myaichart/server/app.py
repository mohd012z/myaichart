from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from myaichart.candles.engine import CandleEngine
from myaichart.data.candles import CandleStore
from myaichart.models import BoundaryProfile, NormalizedTick
from myaichart.server.live_hub import LiveHub, candle_to_chart
from myaichart.server.sessions import session_zones
from myaichart.server.websocket import testing_message

TIMEFRAMES = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1', 'MN1']


class IngestTick(BaseModel):
    """One CSV/JSON tick row from a collector (EA bridge, cTrader runner, ...)."""
    id: int
    utc: str
    symbol: str
    rowtype: str = "TICK"
    tf: str | None = None
    c1: float = 0.0
    c2: float = 0.0
    c3: float = 0.0
    c4: float = 0.0
    c5: float = 0.0


def create_app(*, testing: bool = False, data_dir=None, live_hub: LiveHub | None = None):
    app = FastAPI(title='myaichart')
    app.state.testing = testing

    # Cross-origin read for the chart surfaces. The web page is same-origin
    # (served by /web), but the Capacitor/veyra APK loads the chart from the
    # WebView origin (https://localhost) and must read myaichart REST + WS
    # cross-origin. CORS is a read-control concern only: the market-data
    # authority is unchanged (this server remains the sole source).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    web_root = Path(__file__).resolve().parents[3] / 'web'
    if web_root.exists():
        app.mount('/web', StaticFiles(directory=web_root, html=True), name='web')

    # ---- data spine (real when a store/engine is wired; stubs otherwise) ----
    store = CandleStore(data_dir) if data_dir is not None else None
    engine: CandleEngine | None = None
    if data_dir is not None:
        engine = CandleEngine(TIMEFRAMES, BoundaryProfile.MYT_CALENDAR)
    if live_hub is None:
        async def _backfill():
            if store is None:
                return None
            out = {}
            for tf in TIMEFRAMES:
                rows = list(store.read('XAUUSD', tf) or [])
                if rows:
                    out[tf] = rows
            return out or None
        live_hub = LiveHub(backfill_fn=_backfill)
    app.state.live_hub = live_hub
    app.state.store = store
    app.state.engine = engine

    def _m1_rows():
        if store is None:
            return []
        return list(store.read('XAUUSD', 'M1') or [])

    @app.get('/api/health')
    def health():
        return {'ok': True}

    @app.get('/api/timeframes')
    def timeframes():
        return TIMEFRAMES

    @app.get('/api/candles')
    def candles(symbol: str = 'XAUUSD', timeframe: str = 'M5', side: str = 'mid', limit: int = 500):
        if store is None:
            return {'symbol': symbol, 'timeframe': timeframe, 'side': side, 'candles': []}
        rows = list(store.read(symbol, timeframe) or [])[-limit:]
        return {
            'symbol': symbol, 'timeframe': timeframe, 'side': side,
            'candles': [candle_to_chart(c, side) for c in rows],
        }

    @app.get('/api/events')
    def events():
        return []

    @app.get('/api/backtest/{run_id}')
    def backtest(run_id: str):
        return {'run_id': run_id, 'status': 'unknown'}

    @app.get('/api/health/providers')
    def provider_health():
        """Provider health for the chart's feed-health panel (PR #4 HealthEngine)."""
        h = getattr(app.state, 'health_engine', None)
        return h.report() if h is not None else {
            'symbol': 'XAUUSD', 'hub_state': 'NO_AUTHORITY', 'authority': None,
            'providers': {}, 'divergence': {}, 'switch_log': [],
        }

    @app.get('/api/sessions')
    def sessions():
        """Server-authoritative Tokyo/US first-candle zones (read-only in UI)."""
        now = datetime.now(timezone.utc)
        zones = session_zones(_m1_rows(), now)
        return {'now_utc': now.isoformat(), 'zones': [
            {
                'name': z.name, 'exchange_tz': z.exchange_tz,
                'open_utc': z.open_utc.isoformat(),
                'high': z.high, 'low': z.low,
                'first_candle_utc': z.first_candle_utc.isoformat(),
                'source': z.source,
            } for z in zones
        ]}

    @app.post('/api/replay/control')
    def replay_control(payload: dict):
        return {'ok': True, 'control': payload}

    @app.post('/api/ticks/ingest')
    async def ingest(payload: list[IngestTick]):
        """Collector ingest endpoint (EA/cTrader runner POSTs CSV/JSON ticks).

        Normalizes -> dedupes via the candle engine -> broadcasts the latest
        update on /ws/live. No data configured -> accepted:false, no broadcast.
        """
        if engine is None or live_hub is None:
            return {'ok': False, 'reason': 'no-live-pipeline-configured', 'accepted': 0}
        accepted = 0
        last_candle = None
        for row in payload:
            if row.rowtype == 'CANDLE' and row.tf:
                continue  # candle rows are display-only; ticks are authority
            ts = datetime.fromisoformat(row.utc)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            tick = NormalizedTick(
                symbol=row.symbol,
                source='MT5-BRIDGE',
                source_record_id=str(row.id),
                source_timestamp_utc=ts,
                received_timestamp_utc=datetime.now(timezone.utc),
                bid=row.c1, ask=row.c2,
            )
            updates = engine.on_tick(tick)
            accepted += 1
            if updates:
                last_candle = updates[-1].candle
        if last_candle is not None:
            n = await live_hub.publish(last_candle)
            return {'ok': True, 'accepted': accepted, 'broadcast_to': n}
        return {'ok': True, 'accepted': accepted, 'broadcast_to': 0}

    @app.websocket('/ws/live')
    async def live(ws: WebSocket):
        # WebSocket is not subject to browser CORS (no preflight); the
        # server's market data is public read-only, so accept as before.
        await ws.accept()
        await live_hub.register(ws)
        try:
            while True:
                # keep-alive; client sends nothing, we hold the socket open
                await ws.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            await live_hub.unregister(ws)

    return app
