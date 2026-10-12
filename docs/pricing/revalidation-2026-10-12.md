# Revalidación oficial de precios — 12 de octubre de 2026

## Brent

Se descargó nuevamente la respuesta oficial [EIA mensual](https://www.eia.gov/dnav/pet/hist/leafhandler.ashx?f=m&n=pet&s=rbrte). Release 7 de octubre de 2026. SHA-256 `15df82629c5906c899f741b72258770cd3a5d4f12e884962aa459849db58fdd9`: igual al artefacto retenido el 9 de octubre. Agosto 2026: 91,08 USD/bbl. La respuesta contiene septiembre, pero el snapshot candidato se recorta a agosto aceptado: 472 meses mayo 1987–agosto 2026. Preparación/loader no consultan Next.js; cargan fuente raw revisada, dbt hace valorización y el consumidor actual permanece intacto hasta integración final.

## Gas

La [API oficial del catálogo](https://datos.energia.gob.ar/api/3/action/package_show?id=precios-de-gas-natural) y el [CSV oficial de Res. 1/2018](https://datos.energia.gob.ar/dataset/5ddbdfbb-b6f9-4bc1-9e71-0055e86cf552/resource/d87ca6ab-2979-474b-994a-e4ba259bb217/download/precios-de-gas-natural-.csv) sí pudieron descargarse esta vez. Esto resuelve la limitación de conectividad de la revisión del 11 de octubre; no resuelve los huecos de precio.

CSV: 1.602 filas, SHA-256 `1bd11d294573d30c8f366dfab302ee8bd4b5a19925358263b8f6f608e3576ae4`, mismo contenido retenido. Neuquina/TOTAL: 89 meses enero 2019–mayo 2026; junio–agosto ausentes. Mayo PPP=4,01 USD/MMBTU. No usar precio_expo=4,66 como sustituto ni mezclar categorías TOTAL/FIRME/INTERRUMPIBLE.

El [tablero oficial](https://estadisticasenergia.mecon.gob.ar/superset/dashboard/175/?standalone=true) define ventas de gas de 9.300 kcal/m³. La búsqueda sobre el [informe anual 2024 de ENARGAS](https://www.enargas.gob.ar/secciones/publicaciones/informes-anuales-de-balance-y-gestion/pdf/anuales/2024/informe-anual-2024.pdf) recuperó la aclaración de que la producción SE está expresada al poder calorífico de la fuente de aprovisionamiento y transporte/distribución a 9.300 kcal. Esto refuerza que no se debe asumir equivalencia térmica para aplicar PPP a producción CapIV. El PDF se descargó, pero no se extrajo página/texto local completo en este entorno; esa aclaración procede del índice de búsqueda oficial y no reemplaza una verificación específica del contrato CapIV.

Conclusión operativa: gas USD continúa NULL. Para habilitarlo se requieren precios del mismo mes y poder calorífico trazable compatible con volumen CapIV, o un escenario explícito y separado autorizado como supuesto. No se implementó escenario ni forward filling.

## Estado de validación

12 pruebas offline de importer/loader pasan. El build real del candidato del 12 de octubre completó 83 resultados correctos: 11 modelos, 66 tests de datos y 6 unit tests (3 de producción y 3 de precios), sin errores, advertencias ni omisiones. Los tests de precios cubren ausencia de precio, volumen inválido/cero, huecos de calendario y YTD incompleto. La conciliación independiente de producción y valorización entre pozos, operadores y áreas pasó dentro de tolerancia numérica. [Evidencia de orquestación](../evidence/orchestration/README.md).

La ejecución usa desarrollo candidato y el frontend sigue con el snapshot anterior hasta el cierre integrado. No hubo merge, activación del cron, publicación ni despliegue.
