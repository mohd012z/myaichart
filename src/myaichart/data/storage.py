from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterator
from myaichart.models import NormalizedTick

try:
    import pandas as pd
    import pyarrow  # noqa: F401
    _PARQUET = True
except Exception:
    pd = None
    _PARQUET = False


class RawTickStore:
    """Immutable, idempotent raw tick store.

    Each chunk name is content-addressed from source identities. Replaying the
    exact same source chunk is therefore a no-op instead of a duplicate write.
    Parquet is preferred when available; JSONL is the offline fallback.
    """

    def __init__(self, root: Path):
        self.root = Path(root)

    def append_chunk(self, ticks: list[NormalizedTick]) -> None:
        if not ticks:
            return
        by_day: dict[tuple[str, str], list[NormalizedTick]] = {}
        for tick in ticks:
            key = (tick.symbol, tick.source_timestamp_utc.date().isoformat())
            by_day.setdefault(key, []).append(tick)
        for (symbol, day), group in by_day.items():
            group = sorted(group, key=lambda t: (t.source_timestamp_utc, t.source, t.source_record_id))
            out = self.root / 'raw' / symbol / f'date={day}'
            out.mkdir(parents=True, exist_ok=True)
            digest = _chunk_digest(group)
            suffix = '.parquet' if _PARQUET else '.jsonl'
            first_ms = int(group[0].source_timestamp_utc.timestamp() * 1000)
            path = out / f'part-{first_ms:013d}-{digest}{suffix}'
            if path.exists():
                return
            if _PARQUET:
                pd.DataFrame([t.model_dump(mode='json') for t in group]).to_parquet(path, index=False)
            else:
                with path.open('x', encoding='utf-8') as fh:
                    for tick in group:
                        fh.write(tick.model_dump_json() + '\n')

    def _iter_files(self, symbol: str) -> Iterator[NormalizedTick]:
        base = self.root / 'raw' / symbol
        if not base.exists():
            return
        paths = sorted(list(base.glob('date=*/part-*.jsonl')) + list(base.glob('date=*/part-*.parquet')))
        for path in paths:
            if path.suffix == '.jsonl':
                with path.open(encoding='utf-8') as fh:
                    for line in fh:
                        if line.strip():
                            yield NormalizedTick.model_validate_json(line)
            else:
                if not _PARQUET:
                    raise RuntimeError('pyarrow required to read parquet tick store')
                for row in pd.read_parquet(path).to_dict('records'):
                    yield NormalizedTick.model_validate(row)

    def iter_all(self, symbol: str, *, dedupe: bool = True):
        seen: set[tuple[str, str]] = set()
        for tick in self._iter_files(symbol):
            identity = (tick.source, tick.source_record_id)
            if dedupe and identity in seen:
                continue
            seen.add(identity)
            yield tick

    def iter_range(self, symbol, start_utc, end_utc):
        for tick in self.iter_all(symbol):
            if start_utc <= tick.source_timestamp_utc <= end_utc:
                yield tick


def _chunk_digest(group: list[NormalizedTick]) -> str:
    h = hashlib.sha256()
    for tick in group:
        h.update(tick.source.encode())
        h.update(b'|')
        h.update(tick.source_record_id.encode())
        h.update(b'\n')
    return h.hexdigest()[:24]
