import type {areaRanking} from './area-analysis.ts';
export function bubbleRadius(value:number|null,maximum:number,maxRadius=28){
 return value==null||!Number.isFinite(value)||value<=0||maximum<=0?0:maxRadius*Math.sqrt(value/maximum);
}
export function mapValue(entry:ReturnType<typeof areaRanking>[number]|undefined){
 return !entry||entry.entity.is_absent_current||Number(entry.entity.reported_well_rows)===0?null:entry.value;
}
