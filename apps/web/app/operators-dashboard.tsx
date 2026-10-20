"use client";
import {trendClass,kpiState} from "../lib/presentation";
import { useMemo, useState } from 'react';
import { Line, ComposedChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { Entity, Row } from '../lib/contract';
import { effectiveMode, metric, type Comparison, type Mode, type Prices } from '../lib/metrics';
import { historyTicks } from '../lib/history';
import { useLocale } from '../lib/locale';
import { operatorName } from '../lib/operators';
import { filterOperators, operatorCsv, operatorHistory, operatorRanking, type OperatorDirection, type OperatorSort } from '../lib/operator-analysis';
import { Change, gasReferenceMethod, ChartCard, KpiCard, ReferenceValuationNote, OperatorLogo, RankingItem, shortNames } from './dashboard-components';
import './operators.css';

const text = {
  title:['Operadores','Operators'], intro:['Quiénes producen, su participación y su evolución mensual.','Who produces, their share and their monthly evolution.'],
  eyebrow:['Explorar los operadores','Explore operators'], ranking:['Ranking completo','Complete ranking'], search:['Buscar operador','Search operator'],
  searchHint:['Nombre o identificador','Name or identifier'], filter:['Variación','Change'], all:['Todos','All'], growing:['En crecimiento','Growing'], declining:['En descenso','Declining'], noBase:['Sin base disponible','No available base'],
  sort:['Ordenar por','Sort by'], volume:['Producción','Production'], growth:['Cambio absoluto','Absolute change'], name:['Nombre','Name'],
  total:['Producción de cuenca','Basin production'], estimated:['Valor estimado de cuenca','Estimated basin value'], count:['Operadores con producción','Producing operators'],
  countContext:['Volumen positivo en el período','Positive volume in the period'], top5:['Participación del top 5','Top 5 share'], top5Context:['Sobre el total de cuenca · escala 0–100%','Of basin total · 0–100% scale'],
  largest:['Mayor cambio absoluto','Largest absolute change'], missing:['No disponible','Unavailable'], noComparison:['Sin comparador','No comparator'], vs:['vs.','vs.'],
  results:['operadores','operators'], empty:['No hay operadores que coincidan con los filtros.','No operators match these filters.'], clear:['Restablecer filtros','Reset filters'],
  trend:['Evolución de los líderes','Leading operators over time'], trendIntro:['Los tres mayores del período seleccionado; el liderazgo puede cambiar en meses anteriores.','The selected period’s three largest operators; leadership may differ in previous months.'],
  monthly:['Volúmenes mensuales','Monthly volumes'], monetary:['Valores mensuales estimados','Estimated monthly values'], history:['Histórico','History'],
  period:['Mes','Month'], share:['Participación','Share'], wells:['Pozos productivos','Producing wells'], base:['Base de comparación','Comparison base'], delta:['Cambio absoluto','Absolute change'], pct:['Variación','Change'],
  source:['Fuente: Secretaría de Energía · Capítulo IV · Vaca Muerta no convencional.','Source: Secretariat of Energy · Chapter IV · unconventional Vaca Muerta.'],
  prices:['USD: volumen × precio mensual de referencia EIA; conversión energética estimada para gas. No facturación efectiva.','USD: volume × EIA monthly reference price; estimated energy conversion for gas. Not actual revenue.'],
  noPrice:['Falta el precio validado para este período. Los valores USD permanecen sin calcular.','The validated price for this period is missing. USD values remain uncalculated.'],
  gap:['Meses sin registro se conservan sin dato; no se interpolan ni equivalen a cero.','Months without records retain missing values; they are not interpolated or treated as zero.'],
  back:['← Todos los operadores','← All operators'], detail:['Detalle del operador','Operator detail'], detailVolume:['Producción mensual','Monthly production'], detailValue:['Valor mensual estimado','Estimated monthly value'],
  table:['Datos del operador','Operator data'], csv:['Descargar CSV','Download CSV'], tableCaption:['Datos mensuales y bases exactas de comparación.','Monthly data and exact comparison bases.'],
  invalid:['Este operador no tiene registro en el período y producto seleccionados.','This operator has no record for the selected period and product.'],
  grouped:['Grupo empresarial preparado en la fuente; no equivale a una única entidad legal.','Corporate group prepared in the source; not a single legal entity.'], legal:['Procedencia legal','Legal provenance'],
  previous:['Valor base','Base value'], available:['meses con registro','months with records'], select:['Elegí un operador del ranking para explorar su trayectoria.','Select an operator from the ranking to explore its history.'],
  producing:['Conteo del fluido seleccionado: pozos con volumen positivo.','Selected product count: wells with positive volume.'],
} as const;

export function OperatorsDashboard({entities,rows,current,prices,mode,comparison,range,setRange,operator,onOperator}: {
  entities:Entity[];rows:Row[];current:Row;prices:Prices|null;mode:Mode;comparison:Comparison;range:number;setRange:(n:number)=>void;operator:string;onOperator:(id:string)=>void;onArea?:(id:string)=>void;
}) {
  const {language,compact,number,percent,month,historyMonth,t}=useLocale();
  const L=(key:keyof typeof text)=>text[key][language==='es'?0:1];
  const [query,setQuery]=useState(''),[direction,setDirection]=useState<OperatorDirection>('all'),[sort,setSort]=useState<OperatorSort>('volume');
  const [flipped,setFlipped]=useState<number|null>(null);
  const monetary=effectiveMode(mode,current.fluid)==='value',unit=monetary?'USD':current.fluid==='oil'?'bbl':'MMm³';
  const format=(v:number|null)=>v==null?L('missing'):`${current.fluid==='gas'&&!monetary?number(v,2,0):compact(v)} ${unit}`;
  const signed=(v:number|null)=>v==null?L('noComparison'):`${v>0?'+':v<0?'−':''}${format(Math.abs(v))}`;
  const entries=useMemo(()=>operatorRanking(entities,current,prices,mode,comparison),[entities,current,prices,mode,comparison]);
  const filtered=filterOperators(entries,query,direction,sort);
  const selected=entries.find(e=>e.entity.entity_id===operator);
  const detail=operator ? entities.find(e=>e.dimension==='company'&&e.entity_id===operator&&e.fluid===current.fluid&&e.periodo<=current.periodo) : undefined;
  const detailName=selected?.name??(detail?operatorName(detail.entity_id,detail.entity_name):operator);
  const totalValue=metric(current,rows,prices,'volume',mode).value;
  const top5Share=current.volume>0?entries.slice(0,5).reduce((sum,e)=>sum+e.entity.volume,0)/current.volume*100:null;
  const largest=[...entries].filter(e=>e.delta!=null).sort((a,b)=>Math.abs(b.delta!)-Math.abs(a.delta!))[0];
  const points=useMemo(()=>operatorHistory(entities,rows,current.fluid,current.periodo,range,operator,prices,mode,comparison),[entities,rows,current.fluid,current.periodo,range,operator,prices,mode,comparison]);
  const leaders=useMemo(()=>entries.slice(0,3),[entries]);
  const leaderHistory=useMemo(()=>operator?[]:leaders.map(e=>operatorHistory(entities,rows,current.fluid,current.periodo,range,e.entity.entity_id,prices,mode,comparison)),[operator,leaders,entities,rows,current.fluid,current.periodo,range,prices,mode,comparison]);
  const chartPoints=useMemo(()=>operator?points:leaderHistory[0]?.map((p,i)=>({periodo:p.periodo,...Object.fromEntries(leaders.map((e,j)=>[e.entity.entity_id,leaderHistory[j][i]?.value??null]))}))??[],[operator,points,leaderHistory,leaders]);
  const card=(index:number,brief:string)=>({tooltip:brief+(monetary&&current.fluid==='gas'?' '+t(gasReferenceMethod):''),brief,flipped:flipped===index,onFlip:()=>setFlipped(flipped===index?null:index)});
  const pct=(v:number|null)=>v==null?L('noComparison'):percent(v,true);
  function download(){
    const url=URL.createObjectURL(new Blob(['\uFEFF',operatorCsv(points,current.fluid,mode)],{type:'text/csv;charset=utf-8'}));
    const a=document.createElement('a');a.href=url;a.download=`operator-${operator}-${current.fluid}-${current.periodo.slice(0,7)}-${monetary?'usd':'volume'}.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  const chartTooltip=({active,payload,label}:any)=>!active?null:<div className="chart-tooltip compact-chart-tooltip"><strong>{month(String(label))}</strong>{payload?.map((p:any)=><div className="tooltip-row" key={p.dataKey}><span>{operator?detailName:leaders.find(e=>e.entity.entity_id===p.dataKey)?.name}</span><strong>{format(p.value)}</strong></div>)}</div>;
  const provenance=selected?.entity.legal_operator_provenance;
  const legal=Array.isArray(provenance)?provenance.filter((p:any)=>typeof p?.idempresa==='string'&&typeof p?.empresa==='string') as {idempresa:string;empresa:string}[]:[];
  return <div className="operators-dashboard" data-detail={!!operator}>
    <header className="operators-heading"><div><p className="eyebrow sr-only">{L(operator?'detail':'eyebrow')}</p><h1>{operator?detailName:L('title')}</h1><p className={operator?undefined:"sr-only"}>{operator?`${L('volume')} · ${t(current.fluid==='oil'?'Petróleo':'Gas')}`:L('intro')}</p></div><span className="production-period">{month(current.periodo)}</span></header>
    {operator&&<button className="text-action operators-back" onClick={()=>onOperator('')}>{L('back')}</button>}
    <ReferenceValuationNote fluid={current.fluid} prices={prices} />
    {monetary&&totalValue==null&&<p className="availability-note" role="status">{L('noPrice')}</p>}
    {operator&&!selected&&<p className="availability-note" role="status">{L('invalid')}</p>}
    <div className="kpi-grid">
      <KpiCard {...card(0,monetary?L('prices'):L('monthly'))} variant="primary" label={L(operator?monetary?'detailValue':'detailVolume':monetary?'estimated':'total')} value={operator?format(selected?.value??null).replace(` ${unit}`,''):format(totalValue).replace(` ${unit}`,'')} unit={(operator?selected?.value:totalValue)==null?undefined:unit} context={month(current.periodo)} comparisons={operator?<span className="operators-neutral">{comparison==='mom'?'MoM':'YoY'} · <Change value={selected?.pct}/></span>:undefined}/>
      <KpiCard {...card(1,operator?L('top5Context'):L('countContext'))} label={L(operator?'share':'count')} value={operator?(selected?.share==null?L('missing'):percent(selected.share)):number(entries.filter(e=>e.entity.volume>0).length,0)} context={L(operator?'top5Context':'countContext')}/>
      <KpiCard {...card(2,operator?L('producing'):L('top5Context'))} label={L(operator?'wells':'top5')} value={operator?number(selected?.entity.positive_producing_wells??null,0):top5Share==null?L('missing'):percent(top5Share)} context={L(operator?'producing':'top5Context')}/>
      <KpiCard {...card(3,L('tableCaption'))} state={kpiState(operator?selected?.delta:largest?.delta)} label={L(operator?'delta':'largest')} value={signed(operator?selected?.delta??null:largest?.delta??null).replace(` ${unit}`,'')} unit={(operator?selected?.delta:largest?.delta)==null?undefined:unit} context={operator?`${L('vs')} ${month(selected?.basePeriod??points.at(-1)?.basePeriod??current.periodo)}`:largest?.name??L('noComparison')} comparisons={!operator&&largest?<span className="operators-neutral">{comparison==='mom'?'MoM':'YoY'} · {L('vs')} {month(largest.basePeriod)}</span>:undefined}/>
    </div>
    <div className="operators-grid">
      {!operator&&<ChartCard title={L('ranking')} subtitle={`${entries.length} ${L('results')} · ${month(current.periodo)}`} className="ranking-card operators-ranking">
        <div className="operators-controls"><label className="operators-search">{L('search')}<input type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder={L('searchHint')}/></label><label>{L('filter')}<select value={direction} onChange={e=>setDirection(e.target.value as OperatorDirection)}><option value="all">{L('all')}</option><option value="growing">{L('growing')}</option><option value="declining">{L('declining')}</option><option value="no-base">{L('noBase')}</option></select></label><label>{L('sort')}<select value={sort} onChange={e=>setSort(e.target.value as OperatorSort)}><option value="volume">{L('volume')}</option><option value="growth">{L('growth')}</option><option value="name">{L('name')}</option></select></label></div>
        <p className="operators-result-count" role="status">{filtered.length} / {entries.length} {L('results')}</p>
        {filtered.length?<ol className="ranking-list operators-ranking-list" tabIndex={0} aria-label={L('ranking')}>{filtered.map(e=><RankingItem key={e.entity.entity_id} position={entries.findIndex(r=>r.entity.entity_id===e.entity.entity_id)+1} logo={<OperatorLogo id={e.entity.entity_id}/>} name={shortNames[e.entity.entity_id] ?? e.name} fullName={e.entity.entity_name} production={format(e.value)} productionExact={`${number(e.value,2,0)} ${unit}`} participation={e.share} variation={e.pct} comparison={comparison} comparisonPeriod={month(e.basePeriod)} onSelect={()=>onOperator(e.entity.entity_id)}/>)}</ol>:<div className="operators-empty"><p>{L('empty')}</p><button className="text-action" onClick={()=>{setQuery('');setDirection('all');setSort('volume')}}>{L('clear')}</button></div>}
        <p className="chart-context">{L('top5Context')}. {L('select')}</p>
      </ChartCard>}
      <ChartCard title={operator?L('volume')+' · '+detailName:L('trend')} subtitle={operator?`${L(monetary?'monetary':'monthly')} · ${unit}`:`${L('monthly')} · ${unit}`} className="operators-evolution" action={<div className="ranges" aria-label={t('Período')} role="group">{[12,24,36,0].map(n=><button key={n} aria-pressed={range===n} onClick={()=>setRange(n)}>{n===0?L('history'):`${n}m`}</button>)}</div>}>
        {!operator&&<div className="chart-legend operators-leader-legend">{leaders.map((e,i)=><button key={e.entity.entity_id} onClick={()=>onOperator(e.entity.entity_id)}><i className={`leader-key leader-key-${i}`} style={{borderColor:monetary?'var(--value-line)':'var(--accent)',opacity:1-i*.25}}/>{shortNames[e.entity.entity_id] ?? e.name}</button>)}</div>}
        <div className="operators-plot" aria-hidden="true"><ResponsiveContainer width="100%" height="100%"><ComposedChart data={chartPoints} margin={{top:24,right:20,bottom:10,left:4}} accessibilityLayer={false}><XAxis dataKey="periodo" ticks={historyTicks(chartPoints.map(p=>p.periodo),range===0?chartPoints.length:range)} tickFormatter={p=>historyMonth(p)} minTickGap={34} tick={{fontSize:10,fill:'var(--muted)'}} tickLine={false} axisLine={false} tickMargin={10}/><YAxis width={58} domain={[0,'auto']} tickFormatter={compact} tick={{fontSize:11,fill:'var(--muted)'}} tickLine={false} axisLine={false}/><Tooltip content={chartTooltip} isAnimationActive={false}/>{operator?<Line type="linear" dataKey="value" stroke={monetary?'var(--value-line)':'var(--accent)'} strokeWidth={2.7} dot={chartPoints.length===1?{r:4}:false} activeDot={{r:4}} connectNulls={false} isAnimationActive={false}/>:leaders.map((e,i)=><Line key={e.entity.entity_id} type="linear" dataKey={e.entity.entity_id} stroke={monetary?'var(--value-line)':'var(--accent)'} strokeOpacity={1-i*.25} strokeDasharray={i===1?'6 3':i===2?'2 3':undefined} strokeWidth={i===0?2.8:2} dot={false} connectNulls={false} isAnimationActive={false}/>)}</ComposedChart></ResponsiveContainer></div>
        <p className="chart-context">{L('gap')}</p>
        {!operator&&<details className="data-disclosure"><summary>{t('Ver tabla de datos')}</summary><div className="operators-table-scroll"><table><caption>{L('monthly')} · {unit}</caption><thead><tr><th scope="col">{L('period')}</th>{leaders.map(e=><th scope="col" key={e.entity.entity_id}>{e.name}</th>)}</tr></thead><tbody>{chartPoints.map((p:any)=><tr key={p.periodo}><th scope="row">{historyMonth(p.periodo)}</th>{leaders.map(e=><td key={e.entity.entity_id}>{number(p[e.entity.entity_id],2,0)}</td>)}</tr>)}</tbody></table></div></details>}
        {operator&&<p className="chart-context">{points.filter(p=>p.value!=null).length} / {points.length} {L('available')}</p>}
      </ChartCard>
    </div>
    {operator&&<ChartCard title={L('table')} subtitle={L('tableCaption')} action={<button className="operators-download" onClick={download}>{L('csv')}</button>} className="operators-data"><div className="operators-table-scroll" tabIndex={0} role="region" aria-label={L('table')}><table><caption className="sr-only">{detailName} · {unit}</caption><thead><tr>{[L('period'),`${L(monetary?'detailValue':'detailVolume')} (${unit})`,L('share'),L('wells'),L('delta')+` (${unit})`,L('pct'),L('base'),L('previous')+` (${unit})`].map(v=><th scope="col" key={v}>{v}</th>)}</tr></thead><tbody>{[...points].reverse().map(p=><tr key={p.periodo}><th scope="row"><time dateTime={p.periodo}>{historyMonth(p.periodo)}</time></th><td>{number(p.value,2,0)}</td><td>{p.share==null?'—':percent(p.share)}</td><td>{number(p.wells,0)}</td><td className={trendClass(p.delta)}>{p.delta==null?'—':`${p.delta>0?'+':''}${number(p.delta,2,0)}`}</td><td className={trendClass(p.pct)}>{pct(p.pct)}</td><td>{historyMonth(p.basePeriod)}</td><td>{number(p.baseValue,2,0)}</td></tr>)}</tbody></table></div><p className="chart-context">{L('gap')}</p></ChartCard>}
    {legal.length>1&&<details className="operators-provenance"><summary>{L('legal')}</summary><p>{L('grouped')}</p><ul>{legal.map(p=><li key={p.idempresa}>{p.empresa} ({p.idempresa})</li>)}</ul></details>}
    <p className="operators-source sr-only">{L('source')} {monetary&&L('prices')}</p>
  </div>;
}
