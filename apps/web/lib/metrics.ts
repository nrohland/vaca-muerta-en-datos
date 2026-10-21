import type { Entity, Fluid, Row } from "./contract.ts";
export type Comparison = "mom" | "yoy";
export const comparisonOffset = (comparison: Comparison) =>
  comparison === "mom" ? -1 : -12;
export type Mode = "volume" | "value";
export const GAS_ENERGY_BASIS = "EIA_US_AVERAGE_1036_BTU_PER_CUBIC_FOOT_SCENARIO_V1";
export const GAS_M3_TO_MMBTU = 1036 / 0.028316846592 / 1e6;
export type PriceSource = {provider: string; series: string; url: string; unit: "USD/bbl" | "USD/MMBtu"; frequency: "monthly"; source_updated_at: string; retrieved_at: string; response_sha256: string};
export type GasPrices = {status: "available"; interpretation: "reference_scenario"; source: PriceSource; prices: {periodo: string; usd_per_mmbtu: number}[]; conversion: {energy_basis: typeof GAS_ENERGY_BASIS; m3_to_mmbtu: number; btu_per_cubic_foot: 1036; source_url: string; interpretation: "scenario"}; reviewed_sources: string[]} | {status: "unavailable"; reason: string; reviewed_sources: string[]};
export type Prices = {schema_version: 1; source: PriceSource; prices: {periodo: string; usd_per_bbl: number}[]; gas: GasPrices};
export type Metric = {
  value: number | null;
  yoy: number | null;
  mom: number | null;
};
export function validatePrices(v: unknown): Prices {
  const p = v as Prices;
  if (
    !p ||
    p.schema_version !== 1 ||
    p.source?.unit !== "USD/bbl" ||
    p.source.frequency !== "monthly" ||
    p.source.provider !== "EIA" ||
    !p.source.url.startsWith("https://www.eia.gov/") ||
    !Number.isFinite(Date.parse(p.source.source_updated_at)) ||
    !Number.isFinite(Date.parse(p.source.retrieved_at)) ||
    !/^[a-f0-9]{64}$/.test(p.source.response_sha256) ||
    !Array.isArray(p.prices) ||
    !["unavailable", "available"].includes(p.gas?.status)
  )
    throw Error("Referencia de precios inválida");
  const seen = new Set<string>();
  for (const r of p.prices) {
    if (
      !/^\d{4}-(0[1-9]|1[0-2])-01$/.test(r.periodo) ||
      seen.has(r.periodo) ||
      typeof r.usd_per_bbl !== "number" ||
      !Number.isFinite(r.usd_per_bbl) ||
      r.usd_per_bbl <= 0
    )
      throw Error("Precio mensual inválido");
    seen.add(r.periodo);
  }
  if (p.gas.status === "available") {
    const g = p.gas;
    if (g.interpretation !== "reference_scenario" || g.source?.provider !== "EIA" || g.source.unit !== "USD/MMBtu" || g.source.frequency !== "monthly" || !g.source.url.startsWith("https://www.eia.gov/") || !Number.isFinite(Date.parse(g.source.source_updated_at)) || !Number.isFinite(Date.parse(g.source.retrieved_at)) || !/^[a-f0-9]{64}$/.test(g.source.response_sha256) || g.conversion?.energy_basis !== GAS_ENERGY_BASIS || g.conversion.interpretation !== "scenario" || g.conversion.btu_per_cubic_foot !== 1036 || !Number.isFinite(g.conversion.m3_to_mmbtu) || Math.abs(g.conversion.m3_to_mmbtu - GAS_M3_TO_MMBTU) > 1e-12 || !g.conversion.source_url.startsWith("https://www.eia.gov/") || !Array.isArray(g.prices)) throw Error("Referencia de precios inválida");
    const months = new Set<string>();
    for (const r of g.prices) {
      if (!/^\d{4}-(0[1-9]|1[0-2])-01$/.test(r.periodo) || months.has(r.periodo) || typeof r.usd_per_mmbtu !== "number" || !Number.isFinite(r.usd_per_mmbtu) || r.usd_per_mmbtu <= 0) throw Error("Precio mensual inválido");
      months.add(r.periodo);
    }
  }
  return p;
}
export function shiftMonth(period: string, offset: number) {
  const d = new Date(`${period}T00:00:00Z`);
  d.setUTCMonth(d.getUTCMonth() + offset);
  return d.toISOString().slice(0, 10);
}
export function daysInMonth(period: string) {
  const d = new Date(`${period}T00:00:00Z`);
  return new Date(
    Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 0),
  ).getUTCDate();
}
export function change(
  value: number | null | undefined,
  base: number | null | undefined,
) {
  return value == null || base == null || base <= 0
    ? null
    : (value / base - 1) * 100;
}
export function referencePrice(
  prices: Prices | null,
  period: string,
  fluid: Fluid,
) {
  const g = prices?.gas;
  if (fluid === "gas" && (g?.status !== "available" || g.interpretation !== "reference_scenario" || g.conversion?.energy_basis !== GAS_ENERGY_BASIS || g.conversion.interpretation !== "scenario" || g.conversion.btu_per_cubic_foot !== 1036 || !Number.isFinite(g.conversion.m3_to_mmbtu) || Math.abs(g.conversion.m3_to_mmbtu - GAS_M3_TO_MMBTU) > 1e-12)) return null;
  const price = fluid === "oil" ? prices?.prices.find(p => p.periodo === period)?.usd_per_bbl : g?.status === "available" ? g.prices.find(p => p.periodo === period)?.usd_per_mmbtu : null;
  return typeof price === "number" && Number.isFinite(price) && price > 0 ? price : null;
}
// Values are produced by validated dbt marts. Missing legacy fields stay unavailable.
export function warehouseValue(row: Row | undefined, daily = false): number | null {
  if (!row || !["estimated_reference", "estimated_reference_scenario"].includes(String(row.valuation_method))) return null;
  const value = row[daily ? "estimated_daily_value_usd" : "estimated_value_usd"];
  return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : null;
}
export function metric(
  row: Row,
  rows: Row[],
  prices: Prices | null,
  kind: "rate" | "volume" | "wells" | "estimate" | "price",
  mode: Mode = "volume",
): Metric {
  if (kind === "price") {
    const priceAt=(period:string)=>{
      const candidate=rows.find(r=>r.fluid===row.fluid&&r.periodo===period);
      return warehouseValue(candidate)!==null && typeof candidate?.price_usd_per_unit==='number' && candidate.price_usd_per_unit>0
        ? candidate.price_usd_per_unit : referencePrice(prices,period,row.fluid);
    };
    const value=priceAt(row.periodo);
    return {
      value,
      yoy: change(
        value,
        priceAt(shiftMonth(row.periodo, -12)),
      ),
      mom: change(
        value,
        priceAt(shiftMonth(row.periodo, -1)),
      ),
    };
  }
  const previous = (offset: number) =>
    rows.find(
      (r) =>
        r.fluid === row.fluid && r.periodo === shiftMonth(row.periodo, offset),
    );
  const read = (r: Row | undefined): number | null => {
    if (!r) return null;
    if (kind === "wells") return r.positive_producing_wells;
    if (kind === "estimate" || mode === "value") {
      return warehouseValue(r, kind === "rate");
    }
    return r[kind];
  };
  const value = read(row);
  return {
    value,
    yoy: change(value, read(previous(-12))),
    mom: change(value, read(previous(-1))),
  };
}
export function entityValue(e: Entity, prices: Prices | null, mode: Mode) {
  return mode === "value"
    ? warehouseValue(e)
    : e.volume;
}
export function entityYoY(e: Entity, prices: Prices | null, mode: Mode) {
  return mode === "volume" ? e.yoy_volume_pct : change(warehouseValue(e), numericBase(e.yoy_estimated_value_usd));
}
const numericBase = (v: unknown) => typeof v === "number" && Number.isFinite(v) && v >= 0 ? v : null;
export function entityComparison(e: Entity, prices: Prices | null, mode: Mode, comparison: Comparison) {
  if (comparison === "yoy") return entityYoY(e, prices, mode);
  return mode === "volume" ? e.mom_volume_pct as number | null : change(warehouseValue(e), numericBase(e.mom_estimated_value_usd));
}
// Nonnegative quantities always retain an honest zero origin. Recharts chooses nice ticks.
export const nonnegativeDomain: [number, "auto"] = [0, "auto"];
export function effectiveMode(mode: Mode, fluid: Fluid) {
  return mode;
}
export const estimationNote =
  "Valor estimado a precio de referencia. No representa facturación efectiva.";
