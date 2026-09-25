export function applyCandleUpdate(state,msg){
  const key=`${msg.timeframe}|${msg.bucket_start_utc}`;
  state.candles.set(key,msg);
  state.backendTickCount=Math.max(state.backendTickCount,msg.tick_count??0);
  state.lastMessage=msg;
}
export function createRenderThrottle(render,fps=10){
  let pending=false;
  return ()=>{
    if(pending) return;
    pending=true;
    setTimeout(()=>{pending=false;render();},1000/fps);
  };
}
export function connectLive(url,onMessage,onStatus=()=>{}){
  const ws=new WebSocket(url);
  ws.onopen=()=>onStatus('LIVE');
  ws.onclose=()=>onStatus('STALE');
  ws.onerror=()=>onStatus('SOURCE_ERROR');
  ws.onmessage=e=>onMessage(JSON.parse(e.data));
  return ws;
}
