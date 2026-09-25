from statistics import mean, median, pstdev
import numpy as np


def spread_stats(values):
    vals=[float(v) for v in values]
    if not vals: return {}
    return {'open':vals[0],'close':vals[-1],'min':min(vals),'max':max(vals),'mean':mean(vals),'median':median(vals),
            'std':pstdev(vals) if len(vals)>1 else 0.0,'p90':float(np.percentile(vals,90)),'p95':float(np.percentile(vals,95)),
            'p99':float(np.percentile(vals,99)),'range':max(vals)-min(vals)}


def classify_spread(current,history,*,absolute_wide=None):
    vals=[float(v) for v in history if v is not None]
    if not vals: return 'UNKNOWN'
    p75,p95,p99=np.percentile(vals,[75,95,99])
    if absolute_wide is not None and current>=absolute_wide: return 'EXTREME'
    if current>=p99: return 'EXTREME'
    if current>=p95: return 'WIDE'
    if current>=p75: return 'ELEVATED'
    return 'NORMAL'
