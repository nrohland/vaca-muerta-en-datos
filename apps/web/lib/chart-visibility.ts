import type { Fluid } from "./contract.ts";
export type SeriesView = "both" | "physical" | "value";
// A user-hidden series and an unavailable series are distinct states.
export function chartVisibility({wells, fluid, detailView, selected, hasEstimated}: {
  wells: boolean; fluid: Fluid; detailView: boolean; selected: SeriesView; hasEstimated: boolean;
}) {
  const available = !wells && fluid === "oil" && hasEstimated;
  const activeSeries: SeriesView = wells || !available ? "physical" : detailView ? selected : "both";
  return {
    activeSeries,
    showPhysical: activeSeries !== "value",
    monetary: available && activeSeries !== "physical",
    unavailable: !wells && !available,
  };
}
