# Decisiones de arquitectura

Los ADRs explican elecciones y compromisos del candidato vigente. El historial Git conserva las decisiones iniciales y sus cambios; [arquitectura](../architecture.md) describe la implementación actual.

| ADR | Decisión | Estado |
| --- | --- | --- |
| [0001](0001-stack-choices.md) | Python, BigQuery, dbt y Next.js/Recharts | Implementado; elección inicial de extracción reemplazada |
| [0003](0003-resumen-ui.md) | Componentes comunes y snapshot verificado | Implementado en V1 candidata |
| [0004](0004-product-name.md) | Vaca Muerta en Datos | Adoptado |
| [0005](0005-pricing-layer.md) | Precios dinámicos y valorización en dbt | Implementado con Brent y Henry Hub |
| [0006](0006-candidate-pipeline.md) | CSV oficial, aislamiento y gates | Validación histórica local/runner; calendarios pausados por conectividad |

Cambios de fuente, grano, métricas o arquitectura deben actualizar la decisión y su contrato. El ADR 0002 y el prototipo notebook se retiraron del árbol vigente.

- [0007 — Meltano local y Terraform sin facturación](0007-local-meltano-no-billing.md).

- [0008 — Singer y BigQuery Sandbox](0008-singer-bigquery-sandbox.md).
