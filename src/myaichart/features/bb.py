from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class BollingerResult:
    mid: float
    upper: float
    lower: float
    percent_b: float | None
    bandwidth: float | None


def bollinger(values,period=20,deviations=2):
    vals=np.asarray(list(values)[-period:],dtype=float)
    if len(vals)<period: raise ValueError('insufficient values')
    mid=float(vals.mean()); sd=float(vals.std(ddof=0))
    upper=mid+deviations*sd; lower=mid-deviations*sd
    width=upper-lower
    pb=None if width==0 else float((vals[-1]-lower)/width)
    bw=None if mid==0 else float(width/mid)
    return BollingerResult(mid,upper,lower,pb,bw)
