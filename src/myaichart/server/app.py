from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
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

logger = logging.getLogger('myaichart.server')

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


def create_app(*, testing: bool = False, data_dir=None, live_hub: LiveHub | None = None,
               live_pipeline=None):
    """Build the myaichart server.

    ``live_pipeline`` (optional, a ``LivePipeline`` from ``myaichart.live``)
    wires the live feed: its publisher hook feeds every ``CandleUpdate`` to
    the hub so ``/ws/live`` carries real-time candles, and its HealthEngine
    powers ``/api/health/providers``. The pipeline runs under the app
    lifespan (started on boot, stopped on shutdown). Without a pipeline the
    server is unchanged (static store + manual ingest only).
    """
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
        hub_symbol = live_pipeline.symbol if live_pipeline is not None else 'XAUUSD'

        async def _backfill(symbol: str = hub_symbol):
            if store is None:
                return None
            out = {}
            for tf in TIMEFRAMES:
                rows = list(store.read(symbol, tf) or [])
                if rows:
                    out[tf] = rows
            return out or None
        live_hub = LiveHub(backfill_fn=_backfill, default_symbol=hub_symbol)
    app.state.live_hub = live_hub
    app.state.store = store
    app.state.engine = engine

    # ---- live feed (PR #7 pipeline -> hub: the documented seam) ----
    app.state.live_pipeline = live_pipeline
    if live_pipeline is not None:
        app.state.health_engine = live_pipeline.health

        async def _on_candle_update(update):
            # Every CandleUpdate (per timeframe) is broadcast to /ws/live —
            # the chart renders per-TF streams; the hub is the sole fan-out.
            await live_hub.publish(update.candle)

        async def _run_feed():
            try:
                await live_pipeline.run_with_watchdog()
            except asyncio.CancelledError:
                raise
            except Exception:
                # A broken feed must not take the server down: the health
                # engine reports STALE/DISCONNECTED and /ws/live goes quiet.
                logger.exception('live feed %s crashed', live_pipeline.symbol)

        live_pipeline.publisher = _on_candle_update

        @asynccontextmanager
        async def _lifespan(_app):
            task = asyncio.create_task(_run_feed())
            try:
                yield
            finally:
                live_pipeline.stop()
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        app.router.lifespan_context = _lifespan

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

    @app.get('/api/live/status')
    def live_status():
        """Pipeline state for the feed-health panel (PR #7 stats)."""
        p = getattr(app.state, 'live_pipeline', None)
        if p is None:
            return {'configured': False}
        s = p.stats
        return {
            'configured': True, 'symbol': p.symbol, 'status': p.status,
            'ticks_in': s.ticks_in, 'normalized': s.normalized,
            'duplicates': s.duplicates, 'dropped_no_price': s.dropped_no_price,
            'candles_published': s.candles_published, 'outages': s.outages,
        }

    @app.get('/api/sessions')
    def sessions():
        """Server-authoritative Tokyo/US first-candle zones (read-only in UI).

        The reference time is the latest stored M1 candle (data-driven),
        not the wall clock: in live operation the latest candle ≈ now so
        behaviour is identical, but for historical/backfilled/replayed data
        the zones are computed relative to the data's own timeline — a
        wall-clock reference would walk to *today's* open and miss all
        candles older than that (zones silently empty once data lags)."""
        rows = _m1_rows()
        if rows:
            ref = max(c.time_open_utc for c in rows)
        else:
            ref = datetime.now(timezone.utc)
        zones = session_zones(rows, ref)
        return {'now_utc': datetime.now(timezone.utc).isoformat(), 'zones': [
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
