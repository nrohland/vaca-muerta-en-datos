"use client";
import {useState,useEffect,useRef,type CSSProperties} from 'react';
import type {Row,Fluid} from '../lib/contract';
import {metric,nonnegativeDomain,comparisonOffset,shiftMonth,type Mode,type Prices,type Comparison} from '../lib/metrics';
import {historyRanges,historyWindow,historyTicks,defaultHistoryRange} from '../lib/history';
import {useLocale} from '../lib/locale';
import {chartVisibility} from '../lib/chart-visibility';
import {ChartCard,Change} from './dashboard-components';
import {
  Line,
  ComposedChart,
  Bar,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ReferenceDot,
} from "recharts";
const volumeUnit=(f:Fluid)=>f==='oil'?'bbl':'MMm³';
function TrendTooltip({
  active,
  label,
  fluid,
  prices,
  rows,
}: {
  active?: boolean;
  label?: string | number;
  fluid: Fluid;
  prices: Prices | null;
  rows: Row[];
}) {
  const { t, physical, currency, monthYear } = useLocale();
  const row = rows.find(
    (r) => r.fluid === fluid && r.periodo === String(label ?? ""),
  );
  if (!active || !row) return null;
  const volume = metric(row, rows, prices, "volume", "volume");
  const value = metric(row, rows, prices, "volume", "value");
  return (
    <div className="chart-tooltip compact-chart-tooltip">
      <div className="tooltip-month">{monthYear(row.periodo)}</div>
      <div className="tooltip-row">
        <span>{t("Producción")}</span>
        <strong>{physical(volume.value, fluid)}</strong>
      </div>
      {(
        <div className="tooltip-row">
          <span>{t("Valor estimado")}</span>
          <strong>{currency(value.value)}</strong>
        </div>
      )}
    </div>
  );
}
function WellsTooltip({active, payload}: {active?: boolean; payload?: readonly {payload?: {periodo: string; physical: number | null}}[]}) {
  const {t, number, monthYear} = useLocale();
  const point = payload?.[0]?.payload;
  if (!active || !point) return null;
  return <div className="chart-tooltip compact-chart-tooltip"><strong>{monthYear(point.periodo)}</strong><div className="tooltip-row"><span>{t("Pozos productivos")}</span><strong>{number(point.physical, 0)}</strong></div></div>;
}
export function Evolution({
  mode,
  prices,
  rows,
  fluid,
  period,
  range,
  setRange,
  onDetail,
  comparison,
  kind = "production",
  detailView = false,
}: {
  kind?: "production" | "wells";
  detailView?: boolean;
  rows: Row[];
  mode: Mode;
  prices: Prices | null;
  fluid: Fluid;
  period: string;
  range: number;
  setRange: (n: number) => void;
  onDetail: () => void;
  comparison: Comparison;
}) {
  const { t, number, physical, currency, month, historyMonth } = useLocale();
  const wells = kind === "wells";
  const [seriesView, setSeriesView] = useState<"physical" | "value">(mode === "value" ? "value" : "physical");
  useEffect(() => { setSeriesView(mode === "value" ? "value" : "physical"); }, [mode]);
  const selected = historyRanges.some((n) => n === range)
    ? range
    : defaultHistoryRange;
  const coverage = historyWindow(rows, fluid, period, selected);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [scrollable, setScrollable] = useState(false);
  const [scrollOffset, setScrollOffset] = useState(0);
  const [touchTooltip, setTouchTooltip] = useState(false);
  useEffect(() => {
    const media = window.matchMedia("(pointer: coarse)");
    const update = () => setTouchTooltip(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const compactViewport = window.matchMedia("(max-width: 1100px)");
    let previousMax = Math.max(0, el.scrollWidth-el.clientWidth);
    const measure = () => {
      const atEnd = el.scrollLeft >= previousMax-2;
      setScrollable(compactViewport.matches && el.scrollWidth > el.clientWidth+1);
      if (atEnd) el.scrollLeft = el.scrollWidth;
      previousMax = Math.max(0, el.scrollWidth-el.clientWidth);
      setScrollOffset(el.scrollLeft);
    };
    compactViewport.addEventListener("change", measure);
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    if (el.firstElementChild) observer.observe(el.firstElementChild);
    measure();
    el.scrollLeft = el.scrollWidth;
    setScrollOffset(el.scrollLeft);
    return () => { observer.disconnect(); compactViewport.removeEventListener("change", measure); };
  }, [selected, fluid, period]);
  const series = coverage.points.map((point) => {
    const row = rows.find(
      (r) => r.fluid === fluid && r.periodo === point.periodo,
    );
    const volume = row ? metric(row, rows, prices, wells ? "wells" : "volume", "volume") : null;
    const value = row ? metric(row, rows, prices, "volume", "value") : null;
    return {
      ...point,
      physical: volume?.value ?? null,
      estimated: value?.value ?? null,
      physicalDelta: volume?.[comparison] ?? null,
      valueDelta: value?.[comparison] ?? null,
      base: shiftMonth(point.periodo, comparisonOffset(comparison)),
    };
  });
  const { showPhysical, monetary, unavailable, activeSeries } = chartVisibility({wells, fluid, mode, detailView, selected:seriesView, hasEstimated:series.some(p => p.estimated != null)});
  const last = series.at(-1);
  const lastValue = monetary ? last?.estimated : last?.physical;
  return (
    <ChartCard
      title={t(
        wells ? "Evolución de pozos productivos" : monetary
          ? "Valor estimado"
          : "Evolución de la producción",
      )}
      className={wells ? "evolution wells-evolution" : "evolution production-evolution"}
      controls={!wells && <>
        {detailView && prices && <div className="ranges series-control" role="group" aria-label={t("Series del gráfico")}>{(["physical","value"] as const).map(v => <button key={v} aria-pressed={activeSeries === v} disabled={v !== "physical" && unavailable} onClick={() => setSeriesView(v)}>{t(v === "physical" ? "Producción física" : "Valor estimado")}</button>)}</div>}
        <div className="ranges" role={detailView ? "group" : undefined} aria-label={t("Período de evolución")}>
          {historyRanges.map((n) => (
            <button
              key={n}
              aria-pressed={selected === n}
              onClick={() => setRange(n)}
            >
              {n === 0 ? t("Histórico") : `${n}m`}
            </button>
          ))}
        </div></>
      }
      action={!detailView &&
        <button className="text-action" onClick={onDetail}>
          {t(wells ? "Actividad · Ver detalle" : "Producción · Ver detalle")} <span aria-hidden="true">↗</span>
        </button>
      }
    >
      <div className="chart-legend">
        {showPhysical && <span>
          <i className="legend-bar" aria-hidden="true" />
          {wells ? t("Pozos productivos") : `${t("Producción física")} · ${volumeUnit(fluid)}`}
        </span>}
        {monetary && (
          <span>
            <i className="legend-line" aria-hidden="true" />
            {t("Valor estimado")} · USD
          </span>
        )}
      </div>
      {(selected === 0 || coverage.partial) && (
        <p className="history-coverage" role="status">
          {t(
            "Histórico disponible: {start} – {end}",
            {
              count: coverage.available,
              requested: selected,
              start: coverage.start ? historyMonth(coverage.start) : "—",
              end: coverage.end ? historyMonth(coverage.end) : "—",
            },
          )}
        </p>
      )}
      <div
        className="chart-scroll"
        ref={scrollRef}
        onScroll={(e) => setScrollOffset(e.currentTarget.scrollLeft)}
        tabIndex={0}
        role="region"
        aria-label={t(wells ? "Gráfico desplazable de pozos productivos" : "Gráfico desplazable de producción y valor")}
      >
        <div
          className="line-chart"
          style={
            {
              "--history-width": `${series.length * 28 + 64}px`,
            } as CSSProperties
          }
          aria-hidden="true"
          data-physical-min="0"
          data-value-min="0"
        >
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              accessibilityLayer={false}
              data={series}
              margin={{ left: 12, right: 24, top: 30, bottom: 8 }}
              barCategoryGap={coverage.requested >= 36 ? "15%" : "22%"}
            >
              <XAxis
                dataKey="periodo"
                tickFormatter={(v) => month(v, true)}
                padding={{ left: 12, right: 16 }}
                ticks={historyTicks(
                  series.map((p) => p.periodo),
                  coverage.requested,
                )}
                minTickGap={30}
                tick={{ fill: "var(--muted)", fontSize: 11 }}
                tickMargin={10}
                axisLine={false}
                tickLine={false}
              />
              <YAxis yAxisId="physical" hide={!showPhysical} domain={nonnegativeDomain} width={72} axisLine={false} tickLine={false} tick={{ fill: "var(--muted)", fontSize: 12 }} tickFormatter={v => number(Number(v), 0)} />
              <YAxis yAxisId="value" hide={!monetary} domain={nonnegativeDomain} width={72} axisLine={false} tickLine={false} tick={{ fill: "var(--muted)", fontSize: 12 }} tickFormatter={v => currency(Number(v))} />
              <Tooltip
                isAnimationActive={false}
                trigger={touchTooltip ? "click" : "hover"}
                position={
                  scrollable ? { x: scrollOffset + 12, y: 8 } : undefined
                }
                content={
                  wells ? <WellsTooltip /> : <TrendTooltip fluid={fluid} prices={prices} rows={rows} />
                }
                cursor={{ fill: "var(--chart-grid)" }}
              />
              {wells ? <Line yAxisId="physical" dataKey="physical" type="linear" stroke="var(--accent)" strokeWidth={2.5} dot={series.length === 1 ? {r: 4} : false} activeDot={{r: 4}} connectNulls={false} isAnimationActive={false} /> : showPhysical && <Bar
                yAxisId="physical"
                dataKey="physical"
                fill="var(--accent)"
                fillOpacity={mode === "value" ? 0.65 : 0.9}
                radius={[3, 3, 0, 0]}
                isAnimationActive={false}
              />}
              {monetary && (
                <Line
                  yAxisId="value"
                  type="linear"
                  dataKey="estimated"
                  stroke="var(--value-line)"
                  strokeWidth={mode === "value" ? 3 : 2.5}
                  dot={series.length === 1 ? { r: 4 } : false}
                  activeDot={{ r: 4 }}
                  connectNulls={false}
                  isAnimationActive={false}
                />
              )}
              {last && lastValue != null && (
                <ReferenceDot
                  yAxisId={monetary ? "value" : "physical"}
                  x={last.periodo}
                  y={lastValue}
                  r={4}
                  fill={monetary ? "var(--value-line)" : "var(--accent)"}
                  stroke="var(--surface)"
                  label={({ viewBox }: any) => (
                    <text
                      className="chart-end-label"
                      x={viewBox.x - 10}
                      y={viewBox.y - 13}
                      textAnchor="end"
                      fill="var(--ink)"
                      fontSize={11}
                    >
                      {wells ? number(lastValue, 0) : monetary
                        ? currency(lastValue)
                        : physical(lastValue, fluid)}
                    </text>
                  )}
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
      {scrollable && (
        <p className="chart-scroll-hint">
          {t("Deslizá para explorar los meses →")}
        </p>
      )}
      {unavailable && <p className="chart-context">{t(fluid === "gas" ? "Gas: valor estimado no disponible." : "Referencia de precios no disponible.")}</p>}
      {!detailView && <details className="data-disclosure">
        <summary>{t("Ver tabla de datos")}</summary>
        <table>
          <caption>
            {t(
              "Valores mensuales. Los meses o precios ausentes no equivalen a cero.",
            )}
          </caption>
          <thead>
            <tr>
              <th>{t("Mes")}</th>
              <th>
                {wells ? t("Pozos productivos") : t("Volumen mensual ({unit})", {
                  unit: fluid === "oil" ? "bbl" : "m³",
                })}
              </th>
              <th>{t(comparison === "mom" ? "Mensual" : "Interanual")}</th>
              {monetary && (
                <>
                  <th>{t("Valor mensual (USD estimados)")}</th>
                  <th>{t(comparison === "mom" ? "Mensual" : "Interanual")}</th>
                </>
              )}
              <th>{t("Base de comparación")}</th>
            </tr>
          </thead>
          <tbody>
            {series.map((r) => (
              <tr key={r.periodo}>
                <th>
                  <time
                    dateTime={r.periodo}
                    title={month(r.periodo)}
                    aria-label={month(r.periodo)}
                  >
                    {month(r.periodo, true)}
                  </time>
                </th>
                <td>
                  {number(
                    r.physical == null
                      ? null
                      : r.physical * (!wells && fluid === "gas" ? 1e6 : 1),
                    0,
                  )}
                </td>
                <td>
                  <Change value={r.physicalDelta} />
                </td>
                {monetary && (
                  <>
                    <td>
                      {r.estimated == null
                        ? t("No disponible")
                        : `${number(r.estimated, 2)} USD`}
                    </td>
                    <td>
                      <Change value={r.valueDelta} />
                    </td>
                  </>
                )}
                <td>
                  <time
                    dateTime={r.base}
                    title={month(r.base)}
                    aria-label={month(r.base)}
                  >
                    {month(r.base, true)}
                  </time>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>}
    </ChartCard>
  );
}
