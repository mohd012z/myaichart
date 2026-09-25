from __future__ import annotations

import hashlib
import json
from datetime import timezone
from pathlib import Path
from myaichart.data.storage import RawTickStore


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
    duplicate_count=0
    raw_tick_count=0
    hour_buckets=set()
    first_tick=None
    last_tick=None
    for tick in store.iter_all(symbol, dedupe=False):
        raw_tick_count += 1
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
    data_gap_count=0
    if hour_buckets:
        ordered=sorted(hour_buckets)
        for a,b in zip(ordered,ordered[1:]):
            gap_hours=int((b-a).total_seconds()//3600)-1
            if gap_hours>0:
                missing_hour_count += gap_hours
                data_gap_count += 1
    return {
        'raw_tick_count':raw_tick_count,
        'unique_tick_count':len(seen),
        'duplicate_count':duplicate_count,
        'data_gap_count':data_gap_count,
        'missing_hour_count':missing_hour_count,
        'first_tick_utc':None if first_tick is None else first_tick.isoformat(),
        'last_tick_utc':None if last_tick is None else last_tick.isoformat(),
        'checksum_manifest':checksums,
    }


def write_metadata(root, *, collection=None, provenance=None, integrity=None):
    root=Path(root); meta=root/'metadata'; meta.mkdir(parents=True,exist_ok=True)
    payloads={'collection.json':collection or {},'provenance.json':provenance or {},'integrity.json':integrity or verify_dataset(root)}
    payloads['checksums.json']=payloads['integrity'].get('checksum_manifest',{})
    for name,payload in payloads.items():
        (meta/name).write_text(json.dumps(payload,indent=2,default=str),encoding='utf-8')
    return payloads
