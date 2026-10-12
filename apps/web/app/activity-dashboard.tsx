"use client";
import { useState } from "react";
import { Bar, Cell, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Entity, Row } from "../lib/contract";
import { type Comparison, type Mode, type Prices } from "../lib/metrics";
import { historyRanges, historyWindow, historyTicks } from "../lib/history";
import { activityCsv, activityKpis, activityPoints, type ActivityPoint } from "../lib/activity-analysis";
import { useLocale } from "../lib/locale";
import { ChartCard, Evolution, KpiCard } from "./dashboard-components";
import "./activity.css";

export function ActivityDashboard({ rows, current, prices, mode, comparison, range, setRange }: {
  entities: Entity[]; rows: Row[]; current: Row; prices: Prices | null; mode: Mode; comparison: Comparison; range: number; setRange: (n: number) => void;
}) {
  const { language, number, percent, month, historyMonth } = useLocale();
  const text = (es: string, en: string) => language === "en" ? en : es;
  const [flipped, setFlipped] = useState<number | null>(null);
  const fluid = current.fluid, period = current.periodo;
  const points = activityPoints(rows, fluid, period, range);
  const k = activityKpis(rows, current, comparison);
  const coverage = historyWindow(rows, fluid, period, range);
  const unit = fluid === "oil" ? "bbl/pozo/d" : "m³/pozo/d";
  const translatedUnit = language === "en" ? unit.replace("pozo", "well") : unit;
  const signed = (v: number | null) => v == null ? text("Sin comparador", "No comparison") : `${v > 0 ? "+" : v < 0 ? "−" : ""}${number(Math.abs(v), 0)}`;
  const changeLabel = comparison === "mom" ? text("Mensual", "Month over month") : text("Interanual", "Year over year");
  const baseContext = `${text("vs.", "vs.")} ${historyMonth(k.basePeriod)}`;
  const methods = [
    text("IDs de pozo únicos con producción positiva del fluido elegido durante el mes. Un mismo pozo puede producir petróleo y gas; los conteos no se suman entre fluidos.", "Unique well IDs with positive production of the selected fluid during the month. A well may produce both oil and gas; fluid counts cannot be added."),
    text("Conteo actual menos conteo de su mes base exacto. Es una diferencia neta; no identifica pozos nuevos, reactivados o cerrados.", "Current count minus the count in the exact calendar base month. This net difference does not identify new, reactivated or closed wells."),
    text("Volumen mensual dividido por días calendario y por pozos productivos. Promedio del conjunto, no productividad por tiempo efectivo ni eficiencia de un pozo individual.", "Monthly volume divided by calendar days and productive wells. A population average, not effective operating time productivity or individual well efficiency."),
  ];
  const methodology = (index: number) => ({ tooltip: methods[index], brief: methods[index], flipped: flipped === index, onFlip: () => setFlipped(flipped === index ? null : index) });
  function download() {
    const url = URL.createObjectURL(new Blob(["\uFEFF", activityCsv(points, fluid)], {type: "text/csv;charset=utf-8"}));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = `vaca-muerta-activity-${fluid}-${period.slice(0,7)}.csv`; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const tooltip = (kind: "delta" | "average") => ({active, payload}: {active?: boolean; payload?: readonly {payload?: ActivityPoint}[]}) => {
    const p = payload?.[0]?.payload;
    return !active || !p ? null : <div className="chart-tooltip compact-chart-tooltip"><strong>{month(p.periodo)}</strong><div className="tooltip-row"><span>{kind === "delta" ? text("Cambio neto", "Net change") : text("Promedio diario", "Daily average")}</span><strong>{kind === "delta" ? signed(p[comparison]) : `${number(p.average, 2)} ${translatedUnit}`}</strong></div>{kind === "delta" && <span>{text("vs.", "vs.")} {historyMonth(p[comparison === "mom" ? "momBase" : "yoyBase"])}</span>}</div>;
  };
  return <div className="activity-dashboard">
    <header className="activity-heading"><div><p className="eyebrow">{text("Explorar la actividad", "Explore activity")}</p><h1>{text("Actividad", "Activity")}</h1><p>{text("Pozos productivos, dinámica del conjunto y producción media por pozo.", "Productive wells, population dynamics and average production per well.")}</p></div><span className="activity-period">{month(period)}</span></header>
    {mode === "value" && <p className="availability-note" role="status">{text("Actividad se mide en pozos y unidades físicas. La selección Valor USD se conserva para las demás pestañas.", "Activity uses well counts and physical units. The Value USD selection is retained for other tabs.")}</p>}
    <div className="kpi-grid activity-kpis">
      <KpiCard {...methodology(0)} variant="primary" label={text("Pozos productivos", "Productive wells")} value={number(k.wells, 0)} unit={text("pozos", "wells")} context={month(period)} comparisons={<span className="activity-neutral">{changeLabel} · {k.pct == null ? text("Sin comparador", "No comparison") : percent(k.pct, true)}</span>} />
      <KpiCard {...methodology(1)} label={text("Cambio neto de pozos", "Net well count change")} value={signed(k.delta)} unit={k.delta == null ? undefined : text("pozos", "wells")} context={baseContext} comparisons={<span className="activity-neutral">{text("Diferencia de conteos, no altas o bajas", "Count difference, not additions or closures")}</span>} />
      <KpiCard {...methodology(2)} label={text("Promedio diario por pozo", "Daily average per well")} value={number(k.average, 2)} unit={k.average == null ? undefined : translatedUnit} context={text("Volumen / días calendario / pozos", "Volume / calendar days / wells")} comparisons={<span className="activity-neutral">{changeLabel} · {k.averagePct == null ? text("Sin comparador", "No comparison") : percent(k.averagePct, true)}</span>} />
    </div>
    <div className="activity-range-bar"><span>{text("Ventana histórica", "History window")}</span><div className="ranges" role="group" aria-label={text("Período de actividad", "Activity history range")}>{historyRanges.map(n => <button key={n} aria-pressed={range === n} onClick={() => setRange(n)}>{n === 0 ? text("Histórico", "All history") : `${n}m`}</button>)}</div></div>
    <Evolution kind="wells" detailView rows={rows} fluid={fluid} period={period} range={range} setRange={setRange} prices={prices} mode="volume" comparison={comparison} onDetail={() => {}} />
    <div className="activity-chart-grid">
      <ChartCard title={text("Dinámica de pozos productivos", "Productive well dynamics")} subtitle={`${changeLabel} · ${text("cambio neto de conteo", "net count change")}`}>
        <div className="activity-plot" aria-hidden="true"><ResponsiveContainer width="100%" height="100%"><ComposedChart data={points} margin={{top: 20, right: 12, left: 0, bottom: 12}} accessibilityLayer={false}><XAxis dataKey="periodo" tickFormatter={historyMonth} ticks={historyTicks(points.map(p => p.periodo), coverage.requested)} tick={{fontSize: 10, fill: "var(--muted)"}} tickLine={false} axisLine={false} minTickGap={28}/><YAxis width={42} allowDecimals={false} tick={{fontSize: 10, fill: "var(--muted)"}} tickLine={false} axisLine={false} domain={([min,max]: readonly [number, number]) => [Math.min(0,min), Math.max(0,max)]}/><ReferenceLine y={0} stroke="var(--muted)"/><Tooltip content={tooltip("delta")} isAnimationActive={false}/><Bar dataKey={comparison} isAnimationActive={false}>{points.map(p => <Cell key={p.periodo} fill={p[comparison] == null || p[comparison] === 0 ? "var(--muted)" : p[comparison]! < 0 ? "var(--negative)" : "var(--positive)"}/>)}</Bar></ComposedChart></ResponsiveContainer></div>
        <p className="chart-context">{text("Un cambio neto puede combinar entradas, salidas o reactivaciones. Los agregados disponibles no permiten separarlas.", "Net change may combine entries, exits or reactivations. Available aggregates cannot separate these events.")}</p>
      </ChartCard>
      <ChartCard title={text("Producción media por pozo", "Average production per well")} subtitle={`${text("Promedio diario calendario", "Calendar daily average")} · ${translatedUnit}`}>
        <div className="activity-plot" aria-hidden="true"><ResponsiveContainer width="100%" height="100%"><ComposedChart data={points} margin={{top: 20, right: 12, left: 0, bottom: 12}} accessibilityLayer={false}><XAxis dataKey="periodo" tickFormatter={historyMonth} ticks={historyTicks(points.map(p => p.periodo), coverage.requested)} tick={{fontSize: 10, fill: "var(--muted)"}} tickLine={false} axisLine={false} minTickGap={28}/><YAxis hide domain={[0,"auto"]}/><Tooltip content={tooltip("average")} isAnimationActive={false}/><Line dataKey="average" stroke="var(--accent)" strokeWidth={2.5} dot={points.length === 1} connectNulls={false} isAnimationActive={false}/></ComposedChart></ResponsiveContainer></div>
        <p className="chart-context">{text("El promedio cambia con la composición del conjunto. No mide tiempo efectivo de operación, eficiencia ni rendimiento de pozos comparables.", "The average changes with population composition. It does not measure effective operating time, efficiency or performance of comparable wells.")}</p>
      </ChartCard>
    </div>
    <ChartCard title={text("Datos de actividad", "Activity data")} subtitle={`${coverage.available} ${text("meses disponibles", "available months")} · ${coverage.start ? historyMonth(coverage.start) : "—"} – ${historyMonth(period)}`} className="activity-data" action={<button className="activity-download" onClick={download}>{text("Descargar CSV", "Download CSV")}</button>}>
      <div className="activity-table-scroll" tabIndex={0} role="region" aria-label={text("Tabla de actividad mensual", "Monthly activity table")}><table><caption className="sr-only">{text("Actividad mensual de Vaca Muerta", "Monthly Vaca Muerta activity")}</caption><thead><tr><th scope="col">{text("Mes", "Month")}</th><th scope="col">{text("Pozos productivos", "Productive wells")}</th><th scope="col">{text("Promedio diario", "Daily average")} ({translatedUnit})</th><th scope="col">Δ MoM</th><th scope="col">{text("Base MoM", "MoM base")}</th><th scope="col">Δ YoY</th><th scope="col">{text("Base YoY", "YoY base")}</th></tr></thead><tbody>{[...points].reverse().map(p => <tr key={p.periodo}><th scope="row"><time dateTime={p.periodo}>{historyMonth(p.periodo)}</time></th><td>{number(p.wells,0)}</td><td>{number(p.average,2)}</td><td className={comparison === "mom" ? "activity-selected-column" : ""}>{signed(p.mom)}</td><td>{historyMonth(p.momBase)}</td><td className={comparison === "yoy" ? "activity-selected-column" : ""}>{signed(p.yoy)}</td><td>{historyMonth(p.yoyBase)}</td></tr>)}</tbody></table></div>
      <p className="chart-context">{text("Fuente: Secretaría de Energía · Capítulo IV. Sin registro o sin base exacta: no disponible. No hay datos validados de perforación o completaciones en esta vista.", "Source: Secretaría de Energía · Chapter IV. Missing observation or exact base: unavailable. Validated drilling or completion data are not available in this view.")}</p>
    </ChartCard>
  </div>;
}
