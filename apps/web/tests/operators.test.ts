import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {validateRelease,type Entity,type Row} from '../lib/contract.ts';
import {validatePrices,warehouseValue,type Prices} from '../lib/metrics.ts';
import {filterOperators,operatorRanking,operatorHistory,operatorCsv} from '../lib/operator-analysis.ts';
const release=validateRelease(JSON.parse(readFileSync(new URL('../public/data/release.json',import.meta.url),'utf8')));
const prices=validatePrices(JSON.parse(readFileSync(new URL('../public/data/prices.json',import.meta.url),'utf8')));
const close=(a:number,b:number)=>assert.ok(Math.abs(a-b)<=Math.max(1e-7,Math.abs(b)*1e-10),`${a} != ${b}`);
test('full operator ranking reconciles basin volumes and uses real total shares for every period and product',()=>{
 for(const current of release.production){const entries=operatorRanking(release.entities,current,prices,'volume','yoy');assert.ok(entries.length>5);close(entries.reduce((sum,e)=>sum+e.entity.volume,0),current.volume);close(entries.reduce((sum,e)=>sum+(e.share??0),0),100);assert.ok(entries.every((e,i)=>i===0||e.entity.volume<=entries[i-1].entity.volume));close(entries.slice(0,5).reduce((sum,e)=>sum+(e.share??0),0),Number(current.top5_company_share_pct));}
});
test('exact calendar comparisons independently reproduce prepared monthly and yearly changes',()=>{
 for(const current of release.production)for(const comparison of ['mom','yoy'] as const){for(const e of operatorRanking(release.entities,current,prices,'volume',comparison)){const prepared=e.entity[`${comparison}_volume_pct`];if(e.pct==null)assert.equal(prepared,null);else close(e.pct,Number(prepared));}}
});
test('operator valuation reads warehouse values and calendar entity bases without price arithmetic',()=>{
 const current=release.production.find(r=>r.fluid==='oil'&&r.periodo==='2026-08-01')!;
 for(const e of operatorRanking(release.entities,current,prices,'value','yoy')){assert.equal(e.value,warehouseValue(e.entity));const base=release.entities.find(r=>r.dimension==='company'&&r.fluid==='oil'&&r.entity_id===e.entity.entity_id&&r.periodo===e.basePeriod);assert.equal(e.baseValue,warehouseValue(base));}
 const missing=release.entities.map(e=>({...e,estimated_value_usd:null,valuation_method:'unavailable'}));assert.ok(operatorRanking(missing,current,prices,'value','mom').every(e=>e.value==null&&e.delta==null&&e.pct==null));
});
const template=release.entities.find(e=>e.dimension==='company'&&e.fluid==='oil')!;
const ent=(periodo:string,volume:number,id='TEST')=>({...template,periodo,volume,entity_id:id,entity_name:'Operador Ágil',volume_rank:1}) as Entity;
const row=(periodo:string)=>({...release.production[0],fluid:'oil',periodo,volume:100}) as Row;
test('missing exact bases never borrow nearby observations and zero bases permit deltas but no percentage',()=>{
 const entries=[ent('2025-01-01',10),ent('2025-03-01',15)];const e=operatorRanking(entries,row('2025-03-01'),null,'volume','mom')[0];assert.equal(e.baseValue,null);assert.equal(e.delta,null);assert.equal(e.pct,null);
 const zero=operatorRanking([...entries,ent('2025-02-01',0)],row('2025-03-01'),null,'volume','mom')[0];assert.equal(zero.delta,15);assert.equal(zero.pct,null);
});
test('search, direction and sorting do not mutate ranking or change participation denominator',()=>{
 const entries=operatorRanking([ent('2025-03-01',15),ent('2025-02-01',10)],row('2025-03-01'),null,'volume','mom');assert.equal(filterOperators(entries,'agil','growing')[0].share,15);assert.equal(filterOperators(entries,'','declining').length,0);assert.equal(filterOperators(entries,'TEST').length,1);assert.deepEqual(entries.map(e=>e.share),[15]);
});
test('operator history preserves calendar holes, selection isolation and CSV empty cells',()=>{
 const entries=[ent('2025-01-01',10),ent('2025-03-01',15),ent('2025-02-01',99,'OTHER')];const rows=['2025-01-01','2025-02-01','2025-03-01'].map(row);
 const points=operatorHistory(entries,rows,'oil','2025-03-01',0,'TEST',null,'volume','mom');assert.equal(points.length,3);assert.equal(points[1].volume,null);assert.equal(points[1].value,null);assert.equal(points[2].baseValue,null);assert.equal(points[2].delta,null);assert.equal(points[2].share,15);const lines=operatorCsv(points,'oil','volume').split('\n');assert.equal(lines[2],'2025-02-01,,,,,2025-01-01,10,,');
});
test('gas CSV converts physical MMm3 to m3 without inventing USD prices',()=>{
 const gas={...template,entity_id:'TEST',fluid:'gas',periodo:'2025-01-01',volume:2,estimated_value_usd:null,valuation_method:'unavailable'} as Entity;const basin={...row('2025-01-01'),fluid:'gas',volume:10} as Row;const points=operatorHistory([gas],[basin],'gas','2025-01-01',0,'TEST',null,'value','yoy');assert.match(operatorCsv(points,'gas','value'),/volume_m3,selected_usd/);assert.match(operatorCsv(points,'gas','value'),/2025-01-01,2000000,,20/);
});
