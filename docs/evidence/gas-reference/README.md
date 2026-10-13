# Henry Hub y Gas USD — cierre de referencia

Entrega del 13 de octubre de 2026. Ingesta, build BigQuery y capturas ejecutados el 12 de octubre; pruebas locales finales repetidas el 13. Desarrollo candidato, sin promoción ni despliegue.

## Resultado

Petróleo usa Brent mensual; gas usa Henry Hub mensual, ambos EIA. Se cargaron 828 filas producto-mes: 472 petróleo y 356 gas hasta agosto de 2026. [Manifest de fuentes](price-manifest.json), [recibo de carga](price-load.json), [linaje cargado](linaje.json).

Gas USD está habilitado en Resumen, Producción, Operadores y Áreas. Actividad conserva unidades físicas y explica que la selección USD queda guardada para las demás vistas. Los componentes, colores, ES/EN, temas y contexto de navegación se mantienen.

La equivalencia energética es un **escenario de referencia**, no calorificidad medida de Vaca Muerta: 1.036 BTU/pie³ del promedio estadounidense estimado por EIA en 2026 y 0,028316846592 m³/pie³ exactos de NIST. Factor fijo aproximadamente 0,03658599472346218 MMBtu/m³. Se explicita en la UI y CSV de gas. No se usan PPP Neuquina, forward fill ni factores ocultos. [Contrato de método](../../../specs/017-international-gas-reference.md).

Agosto: Henry Hub 2,78 USD/MMBtu. Valor bruto de referencia de gas: **USD 300.952.130,34**, alrededor de 300,95 millones. No son ingresos realizados. El cálculo independiente con Decimal, los marts por pozo y entidad y el helper del frontend concilian dentro de tolerancia FLOAT64. Petróleo también concilia y conserva su fórmula. [Conciliación](conciliacion.json).

## Verificación

[Extracción real](extract-run.json) y [transformación real](transform-run.json) completaron seis etapas cada una. [dbt](dbt-summary.json): 88 resultados satisfactorios, 11 modelos, 67 tests de datos y 10 unit tests; cero errores, advertencias u omisiones. Los modelos/macros/tests ejecutados coinciden con el checkout integrado. [Digests de paridad](paridad-fuentes.json).

[Pruebas finales](tests.json): 96 Python (33 pipeline, 32 extracción, 31 precios), 54 frontend, typecheck y build estático aprobados. El build usó dependencias del mismo lock en un runtime fresco para evitar fallos de lectura de la instalación local. Código frontend ejecutado y checkout coinciden. No se modificó el lock ni se actualizaron dependencias.

Inspección manual mediante navegador real: cinco vistas con Gas/USD y contexto persistente; Producción con tabla/precios/series; desktop 1280×900 y móvil 390×844 con inglés/modo oscuro. En móvil, ancho del documento y viewport = 390, sin overflow global. Esto no se presenta como una corrida automatizada de Playwright o axe. [Checks de frontend](checks-frontend.json).

La inspección detectó un cálculo antiguo de Brent en la tarjeta total de Operadores. Se reemplazó por el helper compartido y se verificó el valor corregido 300,95 M USD en pantalla. También se corrigieron etiquetas de Áreas para identificar valores monetarios como estimados. CSV de producción y operadores incluye benchmark y basis/factor del escenario; los faltantes quedan vacíos.

## Capturas representativas

- [Resumen](capturas/resumen-gas-usd-desktop.jpg)
- [Producción](capturas/produccion-gas-usd-desktop.jpg)
- [Operadores](capturas/operadores-gas-usd-desktop.jpg)
- [Áreas](capturas/areas-gas-usd-desktop.jpg)
- [Actividad](capturas/actividad-gas-contexto-usd-desktop.jpg)
- [Resumen móvil, inglés y oscuro](capturas/resumen-gas-usd-mobile-en-dark.jpg)

## Alcance pendiente del proyecto

La referencia internacional y la estimación de gas están implementadas y verificadas en desarrollo. El frontend conserva volúmenes del snapshot multianual previo y cálculo compartido TypeScript; migrar todos los exportadores históricos al mart, conciliar la consolidación comercial y cerrar el pipeline de publicación multianual sigue pendiente. El mart candidato actual contiene agosto únicamente: comparadores/YTD sin historia permanecen NULL. La paridad nueva acredita el total de agosto, no reconstrucción completa del histórico desde dbt.

WIF está configurado pero todavía no probado desde GitHub; la confianza sigue limitada a main y el workflow sigue desactivado. No hubo claves nuevas, push, PR nuevo, merge, activación de cron ni publicación/despliegue. El CSV de producción mantiene la redirección HTTP documentada; las fuentes de precios EIA se descargaron por HTTPS con URL exacta.
