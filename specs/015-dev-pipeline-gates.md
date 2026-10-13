# Gates del pipeline candidato

El [CLI](../pipeline/CLI.md) comparte `StageRunner` entre local y GitHub. Las fases `prepare`, `load`, `extract`, `transform`, `export` y `all` tienen recibos; una falla corta las siguientes etapas. `--history` fija enero 2023–agosto 2026.

## Controles

1. Fuentes: esquema, SHA-256, fechas reales, grano y cobertura conciliada. CSV oficiales y referencias EIA dinámicas; sin aceptación automática del mayor mes.
2. Carga: destinos exactos candidatos, identidad por fila y recibos. Rechazar destinos compartidos antes de acceso cloud.
3. Raw/linaje: hashes/corte/conteos y procedencia de fuentes y cotizaciones cargadas, antes de transformación.
4. Freshness: recuperación/ingesta máximo siete días; warning dbt desde cinco días también bloquea. Mes económico y completitud son controles distintos.
5. dbt: parse, compile y build; error, warning o skip impiden aceptación. Datos, claves, conversiones y comparaciones calendario probados.
6. Export: anclajes físicos, sumas entidad/cuenca, unidades y cotizaciones del mismo raw. USD mensual/diario/bases/YTD persistidos; faltantes NULL, sin relleno.
7. Consumidor: contrato y hashes de cuatro assets, typecheck/tests/build en checkout temporal. Sin promoción del snapshot del repo.

Anomalía microscópica fuera de VM en `[-1e-12, 0)` preservada y advertida; cualquier negativo en VM no convencional falla. Nuevas diferencias de volumen, clasificación o área requieren conciliación explícita.

Precios: producto × mes único, benchmark/unidad/currency válidos, precio finito positivo, hashes y corte consistentes. Gas Henry Hub con [escenario energético](017-international-gas-reference.md), sin inventar calorificidad local. Porcentaje base cero → NULL; YTD requiere calendario/precios completos.

## Acceso y aceptación

WIF con identidades por etapa, main/workflow/ambientes restringidos y sin claves nuevas. `DATA_PIPELINE_ENABLED=false`; cron preparado día 5 a las 03:00 Argentina. No publica, despliega, hace push ni reemplaza datasets compartidos.

[Último recorrido integrado](../docs/evidence/orchestration-export/README.md): nueve etapas, 106 nodos dbt en una corrida limpia y consumidor validado. Reutilizó raw fresco aceptado, sin nueva ingesta. Runner GitHub pendiente tras promoción autorizada. [Contrato fuente histórica](019-historical-source-candidate.md), [export](018-historical-dashboard-export.md).
