# ADR 0003 — Componentes analíticos con React y Recharts

**Estado:** implementado en V1 candidata. Resumen conserva la base aprobada.

Next.js y Recharts utilizan cards, KPIs, rankings, gráficos y filtros React reutilizados, con tokens CSS para temas y responsive. analytics-ui guía jerarquía y escalas. Las cinco pestañas mantienen petróleo azul, gas violeta, dinero ámbar y variaciones verde/rojo.

El snapshot agregado se verifica con SHA-256 y manifiestos antes de mostrar métricas. La navegación conserva contexto y ofrece deep links; ES/EN y light/dark comparten estructura. Preliminar comunica ausencia de aprobación pública, independientemente de aceptación técnica.

La elección ofrece control de layout y semántica, con mantenimiento propio de accesibilidad, tooltips y responsive. [Integración](../../specs/014-integrated-dashboard.md), [frontend](../../apps/web/README.md) y [capturas](../screenshots/README.md).
