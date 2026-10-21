# 011 — Operadores: ranking completo y detalle

Hito 3 autorizado. Resumen permanece sin cambios. La vista responde quién produce y cómo cambia su volumen mensual; el detalle explica la trayectoria del operador seleccionado.

## Contrato y cálculos

- Fuente única: `release.entities`, dimensión `company`, fluido y período globales. Los grupos empresariales ya preparados en el release se respetan; se conserva su procedencia legal.
- Ranking completo por volumen del período, búsquedas por nombre/ID y filtros por dirección del cambio. Filtrar nunca cambia el denominador: cuota = volumen operador / volumen de cuenca del período × 100.
- Base de comparación: mes calendario exacto −1 (mensual) o −12 (interanual), mismo operador y fluido. Ausencia no se interpreta como cero. Delta absoluto admite base cero; porcentaje requiere base positiva.
- USD = volumen petróleo × Brent mensual validado EIA para cada mes; no facturación. Gas mantiene unidades físicas y comunica falta de referencia válida. Precio ausente produce null.
- Evolución incluye meses calendario de la ventana global, dejando huecos reales. Tabla accesible ofrece valores exactos, base, variaciones y descarga CSV.
- Selección de operador controlada por el contenedor para deep links/persistencia. Selector de período, producto, idioma, tema y comparación reutilizados.
- No se deducen relaciones operador–área desde agregados marginales.

## Aceptación

Ranking sin truncamiento, búsqueda y filtros independientes del detalle; drill-down seleccionable y botón de regreso; ES/EN y responsive. Misma anatomía KPI/ChartCard/RankingItem y logos del Resumen. Colores de producto heredados; serie de USD ámbar. Pruebas: cuotas, comparadores exactos, nulos/precios, filtros y huecos históricos; navegación validada por integración.
