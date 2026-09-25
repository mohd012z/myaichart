export const TIMEFRAMES=['M1','M5','M15','M30','H1','H4','D1','W1','MN1'];
export const SIDES=['mid','bid','ask'];
export function bindButtons(root,state,onChange){
  root.querySelectorAll('[data-tf]').forEach(b=>b.onclick=()=>{state.timeframe=b.dataset.tf;onChange();});
  root.querySelectorAll('[data-side]').forEach(b=>b.onclick=()=>{state.side=b.dataset.side;onChange();});
}
