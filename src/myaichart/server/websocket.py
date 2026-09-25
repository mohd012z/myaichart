from datetime import datetime, timezone
from zoneinfo import ZoneInfo

MYT=ZoneInfo('Asia/Kuala_Lumpur')

def testing_message():
    ts=datetime(2026,9,25,7,40,tzinfo=timezone.utc)
    def o(v): return {'o':v,'h':v,'l':v,'c':v}
    return {'type':'candle_update','symbol':'XAUUSD','timeframe':'M5','state':'LIVE',
            'bucket_start_utc':ts.isoformat().replace('+00:00','Z'),'bucket_start_myt':ts.astimezone(MYT).isoformat(),
            'bid':o(10.0),'ask':o(10.2),'mid':o(10.1),'spread':{'last':0.2,'mean':0.2,'max':0.2},'tick_count':1}
