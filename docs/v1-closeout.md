# Cierre de V1 — 22/10/2026

V1 entrega cinco vistas funcionales de **Vaca Muerta en Datos**, con datos de enero de 2023 a agosto de 2026. La publicación del snapshot validado fue autorizada por el propietario al solicitar el cierre. Las declaraciones oficiales siguen siendo revisables; se conserva la indicación de datos preliminares y el contrato candidato. No se cambia el criterio de aceptación ni se inventa un certificado de cierre oficial.

## Validación de datos

Corrida real del 21/10/2026 desde la Mac: cuatro archivos anuales, 3.689.451 registros originales, conversión a Parquet de 74,78 MiB y precios Brent/Henry Hub cargados en BigQuery candidato. Facturación deshabilitada; no se ampliaron presupuestos ni permisos.

dbt terminó con 106 resultados aprobados, sin warnings/errores/skips: 83 tests de datos, 10 unitarios, 10 tablas, 2 vistas y 1 seed. El build tardó 84,9 s, excluida la espera previa de estimación; contabilizó 1.666.187.264 bytes frente al presupuesto de 3 GiB. Freshness, gates y export son consultas adicionales. El guard por consulta se mantuvo en 1 GiB.

El snapshot exportado contiene 44 meses, 88 filas de cuenca y 10.208 entidades. SHA-256 del release: `e6daf853a62638d93a25395aed1f937c0005c21032b2029f63024fc7afb28dbd`. Se verificaron anclajes físicos contra el snapshot anterior, sumas por operador/área, precios ligados a su carga, linaje, hashes y contrato del consumidor. Los datos físicos conservan los valores aceptados; la promoción actualiza el bundle y su procedencia real.

La descarga paralela inicial sufrió timeouts; se recuperó secuencialmente con reintentos acotados de lecturas y sin aceptar archivos parciales. Los recibos, originales y logs detallados permanecen fuera de Git, en el reporte local `outputs/local-execution-2026-10-21/README.md` de la sesión de trabajo.

## Operación aceptada para V1

- **Actualización manual desde una máquina con acceso a Energía**, usando el [CLI](../pipeline/CLI.md), ADC y dependencias fijadas. No hay scheduler instalado en la Mac; debe estar encendida y conectada durante la corrida.
- `data-pipeline.yml` y `source-monitor.yml` están deshabilitados manualmente en GitHub, con `DATA_PIPELINE_ENABLED=false` y `SOURCE_MONITOR_ENABLED=false`. No se reactivan al publicar el frontend. CI, seguridad y Dependabot permanecen activos.
- Cada actualización requiere una carpeta nueva, evidencia real de recuperación, controles de costo, dbt, conciliación y contrato frontend. Nuevas diferencias físicas detienen la exportación para revisión.
- La promoción se realiza copiando **el bundle completo** validado (release, manifiestos, precios y shards), pasando CI y revisión antes de integrar/publicar. Nunca subir raw, perfiles ADC ni credenciales.
- El sandbox de BigQuery tiene expiraciones: no es un archivo permanente. Una corrida futura vuelve a comprobar datasets, recursos y acceso; el snapshot estático incluido en Git continúa funcionando sin BigQuery.

## Limitaciones y trabajo futuro fuera de V1

**Automatización externa:** los runners probados no lograron recuperar Energía. El éxito local no resuelve ese acceso. Se cierra el incidente operativo al aceptar actualización manual; habilitar un runner externo gratuito y verificado queda fuera de V1. No se instaló Meltano ni se contrató infraestructura.

**Septiembre de 2026:** excluido. En la observación del 21/10 la cobertura nacional respecto del período de referencia fue 88,19%, por debajo del umbral del 98%; tampoco estaba establecida la ventana de estabilidad de 48 h. No se afirma una observación nueva del 22/10. La presencia de registros no implica mes completo. Incorporarlo exige una nueva observación y aceptación; el corte no avanza automáticamente.

**Chat de datos:** plan guardado para una etapa futura; no forma parte de V1.

## Repositorio e integraciones

Repositorio público: [nrohland/vaca-muerta-en-datos](https://github.com/nrohland/vaca-muerta-en-datos). El nombre anterior redirige. El ID del repositorio se mantiene; los IDs internos GCP/dbt y el prefijo de desarrollo local conservan el identificador anterior para evitar migraciones ajenas al producto.

El plan de WIF en `transform/scripts/configure_pipeline_identity.py` usa el nombre nuevo. La condición desplegada anteriormente puede seguir exigiendo el nombre viejo: antes de reactivar Actions de datos se debe revisar y actualizar **sólo** el `workflow_ref` al nombre nuevo, preservando repository ID, owner ID, rama, evento y environments. No se amplía IAM en este cierre; la ejecución local ADC no depende de ese claim. No habilitar el workflow hasta validar esa condición y la conectividad.

La API de Contributors devuelve únicamente `nrohland` en la rama principal verificada. GitHub puede conservar vistas cacheadas; esto no elimina objetos históricos de releases anteriores ni sus referencias. No se borra la release histórica ni se vuelve a reescribir el historial para forzar una actualización visual.
