import math
import numpy as np


def true_range(*,high,low,prev_close):
    return max(high-low,abs(high-prev_close),abs(low-prev_close))


def atr(true_ranges,period=14):
    vals=list(true_ranges)
    if not vals: return None
    window=vals[-period:]
    return sum(window)/len(window)


def realized_vol(closes,period=20):
    vals=list(closes)[-period-1:]
    if len(vals)<2: return None
    rets=[math.log(vals[i]/vals[i-1]) for i in range(1,len(vals)) if vals[i-1]>0 and vals[i]>0]
    return float(np.std(rets,ddof=0)) if rets else None
