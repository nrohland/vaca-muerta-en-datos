# Revisión de arquitectura y datos antes de compartir

Fecha: 20/10/2026. Alcance: código y documentación del candidato, artefactos versionados y tests offline. No se ejecutaron extracción, consultas BigQuery, nuevos builds dbt cloud ni servicios pagos. Esta revisión no certifica actualización de la fuente.

## Estado y decisiones

La demo pública sirve HTML/JS y agregados desde Vercel; no hay API de consultas, funciones de warehouse o credenciales BigQuery en el runtime de la app. Los filtros operan sobre el snapshot público y validado. La interfaz está publicada, mientras los datos conservan estado **preliminar** con corte aceptado enero de 2023–agosto de 2026. Septiembre parcial está excluido.

La extracción y el monitor permanecen pausados por conectividad de los runners con Energía. La prueba histórica de WIF/pipeline no demuestra que hoy funcione esa conexión. El despliegue frontend y la promoción de un snapshot son operaciones diferentes. Se corrigieron referencias antiguas a hosting pendiente y runner sin validar en arquitectura y ADRs.

| Elección | Revisión y compromiso |
| --- | --- |
| Python → Parquet | El source CSV se conserva como referencia con hashes; Parquet tipado/Zstandard reduce el payload de ingesta. No hace falta convertir los pequeños precios por uniformidad. |
| BigQuery aislado | Permisos separados y límite por query. No depende de este servicio la disponibilidad de una visita al dashboard. |
| Raw particionado por ingesta | Conservar historia en el sandbox sin particiones históricas que expiren al construirlas. No permite asumir pruning por mes de producción. |
| Clustering selectivo | Declarado en hechos pozo/operador/área y dimensiones. Los marts de publicación/valorización no declaran clustering; añadirlo sin benchmark no demuestra mejora. |
| Staging candidato como tabla | Deduplicación/filtro se materializan una vez para varios tests y consumidores; dev/prod mantienen sus configuraciones. |
| Intermediate como vista | Regla reutilizable, no una capa obligatoria para cada fuente. Precios puede alimentar directamente el hecho de valorización. |
| dbt con cuatro threads | El DAG programa nodos independientes; no se lanzan escrituras simultáneas de builds sobre las mismas tablas. Más concurrencia no garantiza menos slot-ms. |
| Export estático por vista | El browser descarga overview y detalles completos cuando los necesita; no consulta raw ni reconstruye importes USD. |

## Queries lentas y N+1

No se encontró un patrón N+1 de consultas warehouse por operador, área o filtro. `pipeline/export_dashboard.py` hace **dos queries de datos por export**: lectura del mart completo y lectura de precios vinculados. El número de queries de esos datos no crece con las 28 compañías o 88 áreas. Los gates de linaje, presupuesto, freshness y transformación ejecutan jobs separados, por lo que no corresponde decir que el pipeline entero sólo hace dos queries.

Los modelos agregan con operaciones de conjunto, ventanas y joins de claves; no hay un bucle Python que consulte por cada entidad. `prepare()` repite recorridos sobre los agregados para conciliación; es CPU offline sobre aproximadamente diez mil filas, no N+1 de red. No se modificó sin una medición que lo justifique.

La evidencia real disponible es la [corrida del 13/10](../performance-optimization/README.md), no una nueva medición del 20/10:

| Nodo | Pared (s) | Bytes facturables reportados | Slot-ms |
| --- | ---: | ---: | ---: |
| `stg_produccion_pozo_mes` | 6,16 | 821.035.008 | 6.888 |
| `fct_reference_valuation_entity_month` | 17,10 | 36.700.160 | 20.135 |
| `fct_dashboard_month` | 10,24 | 31.457.280 | 401.272 |
| Build completo, 106 nodos | 105,83 | 1.708.130.304 | 554.443 |

`fct_reference_valuation_entity_month` tiene la mayor pared de modelos; `fct_dashboard_month` concentra aproximadamente 72% de slot-ms reportados. Staging explica aproximadamente 48% de bytes facturables, aunque su pared es menor. Optimizar sólo el nodo más lento no necesariamente reduce el recurso dominante.

Hay agregaciones por entidad en el mart de valorización y en el mart de publicación. No son reemplazables automáticamente: uno mantiene IDs legales y el otro aplica agrupamiento comercial y grilla completa. Antes de compartir una base agregada o cambiar CTEs/materializaciones se requiere comprobar cardinalidad, faltantes, agrupamiento, bases exactas y YTD con el mismo input. La relectura/reutilización física de CTEs sólo se confirma con plan de ejecución; no se atribuyen scans repetidos a partir del SQL solamente. No se cambiaron cálculos ni se eliminaron tests para mejorar una cifra.

## Presupuestos y límites de interpretación

- El límite de ejecución es 1 GiB por query; el presupuesto de 3 GiB dbt se evalúa **después** del build para aceptar el candidato. No equivale a un límite preventivo total de toda la corrida; freshness, gates y export son independientes.
- El preflight verifica facturación desactivada, almacenamiento accesible y consumo visible antes de warehouse. La falta de permisos o métricas no se interpreta como cero consumo.
- La comparación histórica 176,40 → 105,83 s y 2,37 → 1,59 GiB es orientativa; slot-ms subió de 349.821 a 554.443. Una corrida por variante no es benchmark estadístico.
- CREATE VIEW con cero bytes no prueba costo nulo al consumirla. NULL en métricas permanece desconocido.
- Nombres de assets con hash y cache en memoria no prueban headers HTTP de producción. La revisión frontend verifica requests y caching del host por separado.
- No se acredita una mejora nueva en tiempos BigQuery en esta revisión: no se ejecutó cloud para evitar uso innecesario de cuotas y no confundir una corrida con datos obsoletos con validación real de ingesta.

## Comprobaciones offline ejecutadas

Comando ejecutado desde la raíz:

```sh
python3 -m unittest \
  pipeline.tests.test_dbt_performance \
  pipeline.tests.test_resource_budget \
  pipeline.tests.test_export_dashboard \
  pipeline.tests.test_run_candidate \
  pipeline.tests.test_dbt_lineage
```

Resultado: **52 tests aprobados**. Cubren preservación de NULL y tiempos de nodos paralelos, presupuesto de recursos, aislamiento del recorrido con comandos simulados, conciliaciones y binding de export, y linaje sanitizado. Los mensajes de fallo del stage runner son casos negativos esperados, sin acceso a GCP.

Una invocación inicial incluyó también `test_dbt_isolation`, que no pudo importarse por ausencia de `jinja2` en el Python del sistema. No es un fallo de una consulta ni del pipeline: ese módulo no se acredita como ejecutado en este entorno. No se instalaron dependencias ni se corrió dbt como sustituto de esa verificación. Los 52 tests anteriores se ejecutaron de nuevo sin ese módulo y pasaron.

Se comprobaron enlaces relativos de los documentos modificados y `git diff --check`. La auditoría de grafo existente con dbt_project_evaluator conserva tres advisories (ubicación de fuentes/modelos y fanout deliberado del hecho compartido); no se afirma que esta revisión los haya eliminado ni vuelto a ejecutar.
