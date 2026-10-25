import type { Entity, Row } from './contract.ts';
import { historyWindow } from './history.ts';
import { change, comparisonOffset, effectiveMode, entityValue, shiftMonth, type Comparison, type Mode, type Prices } from './metrics.ts';

export type AreaActivity = 'all' | 'producing' | 'inactive';
export type AreaDirection = 'all' | 'up' | 'down';
export type AreaSort = 'volume' | 'name' | 'change' | 'wells';
export function areaSeries(entities: Entity[], current: Row, id: string) {
  return entities.filter(e => e.dimension === 'area' && e.fluid === current.fluid && e.entity_id === id && e.periodo <= current.periodo).sort((a,b)=>a.periodo.localeCompare(b.periodo));
}
function compareArea(entity: Entity, base: Entity|undefined, prices: Prices|null, mode: Mode, comparison: Comparison) {
  const shown = effectiveMode(mode, entity.fluid);
  const value = entityValue(entity, prices, shown), previous = base ? entityValue(base, prices, shown) : null;
  return {value, base:previous, delta: value == null || previous == null ? null : value-previous, pct: change(value,previous), basePeriod: shiftMonth(entity.periodo,comparisonOffset(comparison))};
}
export function areaChange(entity: Entity, entities: Entity[], prices: Prices|null, mode: Mode, comparison: Comparison) {
  const base = entities.find(e=>e.dimension==='area' && e.entity_id===entity.entity_id && e.fluid===entity.fluid && e.periodo===shiftMonth(entity.periodo, comparisonOffset(comparison)));
  return compareArea(entity,base,prices,mode,comparison);
}
export type AreaEntry = {entity: Entity; share: number|null} & ReturnType<typeof areaChange>;
export type AreaFilters = {query?:string;activity?:AreaActivity;direction?:AreaDirection;sort?:AreaSort};
export function filterAreas(entries: AreaEntry[], options: AreaFilters={}) {
  const q = (options.query??'').trim().toLocaleLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
  return entries.filter(r=> {
    const text=`${r.entity.entity_name} ${r.entity.entity_id}`.toLocaleLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
    return text.includes(q) && (options.activity!=='producing'||r.entity.volume>0) && (options.activity!=='inactive'||r.entity.volume===0) && (options.direction!=='up'||r.delta!=null&&r.delta>0) && (options.direction!=='down'||r.delta!=null&&r.delta<0);
  }).sort((a,b)=>options.sort==='name'?a.entity.entity_name.localeCompare(b.entity.entity_name):options.sort==='wells'?b.entity.positive_producing_wells-a.entity.positive_producing_wells:options.sort==='change'?(b.pct??-Infinity)-(a.pct??-Infinity)||a.entity.volume_rank-b.entity.volume_rank:a.entity.volume_rank-b.entity.volume_rank);
}
export function areaRanking(entities: Entity[], current: Row, prices: Prices|null, mode: Mode, comparison: Comparison, options: AreaFilters={}) {
  const relevant=entities.filter(e=>e.dimension==='area'&&e.fluid===current.fluid);
  const basePeriod=shiftMonth(current.periodo,comparisonOffset(comparison));
  const bases=new Map(relevant.filter(e=>e.periodo===basePeriod).map(e=>[e.entity_id,e]));
  const entries=relevant.filter(e=>e.periodo===current.periodo).map(entity=>({entity,...compareArea(entity,bases.get(entity.entity_id),prices,mode,comparison),share:current.volume>0?entity.volume/current.volume*100:null}));
  return filterAreas(entries,options);
}
export function areaPoints(entities: Entity[], rows: Row[], current: Row, id: string, range: number, prices: Prices|null, mode: Mode, comparison: Comparison) {
  const series = areaSeries(entities,current,id);
  const byPeriod=new Map(series.map(e=>[e.periodo,e]));
  return historyWindow(rows,current.fluid,current.periodo,range).points.map(p=> {
    const e=byPeriod.get(p.periodo);
    const c=e?compareArea(e,byPeriod.get(shiftMonth(p.periodo,comparisonOffset(comparison))),prices,mode,comparison):null;
    return {periodo:p.periodo,value:c?.value??null,volume:e?.volume??null,wells:e?.positive_producing_wells??null,delta:c?.delta??null,pct:c?.pct??null};
  });
}
