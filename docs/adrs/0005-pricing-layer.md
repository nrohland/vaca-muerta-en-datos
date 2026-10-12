# ADR 0005 — Precios y valorización en la capa de datos

Estado: diseño definido; implementación y validación operativa pendientes. No altera los artefactos de la UI actual ni habilita USD de gas.

## Problema

Los volúmenes están modelados en dbt, pero el snapshot de precios llega al frontend como un artefacto independiente y la valoración principal se calcula en TypeScript. Esto fragmenta la definición de la métrica y dificulta reproducir una publicación completa desde la misma cadena de datos.

## Decisión

Ingerir Brent EIA y la referencia nacional de gas como fuentes mensuales con recurso, fecha, unidades, hash y revisiones. BigQuery conserva el raw. dbt normaliza las referencias y cruza el precio del mismo mes con los volúmenes de meses aceptados. Los marts/export entregan importes, bases, variaciones y estados de disponibilidad; el frontend presenta los resultados.

Seeds para catálogos, factores/metodologías estables y un histórico temporal explícitamente versionado. No mantener cotizaciones revisables con edición manual del seed como solución permanente. [dbt recomienda seeds para datos estáticos o que cambian poco](https://docs.getdbt.com/docs/build/seeds).

## Contratos

Precio: producto × mes × benchmark × versión. No sumar referencias alternativas ni categorías ya agregadas. Petróleo: Brent mensual USD/bbl. Gas: referencia propuesta Neuquina/TOTAL PPP USD/MMBTU de Secretaría de Energía. Confirmar cobertura y base térmica antes de habilitar valorización. Los huecos permanecen nulos; comparaciones y YTD exigen todas las bases/precios necesarios. Valor bruto de referencia no es ingreso realizado.

## Cierre operativo

Tests de unicidad/unidades/precios/cobertura, snapshot revisions, gates de freshness por fuente y por período económico, conciliación entidad-total, idempotencia de cargas y vínculo de manifiestos. Integrar marts/exportadores candidatos existentes; configurar identidad de dbt; encadenar extracción y build/tests antes del release. La promoción pública requiere aprobación separada.

## Estado actual verificable

El browser consume precios desde un snapshot local verificado y no hace llamadas a EIA. La lógica de valoración de esta entrega todavía vive en TypeScript. No se ha ejecutado ni desplegado la arquitectura de precios definida por este ADR.
