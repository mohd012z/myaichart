from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
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


def _load_json(path: Path) -> dict:
    try:
        value=json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value,dict) else {}


def _as_utc(value, *, metadata: bool=False):
    if value is None:
        return None
    try:
        parsed=datetime.fromisoformat(value) if isinstance(value,str) else value
    except (TypeError, ValueError):
        return None if metadata else (_ for _ in ()).throw(ValueError('invalid expected timestamp'))
    if not isinstance(parsed,datetime) or parsed.tzinfo is None:
        if metadata:
            return None
        raise ValueError('expected timestamps must be timezone-aware')
    return parsed.astimezone(timezone.utc)


def verify_dataset(
    root,
    symbol='XAUUSD',
    *,
    expected_start_utc=None,
    expected_end_utc=None,
    source_hint=None,
):
    root=Path(root)
    files=sorted([p for p in root.rglob('*') if p.is_file()])
    checksums={str(p.relative_to(root)):_sha256(p) for p in files}

    collection=_load_json(root/'metadata'/'collection.json')
    provenance=_load_json(root/'metadata'/'provenance.json')
    expected_start=_as_utc(expected_start_utc)
    expected_end=_as_utc(expected_end_utc)
    if expected_start is None:
        expected_start=_as_utc(collection.get('requested_start_utc'),metadata=True)
    if expected_end is None:
        expected_end=_as_utc(collection.get('requested_end_utc'),metadata=True)
    if expected_start is not None and expected_end is not None and expected_end < expected_start:
        raise ValueError('expected_end_utc must be >= expected_start_utc')
    if (expected_start is None) != (expected_end is None):
        expected_start=None
        expected_end=None

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

    source=(source_hint or provenance.get('source'))
    if source is None and len(sources)==1:
        source=next(iter(sources))
    source=str(source).lower() if source is not None else None

    if expected_start is not None and expected_end is not None:
        coverage_start=expected_start.replace(minute=0,second=0,microsecond=0)
        coverage_end=expected_end.replace(minute=0,second=0,microsecond=0)
    elif hour_buckets:
        coverage_start=min(hour_buckets)
        coverage_end=max(hour_buckets)
    else:
        coverage_start=None
        coverage_end=None

    missing_hour_count=0
    scheduled_break_hour_count=0
    weekend_closed_hour_count=0
    unexplained_missing_hour_count=0
    data_gap_count=0
    in_unexplained_gap=False

    hour=coverage_start
    while hour is not None and coverage_end is not None and hour <= coverage_end:
        if hour in hour_buckets:
            in_unexplained_gap=False
            hour += timedelta(hours=1)
            continue

        missing_hour_count += 1
        reference_state=(
            dukascopy_reference_state(symbol,hour)
            if source=='dukascopy'
            else None
        )
        weekend = reference_state == 'WEEKEND'
        state=classify_interval(
            ticks_present=False,
            reference_state=None if weekend else reference_state,
            outage=False,
            weekend=weekend,
        ).observed_market_state
        if state=='WEEKEND':
            weekend_closed_hour_count += 1
            in_unexplained_gap=False
        elif state=='SCHEDULED_BREAK':
            scheduled_break_hour_count += 1
            in_unexplained_gap=False
        else:
            unexplained_missing_hour_count += 1
            if not in_unexplained_gap:
                data_gap_count += 1
                in_unexplained_gap=True
        hour += timedelta(hours=1)

    return {
        'raw_tick_count':raw_tick_count,
        'unique_tick_count':len(seen),
        'duplicate_count':duplicate_count,
        'data_gap_count':data_gap_count,
        'missing_hour_count':missing_hour_count,
        'scheduled_break_hour_count':scheduled_break_hour_count,
        'weekend_closed_hour_count':weekend_closed_hour_count,
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
