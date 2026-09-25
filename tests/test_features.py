import pytest
from myaichart.features.liquidity import imbalance
from myaichart.features.spread import classify_spread, spread_stats
from myaichart.features.volatility import true_range, atr
from myaichart.features.bb import bollinger


def test_liquidity_imbalance_formula():
    assert imbalance(30,10)==pytest.approx(0.5)
    assert imbalance(0,0) is None


def test_spread_state_uses_distribution_thresholds():
    history=[1,1,1,1,2,2,2,3,5,8,13,21]
    assert classify_spread(21,history) in {'WIDE','EXTREME'}
    stats=spread_stats(history)
    assert stats['max']==21
    assert stats['p95']>=13


def test_true_range_includes_previous_close():
    assert true_range(high=11,low=9,prev_close=8)==3


def test_atr_is_mean_of_recent_true_ranges():
    assert atr([1,2,3,4],period=3)==pytest.approx(3)


def test_bollinger_returns_mid_upper_lower_and_percent_b():
    result=bollinger([1,2,3,4,5],period=5,deviations=2)
    assert result.upper>result.mid>result.lower
    assert 0 <= result.percent_b <= 1.5
