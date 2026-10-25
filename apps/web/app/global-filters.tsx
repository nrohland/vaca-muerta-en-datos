"use client";
import type { Fluid } from "../lib/contract";
import type { Mode, Comparison } from "../lib/metrics";
import { useLocale } from "../lib/locale";
import { MeasurementIcon } from "./icons";
export function GlobalFilters({
  fluid,
  period,
  periods,
  mode,
  comparison,
  onFluid,
  onPeriod,
  onMode,
  onComparison,
}: {
  fluid: Fluid;
  period: string;
  periods: string[];
  mode: Mode;
  comparison: Comparison;
  onFluid: (f: Fluid) => void;
  onPeriod: (p: string) => void;
  onMode: (m: Mode) => void;
  onComparison: (c: Comparison) => void;
}) {
  const { t, month } = useLocale();
  return (
    <div className="global-filters">
      <fieldset className="fluid-control">
        <legend className="sr-only">{t("Fluido")}</legend>
        {(["oil", "gas"] as Fluid[]).map((f) => (
          <button key={f} aria-pressed={fluid === f} onClick={() => onFluid(f)}>
            {t(f === "oil" ? "Petróleo" : "Gas")}
          </button>
        ))}
      </fieldset>
      <label className="period-selector">
        <span className="sr-only">{t("Período")}</span>
        <select
          aria-label={t("Mes de producción")}
          value={period}
          disabled={!periods.length}
          onChange={(e) => onPeriod(e.target.value)}
        >
          {periods
            .slice()
            .reverse()
            .map((p) => (
              <option key={p} value={p}>
                {month(p)}
              </option>
            ))}
        </select>
      </label>
      <fieldset className="fluid-control mode-control">
        <legend className="sr-only">{t("Unidad de análisis")}</legend>
        {(["volume", "value"] as Mode[]).map((m) => (
          <button key={m} aria-pressed={mode === m} onClick={() => onMode(m)}>
            {m === "volume" ? (
              <MeasurementIcon />
            ) : (
              <span className="currency-symbol" aria-hidden="true">
                $
              </span>
            )}
            {t(m === "volume" ? "Volumen" : "Valor USD")}
          </button>
        ))}
      </fieldset>
      <fieldset className="fluid-control comparison-control">
        <legend className="sr-only">{t("Comparación temporal")}</legend>
        {(["mom", "yoy"] as Comparison[]).map((c) => (
          <button
            key={c}
            aria-pressed={comparison === c}
            onClick={() => onComparison(c)}
          >
            {t(c === "mom" ? "Mensual" : "Interanual")}
          </button>
        ))}
      </fieldset>
    </div>
  );
}
