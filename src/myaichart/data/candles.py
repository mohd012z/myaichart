from __future__ import annotations

from pathlib import Path
from myaichart.models import Candle

try:
    import pandas as pd
    import pyarrow  # noqa: F401
    _PARQUET=True
except Exception:
    pd=None
    _PARQUET=False


class CandleStore:
    def __init__(self, root):
        self.root=Path(root)

    def path_for(self, symbol, timeframe):
        ext='parquet' if _PARQUET else 'jsonl'
        return self.root/'processed'/f'{symbol.lower()}_{timeframe.lower()}.{ext}'

    def write(self, symbol, timeframe, candles):
        candles=list(candles)
        path=self.path_for(symbol,timeframe)
        path.parent.mkdir(parents=True,exist_ok=True)
        if _PARQUET:
            pd.DataFrame([c.model_dump(mode='json') for c in candles]).to_parquet(path,index=False)
        else:
            with path.open('w',encoding='utf-8') as fh:
                for candle in candles:
                    fh.write(candle.model_dump_json()+'\n')
        return path

    def read(self, symbol, timeframe):
        path=self.path_for(symbol,timeframe)
        if not path.exists():
            return
        if path.suffix=='.parquet':
            if not _PARQUET:
                raise RuntimeError('pyarrow required to read parquet candles')
            for row in pd.read_parquet(path).to_dict('records'):
                yield Candle.model_validate(row)
        else:
            with path.open(encoding='utf-8') as fh:
                for line in fh:
                    if line.strip(): yield Candle.model_validate_json(line)
