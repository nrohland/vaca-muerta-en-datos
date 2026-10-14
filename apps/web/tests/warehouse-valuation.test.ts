import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {productionKpis} from '../lib/production.ts';
import {validateRelease} from '../lib/contract.ts';
import {GAS_ENERGY_BASIS,GAS_M3_TO_MMBTU,warehouseValue,metric,entityComparison} from '../lib/metrics.ts';
const source=JSON.parse(readFileSync(new URL('../public/data/release.json',import.meta.url),'utf8'));
function fixture(){
 const fields={estimated_value_usd:300,estimated_daily_value_usd:9,mom_estimated_value_usd:200,yoy_estimated_value_usd:null,estimated_ytd_value_usd:null,yoy_estimated_ytd_value_usd:null,price_usd_per_unit:2.78,price_unit:'USD/MMBtu',energy_basis:GAS_ENERGY_BASIS,valuation_method:'estimated_reference_scenario'};
 const r={...source.production.find((r:any)=>r.fluid==='gas'),...fields};
 const e={...source.entities.find((e:any)=>e.fluid==='gas'&&e.periodo===r.periodo),...fields};
 return {schema_version:1,status:'candidate',valuation:{schema_version:1,producer:'dbt',energy_basis_scenario:GAS_ENERGY_BASIS,m3_to_mmbtu_scenario:GAS_M3_TO_MMBTU},production:[r],entities:[e]};
}
test('warehouse valuation requires dbt producer, scenario and complete monetary fields',()=>{
 const f=fixture();validateRelease(f);
 for(const bad of [{...f,valuation:undefined},{...f,valuation:{...f.valuation,producer:'browser'}},{...f,valuation:{...f.valuation,m3_to_mmbtu_scenario:1}}])assert.throws(()=>validateRelease(bad));
 const missing=fixture();delete (missing.production[0] as any).estimated_daily_value_usd;assert.throws(()=>validateRelease(missing));
});
test('cross-fluid units or energetic methods fail closed before rendering',()=>{
 for(const [key,value] of [['price_unit','USD/bbl'],['valuation_method','estimated_reference'],['energy_basis','MEASURED_VM']]){const f=fixture();(f.production[0] as any)[key]=value;assert.throws(()=>validateRelease(f));}
});
test('warehouse unavailable and zero are distinct; browser quote does not fill absent values',()=>{
 const f=fixture();f.production[0].estimated_value_usd=null;f.production[0].estimated_daily_value_usd=null;f.production[0].valuation_method='unavailable';validateRelease(f);assert.equal(warehouseValue(f.production[0]),null);
 const zero=fixture();zero.production[0].estimated_value_usd=0;zero.production[0].estimated_daily_value_usd=0;validateRelease(zero);assert.equal(warehouseValue(zero.production[0]),0);
});
test('approved physical overview is unchanged while USD uses precomputed monthly/daily aggregates',()=>{
 const release=validateRelease(fixture());const row=release.production[0];assert.equal(metric(row,[row],null,'volume').value,row.volume);assert.equal(metric(row,[row],null,'rate').value,row.rate);assert.equal(metric(row,[row],null,'volume','value').value,300);assert.equal(metric(row,[row],null,'rate','value').value,9);assert.equal(entityComparison(release.entities[0],null,'value','mom'),50);
});

test('USD YTD consumes warehouse complete-calendar aggregates and does not sum a partial browser window',()=>{
 const r=validateRelease(fixture()).production[0];
 const row={...r,periodo:'2026-08-01',estimated_ytd_value_usd:700,yoy_estimated_ytd_value_usd:500};
 const k=productionKpis([row],'gas','2026-08-01',null,'value','yoy');assert.equal(k.accumulated,700);assert.equal(k.previousAccumulated,500);assert.ok(Math.abs(k.accumulatedGrowth!-40)<1e-10);
 assert.equal(productionKpis([{...row,estimated_ytd_value_usd:null}],'gas','2026-08-01',null,'value','yoy').accumulated,null);
});

test('reference price comes from the validated warehouse snapshot when the auxiliary asset is unavailable',()=>{
 const f=fixture();const r=f.production[0];validateRelease(f);
 assert.equal(metric(r,f.production,null,'price').value,2.78);
 const unavailable={...r,valuation_method:'unavailable',estimated_value_usd:null,estimated_daily_value_usd:null};
 assert.equal(metric(unavailable,[unavailable],null,'price').value,null);
});
