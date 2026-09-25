from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from .websocket import testing_message

TIMEFRAMES=['M1','M5','M15','M30','H1','H4','D1','W1','MN1']

def create_app(*,testing=False):
    app=FastAPI(title='myaichart')
    app.state.testing=testing
    web_root = Path(__file__).resolve().parents[3] / 'web'
    if web_root.exists():
        app.mount('/web', StaticFiles(directory=web_root, html=True), name='web')

    @app.get('/api/health')
    def health(): return {'ok':True}

    @app.get('/api/timeframes')
    def timeframes(): return TIMEFRAMES

    @app.get('/api/candles')
    def candles(symbol:str='XAUUSD',timeframe:str='M5',side:str='mid',**kwargs):
        return {'symbol':symbol,'timeframe':timeframe,'side':side,'candles':[]}

    @app.get('/api/events')
    def events(): return []

    @app.get('/api/backtest/{run_id}')
    def backtest(run_id:str): return {'run_id':run_id,'status':'unknown'}

    @app.post('/api/replay/control')
    def replay_control(payload:dict): return {'ok':True,'control':payload}

    @app.websocket('/ws/live')
    async def live(ws:WebSocket):
        await ws.accept()
        await ws.send_json(testing_message())
        if not testing:
            try:
                while True: await ws.receive_text()
            except Exception:
                pass
    return app
