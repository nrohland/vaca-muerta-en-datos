# ADR 0004 — Nombre de producto y referencias técnicas

- **Estado:** Adoptado por instrucción del usuario; pendiente de integración/merge.
- **Fecha:** 2026-10-11.

## Decisión

El nombre oficial es **Vaca Muerta en Datos**, en UI, copy y documentación. El identificador GitHub `vaca-muerta-pulse` permanece. Los identificadores técnicos dejan de depender de la marca: el mart de tasa usa `fct_production_rate`; análisis y notebooks usan nombres descriptivos en inglés.

## Motivo y consecuencias

El nombre explicita tema y propósito ante lectores de negocio y potenciales clientes o empleadores. Separar nombre de producto y nombres técnicos reduce acoplamiento al branding.

Se actualizan referencias activas en el árbol de archivos; no se reescribe el historial Git ni las URLs históricas de PR. Renombrar archivos/modelos en Git no demuestra que el nuevo nombre exista ya en BigQuery: crear/reconstruir relaciones y retirar las antiguas requiere una migración revisada y autorizada, separada del cambio documental. Las evidencias históricas mantienen sus resultados y fechas originales.
