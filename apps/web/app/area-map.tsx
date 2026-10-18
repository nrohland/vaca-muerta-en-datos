"use client";
import {useEffect,useState} from 'react';
import type {areaRanking} from '../lib/area-analysis';
import {useLocale} from '../lib/locale';
import {ChartCard} from './dashboard-components';
type Geometry = {context?:{path:string;extent:{x:number;y:number;width:number;height:number}};features:{id:string;path:string}[];catalog_count:number;retrieved_at:string};
const source='https://hidrocarburos.energianeuquen.gob.ar/gis';
export function AreaMap({entries,selected,onSelect,unit,period}:{entries:ReturnType<typeof areaRanking>;selected:string;onSelect:(id:string)=>void;unit:string;period:string}){
 const {language,month,number,percent}=useLocale(),l=(es:string,en:string)=>language==='es'?es:en;
 const [geometry,setGeometry]=useState<Geometry|null>(null),[failed,setFailed]=useState(false),[active,setActive]=useState('');
 useEffect(()=>{const controller=new AbortController();fetch(`${process.env.NEXT_PUBLIC_BASE_PATH??'/vaca-muerta-pulse'}/geography/areas.json`,{signal:controller.signal}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(g=>{
  if(g.schema_version!==1||g.view_box!=='0 0 760 560'||!Array.isArray(g.features)||g.features.length>300||(g.context&&(!/^[MLZ\d.,\s-]+$/.test(g.context.path)||g.context.path.length>20000||Object.values(g.context.extent).some(v=>typeof v!=='number'||!Number.isFinite(v))))||g.features.some((f:any)=>typeof f.id!=='string'||typeof f.path!=='string'||f.path.length>40000||!/^[MLZ\d.,\s-]+$/.test(f.path)))throw Error();
  setGeometry(g);
 }).catch(()=>{if(!controller.signal.aborted)setFailed(true);});return()=>controller.abort();},[]);
 const lookup=new Map(entries.map(e=>[e.entity.entity_id,e])),ids=new Set(geometry?.features.map(f=>f.id));
 const mapped=entries.filter(e=>ids.has(e.entity.entity_id)),total=entries.reduce((s,e)=>s+e.entity.volume,0),covered=mapped.reduce((s,e)=>s+e.entity.volume,0);
 const max=Math.max(1,...mapped.map(e=>e.value??0)),hover=lookup.get(active||selected),color=unit==='USD'?'var(--value-line)':'var(--accent)';
 return <ChartCard title={l('Mapa de áreas · Neuquén','Area map · Neuquén')} subtitle={`${month(period)} · ${unit}`} className="area-map-card">
  {failed?<p className="chart-context">{l('Mapa no disponible. El ranking y el detalle siguen disponibles.','Map unavailable. Ranking and details remain available.')}</p>:!geometry?<p role="status">{l('Cargando geometrías…','Loading geometry…')}</p>:<>
   <div className="map-readout" aria-live="polite"><strong>{hover?.entity.entity_name??l('Seleccioná un área del mapa','Select an area on the map')}</strong><span>{hover?`${number(hover.value,2)} ${unit} · ${month(period)}`:l('Pasá el cursor o navegá con Tab para ver el detalle.','Hover or use Tab to inspect an area.')}</span>{hover&&<button className="text-action" onClick={()=>onSelect(hover.entity.entity_id)}>{l('Ver detalle','View details')} ↗</button>}</div>
   <div className="map-frame"><svg className="area-map" viewBox="0 0 760 560" aria-label={l('Polígonos oficiales de áreas de Neuquén','Official Neuquén area polygons')} onMouseLeave={()=>setActive('')}>
    {geometry.features.map(f=>{const e=lookup.get(f.id);return <path key={f.id} d={f.path} fillRule="evenodd" fill={e?.value==null?'var(--rule)':color} fillOpacity={e?.value==null?.4:e.value===0?.14:.25+.75*Math.sqrt(e.value/max)} stroke={selected===f.id||active===f.id?'var(--ink)':'var(--surface)'} strokeWidth={selected===f.id||active===f.id?2.5:1} vectorEffect="non-scaling-stroke" role="button" tabIndex={0} aria-pressed={selected===f.id} aria-label={`${e?.entity.entity_name??f.id} · ${number(e?.value??null,2)} ${unit} · ${month(period)}`} onMouseEnter={()=>setActive(f.id)} onFocus={()=>setActive(f.id)} onBlur={()=>setActive('')} onClick={()=>onSelect(f.id)} onKeyDown={event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();onSelect(f.id);}}}/>;})}
   </svg>
   {geometry.context&&<figure className="map-context"><figcaption>Argentina</figcaption><svg viewBox="0 0 160 250" role="img" aria-label={l('Ubicación de las áreas ampliadas dentro de Argentina','Location of the enlarged areas within Argentina')}><path d={geometry.context.path} fill="var(--rule)" stroke="var(--muted)" strokeWidth=".8"/><rect {...geometry.context.extent} fill="var(--accent)" fillOpacity=".3" stroke="var(--accent)" strokeWidth="2"/></svg><span>{l('Neuquén · áreas ampliadas','Neuquén · enlarged areas')}</span></figure>}
   </div>
   <div className="map-legend"><span>{l('Menor','Lower')}</span><i style={{background:`linear-gradient(to right, color-mix(in srgb, ${color} 25%, var(--surface)), ${color})`}}/><span>{l('Mayor','Higher')} · {unit}</span></div>
   <p className="chart-context">{mapped.length}/{entries.length} {l('áreas del período ubicadas','period areas located')} · {total>0?percent(covered/total*100):'—'} {l('del volumen seleccionado','of selected volume')}.</p>
   {selected&&!ids.has(selected)&&<p className="chart-context" role="status">{l('El área seleccionada no tiene geometría verificada; su detalle sigue disponible.','The selected area has no verified geometry; its details remain available.')}</p>}
   <details className="map-source"><summary>{l('Fuente, cobertura y límites del mapa','Map source, coverage and limitations')}</summary><p>{l('Geometrías de referencia del portal oficial de Neuquén, recuperadas el','Reference geometry from the official Neuquén portal, retrieved on')} {geometry.retrieved_at}. {l('Fecha de vigencia no informada: no reconstruye límites históricos ni reemplaza un catastro legal. Coincidencia exacta de código y nombre; no se infieren operadores. Las áreas sin coincidencia permanecen en el ranking. Los filtros locales de búsqueda aplican al ranking.','Effective date unavailable: historical boundaries are not reconstructed and this is not a legal cadastre. Exact code and name match; operators are not inferred. Unmatched areas remain in the ranking. Local search filters apply to the ranking.')} {l('Contexto de Argentina: Natural Earth 1:110m.','Argentina context: Natural Earth 1:110m.')} <a href={source} target="_blank" rel="noreferrer">{l('Fuente oficial','Official source')} ↗</a></p></details>
  </>}
 </ChartCard>;
}
