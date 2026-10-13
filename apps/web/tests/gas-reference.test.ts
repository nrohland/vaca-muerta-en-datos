import {operatorHistory,operatorCsv} from '../lib/operator-analysis.ts';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {GAS_ENERGY_BASIS,GAS_M3_TO_MMBTU,validatePrices,valuedVolume,referencePrice,metric,type Prices} from '../lib/metrics.ts';
import {productionPoints,productionCsv} from '../lib/production.ts';
import {readSelection} from '../lib/navigation.ts';
import {chartVisibility} from '../lib/chart-visibility.ts';
import {validateRelease} from '../lib/contract.ts';

const oil=JSON.parse(readFileSync(new URL('../public/data/prices.json',import.meta.url),'utf8'));
const release=validateRelease(JSON.parse(readFileSync(new URL('../public/data/release.json',import.meta.url),'utf8')));
const fixture=():Prices=>validatePrices({...oil,gas:{status:'available',interpretation:'reference_scenario',source:{...oil.source,series:'Henry Hub Natural Gas Spot Price',url:'https://www.eia.gov/dnav/ng/hist/rngwhhdm.htm',unit:'USD/MMBtu'},
  prices:[{periodo:'2026-07-01',usd_per_mmbtu:2},{periodo:'2026-08-01',usd_per_mmbtu:3}],
  conversion:{energy_basis:GAS_ENERGY_BASIS,m3_to_mmbtu:GAS_M3_TO_MMBTU,btu_per_cubic_foot:1036,source_url:'https://www.eia.gov/tools/faqs/faq.php?id=45&t=8',interpretation:'scenario'},reviewed_sources:[]}});

test('gas MMm3 is converted through m3 and MMBtu once, keeping physical zero',()=>{
 const p=fixture();const expected=1000/0.028316846592*1036/1e6*3;
 assert.ok(Math.abs(valuedVolume(0.001,'gas','2026-08-01',p)!-expected)<1e-10);
 assert.equal(valuedVolume(0,'gas','2026-08-01',p),0);
 assert.equal(valuedVolume(-1,'gas','2026-08-01',p),null);
 assert.equal(valuedVolume(Number.NaN,'gas','2026-08-01',p),null);assert.equal(valuedVolume(Number.MAX_VALUE,'gas','2026-08-01',p),null);
});
test('missing gas price remains null without borrowing neighboring months',()=>{
 const p=fixture();assert.equal(referencePrice(p,'2026-06-01','gas'),null);
 assert.equal(valuedVolume(1,'gas','2026-06-01',p),null);
 assert.equal(valuedVolume(1,'gas','2026-08-01',null),null);
});
test('unreviewed energy basis and changed conversion factor are rejected',()=>{
 for(const key of ['energy_basis','m3_to_mmbtu'] as const){const p=structuredClone(fixture()) as any;p.gas.conversion[key]=key==='energy_basis'?'MEASURED_VM':1;
 assert.throws(()=>validatePrices(p));assert.equal(valuedVolume(1,'gas','2026-08-01',p),null);}
});
test('gas comparisons use both physical volumes and each exact monthly price',()=>{
 const p=fixture(),current=release.production.find(r=>r.fluid==='gas'&&r.periodo==='2026-08-01')!,base=release.production.find(r=>r.fluid==='gas'&&r.periodo==='2026-07-01')!;
 const result=metric(current,release.production,p,'volume','value');
 assert.ok(Math.abs(result.mom!-((current.volume*3)/(base.volume*2)-1)*100)<1e-9);
 assert.equal(result.yoy,null);
});
test('gas USD deep link and chart selection remain available while missing months stay empty in CSV',()=>{
 const p=fixture();assert.equal(readSelection('?fluid=gas&mode=value&tab=production&month=2026-08-01').mode,'value');
 const visible=chartVisibility({wells:false,fluid:'gas',detailView:true,selected:'value',hasEstimated:true});assert.equal(visible.monetary,true);assert.equal(visible.showPhysical,false);
 const points=productionPoints(release.production,'gas','2026-08-01',12,p,'value');assert.equal(points.find(r=>r.periodo==='2026-06-01')!.value,null);
 const csv=productionCsv(points,'gas','value');assert.match(csv,/henry_hub_USD_per_MMBtu/);assert.match(csv,/USD_estimated/);assert.match(csv,/energy_basis_scenario/);assert.match(csv,/EIA_US_AVERAGE_1036_BTU_PER_CUBIC_FOOT_SCENARIO_V1/);
});
test('duplicate months and zero/invalid Henry Hub quotes never validate',()=>{
 const p=fixture() as any;p.gas.prices.push(p.gas.prices[0]);assert.throws(()=>validatePrices(p));
 const zero=fixture() as any;zero.gas.prices[0].usd_per_mmbtu=0;assert.throws(()=>validatePrices(zero));assert.equal(valuedVolume(1,'gas','2026-07-01',zero),null);
});

test('operator CSV carries gas reference metadata and leaves missing valuations empty',()=>{
 const p=fixture();const entity=release.entities.find(e=>e.dimension==='company'&&e.fluid==='gas'&&e.periodo==='2026-08-01'&&e.volume>0)!;
 const points=operatorHistory(release.entities,release.production,'gas','2026-08-01',12,entity.entity_id,p,'value','mom');
 const lines=operatorCsv(points,'gas','value').split('\n');assert.match(lines[0],/benchmark,energy_basis_scenario,m3_to_mmbtu_scenario$/);
 assert.match(lines.find(line=>line.startsWith('2026-08-01,'))!,/EIA_HENRY_HUB_MONTHLY,EIA_US_AVERAGE_1036_BTU_PER_CUBIC_FOOT_SCENARIO_V1/);
 const missing=lines.find(line=>line.startsWith('2026-06-01,'))!.split(',');assert.equal(missing[2],'');assert.deepEqual(missing.slice(-3),['','','']);
});
