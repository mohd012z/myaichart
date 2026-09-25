from __future__ import annotations

import json
from pathlib import Path
from myaichart.models import NormalizedTick

try:
    import pandas as pd
    import pyarrow  # noqa: F401
    _PARQUET = True
except Exception:
    pd = None
    _PARQUET = False


class RawTickStore:
    """Append-only raw tick store.

    Parquet is used when pyarrow is installed. Offline/minimal installations
    use newline-delimited JSON without changing the public API.
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
            out = self.root / 'raw' / symbol / f'date={day}'
            out.mkdir(parents=True, exist_ok=True)
            first = _safe(group[0].source_record_id)
            if _PARQUET:
                path = out / f'part-{first}.parquet'
                pd.DataFrame([t.model_dump(mode='json') for t in group]).to_parquet(path, index=False)
            else:
                path = out / f'part-{first}.jsonl'
                with path.open('x', encoding='utf-8') as fh:
                    for tick in group:
                        fh.write(tick.model_dump_json() + '\n')

    def iter_range(self, symbol, start_utc, end_utc):
        base = self.root / 'raw' / symbol
        if not base.exists():
            return
        paths = sorted(list(base.glob('date=*/part-*.jsonl')) + list(base.glob('date=*/part-*.parquet')))
        for path in paths:
            if path.suffix == '.jsonl':
                with path.open(encoding='utf-8') as fh:
                    rows = (json.loads(line) for line in fh if line.strip())
                    for row in rows:
                        tick = NormalizedTick.model_validate(row)
                        if start_utc <= tick.source_timestamp_utc <= end_utc:
                            yield tick
            else:
                if not _PARQUET:
                    raise RuntimeError('pyarrow required to read parquet tick store')
                for row in pd.read_parquet(path).to_dict('records'):
                    tick = NormalizedTick.model_validate(row)
                    if start_utc <= tick.source_timestamp_utc <= end_utc:
                        yield tick


def _safe(value: str) -> str:
    return ''.join(ch if ch.isalnum() or ch in '-_.' else '_' for ch in value)[:120]
