from myaichart.babylon.backtest import BacktestEngine
from myaichart.babylon.p2_context import shadow_decision


def test_shadow_block_does_not_remove_p1_control_trade():
    raw=[{'id':'s1','engine':'MBC','direction':1,'pnl':1.0},{'id':'s2','engine':'SND','direction':-1,'pnl':-0.5}]
    result=BacktestEngine().run(raw,p2_shadow=True,context_by_id={'s1':{'valid':False},'s2':{'valid':True}})
    assert result.p1_control_trades==raw
    assert result.raw_p1_trades==raw
    assert len(result.p2_shadow_decisions)==2
    assert result.p2_shadow_decisions[0]['decision']=='BLOCK'


def test_shadow_decision_is_annotation_only():
    assert shadow_decision({'valid':False,'reason':'WIDE_SPREAD'})['decision']=='BLOCK'
    assert shadow_decision({'valid':True})['decision']=='ALLOW'
