# Export histórico y conexión del frontend — 13 de octubre de 2026

**Etapa local cerrada con aceptación técnica; sin aprobación de publicación.** El frontend consume `fct_dashboard_month`, con 44 meses enero 2023–agosto 2026, 88 filas de cuenca y 10.208 de entidades. USD mensual/diario/YTD procede de dbt; la UI no vuelve a multiplicar volumen por precio.

## Verificación real

| Verificación | Resultado |
| --- | --- |
| Export y linaje de fuentes/precios | PASS; recibo con jobs, hashes y bytes reales |
| Anclajes físicos y sumatorias cuenca–operadores–áreas | PASS, con revisiones de fuente explícitas |
| Tests frontend | 59 aprobados, 0 fallos |
| Tests exportador | 17 aprobados, 0 fallos |
| Typecheck / build estático | PASS / PASS |
| Descarga CSV gas/USD | 44 meses; comparación exacta con snapshot PASS |
| Revisión navegador integrado | Cinco pestañas, ES/EN, claro/oscuro, filtros, detalles, recarga y atrás |
| Responsive | Sin overflow del documento en 320, 390 y 768 px en las cinco pestañas; desktop inspeccionado a 1440 px |
| Playwright / axe actual | Chromium bloqueado por permisos de procesos de macOS; 28 casos **no ejecutados** |

La primera ejecución unitaria fue 57/59: se corrigieron dos fixtures, sin cambiar métricas, porque el mart ya trae YTD persistido y un top de contribuciones puede no contener negativos. El resultado final es 59/59. La revisión visual y DOM del navegador integrado no se presenta como ejecución de Playwright o axe.

## Revisiones y reparación

- La fuente reclasifica el pozo 164323 (PAL/APO) como no convencional en 24 meses 2024–2025. Se incorporan esas membresías sin modificar sus volúmenes individuales.
- La fuente revisa IDs de área de 96 registros mensuales de 2025: AVI→AVN, MBE→MBE1 y LTAC→LTI/LTII. La comparación read-only confirma que operador y volúmenes individuales no cambian. Totales de cuenca y operador se conservan; cambia la distribución por área.
- La revisión visual detectó que “Áreas reportadas” contaba todo el catálogo histórico: se corrigió de 88 a **82 áreas con registros de agosto**. El ranking mantiene las 88 identidades históricas y los ceros explícitos del mart.
- El primer export quedó bloqueado ante diferencias no explicadas de áreas; se incorporó evidencia acotada. Un intento posterior con un factor petrolero más preciso dejó residuos al restar cerca de cero: se utilizó la conversión contractual exacta 6,28981077, sin relajar tolerancias. El export final pasó.

## Evidencia y límites

[Resumen verificable](qa-summary.json), [recibo del export](export-receipt.json), [reclasificación](reviewed-revision.json), [revisión de áreas](assignment-revision.json), [validación CSV](csv-validation.json). Fuente y dbt previamente validados: [histórico](../historical-dbt/README.md).

El snapshot agregado pesa 17.563.319 bytes (16,75 MiB), sin raw ni credenciales. La prueba de linaje lee sólo agregados raw; el payload de producto sale exclusivamente del mart. Respaldo anterior y capturas están conservados en la carpeta local de outputs. La galería local reúne desktop y mobile de las cinco pestañas.

El export es una migración histórica explícita con anclajes y revisiones ligadas a hashes, todavía no una etapa automática de `run_candidate.py`. Falta coordinación del export en el workflow y prueba desde un runner real de GitHub. Cron desactivado, sin merge a main, push, PR nuevo, despliegue ni publicación. No se infieren relaciones operador–área, entradas/salidas de pozos o completaciones desde agregados. Henry Hub es referencia internacional con escenario energético EIA; no calorificidad medida ni ingresos realizados.
