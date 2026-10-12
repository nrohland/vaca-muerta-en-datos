# Revisión integrada — Vaca Muerta en Datos

Revisión local del 11 de octubre de 2026. Cinco pestañas funcionales sobre el candidato hasta agosto de 2026. Resumen conserva arquitectura/layout/KPIs; sólo conecta identidad cromática y destinos disponibles. No merge, push, publicación, despliegue ni migración de warehouse.

## Resultado y evidencia

- `npm test`: **47/47** tests de cálculos, transformaciones, contrato, idiomas y selección URL. [Log](unit-tests.log).
- `npm run typecheck` y `npm run build`: aprobados. [Build](build.log).
- Auditoría AE independiente: rankings completos concilian en 44 meses, YTD y comparaciones con bases exactas, gas sin USD inventado. [Informe](analytics-engineering-review.md).
- Navegador integrado: 20 estados responsive (320/390/768/1440 × 5 pestañas), gas/inglés/dark, modo USD físico no disponible, series aisladas, rangos 12/24/36/44, recarga, primer mes sin comparador, CSV y deep links/atrás/adelante. [Resultados](ui-checks.json).
- Segunda auditoría independiente: cuatro issues corregidos; [informe](revision-final-pestanas.md) y [regresiones verificadas en navegador](regresiones-finales.json), incluida fixture de precios ausentes sin modificar el release real. Build en copia aislada de app con fuentes idénticas byte a byte.
- Inspección visual desktop y mobile, con ajustes posteriores de contraste, jerarquía, nombres cortos, tablas fijas y grillas compactas de KPIs.

| Vista | Desktop | Mobile |
| --- | --- | --- |
| Resumen | [Captura](01-resumen-desktop.jpg) | [Captura](06-resumen-mobile.jpg) |
| Producción | [Captura](02-produccion-desktop.jpg) | [Captura](07-produccion-mobile.jpg) |
| Operadores | [Captura](03-operadores-desktop.jpg) | [Captura](08-operadores-mobile.jpg) |
| Áreas | [Captura](04-areas-desktop.jpg) | [Captura](09-areas-mobile.jpg) |
| Actividad | [Captura](05-actividad-desktop.jpg) | [Captura](10-actividad-mobile.jpg) |

## Límites de verificación

La suite Playwright está preparada pero no pudo ejecutar sus 28 casos: Chromium falla al registrar un servicio Mach de macOS (`bootstrap_check_in … Permission denied`). Esto es una limitación del entorno y no 28 fallos funcionales del producto. Se realizó la inspección y los checks de UI anteriores con el navegador integrado. No afirmar aprobación de axe automatizado: esa suite quedó pendiente.

El runtime dbt local quedó bloqueado durante importación (timeout de 20 s). Se verificaron referencias de modelos y sintaxis de las 15 celdas Python de notebooks; no se afirma `dbt parse`, `dbt build`, pruebas del warehouse o nueva extracción. El rename a `fct_production_rate` requiere migración posterior controlada.

## Decisiones y límites de datos

Tres KPIs en Producción: mensual, cambio absoluto y acumulado YTD con variación comparable. Actividad: conteo único, diferencia neta y promedio físico por día calendario/pozo; no altas/bajas o eficiencia efectiva. Sin relación conjunta operador–área ni precio de gas validados: estados honestos. Preliminar sigue visible. Pipeline mensual configurado, sin automatización end-to-end ni freshness con SLA monitorizado.
