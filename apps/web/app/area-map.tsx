"use client";
import {useEffect,useRef,useState} from 'react';
import type {Map as LibreMap,Marker} from 'maplibre-gl';
import type {FeatureCollection,MultiPolygon} from 'geojson';
import type {areaRanking} from '../lib/area-analysis';
import {bubbleRadius,mapValue} from '../lib/map-analysis';
import {useLocale} from '../lib/locale';
import {ChartCard} from './dashboard-components';
import 'maplibre-gl/dist/maplibre-gl.css';

type Geometry=FeatureCollection<MultiPolygon,{area_id:string;anchor:[number,number]}>&{
 schema_version:number;bounds:[[number,number],[number,number]];retrieved_at:string;catalog_count:number;
};
const source='https://hidrocarburos.energianeuquen.gob.ar/gis';
export function AreaMap({entries,selected,onSelect,unit,period}:{entries:ReturnType<typeof areaRanking>;selected:string;onSelect:(id:string)=>void;unit:string;period:string}){
 const {language,month,number,compact,percent}=useLocale(),l=(es:string,en:string)=>language==='es'?es:en;
 const [geometry,setGeometry]=useState<Geometry|null>(null),[failed,setFailed]=useState(false),[ready,setReady]=useState(false),[active,setActive]=useState(''),[baseFailed,setBaseFailed]=useState(false);
 const container=useRef<HTMLDivElement>(null),map=useRef<LibreMap|null>(null),markers=useRef<Marker[]>([]);
 const latest=useRef({onSelect});latest.current={onSelect};
 useEffect(()=>{const controller=new AbortController();fetch(`${process.env.NEXT_PUBLIC_BASE_PATH??'/vaca-muerta-pulse'}/geography/areas.json`,{signal:controller.signal}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(g=>{
  if(g.schema_version!==2||g.type!=='FeatureCollection'||!Array.isArray(g.features)||g.features.length>300||g.features.some((f:any)=>typeof f.id!=='string'||f.geometry?.type!=='MultiPolygon'||!Array.isArray(f.properties?.anchor)||f.properties.anchor.length!==2||f.properties.anchor.some((v:any)=>!Number.isFinite(v))))throw Error();
  setGeometry(g);
 }).catch(()=>{if(!controller.signal.aborted)setFailed(true);});return()=>controller.abort();},[]);
 useEffect(()=>{
  if(!geometry||!container.current)return;
  let disposed=false;let instance:LibreMap|undefined;
  import('maplibre-gl').then(ml=>{
   if(disposed||!container.current)return;
   ml.setWorkerUrl(new URL('maplibre-gl/dist/maplibre-gl-worker.mjs',import.meta.url).toString());
   instance=new ml.Map({container:container.current,style:{version:8,sources:{basemap:{type:'raster',tiles:['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],tileSize:256,maxzoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'}},layers:[{id:'base',type:'raster',source:'basemap',paint:{'raster-saturation':-1,'raster-opacity':.65,'raster-contrast':-.1}}]},bounds:geometry.bounds,fitBoundsOptions:{padding:35},maxZoom:14,minZoom:2,cooperativeGestures:true,attributionControl:false,renderWorldCopies:false});
   map.current=instance;
   instance.addControl(new ml.NavigationControl({showCompass:false}),'top-right');
   instance.addControl(new ml.AttributionControl({compact:false}),'bottom-right');
   instance.on('error',event=>{if((event as any).sourceId==='basemap')setBaseFailed(true);});
   instance.on('load',()=>{
    if(disposed||!instance)return;
    instance.on('sourcedata',event=>{if(!disposed&&event.sourceId==='areas'&&event.isSourceLoaded)setReady(true);});
    instance.addSource('areas',{type:'geojson',data:geometry});
    instance.addLayer({id:'area-fill',type:'fill',source:'areas',paint:{'fill-color':'#8c9ba4','fill-opacity':.10}});
    instance.addLayer({id:'area-borders',type:'line',source:'areas',paint:{'line-color':'#627785','line-opacity':.8,'line-width':1.15}});
    instance.on('click','area-fill',event=>{const id=event.features?.[0]?.properties?.area_id;if(typeof id==='string')latest.current.onSelect(id);});
    instance.on('mousemove','area-fill',event=>{if(instance)instance.getCanvas().style.cursor='pointer';const id=event.features?.[0]?.properties?.area_id;if(typeof id==='string')setActive(id);});
    instance.on('mouseleave','area-fill',()=>{if(instance)instance.getCanvas().style.cursor='';setActive('');});
   });
  }).catch(()=>{if(!disposed)setFailed(true);});
  return()=>{disposed=true;setReady(false);markers.current.forEach(m=>m.remove());markers.current=[];instance?.remove();map.current=null;};
 },[geometry]);
 const lookup=new Map(entries.map(e=>[e.entity.entity_id,e])),ids=new Set(geometry?.features.map(f=>String(f.id)));
 const mapped=entries.filter(e=>ids.has(e.entity.entity_id)),total=entries.reduce((s,e)=>s+e.entity.volume,0),covered=mapped.reduce((s,e)=>s+e.entity.volume,0);
 const reported=entries.filter(e=>Number(e.entity.reported_well_rows)>0&&!e.entity.is_absent_current).length;
 const maximum=Math.max(0,...mapped.map(e=>mapValue(e)??0)),hover=lookup.get(active||selected);
 const valueText=(v:number|null)=>v==null?l('Sin dato','No data'):`${unit==='MMm³'?number(v,2):compact(v)} ${unit}`;
 useEffect(()=>{
  if(!ready||!geometry||!map.current)return;
  let disposed=false;
  import('maplibre-gl').then(ml=>{
   if(disposed||!map.current)return;
   markers.current.forEach(m=>m.remove());markers.current=[];
   const sorted=[...geometry.features].sort((a,b)=>(mapValue(lookup.get(String(b.id)))??0)-(mapValue(lookup.get(String(a.id)))??0));
   for(const feature of sorted){
    const id=String(feature.id),entry=lookup.get(id),value=mapValue(entry),radius=bubbleRadius(value,maximum);
    const button=document.createElement('button');button.type='button';button.className='area-bubble';button.dataset.area=id;button.dataset.state=value==null?'missing':value===0?'zero':'positive';
    button.style.setProperty('--bubble-size',`${radius*2}px`);button.style.setProperty('--bubble-color',unit==='USD'?'var(--value-line)':'var(--accent)');button.style.width=`${Math.max(30,radius*2+4)}px`;button.style.height=`${Math.max(30,radius*2+4)}px`;
    button.setAttribute('aria-label',`${entry?.entity.entity_name??id} · ${valueText(value)} · ${month(period)}`);button.setAttribute('aria-pressed',String(selected===id));
    const circle=document.createElement('span');circle.className='area-bubble-symbol';button.append(circle);
    button.addEventListener('mouseenter',()=>setActive(id));button.addEventListener('focus',()=>setActive(id));button.addEventListener('mouseleave',()=>setActive(''));button.addEventListener('blur',()=>setActive(''));
    button.addEventListener('click',event=>{event.stopPropagation();latest.current.onSelect(id);});
    const marker=new ml.Marker({element:button,anchor:'center'}).setLngLat(feature.properties.anchor).addTo(map.current);
    markers.current.push(marker);
   }
   const root=map.current.getContainer();
   for(const [selector,title] of [['.maplibregl-ctrl-zoom-in',l('Acercar','Zoom in')],['.maplibregl-ctrl-zoom-out',l('Alejar','Zoom out')]]){const button=root.querySelector(selector);button?.setAttribute('aria-label',title);button?.setAttribute('title',title);}
  });
  return()=>{disposed=true;};
 // Recreate inexpensive DOM markers when labels, values or selected state change; camera persists.
 },[ready,geometry,entries,unit,period,language]);
 useEffect(()=>{for(const marker of markers.current){const button=marker.getElement();button.setAttribute('aria-pressed',String(button.dataset.area===selected));}},[selected,ready,entries,unit,language]);
 const focusArea=()=>{if(geometry)map.current?.fitBounds(geometry.bounds,{padding:35,duration:350});};
 const seeDetail=()=>{if(!hover)return;onSelect(hover.entity.entity_id);setTimeout(()=>document.getElementById('area-detail')?.scrollIntoView({behavior:'smooth',block:'start'}),0);};
 return <ChartCard title={l('Dónde se concentra la producción','Where production is concentrated')} subtitle={`${month(period)} · ${unit}`} className="area-map-card">
  <div className="map-intro"><p>{unit==='USD'?l('La superficie de cada círculo representa el valor estimado del área.','Each circle’s area represents the concession’s estimated value.'):l('La superficie de cada círculo representa el volumen del área, no su extensión territorial.','Each circle’s area represents the concession’s volume, not its geographic size.')}{unit==='USD'&&<> {l('En USD representa valor estimado a referencia internacional.','In USD it represents estimated value at an international reference.')}</>}</p><div className="map-view-controls" role="group" aria-label={l('Extensión del mapa','Map extent')}><button onClick={()=>map.current?.fitBounds([[-74,-56],[-52,-21]],{padding:24,duration:500})}>Argentina</button><button onClick={focusArea}>{l('Áreas de Vaca Muerta','Vaca Muerta areas')}</button></div></div>
  <p className="map-coverage">{reported} {l('con registros este mes','with records this month')} · {entries.length} {l('en catálogo histórico','in historical catalog')} · {mapped.length} {l('con geometría','with geometry')} · {total>0?percent(covered/total*100):'—'} {l('del volumen ubicado','of volume located')}</p>
  <div className="map-readout" aria-live="polite"><strong>{hover?.entity.entity_name??l('Explorá las áreas en el mapa o el ranking','Explore areas on the map or ranking')}</strong><span>{hover?`${valueText(mapValue(hover))} · ${month(period)}`:l('Acercá el mapa para distinguir áreas cercanas. Los círculos representan concesiones, no pozos.','Zoom in to distinguish nearby areas. Circles represent concessions, not wells.')}</span>{hover&&<button className="text-action" onClick={seeDetail}>{l('Ver indicadores del área','View area metrics')} ↗</button>}</div>
  <div className="bubble-legend" aria-label={l('Escala de volumen de los círculos','Circle volume scale')}><div><strong>{unit==='USD'?l('Valor estimado del mes','Monthly estimated value'):l('Volumen del mes','Monthly volume')} · {unit}</strong><span>{l('Una escala por mes, común a todas las áreas ubicadas.','One scale per month, shared by every located area.')}</span><div className="map-state-key"><span><i className="zero"/>{l('Cero','Zero')}</span><span><i className="missing"/>{l('Sin dato','No data')}</span></div></div>{maximum>0&&<svg className="bubble-size-key" width="250" height="72" role="img" aria-label={[maximum,maximum/4,maximum/16].map(valueText).join('; ')}>{[maximum,maximum/4,maximum/16].map(value=>{const radius=bubbleRadius(value,maximum),top=60-radius*2;return <g key={value}><circle cx="30" cy={60-radius} r={radius} fill="none" stroke={unit==='USD'?'var(--value-line)':'var(--accent)'} strokeWidth="1.3"/><line x1="30" x2="76" y1={top} y2={top} stroke="var(--muted)" strokeWidth=".7"/><text x="82" y={top+4} fill="var(--muted)" fontSize="11">{valueText(value)}</text></g>;})}</svg>}</div>
  <div className={`geo-map ${unit==='USD'?'geo-map--value':''}`} ref={container} role="region" aria-label={l('Mapa de volumen por concesión','Concession volume map')}/>
  {!ready&&!failed&&<p role="status" className="chart-context">{l('Cargando mapa…','Loading map…')}</p>}
  {failed&&<p role="status" className="chart-context">{l('El mapa no pudo iniciarse. Usá el ranking para explorar todas las áreas.','The map could not start. Use the ranking to explore every area.')}</p>}
  {baseFailed&&<p className="chart-context">{l('Fondo geográfico no disponible; se conservan las concesiones y los datos.','Geographic background unavailable; concessions and data remain available.')}</p>}

  {selected&&!ids.has(selected)&&<p role="status" className="chart-context">{l('El área seleccionada no tiene geometría verificada; sus indicadores siguen disponibles.','The selected area has no verified geometry; its metrics remain available.')}</p>}
  <p className="map-caveat">{l('Geometrías de referencia: no reconstruyen límites históricos. La búsqueda y los filtros de la lista afectan sólo al ranking.','Reference geometry does not reconstruct historical boundaries. List search and filters affect only the ranking.')}</p>
  <details className="map-source"><summary>{l('Fuentes y cobertura geográfica','Sources and geographic coverage')}</summary><p>{l('Polígonos oficiales de Neuquén, coincidencia exacta de código y nombre. Recuperados el','Official Neuquén polygons, exact code and name match. Retrieved on')} {geometry?.retrieved_at??'—'}. {l('No se infieren operadores ni posiciones de pozos. Las áreas sin geometría conservan ranking y detalle.','Operators and well locations are not inferred. Areas without geometry retain ranking and details.')} <a href={source} target="_blank" rel="noreferrer">{l('Fuente oficial','Official source')} ↗</a></p></details>
 </ChartCard>;
}
