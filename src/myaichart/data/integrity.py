from __future__ import annotations

import hashlib
import json
from datetime import timedelta, timezone
from pathlib import Path
from myaichart.data.storage import RawTickStore
from myaichart.marketstate.classifier import classify_interval
from myaichart.marketstate.sessions import dukascopy_reference_state


def _sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda:fh.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()


def verify_dataset(root, symbol='XAUUSD'):
    root=Path(root)
    files=sorted([p for p in root.rglob('*') if p.is_file()])
    checksums={str(p.relative_to(root)):_sha256(p) for p in files}
    store=RawTickStore(root)
    seen: set[tuple[str,str]] = set()
    sources=set()
    duplicate_count=0
    raw_tick_count=0
    hour_buckets=set()
    first_tick=None
    last_tick=None
    for tick in store.iter_all(symbol, dedupe=False):
        raw_tick_count += 1
        sources.add(tick.source)
        identity=(tick.source,tick.source_record_id)
        if identity in seen:
            duplicate_count += 1
        else:
            seen.add(identity)
        ts=tick.source_timestamp_utc.astimezone(timezone.utc)
        hour_buckets.add(ts.replace(minute=0,second=0,microsecond=0))
        first_tick = ts if first_tick is None or ts < first_tick else first_tick
        last_tick = ts if last_tick is None or ts > last_tick else last_tick

    missing_hour_count=0
    scheduled_break_hour_count=0
    unexplained_missing_hour_count=0
    data_gap_count=0
    source=next(iter(sources)) if len(sources)==1 else None

    if hour_buckets:
        ordered=sorted(hour_buckets)
        for a,b in zip(ordered,ordered[1:]):
            gap_hours=int((b-a).total_seconds()//3600)-1
            if gap_hours<=0:
                continue

            missing_hour_count += gap_hours
            unexplained_in_gap=0
            for offset in range(1,gap_hours+1):
                hour=a+timedelta(hours=offset)
                reference_state=(
                    dukascopy_reference_state(symbol,hour)
                    if source=='dukascopy'
                    else None
                )
                state=classify_interval(
                    ticks_present=False,
                    reference_state=reference_state,
                    outage=False,
                    weekend=False,
                ).observed_market_state
                if state=='SCHEDULED_BREAK':
                    scheduled_break_hour_count += 1
                else:
                    unexplained_missing_hour_count += 1
                    unexplained_in_gap += 1
            if unexplained_in_gap:
                data_gap_count += 1

    return {
        'raw_tick_count':raw_tick_count,
        'unique_tick_count':len(seen),
        'duplicate_count':duplicate_count,
        'data_gap_count':data_gap_count,
        'missing_hour_count':missing_hour_count,
        'scheduled_break_hour_count':scheduled_break_hour_count,
        'unexplained_missing_hour_count':unexplained_missing_hour_count,
        'first_tick_utc':None if first_tick is None else first_tick.isoformat(),
        'last_tick_utc':None if last_tick is None else last_tick.isoformat(),
        'checksum_manifest':checksums,
    }


def write_metadata(root, *, collection=None, provenance=None, integrity=None):
    root=Path(root)
    meta=root/'metadata'
    meta.mkdir(parents=True,exist_ok=True)

    integrity_payload = integrity if integrity is not None else verify_dataset(root)
    payloads={
        'collection.json': collection or {},
        'provenance.json': provenance or {},
        'integrity.json': integrity_payload,
        'checksums.json': integrity_payload.get('checksum_manifest',{}),
    }
    for name,payload in payloads.items():
        (meta/name).write_text(json.dumps(payload,indent=2,default=str),encoding='utf-8')
    return payloads
