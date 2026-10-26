# 023 — Ingesta Singer candidata

Flujo: cuatro CSV oficiales → validaciones/anclajes existentes → SCHEMA/RECORD/STATE → target Blueprint batch_job → tabla BigQuery aislada por corrida. Carga directa, sin payload Parquet intermedio ni GCS.

Grano: `idpozo, anio, mes`; esquema contractual de producción más `id`, `periodo`, hash y timestamps de recuperación/procesamiento originales. Todas las columnas están declaradas; no se aceptan campos desconocidos. Replicación FULL_TABLE; corte aceptado 2023-01 a 2026-08 y validación de cuatro fuentes sin relajaciones.

Aceptación: facturación observada deshabilitada antes de escribir; proyecto/dataset/stream restringidos; tabla nueva expira en un día; worker sin errores; recibo del tap completo; hash y número de RECORD coinciden; filas de BigQuery coinciden. Sin esos gates no se confirma STATE ni se emite recibo de target completo. Una tabla parcialmente cargada no certifica datos ni habilita su publicación.

CI: discovery sin IO, contratos existentes y prueba real del protocolo/worker con mocks de fuente y cliente BigQuery. Casos negativos: billing activo, destino/modo no permitido, tabla existente, dataset ausente, EOF parcial, payload alterado, duplicación y error de load job. Sin credenciales ni consultas a Energía.

Fuera de alcance: ingesta de precios, programación remota, conectividad oficial, promoción canónica y export. No se cambia `main`, billing, IAM ni Terraform. Ver [operación](../extraction/MELTANO.md) y [ADR](../docs/adrs/0008-singer-bigquery-sandbox.md).
