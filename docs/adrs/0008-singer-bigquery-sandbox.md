# ADR 0008 — Singer con BigQuery directo y facturación deshabilitada

Estado: implementación candidata; sin ejecución real cloud ni programación remota habilitada. Sustituye la integración utilities del ADR 0007.

El propietario exige Meltano con tap/target auténticos, target BigQuery directo, cero cargos y extracción remota. Se implementa `tap-cap4` con singer-sdk y el target de Blueprint fijado al commit `caad808faf94102067a1da42bcfced26845b5b42`. `batch_job` carga NDJSON comprimido mediante `load_table_from_file`; evita GCS y las interfaces de streaming que Sandbox no admite.

La política propia verifica billing deshabilitado y un dataset existente antes de crear un sink. Una subclase conserva los metadatos de origen, crea una tabla aislada nueva con expiración de un día y rechaza campos desconocidos. El transporte/worker sigue siendo Blueprint. No hay DML, creación de datasets, sobrescritura ni promoción implícita. No se promete disponibilidad ilimitada: cuotas gratuitas y permisos insuficientes bloquean. El preflight observa billing; no impide que otro administrador lo active después.

El tap reutiliza validación CSV y anclajes de la ruta histórica. FULL_TABLE contempla rectificativas. El target difiere STATE hasta comprobar recibo completo del tap, hash de registros, terminación de workers y conteo en BigQuery. Un retry ambiguo puede duplicar filas en el candidato, pero la conciliación bloquea su certificación. No se usa append contra el raw canónico.

No se programa extracción en la Mac. Los runners remotos probados todavía no acceden a Energía; no se confunde el cambio de herramienta con resolver esa restricción. El corte histórico sigue fijo y las referencias EIA/dbt/export no forman parte de este job. CI prueba protocolo y errores con IO simulado; falta benchmark de CSV completos y primera carga remota autorizada.

Operación: [Meltano Singer](../../extraction/MELTANO.md). Contrato: [spec 023](../../specs/023-singer-ingestion.md). No cambia el contrato del dashboard.
