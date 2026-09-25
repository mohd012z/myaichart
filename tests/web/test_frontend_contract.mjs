import assert from 'node:assert/strict';
import { applyCandleUpdate, createRenderThrottle } from '../../web/src/realtime.js';

const state={candles:new Map(),backendTickCount:0};
applyCandleUpdate(state,{type:'candle_update',timeframe:'M5',bucket_start_utc:'2026-09-25T07:40:00Z',
  mid:{o:10,h:12,l:9,c:11},bid:{o:9.9,h:11.9,l:8.9,c:10.9},ask:{o:10.1,h:12.1,l:9.1,c:11.1},
  spread:{last:.2,mean:.2,max:.3},tick_count:50});
assert.equal(state.backendTickCount,50);
assert.equal(state.candles.size,1);

let renders=0;
const throttled=createRenderThrottle(()=>renders++,100);
for(let i=0;i<20;i++) throttled();
await new Promise(r=>setTimeout(r,25));
assert.equal(renders,1);
assert.equal(state.backendTickCount,50);
