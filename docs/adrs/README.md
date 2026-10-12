# Decisiones de arquitectura

Los ADRs conservan razones y contexto de cada decisión. La [arquitectura actual](../architecture.md) describe el estado implementado y sus límites.

| ADR | Decisión | Estado |
| --- | --- | --- |
| [0001](0001-stack-choices.md) | Meltano, BigQuery y dbt; Next/React/Recharts vigente | Aceptado Hito 0; kit UI ajustado por 0003 |
| [0002](0002-ui-spike-notebook.md) | Notebook para explorar portada y corregir el grano de tasa | Histórico; no es el frontend final |
| [0003](0003-resumen-ui.md) | React/Recharts y componentes comunes, snapshot verificado | Propuesto para revisión; implementación candidata |
| [0004](0004-product-name.md) | Vaca Muerta en Datos y nombres técnicos descriptivos | Adoptado por instrucción; pendiente de integración/merge |
| [0005](0005-pricing-layer.md) | Precios dinámicos y valoración en la capa de datos | Diseño definido; implementación pendiente |

Formato `NNNN-kebab-title.md`. Una nueva decisión documenta motivación, alternativas, efectos y estado real; no borra el contexto de decisiones anteriores.
