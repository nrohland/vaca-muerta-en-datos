# 013 — Actividad productiva (Hito 3)

La vista responde cuántos pozos produjeron el fluido elegido, cómo varió ese conteo y cuánto volumen calendario produjo en promedio cada pozo productivo.

- Fuente: release aceptado, mart mensual de Capítulo IV. `positive_producing_wells` es conteo de IDs únicos con producción positiva del fluido; no sumar conteos de operadores ni áreas.
- Cambio neto: conteo actual menos conteo del mes calendario exacto anterior o del mismo mes del año anterior. Sin mes base, null. No representa altas, bajas, perforaciones ni completaciones.
- Promedio diario por pozo productivo: volumen mensual / días calendario / pozos productivos, bbl/pozo/d o m³/pozo/d. Cero pozos implica null; no es productividad por tiempo efectivo, ni compara pozos de igual edad/diseño.
- Rangos históricos compartidos. Huecos conservan null y las líneas no unen huecos. La unidad USD global persiste, pero los conteos y el promedio físico no se monetizan.
- Tres KPIs distintos; serie de conteo, cambio neto divergente, promedio físico y tabla verificable CSV. ES/EN local, tema mediante tokens compartidos y scroll contenido en móvil.
- No completaciones, nuevos pozos o actividad de perforación: falta un contrato validado para esas fuentes.
- Aceptación: transformaciones contra release real, bases exactas/ceros/gaps/fluidos, navegación y filtros globales, responsive y acceso a datos en tabla.
