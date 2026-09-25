from statistics import mean, median


def imbalance(bid_size, ask_size):
    if bid_size is None or ask_size is None:
        return None
    den=bid_size+ask_size
    if den==0: return None
    return (bid_size-ask_size)/den


def liquidity_stats(bids,asks):
    pairs=[(b,a) for b,a in zip(bids,asks) if b is not None and a is not None]
    if not pairs: return {}
    bs=[p[0] for p in pairs]; ass=[p[1] for p in pairs]
    ims=[imbalance(b,a) for b,a in pairs]; ims=[x for x in ims if x is not None]
    return {'bid_mean':mean(bs),'bid_median':median(bs),'bid_min':min(bs),'bid_max':max(bs),
            'ask_mean':mean(ass),'ask_median':median(ass),'ask_min':min(ass),'ask_max':max(ass),
            'imbalance_mean':mean(ims) if ims else None,'imbalance_min':min(ims) if ims else None,'imbalance_max':max(ims) if ims else None}
