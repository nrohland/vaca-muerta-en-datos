# CLI compartido del candidato

El rango actual es explícito: **enero 2023–agosto 2026** con `--history`. Extracción y transformación usan identidades separadas en GitHub. Los directorios de ejecución deben ser nuevos; una falla bloquea etapas posteriores y conserva su evidencia.

## Preparación pública y carga separada

En GitHub se instalan dependencias y preparan las fuentes antes de autenticar:

```bash
python pipeline/run_candidate.py prepare --history \
  --run-dir /tmp/vm-prepare --scratch-dir /tmp/vm-source-files
# Autenticación WIF/ADC con la identidad de extracción.
python pipeline/run_candidate.py load --history \
  --prepared-artifact /tmp/vm-prepare \
  --run-dir /tmp/vm-extract --scratch-dir /tmp/vm-source-files
```

`prepare` descarga/revisa cuatro CSV oficiales y ambos HTML EIA, conserva hashes y retrieval reales y deja payloads en scratch. `load` exige un prepare completo aprobado; valida payloads, carga tablas candidatas y ejecuta gates de raw y linaje. Scratch es el mismo, privado al job; no se transfiere ni se sube.

Localmente, con ADC disponible, ambas partes pueden encadenarse:

```bash
python pipeline/run_candidate.py extract --history --run-dir /tmp/vm-extract
```

`--source-inbound` permite reutilizar CSV oficiales retenidos con sus metadatos originales, sujetos a frescura; no rejuvenece la recuperación. No se cambia IAM ni se envían credenciales al portal de datos o a EIA.

## Transformar, exportar y validar el consumidor

```bash
python pipeline/run_candidate.py transform --history \
  --extract-artifact /tmp/vm-extract --run-dir /tmp/vm-transform
```

Diez etapas: resource-preflight → artifact-check → raw-revalidate → loaded-revalidate → dbt-source-freshness → dbt-parse → dbt-compile → dbt-build → dashboard-export → snapshot-check.

Metadata requerida: source-evidence, source-manifest, source-load, price-manifest y price-load. Cada JSON prueba fuente/destino/hash/fechas/corte de su carga. dbt usa el target candidato, pricing habilitado, presupuesto de 1 GiB por consulta y selección explícita de producción, dimensiones, valorización y `+fct_dashboard_month`. Freshness exige ambas fuentes PASS; build no admite errores, warnings ni skips.

El export exige que el summary dbt pertenezca a esos hashes, verifica los anclajes físicos del snapshot revisado y concilia sumas de operador/área a cuenca. Cotizaciones se leen de la carga candidata y su NDJSON canónico debe reproducir exactamente el hash del manifest; cada precio del mart debe coincidir con esa referencia mensual. No se multiplica precio por volumen en Python o frontend.

Resultado en `run-dir/dashboard`: release.json, manifest.json, prices.json, valuation-manifest.json y recibo. El checker Node usa `validateRelease`, `validateManifest`, `validatePair`, `validatePrices` y SHA de producción/cotizaciones. Se escribe un bundle nuevo, sin reemplazar assets del repo, aprobación ni publicación.

## Reexportar una transformación ya aceptada

```bash
python pipeline/run_candidate.py export --history \
  --extract-artifact /tmp/vm-extract \
  --transform-artifact /tmp/vm-transform-aceptado \
  --run-dir /tmp/vm-export
```

Ejecuta artifact-check, dashboard-export y snapshot-check, reusando explícitamente el dbt-summary aceptado. No descarga/carga ni repite dbt; sigue verificando entradas actuales y leyendo el warehouse. Si los hashes no coinciden, se detiene. Este modo no demuestra un nuevo build.

Las dos correcciones de la migración inicial son opcionales únicamente para ese baseline histórico: `export_dashboard.py --revision ... --assignment-revision ...`, ambas ligadas a sus hashes. El flujo normal usa el snapshot dbt ya revisado y no las reaplica. Diferencias físicas nuevas siguen bloqueando.

## Workflow y alcance

GitHub encadena prepare público → auth extracción → load → auth dbt → transform/export/check → typecheck/tests/build frontend. Node/Python/dbt se instalan antes de autenticar. Sólo metadata sanitizada `run-dir/*.json` se conserva siete días. No subir payloads, perfiles, HTML, tokens, logs dbt, manifest completo ni build/dashboard; el workflow no despliega ni hace push.

`--python`, `--dbt-bin`, `--node` y `--dbt-project-dir` seleccionan ejecutables/copia de proyecto revisados, no comandos shell. `all --history` une extract y transform/export/check localmente con una identidad que tenga permisos para ambas capas; GitHub mantiene identidades distintas. Sin `--history` permanece la ruta candidata anual anterior, sin dashboard histórico.

El calendario preparado (día 5, 03:00 Argentina) no prueba fecha de publicación de la fuente. **DATA_PIPELINE_ENABLED=false**, runner real validado y promoción de snapshots sólo con aceptación. El mes máximo raw nunca reemplaza automáticamente el corte completo. [Evidencia actual](../docs/evidence/orchestration-export/README.md), [acceso WIF](../docs/evidence/pipeline-access/README.md) y [calidad/performance dbt](../transform/docs/quality-and-performance.md).

Para disponibilidad de meses nuevos y revisiones históricas: [monitor independiente](MONITOR.md). Se ejecuta antes de aceptar/promover nuevos datos y también luego de finalizar la ingesta.

El histórico prepara `history.raw.parquet` con esquema explícito y Zstandard. `resource-preflight` precede las cargas y transformaciones; requiere lectura de estado de billing desactivado. El perfil generado usa 4 threads; dbt paraleliza nodos independientes automáticamente. Instalar también `extraction/requirements.txt` localmente. Los presupuestos de rendimiento se documentan en `specs/021-performance-optimization.md`.
