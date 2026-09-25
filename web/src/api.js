export async function getJSON(url){const r=await fetch(url);if(!r.ok)throw new Error(`${r.status}`);return r.json();}
