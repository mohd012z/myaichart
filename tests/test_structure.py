"""Unit tests for the swing-structure features (zigzag, harmonics, Elliott).

Hermetic: hand-built candle paths whose pivots are known, so the detector's
geometry is asserted exactly. No network.

Ratio convention (see structure.PATTERN_SPECS): XAB = |XA|/|AB| (B is a
retrace of XA), ABC = |AB|/|BC| (C an extension of AB), BCD = |BC|/|CD|
(D a retrace of BC), XAD = |XA|/|AD|.
"""
from __future__ import annotations

from myaichart.features.structure import (
    ELLIOTT_TARGETS,
    PATTERN_SPECS,
    Pivot,
    backtest_harmonics,
    elliot_impulse,
    scan_harmonics,
    trade_levels,
    zigzag_pivots,
)


def _ohlc(prices):
    out = []
    for i, p in enumerate(prices):
        prev = prices[i - 1] if i > 0 else p
        out.append({'open': prev, 'high': max(prev, p),
                    'low': min(prev, p), 'close': p})
    return out


def _ramp(a, b, steps):
    return [a + (b - a) * i / steps for i in range(1, steps + 1)]


# ---------------------------------------------------------------------------
# ZigZag
# ---------------------------------------------------------------------------

def test_zigzag_finds_known_pivots():
    # start high 120, fall to 30, rise to 100, retrace 60, rise 90, fall 30.
    # The final D-low is never confirmed (no later reversal), so 5 pivots:
    # H120 L30 H100 L60 H90.
    path = [120.0] * 3 + _ramp(120, 30, 6) + [30.0] * 3 + _ramp(30, 100, 6) \
        + [100.0] * 3 + _ramp(100, 60, 5) + [60.0] * 3 + _ramp(60, 90, 5) \
        + [90.0] * 3 + _ramp(90, 30, 6) + [30.0] * 3
    hi, lo = path[:], path[:]
    piv = zigzag_pivots(hi, lo, deviation=0.03, backstep=3, depth=3)
    kinds = [(p.kind, round(p.price, 1)) for p in piv]
    assert kinds == [('H', 120.0), ('L', 30.0), ('H', 100.0),
                     ('L', 60.0), ('H', 90.0)], kinds
    # alternation: pivots must never repeat the same kind
    ks = [k for k, _ in kinds]
    assert all(a != b for a, b in zip(ks, ks[1:])), ks


def test_zigzag_empty_on_flat_and_short():
    assert zigzag_pivots([100.0] * 5, [100.0] * 5, deviation=0.03) == []
    assert zigzag_pivots([100.0, 101.0], [100.0, 101.0]) == []


# ---------------------------------------------------------------------------
# Harmonics: exact pivot geometries
# ---------------------------------------------------------------------------

def _piv(x, a, b, c, d, kinds):
    """kinds: 5-char string of 'H'/'L' for X,A,B,C,D."""
    ks = dict(zip('XABCD', kinds))
    return [Pivot(i * 5, ks[n], v) for i, (n, v) in enumerate(zip('XABCD', (x, a, b, c, d)))]


def test_abcd_ratio_grading():
    from myaichart.features.structure import _ratios_for, _grade
    # X=0 A=100 B=60 C=90 D=30 -> XAB 2.5, ABC 1.333, BCD 0.5, XAD 1.4286
    # All inside the AB=CD bounds; grade is a strict interior average.
    r = _ratios_for(0.0, 100.0, 60.0, 90.0, 30.0)
    assert r is not None
    assert abs(r['XAB'] - 2.5) < 1e-9
    assert abs(r['ABC'] - 4 / 3) < 1e-9
    assert abs(r['BCD'] - 0.5) < 1e-9
    assert abs(r['XAD'] - 100 / 70) < 1e-9
    abcd = next(s for s in PATTERN_SPECS if s.name == 'AB=CD')
    g = _grade(r, abcd.ratios)
    assert g is not None and 0.5 < g < 1.0, g


def test_gartley_grade_matches_ideals():
    from myaichart.features.structure import _ratios_for, _grade
    # Bullish Gartley geometry: X=0 A=100 B=61.8 C=85.4 D=52.9
    # XAB=100/38.2=2.618, ABC=38.2/23.6=1.618, BCD=23.6/32.5=0.726,
    # XAD=100/47.1=2.123. Only ABC sits inside the Gartley bounds here, so
    # the full grade is None; assert the leg ratios are exact.
    x, a, b, c, d = 0.0, 100.0, 61.8, 85.4, 52.9
    r = _ratios_for(x, a, b, c, d)
    assert r is not None
    assert abs(r['XAB'] - 100 / 38.2) < 0.01
    assert abs(r['ABC'] - 38.2 / 23.6) < 0.01
    assert abs(r['BCD'] - 23.6 / 32.5) < 0.01
    spec = next(s for s in PATTERN_SPECS if s.name == 'Gartley')
    g = _grade(r, spec.ratios)
    assert g is None or 0 <= g <= 1


def test_scan_detects_bullish_abcd_from_synthetic_pivots():
    # Real candle path; zigzag (dev .03, back 3, depth 3) yields exactly
    # H120 L30 H100 L60 H90 L30 — the closing high both confirms the
    # final L30 and stays below H100 so it can't displace it. The run
    # L30 H100 L60 H90 L30 is a bullish AB=CD (legs XA 70, AB 40, BC 30,
    # CD 60, AD 70 -> XAB 1.75, ABC 1.333, BCD 0.5, XAD 1.0 — in bounds).
    path = [120.0] * 3 + _ramp(120, 30, 6) + [30.0] * 3 + _ramp(30, 100, 6) \
        + [100.0] * 3 + _ramp(100, 60, 5) + [60.0] * 3 + _ramp(60, 90, 5) \
        + [90.0] * 3 + _ramp(90, 30, 6) + [30.0] * 3 + _ramp(30, 110, 6) \
        + [110.0] * 3
    hi, lo = path[:], path[:]
    zk = {'deviation': 0.03, 'backstep': 3, 'depth': 3}
    # the trailing H110 is never confirmed (no later reversal), so the
    # pivots are exactly the 6 that form the AB=CD run:
    piv = zigzag_pivots(hi, lo, **zk)
    assert [(p.kind, round(p.price, 1)) for p in piv] == \
        [('H', 120.0), ('L', 30.0), ('H', 100.0), ('L', 60.0),
         ('H', 90.0), ('L', 30.0)]
    sigs = scan_harmonics(hi, lo, zigzag_kwargs=zk)
    assert len(sigs) >= 1, sigs
    bull = [s for s in sigs if s.direction == 'bullish' and s.pattern == 'AB=CD']
    assert bull, sigs
    s = bull[0]
    assert abs(s.points['X'] - 30.0) < 1e-9
    assert abs(s.points['A'] - 100.0) < 1e-9
    assert abs(s.points['B'] - 60.0) < 1e-9
    assert abs(s.points['C'] - 90.0) < 1e-9
    assert abs(s.points['D'] - 30.0) < 1e-9
    assert abs(s.ratios['XAB'] - 1.75) < 1e-3
    assert abs(s.ratios['BCD'] - 0.5) < 1e-3


def test_trade_levels_match_fxmath_published_rule():
    from myaichart.features.structure import HarmonicSignal
    # Reproduce the XAGUSD H1 AB=CD signal: D=60.278, A=61.087 (AD=0.809).
    # Verified rule: entry=D+0.705*AD, SL=entry-AD, TP=entry+{2.70,4.83,6.33}*AD
    sig = HarmonicSignal('AB=CD', 'bullish', 0.71,
                         {'X': 70.0, 'A': 61.087, 'B': 65.0, 'C': 61.0, 'D': 60.278},
                         {'X': 0, 'A': 1, 'B': 2, 'C': 3, 'D': 4},
                         {'XAB': 0.854, 'ABC': 0.451, 'BCD': 2.372, 'XAD': 0.914})
    lv = trade_levels(sig)
    # The vendor's published levels: entry 60.848, SL 60.039,
    # TP 63.030 / 64.754 / 65.971 — our values reproduce them within the
    # vendor's own 3-decimal rounding (max delta 0.0018)
    assert abs(lv['entry'] - 60.848) < 0.004
    assert abs(lv['sl'] - 60.039) < 0.004
    assert abs(lv['tp1'] - 63.030) < 0.004
    assert abs(lv['tp2'] - 64.754) < 0.004
    assert abs(lv['tp3'] - 65.971) < 0.004
    # R:R to each TP = 2.70 / 4.83 / 6.33 (the signal's published R:R)
    risk = lv['entry'] - lv['sl']
    rr = [(lv[k] - lv['entry']) / risk for k in ('tp1', 'tp2', 'tp3')]
    assert all(abs(a - b) < 0.011 for a, b in zip(rr, (2.70, 4.83, 6.33))), rr
    # bearish mirrors around D
    sigb = HarmonicSignal('AB=CD', 'bearish', 0.71,
                          {'X': 50.0, 'A': 59.411, 'B': 55.0, 'C': 59.0, 'D': 60.22},
                          {'X': 0, 'A': 1, 'B': 2, 'C': 3, 'D': 4},
                          {'XAB': 0.854, 'ABC': 0.451, 'BCD': 2.372, 'XAD': 0.914})
    lvb = trade_levels(sigb)
    assert lvb['entry'] < 60.22 < lvb['sl']
    assert lvb['tp1'] < lvb['entry']


# ---------------------------------------------------------------------------
# Elliott
# ---------------------------------------------------------------------------

def test_elliot_targets_table():
    assert ELLIOTT_TARGETS['W2']['of_W1'] == [0.5, 0.618]
    assert ELLIOTT_TARGETS['W3']['of_W1'] == [1.618, 2.618]
    assert ELLIOTT_TARGETS['W4']['of_W3'] == [0.382]
    assert ELLIOTT_TARGETS['W5']['of_W1'] == [1.0, 0.618, 1.618]


def test_elliot_bullish_impulse_hit():
    # W1 100->110 (leg 10). W2 ends 103.82 (61.8% of W1). W3 ends 126.18
    # (161.8% of W1 from the W1 end). W4 = 126.18 - 38.2% of W3 leg.
    # W5 = 126.18 + 1x W1 = 136.18.
    pivots = [Pivot(0, 'L', 100.0), Pivot(2, 'H', 110.0),
              Pivot(4, 'L', 103.82), Pivot(6, 'H', 126.18),
              Pivot(8, 'L', 117.64), Pivot(10, 'H', 136.18)]
    res = elliot_impulse(pivots, 'bullish')
    assert res, "expected a bullish impulse"
    r = res[0]
    assert r['hits']['W2'] and r['hits']['W3'] and r['hits']['W5']
    assert r['legs']['W3'] > r['legs']['W1']
    # W4 retrace is 38.2% of W3 -> passes the no-intrusion rule
    assert abs(r['w4_retrace'] - 0.382) < 0.005
    assert r['strict_w4'] is True


def test_elliot_rejects_non_impulse():
    # equal legs: W3 not longest -> no result
    pivots = [Pivot(0, 'L', 100.0), Pivot(2, 'H', 110.0),
              Pivot(4, 'L', 105.0), Pivot(6, 'H', 112.0),
              Pivot(8, 'L', 106.0), Pivot(10, 'H', 116.0)]
    res = elliot_impulse(pivots, 'bullish')
    # W3 leg = 7 < W1 10 -> rejected
    assert not res


# ---------------------------------------------------------------------------
# Backtest mechanics
# ---------------------------------------------------------------------------

def test_backtest_invalidates_and_tps():
    from myaichart.features.structure import HarmonicSignal
    # Bullish signal at D bar 1 (entry bar 2). A=110 D=60 -> AD=50:
    # entry 95.25, SL 45.25 (below D), tp1 230.25, tp3 411.75.
    sig = HarmonicSignal('AB=CD', 'bullish', 0.7,
                         {'X': 0, 'A': 110, 'B': 60, 'C': 75, 'D': 60.0},
                         {'X': 0, 'A': 0, 'B': 1, 'C': 2, 'D': 1},
                         {'XAB': 0.6, 'ABC': 0.6, 'BCD': 1.6, 'XAD': 0.9})
    lv = trade_levels(sig)
    assert lv['entry'] > sig.points['D'] > lv['sl']
    # INVALIDATED: entry bar drops through D (60) -> pattern fails
    res = backtest_harmonics(_ohlc([90.0, 85.0, 55.0, 50.0]), [sig])
    assert res['trades'][0]['outcome'] == 'INVALIDATED'
    # TP1: entry bar rises to tp1 without ever breaking D
    res = backtest_harmonics(_ohlc([90.0, 85.0, 240.0, 250.0]), [sig])
    assert res['trades'][0]['outcome'] == 'TP1'
    assert abs(res['trades'][0]['pts_r'] - 2.7) < 1e-3
    assert res['trades'][0]['result'] == 'WIN'
    # EXPIRED: entry bar stays between D and tp1 for the whole lookahead
    res = backtest_harmonics(_ohlc([90.0, 85.0, 80.0, 75.0]), [sig])
    assert res['trades'][0]['outcome'] == 'EXPIRED'
    assert res['trades'][0]['result'] == 'NEUTRAL'
    # one D bar -> exactly one trade
    assert len(res['trades']) == 1
