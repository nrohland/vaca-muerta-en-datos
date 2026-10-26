# Contratos y alcance de V1

Estas especificaciones documentan preguntas, granos, semántica y aceptación. El README raíz resume el estado integrado; un resultado de una iteración anterior no equivale a aceptación pública.

| Contrato | Alcance |
| --- | --- |
| [Modelo de datos](001-vaca-muerta-pulse/data-model.md) | Granos y definiciones de origen; los contratos históricos y de export precisan la implementación vigente |
| [Producción](010-production-drilldown.md) | Historia, comparaciones, KPIs y tabla |
| [Operadores](011-operators.md) | Ranking y detalle |
| [Áreas](012-areas.md) | Ranking y detalle, límites de relaciones |
| [Actividad](013-activity.md) | Pozos productivos y dinámica respaldada |
| [Integración](014-integrated-dashboard.md) | Componentes, navegación y revisión común |
| [Gates](015-dev-pipeline-gates.md) | Base de controles; el CLI histórico amplía el recorrido |
| [Precios](016-candidate-pricing.md) | Cotizaciones dinámicas y valorización |
| [Gas internacional](017-international-gas-reference.md) | Henry Hub y supuesto energético |
| [Export histórico](018-historical-dashboard-export.md) | Contrato frontend y conciliación |
| [Monitor](020-source-monitor.md) | Disponibilidad, estabilidad, rectificativas y avisos |
| [Fuente histórica](019-historical-source-candidate.md) | Cuatro CSV, revisiones y corte aceptado |

Los planes de hitos, checklists antiguos y specs de iteraciones visuales superadas se retiraron del árbol actual y permanecen en Git. Antes de cambiar una regla, actualizar su contrato y pruebas. No inventar definiciones para fuentes ausentes.

- [021 · Rendimiento y operación sin facturación](021-performance-optimization.md)

- [023 · Ingesta Singer candidata](023-singer-ingestion.md)
