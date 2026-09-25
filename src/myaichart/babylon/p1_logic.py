from dataclasses import dataclass

@dataclass(frozen=True)
class TLContext:
    h1_ema50: float; h1_ema200: float
    m15_close: float; m15_open: float; m15_ema20: float
    prior_high: float; prior_low: float

@dataclass(frozen=True)
class MBCContext:
    m5_ema20: float; m5_ema50: float
    open: float; close: float; atr: float
    prior_high: float; prior_low: float

@dataclass(frozen=True)
class SNDContext:
    h1_ema50: float; h1_ema200: float
    open: float; high: float; low: float; close: float; atr: float
    prior_high: float; prior_low: float
    zone_type: str='RANGE_EDGE_ZONE'


def tl_signal(ctx: TLContext) -> int:
    if ctx.h1_ema50 > ctx.h1_ema200 and ctx.m15_close > ctx.m15_ema20 and ctx.m15_close > ctx.m15_open and ctx.m15_close > ctx.prior_high:
        return 1
    if ctx.h1_ema50 < ctx.h1_ema200 and ctx.m15_close < ctx.m15_ema20 and ctx.m15_close < ctx.m15_open and ctx.m15_close < ctx.prior_low:
        return -1
    return 0


def mbc_signal(ctx: MBCContext) -> int:
    if ctx.atr <= 0:
        return 0
    body=abs(ctx.close-ctx.open)
    if body < 0.35*ctx.atr:
        return 0
    if ctx.m5_ema20 > ctx.m5_ema50 and ctx.close > ctx.open and ctx.close > ctx.prior_high:
        return 1
    if ctx.m5_ema20 < ctx.m5_ema50 and ctx.close < ctx.open and ctx.close < ctx.prior_low:
        return -1
    return 0


def snd_signal(ctx: SNDContext) -> int:
    if ctx.atr <= 0:
        return 0
    if (ctx.high-ctx.low) < 0.25*ctx.atr:
        return 0
    buffer=0.20*ctx.atr
    if ctx.h1_ema50 >= ctx.h1_ema200 and ctx.low <= ctx.prior_low + buffer and ctx.close > ctx.open and ctx.close > ctx.prior_low + 0.5*buffer:
        return 1
    if ctx.h1_ema50 <= ctx.h1_ema200 and ctx.high >= ctx.prior_high - buffer and ctx.close < ctx.open and ctx.close < ctx.prior_high - 0.5*buffer:
        return -1
    return 0
