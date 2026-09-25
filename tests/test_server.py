from fastapi.testclient import TestClient
from myaichart.server.app import create_app


def test_health_and_timeframe_contract():
    client=TestClient(create_app(testing=True))
    assert client.get('/api/health').json()['ok'] is True
    frames=client.get('/api/timeframes').json()
    assert frames==['M1','M5','M15','M30','H1','H4','D1','W1','MN1']


def test_ws_message_contains_myt_and_bid_ask_mid():
    client=TestClient(create_app(testing=True))
    with client.websocket_connect('/ws/live') as ws:
        msg=ws.receive_json()
        assert {'type','symbol','timeframe','state','bucket_start_utc','bucket_start_myt'} <= msg.keys()
        assert {'bid','ask','mid','spread','tick_count'} <= msg.keys()
