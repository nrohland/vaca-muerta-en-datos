# Rendimiento: evidencia real

Validación del 13 de octubre de 2026 (Argentina), sobre la ingesta histórica Parquet y modelos de la rama de optimización. Los receipts privados y fuentes originales se conservan localmente; aquí sólo hay resúmenes y métricas sanitizadas.

- 3.614.213 filas: payload Parquet 77 MB; NDJSON anterior 4,54 GB. Carga batch real aceptada; schema, hashes, claves, volúmenes y cronología pasaron.
- Recorrido local: preflight sin facturación → linaje/raw/freshness → dbt → export → entrega y contrato frontend. Diez etapas aprobadas.
- 106 nodos dbt sin errores/warnings/skips. Pared del reporte 105,83 s frente a referencia anterior 176,40 s. Bytes facturables reportados 1,59 GiB frente a 2,37 GiB. **Slot-ms aumentó** de 349.821 a 554.443; paralelismo y materialización no implican menor cómputo en todas las métricas.
- Las 10.296 claves y métricas exportadas coinciden con el snapshot canónico (rel_tol 1e-9, abs_tol 1e-6). Sólo cambió `source_loaded_at`. No se promovió ese candidato ni se alteró el JSON canónico de la aplicación.
- Resumen: 248.948 bytes gzip verificados explícitamente. JS moderno inicial: 914.927 bytes antes de compresión; 268.331 bytes gzip nivel 9. Son tamaños de assets, no una medición de Web Vitals de usuarios.

El PR incorpora tests de Chromium Linux y auditoría de grafo DuckDB; la ejecución exacta se consulta en los checks del PR. Los tiempos anteriores/nuevos son una referencia, no un benchmark estadístico: precio/recovery metadata y condiciones pueden variar. Los presupuestos de bytes bloquean aceptación; tiempos son advisory. No se habilitó facturación, cron de carga ni hosting.

[Contrato de rendimiento](../../../specs/021-performance-optimization.md).
