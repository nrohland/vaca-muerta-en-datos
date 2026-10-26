# Pipeline candidato — Vaca Muerta en Datos

Meltano/Singer → BigQuery candidato aislado; la promoción hacia dbt/export continúa pendiente. El CLI Python de ingesta fue retirado. El workflow fue verificado en GitHub; el calendario conserva **DATA_PIPELINE_ENABLED=false** y el monitor **SOURCE_MONITOR_ENABLED=false** por conectividad con la fuente. La demo pública en Vercel se despliega por separado y sirve el snapshot incluido en Git. WIF sigue restringido a main, workflow y ambientes autorizados, con identidades separadas de extracción y transformación.

La extracción implementada usa **Meltano con taps Singer**, cuatro CSV oficiales de Capítulo IV (2023–2026) y HTML oficial EIA para Brent/Henry Hub. El corte aceptado es fijo: enero 2023–agosto 2026; septiembre parcial se excluye. No hay descubrimiento ni aceptación automática de meses nuevos.

## Operación vigente

Producción Capítulo IV y referencias EIA ingresan por [Meltano con tap/target Singer](../extraction/MELTANO.md). Los comandos batch anteriores están retirados; las bibliotecas Python de parsing, integridad y monitoreo se conservan como dependencias revisadas. El CLI downstream sólo permite transform/export para artefactos canónicos aceptados.

El workflow `data-pipeline.yml` contiene verificación offline y una ingesta con opt-in estricto de main y dos flags de readiness. No hay cron armado, carga habilitada ni transformación implícita. Se mantienen billing deshabilitado y las identidades existentes, sin modificar IAM. El repositorio recreado todavía necesita revisar su trust WIF antes de cualquier carga real.

Los candidatos Singer tienen nombres por corrida y TTL de un día. No reemplazan el raw canónico que lee dbt. El puente de promoción/recibos, el benchmark completo y la certificación end-to-end siguen pendientes; una prueba de plugins no equivale a producción activa. [CLI downstream](CLI.md), [ADR 0009](../docs/adrs/0009-meltano-exclusive-ingestion.md).

La fuente oficial continúa inaccesible desde los runners probados. No se configura extracción en la Mac. Los workflows de datos siguen deshabilitados en GitHub; CI de contratos y seguridad continúa activo. No se habilitan servicios pagos ni se suben .env/credenciales/payloads.
