# ADR 0009 — Meltano como única entrada de ingesta

Estado: implementación preparada para revisión; activación productiva bloqueada por conectividad y aceptación end-to-end.

El propietario decide retirar la extracción batch Python y operar con Meltano. `candidate-history` encadena `tap-cap4 → target-bigquery` y `tap-eia-prices → target-bigquery-prices`. Ambos taps usan el SDK Singer; conservar Python como lenguaje de los taps no conserva el antiguo pipeline independiente.

Se reutilizan contratos, anclajes físicos, parsing de precios, hashes y controles de frescura. Los comandos batch y sus escrituras BigQuery quedan retirados; el CLI downstream sólo conserva transform/export para artefactos canónicos aceptados. No se elimina código de validación del que dependen los taps y el monitor.

Los dos loaders usan el worker Blueprint fijado al mismo commit, `batch_job`, ADC/WIF, billing observado deshabilitado y tablas nuevas que expiran en un día. Los precios exigen ambos benchmarks y cobertura completa de los meses aceptados. El cierre de corrida exige dos recibos certificados del mismo ID, destinos y hashes concordantes, sin afirmar publicación o transformación.

El workflow antiguo se sustituye por verificación offline por defecto e ingesta opt-in con main, dos flags y fuente alcanzable antes de autenticar. Sin cron armado, buckets, servicios cloud nuevos, payloads/artifacts subidos ni cambios de IAM/billing. El workflow permanece deshabilitado en GitHub. No se ejecuta desde la Mac.

La certificación productiva requiere resolver acceso remoto a Energía, revisar trust WIF tras recrear el repo, validar renovación/duración de credenciales durante una carga completa, benchmark y contrato de promoción/recibos hacia dbt. No se conecta dbt a tablas nuevas silenciosamente, ni se presenta CI verde como ingesta activa. Los candidatos son temporales; no hay aún promoción canónica automática.
