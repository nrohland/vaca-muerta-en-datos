# ADR 0007 — Meltano local y Terraform sin facturación

Estado: implementación local de la integración; ejecución cloud y programación no habilitadas.

## Restricción y decisión

La facturación de GCP permanece deshabilitada por instrucción del propietario. No se crean Cloud Run, Scheduler, GCS, NAT, VMs ni cuentas de facturación. El sandbox BigQuery y sus preflights existentes se conservan; la renovación del dashboard no depende de que sus tablas persistan indefinidamente.

Meltano 4.4.1 ejecuta el CLI revisado como utilities: prepare → load → transform/export/check. Reutiliza CSV oficiales → Parquet y mantiene cortes, anclajes, hashes, identidades y presupuestos. Esta etapa no convierte el extractor en Singer ni vuelve a CKAN DataStore. Un tap propio futuro necesita una decisión y benchmark de batch antes de sustituir el flujo vigente.

La ejecución requiere una máquina existente con acceso a Energía, Python 3.12 y Node. Un lock local impide que corridas solapadas escriban los datasets candidatos. La máquina debe permanecer encendida y conectada. No se afirma autonomía permanente ni disponibilidad de la fuente.

Terraform es optativo y usa estado local respaldado. Por defecto no administra ningún dataset. La adopción de los cuatro datasets existentes exige importarlos antes de planificar cambios; preserve ACLs/expiraciones y prevent_destroy. No administra billing ni habilita APIs. No se ejecuta apply en esta entrega.

## Separación de responsabilidades

- Meltano configura/ejecuta; los scripts siguen validando y conservando evidencia.
- El preflight existente verifica billing deshabilitado antes de warehouse; ausencia de permiso bloquea.
- CI frontend usa sólo snapshots; ninguna consulta al gobierno en un PR/build.
- El nuevo instalador sustituye el bundle completo y conserva last-good si falla el swap; no arrastra aprobaciones anteriores.
- Nuevos meses y revisiones conservan revisión explícita. No se aprueban por incrementar cutoff o actualizar hashes.
- No se cambia el historial Git, no se instalan schedulers y no se promueven/despliegan datos automáticamente.

## Operación

Ver [Meltano local](../../extraction/MELTANO.md) y [Terraform](../../infra/terraform/README.md). Este ADR extiende la ejecución del ADR 0006; sus contratos y restricciones permanecen vigentes.
