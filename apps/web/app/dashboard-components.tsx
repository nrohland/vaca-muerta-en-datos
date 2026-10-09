"use client";
import { useId, useState, type ReactNode } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  availableRanges,
  month,
  number,
  prepareEntities,
  trend,
  type Entity,
  type Fluid,
  type Row,
} from "../lib/contract";
import { operatorName } from "../lib/operators";
import type { Tab } from "../lib/navigation";
const rateUnit = (f: Fluid) => (f === "oil" ? "bbl/d" : "MMm³/d");
const volumeUnit = (f: Fluid) => (f === "oil" ? "bbl" : "MMm³");
export function periodTitle(p: string) {
  const label = month(p);
  return label.charAt(0).toLocaleUpperCase("es-AR") + label.slice(1);
}
function comparisonMonth(p: string, offset: number) {
  const d = new Date(`${p}T00:00:00Z`);
  d.setUTCMonth(d.getUTCMonth() + offset);
  return month(d.toISOString().slice(0, 10));
}
export function Change({
  value,
  compact = false,
}: {
  value: number | null | undefined;
  compact?: boolean;
}) {
  if (value == null && compact)
    return (
      <span className="change neutral" title="Sin comparador">
        <span aria-hidden="true">—</span>
        <span className="sr-only">Sin comparador</span>
      </span>
    );
  return (
    <span
      className={`change ${value == null || value === 0 ? "neutral" : value > 0 ? "positive" : "negative"}`}
    >
      {value == null
        ? "Sin comparador"
        : `${value > 0 ? "+" : value < 0 ? "−" : ""}${number(Math.abs(value))}%`}
    </span>
  );
}

// One KPI anatomy; visual prominence is a variant, not a separate component.
export function KpiCard({
  label,
  value,
  unit,
  context,
  variant = "secondary",
  state = "neutral",
  tooltip,
  onDetail,
  comparisons,
}: {
  label: string;
  value: ReactNode;
  comparisons?: ReactNode;
  unit?: string;
  context: string;
  variant?: "primary" | "secondary";
  state?: "neutral" | "favorable" | "unfavorable";
  tooltip?: string;
  onDetail?: () => void;
}) {
  return (
    <article
      className={`kpi-card kpi-card--${variant}`}
      data-state={state}
      title={tooltip}
    >
      <span className="metric-label">{label}</span>
      <div className="kpi-value">
        {value}
        {unit && <span>{unit}</span>}
      </div>
      {comparisons && <div className="kpi-comparisons">{comparisons}</div>}
      <div className="kpi-context">
        <span>{context}</span>
        {onDetail && (
          <button
            className="icon-action"
            onClick={onDetail}
            aria-label={`Ver detalle de ${label.toLocaleLowerCase("es-AR")}`}
          >
            ↗
          </button>
        )}
      </div>
    </article>
  );
}
function ModuleCard({
  title,
  subtitle,
  controls,
  action,
  children,
  className = "",
}: {
  title: string;
  subtitle: string;
  controls?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  const id = useId();
  return (
    <section className={`module-card ${className}`} aria-labelledby={id}>
      <header className="module-heading">
        <div>
          <h2 id={id}>{title}</h2>
          <p>{subtitle}</p>
        </div>
        <div className="module-controls">
          {controls}
          {action}
        </div>
      </header>
      {children}
    </section>
  );
}
export function ChartCard(props: Parameters<typeof ModuleCard>[0]) {
  return <ModuleCard {...props} />;
}
export function GlobalFilters({
  fluid,
  period,
  periods,
  preliminary,
  onFluid,
  onPeriod,
}: {
  fluid: Fluid;
  period: string;
  periods: string[];
  preliminary: boolean;
  onFluid: (f: Fluid) => void;
  onPeriod: (p: string) => void;
}) {
  return (
    <div className="global-filters">
      <fieldset className="fluid-control">
        <legend className="sr-only">Fluido</legend>
        {(["oil", "gas"] as Fluid[]).map((f) => (
          <button key={f} aria-pressed={fluid === f} onClick={() => onFluid(f)}>
            {f === "oil" ? "Petróleo" : "Gas"}
          </button>
        ))}
      </fieldset>
      <label className="period-selector">
        <span>Período</span>
        <select
          aria-label="Mes de producción"
          value={period}
          disabled={!periods.length}
          onChange={(e) => onPeriod(e.target.value)}
        >
          {periods
            .slice()
            .reverse()
            .map((p) => (
              <option key={p} value={p}>
                {periodTitle(p)}
              </option>
            ))}
        </select>
      </label>
      <div className="release-status">
        <span>Datos oficiales · mensuales</span>
        {preliminary && (
          <span
            className="status-badge"
            title="Agregados pendientes de revisión final"
          >
            Preliminar
          </span>
        )}
      </div>
    </div>
  );
}
function TrendTooltip({
  active,
  payload,
  label,
  fluid,
}: {
  active?: boolean;
  payload?: readonly { value?: number | string | (number | string)[] }[];
  label?: string | number;
  fluid: Fluid;
}) {
  const value = payload?.[0]?.value;
  if (!active || value == null || label == null) return null;
  return (
    <div className="chart-tooltip">
      <span>{periodTitle(String(label))}</span>
      <strong>
        {number(Number(value), fluid === "oil" ? 0 : 2)} {rateUnit(fluid)}
      </strong>
    </div>
  );
}
export function Evolution({
  rows,
  fluid,
  period,
  range,
  setRange,
  onDetail,
}: {
  rows: Row[];
  fluid: Fluid;
  period: string;
  range: number;
  setRange: (n: number) => void;
  onDetail: () => void;
}) {
  const ranges = availableRanges(rows, fluid, period),
    selected = ranges.includes(range) ? range : (ranges[0] ?? 12),
    series = trend(rows, fluid, period, selected);
  return (
    <ChartCard
      title="Evolución de la producción"
      subtitle={`Tasa diaria equivalente · ${rateUnit(fluid)}`}
      className="evolution"
      controls={
        <div className="ranges" aria-label="Período de evolución">
          {ranges.map((n) => (
            <button
              key={n}
              aria-pressed={selected === n}
              onClick={() => setRange(n)}
            >
              {n}m
            </button>
          ))}
        </div>
      }
      action={
        <button className="text-action" onClick={onDetail}>
          Ver producción <span aria-hidden="true">↗</span>
        </button>
      }
    >
      <div className="line-chart" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={series}
            margin={{ left: 0, right: 20, top: 8, bottom: 0 }}
          >
            <CartesianGrid vertical={false} stroke="var(--chart-grid)" />
            <XAxis
              dataKey="periodo"
              tickFormatter={(v) =>
                new Intl.DateTimeFormat("es-AR", {
                  month: "short",
                  year: "2-digit",
                  timeZone: "UTC",
                }).format(new Date(`${v}T00:00:00Z`))
              }
              minTickGap={60}
              tick={{ fill: "var(--muted)", fontSize: 11 }}
              tickMargin={12}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              width={65}
              domain={["auto", "auto"]}
              tickCount={3}
              tickFormatter={(v) => number(v, fluid === "oil" ? 0 : 1)}
              tick={{ fill: "var(--muted)", fontSize: 11 }}
              tickMargin={8}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              content={<TrendTooltip fluid={fluid} />}
              cursor={{ stroke: "var(--rule)" }}
            />
            <Line
              type="linear"
              dataKey="rate"
              stroke="var(--accent)"
              strokeWidth={2.5}
              dot={series.length === 1 ? { r: 4 } : false}
              activeDot={{ r: 4 }}
              connectNulls={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <details className="data-disclosure">
        <summary>Ver tabla de datos</summary>
        <table>
          <caption>
            Tasa mensual. Los meses ausentes no equivalen a cero.
          </caption>
          <thead>
            <tr>
              <th>Mes</th>
              <th>Tasa ({rateUnit(fluid)})</th>
            </tr>
          </thead>
          <tbody>
            {series.map((r) => (
              <tr key={r.periodo}>
                <th>{r.label}</th>
                <td>
                  {r.rate == null
                    ? "No disponible"
                    : number(r.rate, fluid === "oil" ? 0 : 2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </ChartCard>
  );
}

const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "/vaca-muerta-pulse";
const assets: Record<string, string> = {
  YPF: "YPF.svg",
  PLUSPETROL: "PLUSPETROL.svg",
  PAL: "PAL.png",
  PAM: "PAM.svg",
  TAU: "TAU.svg",
  TPT: "TPT.jpg",
  SHE: "SHE.jpg",
  PGR: "PGR.png",
  VST: "VST.svg",
};
const shortNames: Record<string, string> = {
  YPF: "YPF",
  PLUSPETROL: "Pluspetrol",
  PAL: "Pan American Energy",
  PAM: "Pampa Energía",
  TAU: "Total Austral",
  TPT: "Tecpetrol",
  SHE: "Shell",
  PGR: "Phoenix",
  VST: "Vista",
};
function OperatorLogo({ id }: { id: string }) {
  const [failed, setFailed] = useState(false);
  return (
    <span
      className={`operator-logo ${["PLUSPETROL", "PAM", "VST", "PAL", "PGR"].includes(id) ? "operator-logo--reverse" : ""}`}
      aria-hidden="true"
    >
      {assets[id] && !failed ? (
        <img
          src={`${base}/operators/${assets[id]}`}
          alt=""
          onError={() => setFailed(true)}
        />
      ) : (
        id.slice(0, 2)
      )}
    </span>
  );
}

export function RankingCard({
  entities,
  current,
  fluid,
  dimension,
  onNavigate,
}: {
  entities: Entity[];
  current: Row;
  fluid: Fluid;
  dimension: "company" | "area";
  onNavigate: (tab: Tab, id?: string) => void;
}) {
  const operators = dimension === "company",
    tab = operators ? "operators" : "areas",
    shown = prepareEntities(entities, fluid, dimension, current.periodo).top;
  return (
    <ModuleCard
      title={operators ? "Principales operadores" : "Principales áreas"}
      subtitle={`Top 5 · volumen mensual · ${volumeUnit(fluid)}`}
      className={`ranking-card ${operators ? "ranking-operators" : "ranking-areas"}`}
      action={
        <button className="text-action" onClick={() => onNavigate(tab)}>
          Ver {operators ? "operadores" : "áreas"} ↗
        </button>
      }
    >
      <div className="ranking-columns" aria-hidden="true">
        <span>{operators ? "Operador" : "Área"}</span>
        <span>Producción</span>
        {operators && <span>Cuota</span>}
        <span>YoY</span>
      </div>
      <ol className="ranking-list">
        {shown.map((e) => {
          // Display composition on a true 0–100% total-volume scale. No growth calculations in UI.
          const share =
            current.volume > 0 ? (e.volume / current.volume) * 100 : null;
          const label = operators
            ? operatorName(e.entity_id, e.entity_name)
            : e.entity_name;
          return (
            <li key={e.entity_id}>
              <button
                className="ranking-row"
                onClick={() => onNavigate(tab, e.entity_id)}
              >
                <span className="entity-name">
                  <span className="rank" aria-hidden="true">
                    {e.volume_rank.toString().padStart(2, "0")}
                  </span>
                  {operators && <OperatorLogo id={e.entity_id} />}
                  <span title={label}>
                    {operators ? (shortNames[e.entity_id] ?? label) : label}
                  </span>
                </span>
                <span className="bar-value">
                  <span className="mobile-label">Producción</span>
                  {number(e.volume, fluid === "oil" ? 0 : 2)}
                </span>
                {operators && (
                  <span className="share-value">
                    <span className="mobile-label">Cuota</span>
                    {share == null ? "No disponible" : `${number(share)}%`}
                  </span>
                )}
                <span className="yoy-value">
                  <span className="mobile-label">YoY</span>
                  <Change value={e.yoy_volume_pct} compact />
                </span>
                <span className="bar-track" aria-hidden="true">
                  <span style={{ width: `${share ?? 0}%` }} />
                </span>
              </button>
            </li>
          );
        })}
      </ol>
      {!shown.length && (
        <p className="empty">
          Sin {operators ? "operadores" : "áreas"} para este período.
        </p>
      )}
      <p className="ranking-scale">
        Barras: participación en el volumen total · escala 0–100%
      </p>
    </ModuleCard>
  );
}
export function SummaryDashboard({
  current,
  rows,
  entities,
  fluid,
  period,
  range,
  setRange,
  onNavigate,
}: {
  current: Row;
  rows: Row[];
  entities: Entity[];
  fluid: Fluid;
  period: string;
  range: number;
  setRange: (n: number) => void;
  onNavigate: (tab: Tab, id?: string) => void;
}) {
  return (
    <>
      <div className="summary-heading">
        <div>
          <p className="eyebrow">Vaca Muerta · No convencional</p>
          <h1>Resumen de producción</h1>
        </div>
        <p>Qué se produce, cómo evoluciona y quiénes lideran.</p>
      </div>
      <div className="kpi-grid">
        <KpiCard
          variant="primary"
          label={
            fluid === "oil"
              ? "Barriles extraídos por día"
              : "Gas producido por día"
          }
          value={number(current.rate, fluid === "oil" ? 0 : 2)}
          unit={rateUnit(fluid)}
          context="Tasa diaria equivalente del mes"
          comparisons={
            <>
              <span title={`vs. ${comparisonMonth(period, -12)}`}>
                <span className="comparison-label">YoY</span>{" "}
                <Change value={current.yoy_rate_pct} />
              </span>
              <span title={`vs. ${comparisonMonth(period, -1)}`}>
                <span className="comparison-label">MoM</span>{" "}
                <Change value={current.mom_rate_pct} />
              </span>
            </>
          }
          onDetail={() => onNavigate("production")}
        />
        <KpiCard
          label="Pozos productivos"
          value={number(current.positive_producing_wells, 0)}
          context="Con producción positiva"
          onDetail={() => onNavigate("activity")}
        />
        <KpiCard
          label="Volumen mensual"
          value={number(current.volume, fluid === "oil" ? 0 : 2)}
          unit={volumeUnit(fluid)}
          context={periodTitle(period)}
          onDetail={() => onNavigate("production")}
        />
        <KpiCard
          label="Cuota del Top 5"
          value={
            current.top5_company_share_pct == null
              ? "No disponible"
              : `${number(current.top5_company_share_pct)}%`
          }
          context="Participación de operadores"
          onDetail={() => onNavigate("operators")}
        />
      </div>
      <Evolution
        rows={rows}
        fluid={fluid}
        period={period}
        range={range}
        setRange={setRange}
        onDetail={() => onNavigate("production")}
      />
      <div className="ranking-grid">
        <RankingCard
          entities={entities}
          current={current}
          fluid={fluid}
          dimension="company"
          onNavigate={onNavigate}
        />
        <RankingCard
          entities={entities}
          current={current}
          fluid={fluid}
          dimension="area"
          onNavigate={onNavigate}
        />
      </div>
      <p className="scope-note">
        Operador declarado cada mes; las transferencias de activos pueden
        modificar el ranking. Área: permiso o concesión. YoY de los rankings
        compara volumen mensual.
      </p>
    </>
  );
}
