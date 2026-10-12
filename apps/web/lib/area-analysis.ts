import type { Entity, Row } from './contract.ts';
import { historyWindow } from './history.ts';
import { change, comparisonOffset, effectiveMode, entityValue, shiftMonth, type Comparison, type Mode, type Prices } from './metrics.ts';

export type AreaActivity = 'all' | 'producing' | 'inactive';
export type AreaDirection = 'all' | 'up' | 'down';
export type AreaSort = 'volume' | 'name' | 'change' | 'wells';
export function areaSeries(entities: Entity[], current: Row, id: string) {
  return entities.filter(e => e.dimension === 'area' && e.fluid === current.fluid && e.entity_id === id && e.periodo <= current.periodo).sort((a,b)=>a.periodo.localeCompare(b.periodo));
}
export function areaChange(entity: Entity, entities: Entity[], prices: Prices|null, mode: Mode, comparison: Comparison) {
  const shown = effectiveMode(mode, entity.fluid);
  const base = entities.find(e=>e.dimension==='area' && e.entity_id===entity.entity_id && e.fluid===entity.fluid && e.periodo===shiftMonth(entity.periodo, comparisonOffset(comparison)));
  const value = entityValue(entity, prices, shown), previous = base ? entityValue(base, prices, shown) : null;
  return {value, base:previous, delta: value == null || previous == null ? null : value-previous, pct: change(value,previous), basePeriod: shiftMonth(entity.periodo,comparisonOffset(comparison))};
}
export function areaRanking(entities: Entity[], current: Row, prices: Prices|null, mode: Mode, comparison: Comparison, options: {query?:string;activity?:AreaActivity;direction?:AreaDirection;sort?:AreaSort}={}) {
  const q = (options.query??'').trim().toLocaleLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
  return entities.filter(e=>e.dimension==='area' && e.fluid===current.fluid && e.periodo===current.periodo).map(e=>({entity:e, ...areaChange(e,entities,prices,mode,comparison), share: current.volume>0?e.volume/current.volume*100:null})).filter(r=> {
    const text=`${r.entity.entity_name} ${r.entity.entity_id}`.toLocaleLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
    return text.includes(q) && (options.activity!=='producing'||r.entity.volume>0) && (options.activity!=='inactive'||r.entity.volume===0) && (options.direction!=='up'||r.pct!=null&&r.pct>0) && (options.direction!=='down'||r.pct!=null&&r.pct<0);
  }).sort((a,b)=>options.sort==='name'?a.entity.entity_name.localeCompare(b.entity.entity_name):options.sort==='wells'?b.entity.positive_producing_wells-a.entity.positive_producing_wells:options.sort==='change'?(b.pct??-Infinity)-(a.pct??-Infinity)||a.entity.volume_rank-b.entity.volume_rank:a.entity.volume_rank-b.entity.volume_rank);
}
export function areaPoints(entities: Entity[], rows: Row[], current: Row, id: string, range: number, prices: Prices|null, mode: Mode, comparison: Comparison) {
  const series = areaSeries(entities,current,id);
  return historyWindow(rows,current.fluid,current.periodo,range).points.map(p=> {
    const e=series.find(e=>e.periodo===p.periodo);
    const c=e?areaChange(e,entities,prices,mode,comparison):null;
    return {periodo:p.periodo,value:c?.value??null,volume:e?.volume??null,wells:e?.positive_producing_wells??null,delta:c?.delta??null,pct:c?.pct??null};
  });
}
