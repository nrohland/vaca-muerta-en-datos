import type { Fluid, Row } from "./contract.ts";
import { historyWindow } from "./history.ts";
import { change, daysInMonth, shiftMonth, type Comparison } from "./metrics.ts";

export type ActivityPoint = {
  periodo: string; wells: number | null; average: number | null;
  mom: number | null; yoy: number | null; momBase: string; yoyBase: string;
};
export function averagePerProductiveWell(row: Row | undefined): number | null {
  if (!row || row.positive_producing_wells <= 0) return null;
  // Gas mart volumes are million m³; the displayed average uses m³.
  return row.volume * (row.fluid === "gas" ? 1e6 : 1) / daysInMonth(row.periodo) / row.positive_producing_wells;
}
export function activityPoints(rows: Row[], fluid: Fluid, period: string, range: number): ActivityPoint[] {
  const observations = new Map(rows.filter(r => r.fluid === fluid).map(r => [r.periodo, r]));
  return historyWindow(rows, fluid, period, range).points.map(p => {
    const row = observations.get(p.periodo);
    const wells = row?.positive_producing_wells ?? null;
    const momBase = shiftMonth(p.periodo, -1), yoyBase = shiftMonth(p.periodo, -12);
    const delta = (base: string) => wells == null || !observations.has(base) ? null : wells - observations.get(base)!.positive_producing_wells;
    return { periodo: p.periodo, wells, average: averagePerProductiveWell(row), mom: delta(momBase), yoy: delta(yoyBase), momBase, yoyBase };
  });
}
export function activityKpis(rows: Row[], current: Row, comparison: Comparison) {
  const point = activityPoints(rows, current.fluid, current.periodo, 1)[0];
  const basePeriod = shiftMonth(current.periodo, comparison === "mom" ? -1 : -12);
  const base = rows.find(r => r.fluid === current.fluid && r.periodo === basePeriod);
  const average = averagePerProductiveWell(current);
  return { wells: current.positive_producing_wells, delta: point?.[comparison] ?? null, basePeriod,
    pct: change(current.positive_producing_wells, base?.positive_producing_wells), average,
    averagePct: change(average, averagePerProductiveWell(base)) };
}
export function activityCsv(points: ActivityPoint[], fluid: Fluid) {
  const columns = ["periodo", "positive_producing_wells", fluid === "oil" ? "bbl_per_productive_well_calendar_day" : "m3_per_productive_well_calendar_day", "net_wells_mom", "mom_base", "net_wells_yoy", "yoy_base"];
  return [columns.join(","), ...points.map(p => [p.periodo, p.wells, p.average, p.mom, p.momBase, p.yoy, p.yoyBase].map(v => v ?? "").join(","))].join("\n") + "\n";
}
