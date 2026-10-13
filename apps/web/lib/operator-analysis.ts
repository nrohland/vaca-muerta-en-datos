import type { Entity, Fluid, Row } from './contract.ts';
import { GAS_ENERGY_BASIS, GAS_M3_TO_MMBTU, change, comparisonOffset, effectiveMode, entityValue, shiftMonth, type Comparison, type Mode, type Prices } from './metrics.ts';
import { historyWindow } from './history.ts';
import { operatorName } from './operators.ts';

export type OperatorEntry = { entity: Entity; name: string; value: number | null; share: number | null; baseValue: number | null; delta: number | null; pct: number | null; basePeriod: string };
export type OperatorDirection = 'all' | 'growing' | 'declining' | 'no-base';
export type OperatorSort = 'volume' | 'growth' | 'name';
export function operatorRanking(entities: Entity[], current: Row, prices: Prices | null, mode: Mode, comparison: Comparison): OperatorEntry[] {
  const shown = effectiveMode(mode, current.fluid);
  const basePeriod = shiftMonth(current.periodo, comparisonOffset(comparison));
  const relevant = entities.filter(e => e.dimension === 'company' && e.fluid === current.fluid);
  const bases = new Map(relevant.filter(e => e.periodo === basePeriod).map(e => [e.entity_id, e]));
  return relevant.filter(e => e.periodo === current.periodo).map(entity => {
    const base = bases.get(entity.entity_id);
    const value = entityValue(entity, prices, shown);
    const baseValue = base ? entityValue(base, prices, shown) : null;
    return {entity, name:operatorName(entity.entity_id,entity.entity_name), value, baseValue, basePeriod,
      share:current.volume > 0 ? entity.volume / current.volume * 100 : null,
      delta:value == null || baseValue == null ? null : value-baseValue, pct:change(value,baseValue)};
  }).sort((a,b)=>b.entity.volume-a.entity.volume || a.entity.entity_id.localeCompare(b.entity.entity_id));
}
export function filterOperators(entries: OperatorEntry[], query = '', direction: OperatorDirection = 'all', sort: OperatorSort = 'volume') {
  const q = query.trim().normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  const contains = (s:string) => s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().includes(q);
  return entries.filter(e => (!q || contains(e.name) || contains(e.entity.entity_id) || contains(e.entity.entity_name)) &&
    (direction === 'all' || direction === 'growing' && e.delta != null && e.delta>0 || direction === 'declining' && e.delta != null && e.delta<0 || direction === 'no-base' && e.baseValue==null))
    .sort((a,b)=>sort==='name'?a.name.localeCompare(b.name):sort==='growth'?(b.delta??-Infinity)-(a.delta??-Infinity)||a.entity.volume_rank-b.entity.volume_rank:b.entity.volume-a.entity.volume);
}
export function operatorHistory(entities:Entity[], rows:Row[], fluid:Fluid, period:string, range:number, id:string, prices:Prices|null, mode:Mode, comparison:Comparison) {
  const selected = entities.filter(e=>e.dimension==='company'&&e.fluid===fluid&&e.entity_id===id);
  const byPeriod = new Map(selected.map(e=>[e.periodo,e]));
  const basin = new Map(rows.filter(r=>r.fluid===fluid).map(r=>[r.periodo,r]));
  const shown=effectiveMode(mode,fluid);
  return historyWindow(rows,fluid,period,range).points.map(p=>{
    const row=byPeriod.get(p.periodo), basePeriod=shiftMonth(p.periodo,comparisonOffset(comparison)), base=byPeriod.get(basePeriod);
    const value=row?entityValue(row,prices,shown):null, baseValue=base?entityValue(base,prices,shown):null;
    const total=basin.get(p.periodo)?.volume;
    return {periodo:p.periodo,volume:row?.volume??null,value,baseValue,basePeriod,delta:value==null||baseValue==null?null:value-baseValue,pct:change(value,baseValue),
      share:row&&total!=null&&total>0?row.volume/total*100:null,wells:row?.positive_producing_wells??null};
  });
}
export function operatorCsv(points: ReturnType<typeof operatorHistory>, fluid:Fluid, mode:Mode) {
  const selected=effectiveMode(mode,fluid),factor=fluid==='gas'?1e6:1;
  const cell=(v:number|null)=>v==null?'':String(v);
  const scenario=fluid==='gas'&&selected==='value';
  return ['period,volume_'+(fluid==='oil'?'bbl':'m3')+',selected_'+(selected==='value'?'usd':fluid==='oil'?'bbl':'m3')+',share_pct,productive_wells,comparison_base,base_value,delta,pct'+(scenario?',benchmark,energy_basis_scenario,m3_to_mmbtu_scenario':''),
    ...points.map(p=>[p.periodo,cell(p.volume==null?null:p.volume*factor),cell(p.value==null?null:p.value*(selected==='value'?1:factor)),cell(p.share),cell(p.wells),p.basePeriod,cell(p.baseValue==null?null:p.baseValue*(selected==='value'?1:factor)),cell(p.delta==null?null:p.delta*(selected==='value'?1:factor)),cell(p.pct),...(scenario?(p.value==null?['','','']:['EIA_HENRY_HUB_MONTHLY',GAS_ENERGY_BASIS,String(GAS_M3_TO_MMBTU)]):[])].join(','))].join('\n');
}
