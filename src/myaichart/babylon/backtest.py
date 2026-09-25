from dataclasses import dataclass
from .p2_context import shadow_decision

@dataclass(frozen=True)
class BacktestResult:
    raw_p1_trades: list
    p1_control_trades: list
    p2_shadow_decisions: list
    equity_curve: list[float]

class BacktestEngine:
    def __init__(self, initial_cash: float=1000.0):
        self.initial_cash=float(initial_cash)

    def run(self, raw_p1_trades, *, p2_shadow=False, context_by_id=None):
        raw=list(raw_p1_trades)
        equity=[self.initial_cash]
        balance=self.initial_cash
        for trade in raw:
            balance += float(trade.get('pnl',0.0))
            equity.append(balance)
        decisions=[]
        if p2_shadow:
            contexts=context_by_id or {}
            for trade in raw:
                d=shadow_decision(contexts.get(trade.get('id'),{}))
                decisions.append({'signal_id':trade.get('id'),**d})
        return BacktestResult(raw_p1_trades=raw,p1_control_trades=list(raw),p2_shadow_decisions=decisions,equity_curve=equity)
