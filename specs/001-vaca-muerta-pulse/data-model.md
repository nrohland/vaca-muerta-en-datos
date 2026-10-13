# Modelo de datos — Vaca Muerta en Datos

## Granos vigentes

| Capa | Grano / propósito |
| --- | --- |
| Raw producción | Declaración oficial pozo × mes; conserva campos y procedencia de cuatro CSV |
| Staging | Tipos normalizados, deduplicación y filtro VM no convencional |
| Intermediate | Clave pozo × mes y días calendario |
| fct_well_month | Hecho físico de cada pozo y mes |
| Dimensiones | IDs oficiales de operador y área; nombres no reemplazan claves |
| Referencias | Producto × mes, Brent o Henry Hub, unidades y procedencia |
| Valorización | Valores de referencia a grano pozo × mes y entidad × mes |
| fct_dashboard_month | Fluido × dimensión × ID × mes; salida agregada del consumidor |

Corte aceptado enero 2023–agosto 2026. Petróleo m³ × 6,28981077 → bbl; gas miles de m³ → MMm³. Tasa mensual / días calendario. Pozos productivos únicos con volumen positivo del fluido; los conteos no se suman.

Comparaciones contra mes calendario exacto, sin saltar huecos. Porcentaje con base cero → NULL; YTD exige calendario y precios completos. Ausencias dentro de meses aceptados tienen cero explícito por entidad, sin extender cobertura a meses no aceptados.

Precios dinámicos en raw; valorización persistida en dbt. Gas usa Henry Hub con escenario energético EIA documentado, no calorificidad medida. No inferir ingresos, productividad por día efectivo, altas/bajas, completaciones ni relación operador–área actual desde agregados marginales.

Contratos detallados: [histórico](../019-historical-source-candidate.md), [export](../018-historical-dashboard-export.md), [precios](../016-candidate-pricing.md), [gas](../017-international-gas-reference.md). [Linaje real](../../docs/lineage/README.md).
