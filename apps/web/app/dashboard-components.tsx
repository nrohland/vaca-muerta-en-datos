"use client";
import dynamic from "next/dynamic";
import {
  useId,
  useState,
  useEffect,
  useRef,
  type CSSProperties,
  type ReactNode,
} from "react";
import {
  prepareEntities,
  type Entity,
  type Fluid,
  type Row,
} from "../lib/contract";
import { kpiParts } from "../lib/presentation";
import { operatorName } from "../lib/operators";
import type { Tab } from "../lib/navigation";
import {
  metric,
  referencePrice,
  entityValue,
  entityComparison,
  comparisonOffset,
  shiftMonth,
  nonnegativeDomain,
  type Comparison,
  effectiveMode,
  type Mode,
  type Prices,
  type Metric,
} from "../lib/metrics";
import { useLocale } from "../lib/locale";
import {
  historyRanges,
  historyWindow,
  historyTicks,
  defaultHistoryRange,
} from "../lib/history";
import { chartVisibility } from "../lib/chart-visibility";
function Comparisons({
  metric: m,
  period,
  comparison,
}: {
  metric: Metric;
  period: string;
  comparison: Comparison;
}) {
  const { t, month } = useLocale();
  const base = month(shiftMonth(period, comparisonOffset(comparison)));
  return (
    <span className="comparison-pair" title={t("vs. {period}", { period: base })}>
      <span className="comparison-label">
        {t(comparison === "mom" ? "Mensual" : "Interanual")}
      </span>
      <Change value={m[comparison]} compact />
      <span className="sr-only"> · {t("vs. {period}", { period: base })}</span>
    </span>
  );
}
const rateUnit = (f: Fluid) => (f === "oil" ? "bbl/d" : "MMm³/d");
const volumeUnit = (f: Fluid) => (f === "oil" ? "bbl" : "MMm³");
export function Change({
  value,
  compact = false,
}: {
  value: number | null | undefined;
  compact?: boolean;
}) {
  const { t, percent } = useLocale();
  if (value == null && compact)
    return (
      <span className="change neutral" title={t("Sin comparador")}>
        <span aria-hidden="true">—</span>
        <span className="sr-only">{t("Sin comparador")}</span>
      </span>
    );
  return (
    <span
      className={`change ${value == null || value === 0 ? "neutral" : value > 0 ? "positive" : "negative"}`}
    >
      {value == null ? t("Sin comparador") : percent(value, true)}
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
  flipped = false,
  onFlip,
  brief,
  methodSource,
}: {
  label: string;
  flipped?: boolean;
  onFlip?: () => void;
  brief?: string;
  methodSource?: string;
  value: ReactNode;
  comparisons?: ReactNode;
  unit?: string;
  context: string;
  variant?: "primary" | "secondary";
  state?: "neutral" | "favorable" | "unfavorable";
  tooltip?: string;
  onDetail?: () => void;
}) {
  const { t, locale } = useLocale();
  const id = useId();
  const amount = typeof value === "string" ? kpiParts(value, unit) : {value, unit};
  const info = useRef<HTMLButtonElement>(null);
  const back = useRef<HTMLButtonElement>(null);
  const wasFlipped = useRef(false);
  useEffect(() => {
    if (flipped) back.current?.focus();
    // Returning through this card restores focus; switching cards must not steal it.
    else if (wasFlipped.current && document.activeElement === back.current)
      info.current?.focus();
    wasFlipped.current = flipped;
  }, [flipped]);
  return (
    <article
      className={`kpi-card kpi-card--${variant}`}
      data-state={state}
      data-flipped={flipped}
      onKeyDown={(e) => {
        if (e.key === "Escape" && flipped) {
          info.current?.focus();
          onFlip?.();
        }
      }}
    >
      <div className="kpi-inner">
        <div className="kpi-front" inert={flipped} aria-hidden={flipped}>
          <div className="metric-heading">
            <span className="metric-label">{label}</span>
            {tooltip && (
              <span className="metric-info">
                <button
                  ref={info}
                  type="button"
                  aria-label={t("Metodología de {label}", { label })}
                  aria-expanded={flipped}
                  aria-controls={`${id}-back`}
                  aria-describedby={`${id}-tip`}
                  onClick={onFlip}
                >
                  ⓘ
                </button>
                <span role="tooltip" id={`${id}-tip`} className="metric-tip">
                  {brief ?? label}
                </span>
              </span>
            )}
          </div>
          <div className="kpi-value">
            {amount.value}{amount.unit && <> <span className="kpi-unit">{amount.unit}</span></>}
          </div>
          {comparisons && <div className="kpi-comparisons">{comparisons}</div>}
          <div className="kpi-context">
            <span>{context}</span>
            {onDetail && (
              <button
                className="icon-action"
                onClick={onDetail}
                title={t("Ver detalle")}
                aria-label={t("Detalle de {label}", {
                  label: label.toLocaleLowerCase(locale),
                })}
              >
                ↗
              </button>
            )}
          </div>
        </div>
        <div
          id={`${id}-back`}
          className="kpi-back"
          inert={!flipped}
          aria-hidden={!flipped}
        >
          <div className="kpi-back-heading">
            <strong>{label}</strong>
            <button
              ref={back}
              type="button"
              onClick={() => {
                info.current?.focus();
                onFlip?.();
              }}
              aria-label={t("Volver a {label}", { label })}
            >
              ↶
            </button>
          </div>
          <div className="kpi-methodology">
            <p>{tooltip}</p>
            <p>
              {methodSource ??
                t("Fuente: Secretaría de Energía · formación Vaca Muerta.")}
            </p>
            <a
              href="#methodology"
              onClick={() => {
                const detail = document.getElementById("methodology");
                if (detail instanceof HTMLDetailsElement) detail.open = true;
              }}
            >
              {t("Ver metodología →")}
            </a>
          </div>
        </div>
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
  subtitle?: string;
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
          {subtitle && <p>{subtitle}</p>}
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
export { GlobalFilters } from './global-filters';
export const gasReferenceMethod = "Henry Hub · escenario internacional de referencia. Conversión energética estimada con referencia EIA: 1.036 BTU/pie³; no poder calorífico medido de Vaca Muerta. No representa facturación efectiva.";
// Methodology belongs to the relevant KPI disclosure, not a banner above all views.
export function ReferenceValuationNote(_props: {fluid: Fluid; prices: Prices | null}) { return null; }
// KPIs/rankings render in HTML; only the responsive chart waits for browser layout.
export const Evolution=dynamic(()=>import('./evolution-chart').then(m=>m.Evolution),{
  ssr:false,
  loading:()=> <div className="chart-card" aria-label="Gráfico de evolución" style={{minHeight:420}} />,
});

const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "/vaca-muerta-pulse";
const assets: Record<string, string> = {
  YPF: "YPF.svg",
  PLUSPETROL: "PLUSPETROL.svg",
  PAL: "PAL.png",
  PAM: "PAM.svg",
  TAU: "TAU.svg",
  TPT: "TPT.webp",
  SHE: "SHE.webp",
  PGR: "PGR.png",
  VST: "VST.svg",
};
export const shortNames: Record<string, string> = {
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
export function OperatorLogo({ id }: { id: string }) {
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
          width={36}
          height={36}
          decoding="async"
          loading="lazy"
          onError={() => setFailed(true)}
        />
      ) : (
        id.slice(0, 2)
      )}
    </span>
  );
}

export function RankingItem({
  position,
  logo,
  name,
  fullName,
  production,
  productionExact,
  participation,
  variation,
  comparison,
  comparisonPeriod,
  onSelect,
}: {
  position: number;
  logo?: ReactNode;
  name: string;
  fullName: string;
  production: ReactNode;
  productionExact: string;
  participation: number | null;
  variation: number | null;
  comparison: Comparison;
  comparisonPeriod: string;
  onSelect: () => void;
}) {
  const { t, percent } = useLocale();
  return (
    <li>
      <button
        className="ranking-row ranking-item"
        data-leader={position === 1}
        data-has-logo={!!logo}
        onClick={onSelect}
      >
        <span className="ranking-main">
          <span className="entity-name">
            <span className="rank">{position.toString().padStart(2, "0")}</span>
            {logo}
            <span className="ranking-name" title={fullName}>
              {name}
            </span>
          </span>
          <span
            className="share-value"
            title={t("Barras: participación en el total · escala 0–100%")}
          >
            <span className="sr-only">{t("Cuota")} </span>
            {participation == null
              ? t("No disponible")
              : percent(participation)}
          </span>
        </span>
        <span className="ranking-meta">
          <span className="bar-value">
            <span className="ranking-amount" title={productionExact}>
              {production}
            </span>
          </span>
          <span
            className="yoy-value"
            title={t("vs. {period}", { period: comparisonPeriod })}
          >
            <span className="ranking-comparison-label">
              {t(comparison === "mom" ? "Mensual" : "Interanual")}
            </span>
            <Change value={variation} compact />
          </span>
        </span>
        <span className="bar-track" aria-hidden="true">
          <span style={{ width: `${participation ?? 0}%` }} />
        </span>
      </button>
    </li>
  );
}

export function RankingCard({
  mode,
  prices,
  entities,
  current,
  fluid,
  dimension,
  comparison,
  onNavigate,
}: {
  mode: Mode;
  prices: Prices | null;
  entities: Entity[];
  current: Row;
  fluid: Fluid;
  dimension: "company" | "area";
  comparison: Comparison;
  onNavigate: (tab: Tab, id?: string) => void;
}) {
  const { t, compact, number, month } = useLocale();
  const operators = dimension === "company",
    tab = operators ? "operators" : "areas",
    shown = prepareEntities(entities, fluid, dimension, current.periodo).top;
  return (
    <ModuleCard
      title={t(operators ? "Principales operadores" : "Principales áreas")}
      subtitle={t(
        mode === "value"
          ? "Top 5 · valor bruto estimado · USD"
          : "Top 5 · volumen mensual · {unit}",
        { unit: volumeUnit(fluid) },
      )}
      className={`ranking-card ${operators ? "ranking-operators" : "ranking-areas"}`}
      action={
        <button className="text-action" onClick={() => onNavigate(tab)}>
          {t("{section} · Ver detalle ↗", {
            section: t(operators ? "Operadores" : "Áreas"),
          })}
        </button>
      }
    >
      <ol className="ranking-list">
        {shown.map((e) => {
          // Prepared volumes retain the true total-volume denominator in both comparisons.
          const share =
            current.volume > 0 &&
            (mode === "volume" ||
              referencePrice(prices, current.periodo, fluid) != null)
              ? (e.volume / current.volume) * 100
              : null;
          const label = operators
            ? operatorName(e.entity_id, e.entity_name)
            : e.entity_name;
          const value = entityValue(e, prices, mode);
          return (
            <RankingItem
              key={e.entity_id}
              position={e.volume_rank}
              logo={operators ? <OperatorLogo id={e.entity_id} /> : undefined}
              name={operators ? (shortNames[e.entity_id] ?? label) : label}
              fullName={label}
              participation={share}
              production={
                <>
                  {compact(value)}
                  {value != null && (
                    <span className="ranking-unit">
                      {" "}
                      {mode === "value" ? "USD" : volumeUnit(fluid)}
                    </span>
                  )}
                </>
              }
              productionExact={
                mode === "value"
                  ? `${number(value, 2, 0)} USD`
                  : `${number(value, fluid === "oil" ? 0 : 2, 0)} ${volumeUnit(fluid)}`
              }
              variation={entityComparison(e, prices, mode, comparison)}
              comparison={comparison}
              comparisonPeriod={month(
                shiftMonth(current.periodo, comparisonOffset(comparison)),
              )}
              onSelect={() => onNavigate(tab, e.entity_id)}
            />
          );
        })}
      </ol>
      {!shown.length && (
        <p className="empty">
          {t(
            operators
              ? "Sin operadores para este período."
              : "Sin áreas para este período.",
          )}
        </p>
      )}
      <p className="ranking-scale">
        {t("Barras: participación en el total · escala 0–100%")}
        {mode === "value" && t(" · Referencia uniforme, no ingresos efectivos")}
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
  mode,
  prices,
  comparison,
}: {
  current: Row;
  rows: Row[];
  entities: Entity[];
  fluid: Fluid;
  period: string;
  range: number;
  setRange: (n: number) => void;
  onNavigate: (tab: Tab, id?: string) => void;
  mode: Mode;
  prices: Prices | null;
  comparison: Comparison;
}) {
  const { t, number, million, month } = useLocale();
  const [flipped, setFlipped] = useState<number | null>(null);
  const flipProps = (id: number) => ({
    methodSource: t(
      id === 3 && monetary
        ? "Fuente: EIA."
        : id !== 2 && (monetary || id === 3)
          ? "Fuente: Secretaría de Energía · EIA."
          : "Fuente: Secretaría de Energía.",
    ),
    flipped: flipped === id,
    onFlip: () => setFlipped((active) => (active === id ? null : id)),
  });
  const shownMode = effectiveMode(mode, fluid),
    monetary = shownMode === "value";
  const daily = metric(current, rows, prices, "rate", shownMode),
    monthly = metric(current, rows, prices, "volume", shownMode),
    wells = metric(current, rows, prices, "wells"),
    fourth = metric(current, rows, prices, monetary ? "price" : "estimate");
  const price = metric(current, rows, prices, "price").value;
  const valuationHelp = t(
    price == null
      ? "Estimación pendiente: referencia monetaria sin validar para este período."
      : fluid === "gas" ? gasReferenceMethod : "Volumen mensual × precio del período. Estimación, no facturación efectiva.",
  );
  const comparisons = (m: Metric) => (
    <Comparisons metric={m} period={period} comparison={comparison} />
  );
  return (
    <>
      <h1 className="sr-only">{t("Resumen de Vaca Muerta")}</h1>
      <ReferenceValuationNote fluid={fluid} prices={prices} />
      {monetary && price == null && (
        <p className="availability-note" role="status">
          {t(
            "Precio de referencia no disponible para este período; el valor estimado permanece sin calcular.",
          )}
        </p>
      )}
      <div className="kpi-grid">
        <KpiCard
          {...flipProps(0)}
          brief={t(
            monetary
              ? "Promedio diario del valor estimado del mes."
              : "Promedio diario de producción del mes.",
          )}
          variant="primary"
          label={t(monetary ? "Valor diario estimado" : "Producción diaria")}
          value={
            monetary
              ? million(daily.value, 2)
              : number(daily.value, fluid === "oil" ? 0 : 2)
          }
          unit={monetary ? t("M USD/día") : rateUnit(fluid)}
          context={month(period)}
          comparisons={comparisons(daily)}
          tooltip={t(
            monetary
              ? "Valor mensual estimado / días calendario. No representa facturación efectiva."
              : "Volumen mensual dividido por los días del período.",
          )}
          onDetail={() => onNavigate("production")}
        />
        <KpiCard
          {...flipProps(1)}
          brief={t(
            monetary
              ? "Producción valorizada a precio de referencia."
              : "Producción acumulada durante el mes.",
          )}
          label={t(monetary ? "Valor mensual estimado" : "Volumen mensual")}
          value={
            monetary || fluid === "oil"
              ? million(monthly.value)
              : number(monthly.value, 1)
          }
          unit={monetary ? "M USD" : fluid === "oil" ? "M bbl" : "MMm³"}
          context={month(period)}
          comparisons={comparisons(monthly)}
          tooltip={
            monetary
              ? valuationHelp
              : t("Suma de la producción registrada durante el mes.")
          }
          onDetail={() => onNavigate("production")}
        />
        <KpiCard
          {...flipProps(2)}
          brief={t("Pozos con producción positiva en el mes.")}
          label={t("Pozos productivos")}
          value={number(wells.value, 0)}
          unit={t("pozos")}
          context={t("Con producción positiva")}
          comparisons={comparisons(wells)}
          tooltip={t("Pozos únicos con producción positiva durante el mes.")}
          onDetail={() => onNavigate("activity")}
        />
        <KpiCard
          {...flipProps(3)}
          brief={t(
            price == null
              ? "Estimación monetaria no disponible."
              : monetary
                ? "Precio promedio mensual de referencia."
                : "Producción valorizada a precio de referencia.",
          )}
          label={t(
            monetary ? fluid === "oil" ? "Precio de referencia Brent" : "Precio de referencia Henry Hub" : "Valor estimado a precio de referencia",
          )}
          value={monetary ? number(fourth.value, 2) : million(fourth.value)}
          unit={
            fourth.value == null ? undefined : monetary ? (fluid === "oil" ? "USD/bbl" : "USD/MMBtu") : "M USD"
          }
          context={t(
            monetary
              ? "Promedio mensual · EIA"
              : fourth.value == null
                ? "Estimación pendiente"
                : fluid === "oil" ? "A precio Brent · estimación" : "Henry Hub · escenario estimado",
          )}
          comparisons={comparisons(fourth)}
          tooltip={
            monetary
              ? t(
                  fluid === "gas" ? gasReferenceMethod : "Promedio mensual de referencia; no es el precio efectivo de venta.",
                )
              : valuationHelp
          }
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
        onDetail={() => onNavigate("production")}
      />
      <div className="ranking-grid">
        {(["company", "area"] as const).map((dimension) => (
          <RankingCard
            key={dimension}
            entities={entities}
            current={current}
            fluid={fluid}
            dimension={dimension}
            mode={shownMode}
            prices={prices}
            comparison={comparison}
            onNavigate={onNavigate}
          />
        ))}
      </div>
    </>
  );
}
