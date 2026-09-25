import {applyCandleUpdate,createRenderThrottle,connectLive} from './realtime.js';
import {createPriceChart,candleDatum,upsertCandle} from './chart.js';
import {bindButtons} from './controls.js';

const state={candles:new Map(),backendTickCount:0,timeframe:'M5',side:'mid',layers:{bb:true,news:true,p1:true,p2:true}};
const chart=createPriceChart(document.getElementById('priceChart'));
const render=createRenderThrottle(()=>{
  const msg=state.lastMessage;if(!msg||msg.timeframe!==state.timeframe)return;
  upsertCandle(chart,candleDatum(msg,state.side));chart.update('none');
  document.getElementById('price').textContent=`${msg.mid.c.toFixed(2)}  spread ${msg.spread.last.toFixed(2)}  ticks ${msg.tick_count}`;
},10);
bindButtons(document,state,()=>chart.update('none'));
connectLive(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws/live`,msg=>{applyCandleUpdate(state,msg);render();},status=>document.getElementById('status').textContent=status);
setInterval(()=>document.getElementById('clock').textContent=new Intl.DateTimeFormat('en-MY',{timeZone:'Asia/Kuala_Lumpur',hour12:false,dateStyle:'medium',timeStyle:'medium'}).format(new Date())+' MYT',1000);
