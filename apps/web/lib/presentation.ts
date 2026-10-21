/** Split notation without scaling or recalculating the metric. */
export function kpiParts(value: string, unit?: string) {
  const compact = value.match(/^([+−-]?[\d.,]+)\s*([KM])(?:\s+(.+))?$/);
  if (compact) return {value:compact[1],unit:[compact[2],compact[3],unit].filter(Boolean).join(' ')};
  const percentage = value.match(/^([+−-]?[\d.,]+)\s*%$/);
  if (percentage && !unit) return {value:percentage[1],unit:'%'};
  return {value,unit};
}
export function trendClass(value: number | null | undefined) {
  return value == null || !Number.isFinite(value) || value === 0 ? 'trend-neutral' : value > 0 ? 'trend-positive' : 'trend-negative';
}
export function kpiState(value: number | null | undefined): 'neutral' | 'favorable' | 'unfavorable' {
  return value == null || !Number.isFinite(value) || value === 0 ? 'neutral' : value > 0 ? 'favorable' : 'unfavorable';
}
