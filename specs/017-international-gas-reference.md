# Referencias internacionales y escenario energético de gas

Decisión autorizada por Nicolás el 12 de octubre de 2026: usar Henry Hub mensual de EIA para gas, alineado con Brent mensual de EIA para petróleo. Cerrar la dependencia operativa de PPP Neuquina para esta métrica. No cambiar el universo de producción ni presentar ingresos efectivos.

## Definición

Petróleo: barriles × precio Brent del mismo mes (USD/bbl). Gas: m³ declarados × equivalencia energética de referencia × Henry Hub del mismo mes (USD/MMBtu). Marts reciben gas de CapIV en miles de m³, multiplican por 1.000; frontend recibe MMm³ y multiplica por 1.000.000. La conversión se realiza una sola vez por capa y se verifica su paridad.

El [calculador EIA](https://www.eia.gov/energyexplained/units-and-calculators/energy-conversion-calculators.php) publica 1.036 BTU/pie³ como estimación del promedio estadounidense entregado a consumidores en 2026. El [NIST](https://www.nist.gov/system/files/documents/2021/11/30/2022-HB44-Section-Appendix-C.pdf) define exactamente 1 pie³ = 0,028316846592 m³. Factor fijo del escenario: 1036 / 0.028316846592 / 1e6 = aproximadamente 0,03658599472346218 MMBtu/m³.

Esto es un **supuesto energético versionado para una estimación internacional**, no calorificidad medida de Vaca Muerta. No se corrigen condiciones de temperatura/presión ni composición del gas; el volumen declarado se usa como volumen del escenario. No afirmar que este valor equivale a energía vendida, ingresos, margen o precio argentino. El mismo factor de referencia 2026 se aplica al histórico para hacer comparaciones homogéneas, no se presenta como medición histórica de cada año.

Basis obligatorio: `EIA_US_AVERAGE_1036_BTU_PER_CUBIC_FOOT_SCENARIO_V1`. Constantes, contexto, URLs y digest del documento EIA retenido en `extraction/contracts/reference_energy.json`. Cambiar el factor requiere nueva versión del contrato; no seleccionar silenciosamente otro poder calorífico.

## Contratos y controles

Precio raw: producto × mes, con benchmark, moneda, unidad, URL exacta, SHA-256 de respuesta, snapshot, publicación de fuente, recuperación y corte. Manifest v2 distingue products.oil y products.gas y digest conjunto de filas. Freshness se comprueba por fuente; timestamp combinado conserva la recuperación más antigua. Ambas referencias requieren precio del corte. Agosto 2026: Brent 91,08 USD/bbl; Henry Hub 2,78 USD/MMBtu.

No forward fill, sustitución de precio ni fallback a volumen cuando se pide USD. Precio o volumen inválido/ausente → NULL. Cero volumen con precio válido → cero valor; base cero → comparación porcentual NULL. Un precio duplicado no multiplica pozos: se considera indisponible y el test de unicidad falla. MoM/YoY usan calendario; YTD requiere todos los meses y precios. Estado de gas disponible: `reference_scenario`; método `estimated_reference_scenario` y factor/basis persistidos.

UI: selector Gas USD habilitado con valores estimados; aviso común en vistas monetarias, ES/EN y CSV con benchmark y supuesto. Petróleo mantiene la fórmula y componentes aprobados. Valor monetario sigue ámbar, volumen de gas violeta. Si un mes no tiene precio se muestra indisponibilidad, sin ocultar la selección USD.

## Integración y límites

La rama candidata usa dbt y controles reales en BigQuery. El snapshot multianual de revisión todavía contiene sus volúmenes agregados previos y calcula referencias con el helper TypeScript compartido; se verifica su paridad numérica con dbt para agosto. Este cambio cierra la definición y habilitación de gas de referencia, no afirma haber migrado todos los exportadores históricos al warehouse. El cierre integrado mantiene esa tarea independiente.

No merge, activación del workflow, publicación ni despliegue. Pruebas/capturas y resultados reales quedan en docs/evidence/gas-reference/README.md al completar la validación.
