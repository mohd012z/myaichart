from __future__ import annotations

import argparse, asyncio, json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from myaichart.data.dukascopy import DukascopyHistoricalProvider, collect_range
from myaichart.data.storage import RawTickStore
from myaichart.data.integrity import verify_dataset, write_metadata
from myaichart.data.candles import CandleStore
from myaichart.candles.from_ticks import build_tick_candles
from myaichart.models import BoundaryProfile
from myaichart.server.app import create_app

MYT=ZoneInfo('Asia/Kuala_Lumpur')


def _range(args):
    if args.from_time:
        start=datetime.fromisoformat(args.from_time).replace(tzinfo=MYT).astimezone(timezone.utc)
    else:
        end=datetime.now(timezone.utc); start=end-timedelta(days=30*args.months)
    if args.to_time:
        end=datetime.fromisoformat(args.to_time).replace(tzinfo=MYT).astimezone(timezone.utc)
    else:
        end=datetime.now(timezone.utc)
    return start,end


def build_parser():
    p=argparse.ArgumentParser(prog='myaichart',description='XAUUSD evidence collector and realtime/replay workbench')
    p.add_argument('--data-dir',default='data')
    sub=p.add_subparsers(dest='command')
    c=sub.add_parser('collect'); c.add_argument('symbol',default='XAUUSD'); c.add_argument('--months',type=int,default=6); c.add_argument('--from',dest='from_time'); c.add_argument('--to',dest='to_time')
    v=sub.add_parser('verify'); v.add_argument('symbol',default='XAUUSD')
    a=sub.add_parser('aggregate'); a.add_argument('symbol'); a.add_argument('--timeframes',nargs='+',default=['M1','M5','M15','M30','H1','H4','D1','W1','MN1'])
    e=sub.add_parser('events'); e.add_argument('action',choices=['sync'])
    ef=sub.add_parser('effects'); ef.add_argument('action',choices=['build']); ef.add_argument('symbol',nargs='?',default='XAUUSD')
    s=sub.add_parser('serve'); s.add_argument('symbol',nargs='?',default='XAUUSD'); s.add_argument('--timezone',default='Asia/Kuala_Lumpur'); s.add_argument('--host',default='127.0.0.1'); s.add_argument('--port',type=int,default=8000)
    l=sub.add_parser('live'); l.add_argument('symbol'); l.add_argument('--source',default='mt5'); l.add_argument('--timezone',default='Asia/Kuala_Lumpur')
    r=sub.add_parser('replay'); r.add_argument('symbol'); r.add_argument('--from',dest='from_time'); r.add_argument('--speed',type=float,default=1); r.add_argument('--timezone',default='Asia/Kuala_Lumpur')
    return p


async def _collect(args):
    start,end=_range(args); root=Path(args.data_dir); store=RawTickStore(root); provider=DukascopyHistoricalProvider()
    stats=await collect_range(provider,store,args.symbol,start,end)
    report=verify_dataset(root,args.symbol)
    write_metadata(root,collection={'symbol':args.symbol,'requested_start_utc':start.isoformat(),'requested_end_utc':end.isoformat(),'tick_count':stats.tick_count,'chunk_count':stats.chunk_count,'first_tick_utc':stats.first_tick_utc,'last_tick_utc':stats.last_tick_utc},
                   provenance={'source':'dukascopy','display_timezone':'Asia/Kuala_Lumpur'},integrity=report)
    print(json.dumps({'ticks':stats.tick_count,'chunks':stats.chunk_count,'start_utc':start.isoformat(),'end_utc':end.isoformat()},default=str))


def main(argv=None):
    p=build_parser(); args=p.parse_args(argv)
    if not args.command: p.print_help(); return 0
    if args.command=='collect': asyncio.run(_collect(args)); return 0
    if args.command=='verify': print(json.dumps(verify_dataset(Path(args.data_dir),args.symbol),indent=2)); return 0
    if args.command=='aggregate':
        raw=RawTickStore(Path(args.data_dir))
        bars=build_tick_candles(raw.iter_all(args.symbol,dedupe=False),args.timeframes,BoundaryProfile.MYT_CALENDAR)
        processed=CandleStore(Path(args.data_dir))
        outputs={}
        for tf,items in bars.items():
            path=processed.write(args.symbol,tf,items); outputs[tf]={'candles':len(items),'path':str(path)}
        print(json.dumps({'symbol':args.symbol,'timeframes':outputs},default=str)); return 0
    if args.command in {'events','effects'}: print(json.dumps({'command':args.command,'action':args.action,'status':'configured'})); return 0
    if args.command=='serve':
        import uvicorn; uvicorn.run(create_app(),host=args.host,port=args.port); return 0
    if args.command=='live': print(json.dumps({'symbol':args.symbol,'source':args.source,'timezone':args.timezone,'status':'adapter-required'})); return 0
    if args.command=='replay': print(json.dumps({'symbol':args.symbol,'from':args.from_time,'speed':args.speed,'timezone':args.timezone,'status':'configured'})); return 0
    return 0

if __name__=='__main__': raise SystemExit(main())
