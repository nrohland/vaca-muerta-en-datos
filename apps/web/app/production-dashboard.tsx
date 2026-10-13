"use client";
import { useState } from "react";
import {
  Bar,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Row } from "../lib/contract";
import { historyWindow } from "../lib/history";
import {
  effectiveMode,
  type Comparison,
  type Mode,
  type Prices,
} from "../lib/metrics";
import {
  productionCsv,
  productionKpis,
  productionPoints,
  yearlyComparison,
} from "../lib/production";
import { useLocale } from "../lib/locale";
import { ChartCard, Evolution, KpiCard, ReferenceValuationNote } from "./dashboard-components";

export function ProductionDashboard({
  rows,
  current,
  prices,
  mode,
  comparison,
  range,
  setRange,
}: {
  rows: Row[];
  current: Row;
  prices: Prices | null;
  mode: Mode;
  comparison: Comparison;
  range: number;
  setRange: (n: number) => void;
}) {
  const { t, compact, number, percent, month, historyMonth, locale } =
    useLocale();
  const [flipped, setFlipped] = useState<number | null>(null);
  const fluid = current.fluid,
    period = current.periodo;
  const shownMode = effectiveMode(mode, fluid),
    monetary = shownMode === "value";
  const unit = monetary ? "USD" : fluid === "oil" ? "bbl" : "MMm³";
  const fullUnit = unit;
  const factor = fluid === "gas" && !monetary ? 1e6 : 1;
  const k = productionKpis(rows, fluid, period, prices, mode, comparison);
  const points = productionPoints(rows, fluid, period, range, prices, mode);
  const coverage = historyWindow(rows, fluid, period, range);
  const annual = yearlyComparison(rows, fluid, period, prices, mode);
  const colors = monetary ? ["var(--monetary-oldest)", "var(--monetary-secondary)", "var(--value-line)"] : ["var(--year-oldest)", "var(--product-secondary)", "var(--accent)"];
  const shortMonth = (m: string) =>
    new Intl.DateTimeFormat(locale, { month: "short", timeZone: "UTC" })
      .format(new Date(`2024-${m}-01T00:00:00Z`))
      .replace(/\./g, "");
  const exact = (v: number | null) =>
    number(v == null ? null : v * factor, 2, 0);
  const format = (v: number | null) =>
    v == null
      ? t("No disponible")
      : `${monetary || fluid === "oil" ? compact(v) : number(v, 2, 0)} ${unit}`;
  const signed = (v: number | null) =>
    v == null
      ? t("Sin comparador")
      : `${v > 0 ? "+" : v < 0 ? "−" : ""}${format(Math.abs(v))}`;
  const props = (index: number, help: string) => ({
    flipped: flipped === index,
    onFlip: () => setFlipped(flipped === index ? null : index),
    tooltip: t(help),
    brief: t([monetary ? "Producción valorizada a precio de referencia." : "Producción acumulada durante el mes.", "Diferencia frente al mes base.", "Acumulado enero–mes vs. año anterior.", "Mayor mes dentro del histórico disponible."][index]),
  });
  function download() {
    const url = URL.createObjectURL(
      new Blob(["\uFEFF", productionCsv(points, fluid, mode)], {
        type: "text/csv;charset=utf-8",
      }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = `vaca-muerta-${fluid}-${period.slice(0, 7)}-${shownMode}.csv`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const yearTooltip = ({ active, label, payload }: any) =>
    !active ? null : (
      <div className="chart-tooltip compact-chart-tooltip">
        <strong>{shortMonth(String(label))}</strong>
        {payload?.map((p: any) => (
          <div className="tooltip-row" key={p.dataKey}>
            <span>{p.dataKey}</span>
            <strong>{format(p.value)}</strong>
          </div>
        ))}
      </div>
    );
  const deltaTooltip = ({ active, payload }: any) => {
    const p = payload?.[0]?.payload;
    return !active || !p ? null : (
      <div className="chart-tooltip compact-chart-tooltip">
        <strong>{month(p.periodo)}</strong>
        <div className="tooltip-row">
          <span>{t("Cambio absoluto")}</span>
          <strong>{signed(p[comparison])}</strong>
        </div>
        <span>
          {t("vs. {period}", {
            period: month(p[comparison === "mom" ? "momBase" : "yoyBase"]),
          })}
        </span>
      </div>
    );
  };
  return (
    <div className="production-dashboard">
      <header className="production-heading">
        <div>
          <p className="eyebrow">{t("Explorar la producción")}</p>
          <h1>{t("Producción")}</h1>
          <p>
            {t("Evolución, comparaciones y datos mensuales de Vaca Muerta.")}
          </p>
        </div>
        <span className="production-period">{month(period)}</span>
      </header>
      <ReferenceValuationNote fluid={fluid} prices={prices} />
      {monetary && k.value == null && (
        <p className="availability-note" role="status">
          {t(
            "Precio de referencia no disponible para este período; el valor estimado permanece sin calcular.",
          )}
        </p>
      )}
      <div className="kpi-grid">
        <KpiCard
          {...props(
            0,
            monetary
              ? "Volumen mensual × precio del período. Estimación, no facturación efectiva."
              : "Suma de la producción registrada durante el mes.",
          )}
          variant="primary"
          label={t(monetary ? "Valor mensual estimado" : "Producción mensual")}
          value={
            k.value == null
              ? t("No disponible")
              : monetary || fluid === "oil"
                ? compact(k.value)
                : number(k.value, 2, 0)
          }
          unit={k.value == null ? undefined : unit}
          context={month(period)}
          comparisons={
            <span className="production-neutral">
              {t(comparison === "mom" ? "Mensual" : "Interanual")} ·{" "}
              {k.pct == null ? t("Sin comparador") : percent(k.pct, true)}
            </span>
          }
        />
        <KpiCard
          {...props(
            1,
            "Valor del mes menos el valor de su base calendario exacta.",
          )}
          label={t("Cambio absoluto")}
          value={
            k.delta == null
              ? t("Sin comparador")
              : `${k.delta > 0 ? "+" : k.delta < 0 ? "−" : ""}${compact(Math.abs(k.delta))}`
          }
          unit={k.delta == null ? undefined : unit}
          context={t("vs. {period}", { period: historyMonth(k.basePeriod) })}
          comparisons={
            <span className="production-neutral">
              {comparison === "mom" ? "MoM" : "YoY"}
            </span>
          }
        />
        <KpiCard
          {...props(
            2,
            "Suma enero–mes frente al mismo período del año anterior; requiere todos los meses y precios necesarios.",
          )}
          label={t(monetary ? "Valor acumulado del año" : "Producción acumulada del año")}
          value={k.accumulated == null ? t("No disponible") : monetary || fluid === "oil" ? compact(k.accumulated) : number(k.accumulated, 2, 0)}
          unit={k.accumulated == null ? undefined : unit}
          context={`${historyMonth(k.start)} – ${historyMonth(period)}`}
          comparisons={<span className="production-neutral">{k.accumulatedGrowth == null ? t("Sin comparador") : percent(k.accumulatedGrowth, true)} · {t("vs. mismo acumulado de {year}", {year: Number(period.slice(0,4))-1})}</span>}
        />
      </div>
      <Evolution
        rows={rows}
        fluid={fluid}
        period={period}
        range={range}
        setRange={setRange}
        mode={shownMode}
        prices={prices}
        comparison={comparison}
        detailView
        onDetail={() => {}}
      />
      <div className="production-chart-grid">
        <ChartCard
          title={t("Comparación entre años")}
          subtitle={t("Totales por mes · {unit}", { unit })}
          className="production-annual"
        >
          <div className="chart-legend">
            {annual.years.map((year, i) => (
              <span key={year}>
                <i
                  className="production-year-key"
                  style={{ background: colors[i] }}
                  aria-hidden="true"
                />
                {year}
              </span>
            ))}
          </div>
          <div
            className="production-plot-scroll"
            tabIndex={0}
            role="region"
            aria-label={t("Gráfico de comparación entre años")}
          >
            <div className="production-small-plot" aria-hidden="true">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  data={annual.points}
                  margin={{ top: 18, right: 16, bottom: 8, left: 0 }}
                  accessibilityLayer={false}
                >
                  <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
                  <XAxis
                    dataKey="month"
                    padding={{ left: 12, right: 12 }}
                    tickFormatter={shortMonth}
                    interval={0}
                    tick={{ fontSize: 10, fill: "var(--muted)" }}
                    tickLine={false}
                    axisLine={false}
                    tickMargin={10}
                  />
                  <YAxis hide domain={[0, "auto"]} />
                  <Tooltip content={yearTooltip} isAnimationActive={false} />
                  {annual.years.map((year, i) => (
                    <Line
                      key={year}
                      dataKey={year}
                      name={year}
                      type="linear"
                      stroke={colors[i]}
                      strokeWidth={i === annual.years.length - 1 ? 2.8 : 1.8}
                      dot={{ r: 2.5 }}
                      activeDot={{ r: 4 }}
                      connectNulls={false}
                      isAnimationActive={false}
                    />
                  ))}
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
          <p className="chart-context">
            {t(
              "Meses sin registro o posteriores al período seleccionado: sin dato.",
            )}
          </p>
          <details className="data-disclosure">
            <summary>{t("Ver comparación en tabla")}</summary>
            <table>
              <caption>
                {t("Comparación entre años")} · {unit}
              </caption>
              <thead>
                <tr>
                  <th scope="col">{t("Mes")}</th>
                  {annual.years.map((y) => (
                    <th scope="col" key={y}>
                      {y}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {annual.points.map((p) => (
                  <tr key={p.month}>
                    <th scope="row">{shortMonth(p.month)}</th>
                    {annual.years.map((y) => (
                      <td key={y}>{number(p[y] as number | null, 2, 0)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </ChartCard>
        <ChartCard
          title={t("Cambio absoluto por mes")}
          subtitle={t("{comparison} · {unit}", {
            comparison: comparison === "mom" ? "MoM" : "YoY",
            unit,
          })}
          className="production-deltas"
        >
          <div
            className="production-plot-scroll"
            tabIndex={0}
            role="region"
            aria-label={t("Gráfico de cambios absolutos")}
          >
            <div className="production-small-plot" aria-hidden="true">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  data={points}
                  margin={{ top: 18, right: 16, bottom: 8, left: 4 }}
                  accessibilityLayer={false}
                >
                  <XAxis
                    dataKey="periodo"
                    tickFormatter={(p) => month(p, true)}
                    minTickGap={38}
                    tick={{ fontSize: 10, fill: "var(--muted)" }}
                    tickLine={false}
                    axisLine={false}
                    tickMargin={10}
                  />
                  <YAxis
                    hide
                    width={0}
                    tickFormatter={(v) => compact(v)}
                    tick={{ fontSize: 10, fill: "var(--muted)" }}
                    tickLine={false}
                    axisLine={false}
                    domain={([min, max]: readonly [number, number]) => [
                      Math.min(0, min),
                      Math.max(0, max),
                    ]}
                  />
                  <ReferenceLine y={0} stroke="var(--muted)" />
                  <Tooltip
                    content={deltaTooltip}
                    isAnimationActive={false}
                    cursor={{ fill: "var(--chart-grid)" }}
                  />
                  <Bar
                    dataKey={comparison}
                    fill="var(--accent)"
                    isAnimationActive={false}
                  >
                    {points.map(p => <Cell key={p.periodo} fill={p[comparison] == null || p[comparison] === 0 ? "var(--muted)" : p[comparison]! > 0 ? "var(--delta-positive)" : "var(--delta-negative)"} />)}
                  </Bar>
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
          <p className="chart-context">
            {t(
              "Diferencia de totales mensuales; no de tasas diarias. Sin base exacta, no se calcula.",
            )}
          </p>
          <a
            className="text-action production-table-link"
            href="#production-data"
          >
            {t("Ver datos y bases de comparación")}
          </a>
        </ChartCard>
      </div>
      <div id="production-data">
        <ChartCard
          title={t("Datos mensuales")}
          subtitle={t(
            "{count} registros de {requested} meses · {start} – {end}",
            {
              count: coverage.available,
              requested: coverage.requested,
              start: coverage.start ? historyMonth(coverage.start) : "—",
              end: historyMonth(period),
            },
          )}
          className="production-data"
          action={
            <button className="production-download" onClick={download}>
              {t("Descargar CSV")}
            </button>
          }
        >
          <p className="chart-context">
            {t(
              "Cambios absolutos en {unit}. Celdas vacías en CSV indican datos no disponibles.",
              { unit: fullUnit },
            )}
          </p>
          <div
            className="production-table-scroll"
            tabIndex={0}
            role="region"
            aria-label={t("Tabla de producción mensual")}
          >
            <table>
              <caption className="sr-only">
                {t("Tabla de producción mensual")} ·{" "}
                {t(fluid === "oil" ? "Petróleo" : "Gas")}
              </caption>
              <thead>
                <tr>
                  <th scope="col">{t("Mes")}</th>
                  <th scope="col">
                    {t("Volumen mensual ({unit})", {
                      unit: fluid === "oil" ? "bbl" : "m³",
                    })}
                  </th>
                  <th scope="col">
                    {t("Tasa ({unit})", {
                      unit: fluid === "oil" ? "bbl/d" : "m³/d",
                    })}
                  </th>
                  {<><th scope="col">{fluid === "oil" ? "Brent USD/bbl" : "Henry Hub USD/MMBtu"}</th><th scope="col">{t("Valor estimado")} USD</th></>}
                  <th scope="col">Δ {comparison === "mom" ? "MoM" : "YoY"} ({fullUnit})</th>
                  <th scope="col">{t("Base de comparación")}</th>
                </tr>
              </thead>
              <tbody>
                {[...points].reverse().map((p) => (
                  <tr key={p.periodo}>
                    <th scope="row">
                      <time dateTime={p.periodo}>
                        {historyMonth(p.periodo)}
                      </time>
                    </th>
                    <td>{p.volume == null ? t("No disponible") : `${fluid === "oil" ? compact(p.volume) : compact(p.volume * 1e6)} ${fluid === "oil" ? "bbl" : "m³"}`}</td>
                    <td>{p.rate == null ? t("No disponible") : `${fluid === "oil" ? number(p.rate, 0) : compact(p.rate * 1e6)} ${fluid === "oil" ? "bbl/d" : "m³/d"}`}</td>
                    {<><td>{p.price == null ? t("No disponible") : `US$ ${number(p.price, 2)}`}</td><td>{p.estimated == null ? t("No disponible") : `US$ ${compact(p.estimated)}`}</td></>}
                    <td className="production-selected-column">{signed(p[comparison])}</td>
                    <td>{historyMonth(p[comparison === "mom" ? "momBase" : "yoyBase"])}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="chart-context">
            {t(
              "Fuente: Secretaría de Energía · Capítulo IV. USD: volumen × precio mensual EIA y conversión energética de referencia para gas; estimación, no facturación.",
            )}
          </p>
        </ChartCard>
      </div>
    </div>
  );
}
