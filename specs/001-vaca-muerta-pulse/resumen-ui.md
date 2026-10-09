# Resumen — iteración autorizada 2026-10-09

Esta entrega de Hito 3 implementa únicamente Resumen en `apps/web`, por instrucción explícita del usuario. Sustituye para esta iteración el contador editorial/live de R6 por la tasa mensual diaria equivalente. No cierra todo Hito 3.

Base: frontend local del 6 de octubre, no publicado en GitHub; se conservan sin cambios `lib/contract.ts`, `lib/operators.ts`, release y manifiesto. El snapshot candidato depende de los marts/export de los PRs #27, #29 y #31 y sigue marcado Preliminar. No hay consultas a raw ni cambios en extracción, dbt o harness.

## Componentes y aceptación

- KPI Card base: principal (doble ancho) y secundaria; etiqueta, valor, unidad, contexto y estado semántico. Por corrección explícita del usuario, las variaciones positivas se muestran verdes y las negativas rojas; cero/sin comparador permanecen neutrales.
- Chart Card: estructura común de encabezado, controles, contenido y acción; evolución a todo el ancho, 12/24/36 meses según cobertura, tooltip y tabla accesible; huecos nunca son cero.
- Ranking Card: Top 5 operadores con producción mensual, participación y YoY de volumen; Top 5 áreas con producción mensual y YoY de volumen. Barras sobre cuota del total, escala real 0–100%; no normalizar al líder.
- Global Filters: petróleo/gas y mes aceptado; URL y atrás/adelante preservan selección entre destinos.
- Navegación preparada: Resumen → Producción/Operadores/Áreas/Actividad → entidad. Destinos previstos muestran aviso Próximamente; no se implementan drill-downs, mapa ni detalle.
- Desktop sin scroll en overview cerrado (1440×900 y 1366×768): tasa diaria con YoY/MoM dentro de la misma card, pozos productivos, volumen mensual y cuota del Top 5 de operadores. Los dos KPIs adicionales provienen de columnas existentes del snapshot. Logos oficiales recuperados de la entrega local; nombres cortos de presentación por ID con nombre fuente en tooltip. Mobile conserva apilado y scroll para legibilidad. Expandir tabla permite scroll deliberadamente. Modo oscuro.
- Validación: contrato y hash, filtros, navegación/history, meses sin comparador, estados de error, accesibilidad y capturas desktop/mobile.

## Límites

Solo revisión en rama/PR. Sin merge, deploy o promoción de datos. Fuente, cálculos, IDs y agrupación de operadores permanecen en contratos/agregados. Área significa permiso o concesión. No incluye completaciones ni causalidad.
