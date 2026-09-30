"""Swing-structure features: ZigZag pivots, harmonic patterns, Elliott targets.

Method source (studied 2026-09-30 from public docs; no third-party code ingested):
FxMath Harmonic Hunter's published free-tools spec — in-EA ZigZag (deviation /
backstep 3 / depth), a pattern table with Fibonacci ratio bounds + ideals,
accuracy grading against the bounds, and explicit backtest trade rules.

Their FAQ text says "entry at D + 0.238×CD/2, SL 0.05×CD", but their actual
published signal (XAGUSD H1 bullish AB=CD, 2026-09-29: D=60.278, A=61.087,
AD=0.809) is arithmetically consistent ONLY with:
    entry = D + 0.705·AD         SL = entry − AD
    TP1/2/3 = entry + {2.70, 4.83, 6.33}·AD
which reproduces entry 60.848 / SL 60.039 (80.9 pips) / TP 63.030, 64.754,
65.971 / R:R 2.70, 4.83, 6.33 within ≤0.3 pips (the FAQ formula does not).
This module implements the *verified* rule and documents the discrepancy.

Elliott impulse targets use the public 5-wave table (wave 2 = 50–61.8% of 1,
wave 3 = 161.8/261.8% of 1, wave 4 = 38.2% of 3, wave 5 = 1/0.618/1.618 of 1).
"""
from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# ZigZag pivots (classic MetaQuotes-style: deviation / backstep / depth)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Pivot:
    index: int
    kind: str  # 'H' | 'L'
    price: float


def zigzag_pivots(highs, lows, *, deviation=0.03, backstep: int = 3, depth: int = 10):
    """Classic ZigZag pivots (deviation / backstep / depth).

    Candidates are local extrema: a high >= all highs within `backstep` bars
    on each side (lows mirrored). Walking the candidates, the current extreme
    is provisionally confirmed the moment price reverses from the *accepted*
    extreme by >= `deviation` and the new extreme is >= `depth` bars away;
    same-direction candidates that fail to meet deviation are dropped (noise),
    which is what keeps pivots alternating and >= deviation apart.
    """
    n = len(highs)
    if n < 3:
        return []
    cands: list[tuple[int, float, str]] = []
    for i in range(n):
        lo = max(0, i - backstep)
        hi = min(n, i + backstep + 1)
        if highs[i] == max(highs[lo:hi]) and hi - lo >= 2:
            cands.append((i, highs[i], 'H'))
        if lows[i] == min(lows[lo:hi]) and hi - lo >= 2:
            cands.append((i, lows[i], 'L'))
    cands.sort()
    out: list[Pivot] = []
    cur_i, cur_p, cur_k = -1, 0.0, ''
    for (i, p, k) in cands:
        if i <= cur_i:
            continue  # same bar already used, or going backwards
        if k == cur_k:
            # same direction: keep the more extreme candidate
            if (k == 'H' and p >= cur_p) or (k == 'L' and p <= cur_p):
                cur_i, cur_p = i, p
            continue
        if cur_i < 0:
            cur_i, cur_p, cur_k = i, p, k
            continue
        # direction change: confirm the previous extreme when price has
        # reversed from it by >= deviation and the extremes are deep enough
        if abs(p - cur_p) >= deviation * cur_p and (i - cur_i) >= depth:
            out.append(Pivot(cur_i, cur_k, cur_p))
            cur_i, cur_p, cur_k = i, p, k
    return out


# ---------------------------------------------------------------------------
# Harmonic patterns
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PatternSpec:
    name: str
    ratios: tuple  # ((key, lo, hi, ideal), ...)


# Ratio keys (canonical harmonic convention — retrace/extension ratios):
#   XAB = |XA|/|AB|  (>=1; a 38.2% retracement of XA => XAB ~ 2.618)
#   ABC = |AB|/|BC|  (>=1; a 61.8% extension of AB => ABC ~ 1.618)
#   BCD = |BC|/|CD|  (>=1; a 1.272 extension of BC => BCD ~ 1.272)
#   XAD = |XA|/|AD|  (>=1; a 78.6% extension of XA => XAD ~ 0.786... here
#                     XAD is also expressed as |XA|/|AD| so an extension
#                     beyond X gives XAD < 1)
# Bounds are the published harmonic tables; ideal = the ratio that grades 1.0.
# (The FxMath signal's published "XAB 0.854 / ABC 0.451 / BCD 2.372 / XAD
# 0.914" ratios were checked and do NOT reconcile under any one leg-ratio
# convention — likely a vendor typo. Only the trade levels are verified:
# entry/SL/TP reproduce from D=60.278, A=61.087 (AD=0.809) within 0.3 pips,
# which is what trade_levels implements.)
PATTERN_SPECS: tuple[PatternSpec, ...] = (
    PatternSpec('AB=CD', (
        ('XAB', 0.382, 2.618, 1.0),
        ('ABC', 0.618, 1.618, 1.0),
        ('BCD', 0.382, 1.618, 1.0),
        ('XAD', 0.382, 1.618, 1.0),
    )),
    PatternSpec('Gartley', (
        ('XAB', 1.272, 2.618, 1.377),   # B retrace of XA: 0.382-0.5
        ('ABC', 0.886, 1.618, 1.0),     # C extension of AB: 0.618-0.886
        ('BCD', 1.272, 1.618, 1.272),   # CD extension of BC: 1.272-1.618
        ('XAD', 0.618, 0.786, 0.786),   # D retrace of XA: 0.755-0.826
    )),
    PatternSpec('Bat', (
        ('XAB', 1.272, 2.618, 1.563),   # 0.382-0.5
        ('ABC', 0.886, 1.618, 1.0),
        ('BCD', 1.618, 2.618, 1.618),   # 1.618-2.618
        ('XAD', 0.809, 1.0, 0.886),     # 0.886-1.0
    )),
    PatternSpec('Crab', (
        ('XAB', 1.272, 2.618, 1.618),   # 0.382-0.618
        ('ABC', 0.886, 1.618, 1.0),
        ('BCD', 2.25, 3.618, 2.618),    # 0.272-0.45 extension of BC
        ('XAD', 1.0, 1.618, 1.272),     # 1.272-1.618
    )),
    PatternSpec('Butterfly', (
        ('XAB', 0.886, 1.272, 1.0),     # 0.786-0.886
        ('ABC', 0.886, 1.618, 1.0),
        ('BCD', 1.618, 2.618, 2.0),     # 1.618-2.618
        ('XAD', 0.786, 1.0, 0.786),     # 1.272-1.618 (XAD < 1 = extension)
    )),
)


@dataclass(frozen=True)
class HarmonicSignal:
    pattern: str
    direction: str  # 'bullish' (buy at D) | 'bearish' (sell at D)
    accuracy: float  # 0..1, average closeness of all ratios to their ideals
    points: dict  # {'X','A','B','C','D'} -> price
    bars: dict  # {'X','A','B','C','D'} -> bar index
    ratios: dict  # XAB/ABC/BCD/XAD actual values


def _ratios_for(x, a, b, c, d):
    xa, ab, bc, cd, ad = abs(a - x), abs(b - a), abs(c - b), abs(d - c), abs(d - a)
    if min(xa, ab, bc, cd, ad) <= 0:
        return None
    return {'XAB': xa / ab, 'ABC': ab / bc, 'BCD': bc / cd, 'XAD': xa / ad}


def _grade(ratios, bounds):
    """Per ratio: 1.0 at the ideal, 0.0 at either bound, linear between.
    A ratio outside its bounds disqualifies the pattern (None)."""
    accs = []
    for key, lo, hi, ideal in bounds:
        v = ratios[key]
        if v < lo or v > hi:
            return None
        if v == ideal:
            accs.append(1.0)
        else:
            accs.append(max(0.0, 1.0 - abs(v - ideal) / max(hi - lo, 1e-12)))
    return round(sum(accs) / len(accs), 4)


def scan_harmonics(highs, lows, *, zigzag_kwargs=None, min_gap: int = 1):
    """Detect harmonic patterns over the zigzag pivot list.

    Bullish pattern: X, B, D lows; A, C highs (L,H,L,H,L). Bearish: the
    inverse. Pivots alternate by construction, so XABCD must be a strict
    L-H-L-H-L / H-L-H-L-H run (gaps of `min_gap` pivots or more allowed).
    Returns at most 3 signals per D bar (best accuracy first)."""
    zk = dict(deviation=0.03, backstep=3, depth=10)
    zk.update(zigzag_kwargs or {})
    piv = zigzag_pivots(highs, lows, **zk)
    if len(piv) < 5:
        return []
    best: dict[int, list[HarmonicSignal]] = {}
    L = len(piv)
    for i in range(0, L - 4):
        for j in range(i + 1, L - 3):
            if j - i < min_gap:
                continue
            for k in range(j + 1, L - 2):
                if k - j < min_gap:
                    continue
                for m in range(k + 1, L - 1):
                    if m - k < min_gap:
                        continue
                    for p in range(m + 1, L):
                        if p - m < min_gap:
                            continue
                        x, a, b, c, d = piv[i], piv[j], piv[k], piv[m], piv[p]
                        for direction, lk, hk in (('bullish', 'L', 'H'), ('bearish', 'H', 'L')):
                            # zigzag pivots alternate, so a 5-pivot run already
                            # enforces X,D same kind and A,B,C the other
                            if x.kind != lk or a.kind != hk or b.kind != lk \
                               or c.kind != hk or d.kind != lk:
                                continue
                            # B retraces XA (not a new extreme); C extends AB
                            if direction == 'bullish' and not (b.price > x.price and c.price > b.price):
                                continue
                            if direction == 'bearish' and not (b.price < x.price and c.price < b.price):
                                continue
                            r = _ratios_for(x.price, a.price, b.price, c.price, d.price)
                            if r is None:
                                continue
                            for spec in PATTERN_SPECS:
                                g = _grade(r, spec.ratios)
                                if g is None:
                                    continue
                                sig = HarmonicSignal(
                                    spec.name, direction, g,
                                    {'X': x.price, 'A': a.price, 'B': b.price,
                                     'C': c.price, 'D': d.price},
                                    {'X': x.index, 'A': a.index, 'B': b.index,
                                     'C': c.index, 'D': d.index},
                                    {kk: round(vv, 4) for kk, vv in r.items()})
                                best.setdefault(d.index, []).append(sig)
    out = []
    for bi in sorted(best):
        for sig in sorted(best[bi], key=lambda s: -s.accuracy)[:3]:
            out.append(sig)
    return out


def trade_levels(sig: HarmonicSignal):
    """Entry/SL/TP per the FxMath *verified* AD-based rule (see module doc).

    entry = D + s·0.705·AD;  SL = entry − s·AD;
    TP1/2/3 = entry + s·{2.70, 4.83, 6.33}·AD   (s=+1 bullish)."""
    d, a = sig.points['D'], sig.points['A']
    ad = abs(d - a)
    s = 1 if sig.direction == 'bullish' else -1
    entry = d + s * 0.705 * ad
    risk = ad
    return {'entry': round(entry, 8),
            'sl': round(entry - s * risk, 8),
            'tp1': round(entry + s * 2.70 * risk, 8),
            'tp2': round(entry + s * 4.83 * risk, 8),
            'tp3': round(entry + s * 6.33 * risk, 8)}


# ---------------------------------------------------------------------------
# Elliott impulse targets (5-wave)
# ---------------------------------------------------------------------------

ELLIOTT_TARGETS = {
    'W2': {'of_W1': [0.5, 0.618]},
    'W3': {'of_W1': [1.618, 2.618]},
    'W4': {'of_W3': [0.382]},
    'W5': {'of_W1': [1.0, 0.618, 1.618]},
}


def elliot_impulse(pivots, direction='bullish'):
    """Check consecutive 6-pivot runs against the 5-wave impulse relationships.

    Legs are measured between consecutive pivots. Targets: W2 below/above the
    W1 end by 50/61.8% of W1; W3 at 161.8/261.8% of W1 from the W1 end;
    W4 at 38.2% of W3 back from the W3 end; W5 at 1/0.618/1.618 of W1 from
    the W3 end.
    Hit tolerance: 1% of the reference leg for W2/W3/W5, 1% of the W3 leg
    for W4.
    """
    res = []
    if len(pivots) < 6:
        return res
    w3_dir = 1 if direction == 'bullish' else -1
    need = ('L', 'H', 'L', 'H', 'L', 'H') if direction == 'bullish' else ('H', 'L', 'H', 'L', 'H', 'L')
    for i in range(0, len(pivots) - 5):
        w = pivots[i:i + 6]
        if tuple(p.kind for p in w) != need:
            continue
        leg1 = abs(w[1].price - w[0].price)
        leg3 = abs(w[3].price - w[2].price)
        leg5 = abs(w[5].price - w[4].price)
        if leg1 <= 0 or leg3 <= 0 or leg5 <= 0:
            continue
        # Wave 3 must be the longest leg (core Elliott rule)
        if leg3 < max(leg1, leg5):
            continue
        # Wave 4 must not intrude into wave 1: retrace <= ~38.2% of wave 3
        rec4 = abs(w[4].price - w[3].price) / leg3
        strict4 = rec4 <= 0.382
        t2 = [w[1].price - w3_dir * r * leg1 for r in ELLIOTT_TARGETS['W2']['of_W1']]
        t3 = [w[1].price + w3_dir * r * leg1 for r in ELLIOTT_TARGETS['W3']['of_W1']]
        t4 = [w[3].price - w3_dir * r * leg3 for r in ELLIOTT_TARGETS['W4']['of_W3']]
        t5 = [w[3].price + w3_dir * r * leg1 for r in ELLIOTT_TARGETS['W5']['of_W1']]
        hits = {
            'W2': any(abs(w[2].price - t) <= 0.01 * leg1 for t in t2),
            'W3': any(abs(w[3].price - t) <= 0.01 * leg1 for t in t3),
            'W4': any(abs(w[4].price - t) <= 0.01 * leg3 for t in t4),
            'W5': any(abs(w[5].price - t) <= 0.01 * leg1 for t in t5),
        }
        res.append({
            'direction': direction,
            'waves': {f'W{k}': {'bar': w[k - 1].index, 'price': w[k - 1].price}
                      for k in (1, 3, 5)},
            'w5_end': {'bar': w[5].index, 'price': w[5].price},
            'legs': {'W1': round(leg1, 8), 'W3': round(leg3, 8), 'W5': round(leg5, 8)},
            'w4_retrace': round(rec4, 4),
            'targets': {
                'W2': [round(t, 8) for t in t2], 'W3': [round(t, 8) for t in t3],
                'W4': [round(t, 8) for t in t4], 'W5': [round(t, 8) for t in t5]},
            'hits': hits,
            'hits_count': sum(hits.values()),
            'strict_w4': bool(strict4),
        })
    return res


# ---------------------------------------------------------------------------
# Backtest (entry on bar D+1; per bar the D invalidation line is checked
# before TP — D is the NEAREST protective level: SL = entry − s·AD =
# D − s·0.295·AD sits BEYOND D, so breaking D always precedes the printed
# SL. A D-break therefore closes the trade AT D as a loss of −0.705R
# (entry is 0.705R beyond D); the SL line is kept in `levels` for
# charting but is unreachable in this model. Conservative in-bar rule:
# when both a protective level and a TP are touched in one bar, the
# protective level is assumed first — OHLC data cannot prove the
# intra-bar order. No spread.)
# ---------------------------------------------------------------------------

def backtest_harmonics(candles, signals, *, lookahead=120):
    """candles: [{'open','high','low','close'} ...] ascending, indexed by bar.
    Returns {'trades': [...], 'stats': per-pattern aggregates}.

    Scoring (pts_r = P&L in R where R = |entry − SL| = AD):
      INVALIDATED  -> LOSS  at −0.705 (closed at D)
      TP1/TP2/TP3  -> WIN   at +2.70 / +4.83 / +6.33
      EXPIRED      -> NEUTRAL at close-based P&L in R (time stop).
    """
    trades = []
    seen: set[int] = set()
    for sig in signals:
        db = sig.bars['D']
        if db in seen or db >= len(candles):
            continue
        seen.add(db)
        lv = trade_levels(sig)
        bull = sig.direction == 'bullish'
        s = 1 if bull else -1
        D = sig.points['D']
        outcome, ptp = 'EXPIRED', None
        for k in range(db + 1, min(db + 1 + lookahead, len(candles))):
            c = candles[k]
            if bull:
                if c['low'] <= D:
                    outcome, ptp = 'INVALIDATED', D
                    break
                hit = None
                for tp in ('tp1', 'tp2', 'tp3'):
                    if c['high'] >= lv[tp]:
                        hit = tp
                        break
                if hit:
                    outcome, ptp = hit.upper(), lv[hit]
                    break
            else:
                if c['high'] >= D:
                    outcome, ptp = 'INVALIDATED', D
                    break
                hit = None
                for tp in ('tp1', 'tp2', 'tp3'):
                    if c['low'] <= lv[tp]:
                        hit = tp
                        break
                if hit:
                    outcome, ptp = hit.upper(), lv[hit]
                    break
        risk = abs(lv['entry'] - lv['sl'])
        if risk == 0:
            pts, res = 0.0, 'NEUTRAL'
        elif outcome == 'INVALIDATED':
            # stopped at D: entry is 0.705R beyond D, in the loss direction
            pts, res = s * (ptp - lv['entry']) / risk, 'LOSS'
        elif outcome in ('TP1', 'TP2', 'TP3'):
            pts, res = abs(ptp - lv['entry']) / risk, 'WIN'
        else:
            # time stop: mark at the last close actually traded
            last_close = candles[min(db + 1 + lookahead, len(candles)) - 1]['close']
            pts, res = round(s * (last_close - lv['entry']) / risk, 3), 'NEUTRAL'
        trades.append({
            'pattern': sig.pattern, 'direction': sig.direction,
            'd_bar': db, 'entry_bar': db + 1, 'levels': lv,
            'outcome': outcome, 'result': res, 'pts_r': round(pts, 3),
        })
    stats = {}
    for t in trades:
        s = stats.setdefault(t['pattern'], {'n': 0, 'wins': 0, 'losses': 0,
                                            'neutral': 0, 'win_pts': 0.0, 'loss_pts': 0.0})
        s['n'] += 1
        if t['result'] == 'WIN':
            s['wins'] += 1
            s['win_pts'] += t['pts_r']
        elif t['result'] == 'LOSS':
            s['losses'] += 1
            s['loss_pts'] += abs(t['pts_r'])
        else:
            s['neutral'] += 1
    for s in stats.values():
        s['win_rate'] = round(s['wins'] / s['n'], 4)
        s['avg_win_pts'] = round(s['win_pts'] / s['wins'], 3) if s['wins'] else 0.0
        s['avg_loss_pts'] = round(s['loss_pts'] / s['losses'], 3) if s['losses'] else 0.0
        s['profit_factor'] = round(s['win_pts'] / s['loss_pts'], 3) if s['loss_pts'] else None
    return {'trades': trades, 'stats': stats}
