from myaichart.babylon.p1_logic import TLContext, MBCContext, SNDContext, tl_signal, mbc_signal, snd_signal


def test_tl_requires_closed_m15_breakout_and_h1_bias():
    ctx=TLContext(h1_ema50=2100,h1_ema200=2050,m15_close=2110,m15_open=2090,m15_ema20=2080,prior_high=2105,prior_low=2000)
    assert tl_signal(ctx)==1


def test_tl_sell_is_inverse():
    ctx=TLContext(h1_ema50=2000,h1_ema200=2050,m15_close=1980,m15_open=2010,m15_ema20=2020,prior_high=2100,prior_low=1990)
    assert tl_signal(ctx)==-1


def test_mbc_requires_body_at_least_point35_atr():
    ctx=MBCContext(m5_ema20=2100,m5_ema50=2050,open=2099,close=2100,atr=10,prior_high=2095,prior_low=2000)
    assert mbc_signal(ctx)==0


def test_mbc_breakout_with_large_body():
    ctx=MBCContext(m5_ema20=2100,m5_ema50=2050,open=2090,close=2110,atr=10,prior_high=2105,prior_low=2000)
    assert mbc_signal(ctx)==1


def test_snd_is_range_edge_rejection_not_named_supply_demand():
    ctx=SNDContext(h1_ema50=2100,h1_ema200=2050,open=2002,high=2005,low=1999,close=2004,atr=10,prior_high=2100,prior_low=2000)
    assert ctx.zone_type=='RANGE_EDGE_ZONE'
    assert snd_signal(ctx)==1
