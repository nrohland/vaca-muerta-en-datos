# ADR 0003 — Resumen modular con React y Recharts

Estado: propuesto para revisión. Fecha: 2026-10-09.

El usuario autoriza llevar el frontend local al repositorio y rediseñar únicamente Resumen con analytics-ui. Conservamos Next.js y la biblioteca Recharts del frontend local, con cards reutilizables en lugar de incorporar Tremor ahora. Este ADR acota la excepción al stack UI del ADR 0001. No cambia ingesta, warehouse, dbt ni fórmulas.

La skill adjunta define estructura independiente del tema. El primer nivel muestra tasa actual, variaciones, pozos, evolución y rankings; las vistas profundas quedan pendientes. Los agregados cacheados del export candidato se verifican con SHA-256 y manifiesto antes de mostrarse. Se conserva la señal Preliminar y la validación del sidecar de aprobación.

Consecuencia: el PR introduce la base funcional local necesaria para revisar Resumen; no incorpora la implementación local de mapas u operadores. Hito 3 permanece abierto. Spec: ../../specs/001-vaca-muerta-pulse/resumen-ui.md.
