export function candleDatum(msg,side='mid'){
  const p=msg[side];
  return {x:new Date(msg.bucket_start_utc).valueOf(),o:p.o,h:p.h,l:p.l,c:p.c};
}
export function createPriceChart(canvas){
  if(!globalThis.Chart) throw new Error('Chart.js not loaded');
  return new Chart(canvas,{type:'candlestick',data:{datasets:[{label:'XAUUSD',data:[]}]},options:{animation:false,parsing:false,plugins:{legend:{display:false},zoom:{zoom:{wheel:{enabled:true},pinch:{enabled:true},mode:'x'},pan:{enabled:true,mode:'x'}}},scales:{x:{type:'time'}}}});
}
export function upsertCandle(chart,datum){
  const data=chart.data.datasets[0].data;
  const i=data.findIndex(x=>x.x===datum.x);
  if(i>=0)data[i]=datum;else data.push(datum);
  data.sort((a,b)=>a.x-b.x);
}
