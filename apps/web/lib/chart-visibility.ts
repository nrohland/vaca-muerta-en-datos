import type { Fluid } from "./contract.ts";
import type { Mode } from "./metrics.ts";
export type SeriesView = "physical" | "value";
// One visible magnitude: volume and reference USD never share independent axes.
export function chartVisibility({wells, detailView, selected, hasEstimated, mode}: {
  wells: boolean; fluid: Fluid; detailView: boolean; selected: SeriesView;
  hasEstimated: boolean; mode: Mode;
}) {
  const available = !wells && hasEstimated;
  const activeSeries: SeriesView = wells || !available ? "physical"
    : detailView ? selected : mode === "value" ? "value" : "physical";
  return {
    activeSeries,
    showPhysical: activeSeries === "physical",
    monetary: available && activeSeries === "value",
    unavailable: !wells && !available,
  };
}
