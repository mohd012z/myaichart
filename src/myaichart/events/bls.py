from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import hashlib
import httpx

from .models import EconomicEvent

BLS_ICS_URL = 'https://www.bls.gov/schedule/news_release/bls.ics'

_FAMILIES = (
    ('consumer price index', 'CPI'),
    ('employment situation', 'EMPLOYMENT_SITUATION'),
    ('producer price index', 'PPI'),
    ('job openings', 'JOLTS'),
    ('employment cost index', 'ECI'),
    ('real earnings', 'REAL_EARNINGS'),
    ('import and export price', 'IMPORT_EXPORT_PRICES'),
)


def _unfold_ics(text: str) -> list[str]:
    lines=[]
    for raw in text.replace('\r\n','\n').replace('\r','\n').split('\n'):
        if raw.startswith((' ', '\t')) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _family(summary: str) -> str:
    lower=summary.lower()
    for needle, family in _FAMILIES:
        if needle in lower:
            return family
    return 'BLS_OTHER'


def _parse_dt(key: str, value: str) -> datetime:
    tz=timezone.utc
    if ';TZID=' in key:
        tz=ZoneInfo(key.split(';TZID=',1)[1])
    if value.endswith('Z'):
        tz=timezone.utc
        value=value[:-1]
    fmt='%Y%m%dT%H%M%S' if len(value)>=15 else '%Y%m%dT%H%M'
    return datetime.strptime(value,fmt).replace(tzinfo=tz)


def parse_ics(text: str) -> list[EconomicEvent]:
    events=[]
    block=None
    for line in _unfold_ics(text):
        if line == 'BEGIN:VEVENT':
            block={}
            continue
        if line == 'END:VEVENT':
            if block is not None:
                dt_pair=next(((k,v) for k,v in block.items() if k.startswith('DTSTART')),None)
                summary=block.get('SUMMARY')
                if dt_pair and summary:
                    source_time=_parse_dt(*dt_pair)
                    fallback=hashlib.sha256(f'{source_time.isoformat()}|{summary}'.encode()).hexdigest()[:20]
                    uid=block.get('UID') or f'bls-{fallback}'
                    events.append(EconomicEvent.from_source_time(
                        event_id=uid,
                        family=_family(summary),
                        name=summary,
                        source='BLS',
                        source_time=source_time,
                        source_url=block.get('URL') or BLS_ICS_URL,
                    ))
            block=None
            continue
        if block is not None and ':' in line:
            key,value=line.split(':',1)
            block[key]=value.replace('\\,',',').replace('\\n',' ')
    return sorted(events,key=lambda e:e.scheduled_time_utc)


def parse_events(records):
    return [r if isinstance(r,EconomicEvent) else EconomicEvent.from_source_time(**r) for r in records]


async def fetch_calendar(*, client: httpx.AsyncClient | None = None) -> list[EconomicEvent]:
    owns=client is None
    client=client or httpx.AsyncClient(timeout=30,headers={'User-Agent':'myaichart/0.1 research calendar client'})
    try:
        response=await client.get(BLS_ICS_URL)
        response.raise_for_status()
        return parse_ics(response.text)
    finally:
        if owns:
            await client.aclose()
