from __future__ import annotations

import hashlib
import json
from datetime import timedelta
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
    ticks=[]
    for path in sorted((root/'raw'/symbol).glob('date=*/*')) if (root/'raw'/symbol).exists() else []:
        if path.suffix not in {'.jsonl','.parquet'}: continue
        if path.suffix=='.jsonl':
            from myaichart.models import NormalizedTick
            with path.open(encoding='utf-8') as fh:
                for line in fh:
                    if line.strip(): ticks.append(NormalizedTick.model_validate_json(line))
    ticks.sort(key=lambda t:(t.source_timestamp_utc,t.source,t.source_record_id))
    ids=[(t.source,t.source_record_id) for t in ticks]
    duplicate_count=len(ids)-len(set(ids))
    missing_hour_count=0
    data_gap_count=0
    for a,b in zip(ticks,ticks[1:]):
        gap=(b.source_timestamp_utc-a.source_timestamp_utc).total_seconds()
        if gap>3600:
            missing_hour_count += max(1,int(gap//3600)-1)
            data_gap_count += 1
    report={'raw_tick_count':len(ticks),'duplicate_count':duplicate_count,'data_gap_count':data_gap_count,
            'missing_hour_count':missing_hour_count,'checksum_manifest':checksums}
    return report


def write_metadata(root, *, collection=None, provenance=None, integrity=None):
    root=Path(root); meta=root/'metadata'; meta.mkdir(parents=True,exist_ok=True)
    payloads={'collection.json':collection or {},'provenance.json':provenance or {},'integrity.json':integrity or verify_dataset(root)}
    payloads['checksums.json']=payloads['integrity'].get('checksum_manifest',{})
    for name,payload in payloads.items():
        (meta/name).write_text(json.dumps(payload,indent=2,default=str),encoding='utf-8')
    return payloads
