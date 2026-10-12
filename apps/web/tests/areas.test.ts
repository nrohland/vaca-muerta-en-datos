import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {areaRanking,areaChange,areaPoints} from '../lib/area-analysis.ts';
import {validateRelease} from '../lib/contract.ts';
import {validatePrices,shiftMonth} from '../lib/metrics.ts';
const release=validateRelease(JSON.parse(readFileSync(new URL('../public/data/release.json',import.meta.url),'utf8')));
const prices=validatePrices(JSON.parse(readFileSync(new URL('../public/data/prices.json',import.meta.url),'utf8')));
const close=(a:number,b:number)=>assert.ok(Math.abs(a-b)<Math.max(1e-7,Math.abs(b)*1e-10),`${a} ≠ ${b}`);
test('complete area ranking reconciles to basin volume and shares sum to 100 in every observed period',()=>{
 for(const current of release.production){const ranking=areaRanking(release.entities,current,prices,'volume','yoy');assert.ok(ranking.length);close(ranking.reduce((s,r)=>s+r.entity.volume,0),current.volume);close(ranking.reduce((s,r)=>s+(r.share??0),0),100);assert.ok(ranking.every((r,i)=>i===0||ranking[i-1].entity.volume_rank<=r.entity.volume_rank));}
});
test('search/filter retain original rank and basin share, never renormalize',()=>{
 const current=release.production.filter(r=>r.fluid==='oil').at(-1)!;const all=areaRanking(release.entities,current,prices,'volume','mom');const leader=all[0];const result=areaRanking(release.entities,current,prices,'volume','mom',{query:leader.entity.entity_id,activity:'producing'});const item=result.find(r=>r.entity.entity_id===leader.entity.entity_id)!;assert.equal(item.share,leader.share);assert.equal(item.entity.volume_rank,leader.entity.volume_rank);
 assert.equal(areaRanking(release.entities,current,prices,'volume','mom',{query:'unknown area xyz'}).length,0);
 const up=areaRanking(release.entities,current,prices,'volume','mom',{direction:'up'});assert.ok(up.every(r=>r.delta!=null&&r.delta>0));
});
test('USD change values each historical month separately and gas stays physical',()=>{
 const current=release.production.filter(r=>r.fluid==='oil').at(-1)!;const entity=areaRanking(release.entities,current,prices,'volume','yoy')[0].entity;const c=areaChange(entity,release.entities,prices,'value','yoy');const base=release.entities.find(e=>e.dimension==='area'&&e.fluid==='oil'&&e.entity_id===entity.entity_id&&e.periodo===shiftMonth(current.periodo,-12))!;close(c.value!,entity.volume*prices.prices.find(p=>p.periodo===current.periodo)!.usd_per_bbl);close(c.delta!,c.value!-base.volume*prices.prices.find(p=>p.periodo===base.periodo)!.usd_per_bbl);
 const gas=release.entities.find(e=>e.dimension==='area'&&e.fluid==='gas')!;assert.equal(areaChange(gas,release.entities,prices,'value','yoy').value,gas.volume);
 assert.equal(areaChange(entity,release.entities,null,'value','yoy').value,null);
});
test('missing entity month and exact comparison base remain null, observed zeros remain zero',()=>{
 const current=release.production.filter(r=>r.fluid==='oil').at(-1)!;const entity=areaRanking(release.entities,current,prices,'volume','mom')[0].entity;const missing=shiftMonth(current.periodo,-1);const sparse=release.entities.filter(e=>!(e.dimension==='area'&&e.entity_id===entity.entity_id&&e.fluid==='oil'&&e.periodo===missing));const pts=areaPoints(sparse,release.production,current,entity.entity_id,12,prices,'volume','mom');assert.equal(pts.find(p=>p.periodo===missing)!.value,null);assert.equal(pts.at(-1)!.delta,null);
 const zero={...entity,volume:0};assert.equal(areaChange(zero,sparse,prices,'volume','mom').value,0);
});

test('direction detects increases from an observed zero without fabricating a percentage',()=>{
 const current = release.production.find(r=>r.fluid==='gas'&&r.periodo==='2026-01-01')!;
 const growing = areaRanking(release.entities,current,prices,'volume','mom',{direction:'up'});
 const area = growing.find(r=>r.entity.entity_id==='AGCA')!;
 assert.ok(area);assert.ok(area.delta!>0);assert.equal(area.pct,null);
});
