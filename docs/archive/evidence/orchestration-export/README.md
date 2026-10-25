# Orquestación, export y consumidor — 13 de octubre de 2026

**Integración local validada, workflow desactivado.** Un mismo run ejecutó nueve etapas: revalidación de inputs/raw/linaje, freshness, parse, compile, build, export y contrato frontend. Luego el bundle generado se consumió en una copia aislada de la aplicación para typecheck, tests y build estático.

## Resultados reales

- **dbt: 106/106 nodos aprobados en una sola corrida limpia**, 0 warn/error/skip. 9 tablas, 3 vistas, 1 seed, 83 tests de datos y 10 unit tests. Duración del build: 274,47 s. Esta corrida complementa y supera la validación anterior por build + reparación; no borra esa evidencia.
- **64 tests pipeline aprobados**, incluidos corte ante fallo de build/export, revisión de baseline, hash de cotizaciones, tipos fecha, aislamiento, secuencia/identidades/artifacts del workflow y sanitización del linaje.
- **59 tests frontend aprobados**, typecheck y build correctos sobre el bundle generado por este recorrido, en `/private/tmp/vm-orchestrated-web` aislado.
- Export: 44 meses, 88 filas de cuenca y 10.208 de entidades. Cotizaciones se reconstruyen desde las mismas 828 filas cargadas y reproducen su digest canónico. Cada quote del mart coincide con su precio mensual.
- Paridad contra el snapshot revisado: mismos 10.296 granos y conteos, producción y USD dentro de tolerancia de coma flotante. Diferencia máxima USD mensual ~0,0000011, inferior a un centavo; no cambia precisión mostrada. Se conserva el snapshot del repo para evitar una promoción implícita.
- Nuevo linaje dbt real: 12 modelos, 2 fuentes, 1 seed y 15 dependencias; sólo nombres/relaciones sanitizados, sin conexiones ni manifest completo.

## Qué quedó integrado

El CLI histórico ejecuta export y checker Node después del build. Existe modo `export` para reutilizar explícitamente un summary aceptado; no se presenta como nuevo build. El baseline actual ya incorpora las revisiones históricas y no las reaplica; las correcciones explícitas siguen disponibles para la migración original. Nuevas diferencias físicas siguen bloqueando.

El export compara precios contra el NDJSON canónico del artifact, escribe release/manifiestos/cotizaciones en staging temporal y mueve el bundle completo al finalizar. Node ejecuta los contratos reales del consumidor y sus hashes. Los assets del repo y la aprobación no se modifican.

GitHub prepara fuentes públicas antes de WIF, instala dependencias antes de auth, usa identidades separadas y ejecuta gates/test/build del frontend. Restricción main explícita, permisos contents:read y uploads sólo de JSON reducidos. No hay token permanente, ampliación IAM, upload del dashboard/build/raw, push o deploy. El archivo ADC oficial conserva la ruta de renovación de credenciales; su operación real se debe verificar en GitHub.

## Fallos encontrados y límites

El primer ensayo de export falló por comparar fechas DATE de BigQuery con claves string sin normalización. El segundo export pasó pero el contrato frontend rechazó la escritura de la unidad de gas (USD/MMBTU frente a USD/MMBtu). Se normalizaron fecha y unidad de presentación y se añadieron regresiones. El run integrado final pasó completo. Los dos ensayos fallidos permanecen en outputs, sin reescribir sus estados.

Se reutilizó la carga fuente/precios histórica aceptada y fresca. **No se volvió a descargar o cargar raw** en este recorrido; las nuevas fases prepare/load se probaron con tests del plan/gates/workflow y usan los helpers de carga previamente verificados. No afirmar una corrida nueva desde descarga inicial ni una ejecución real de GitHub/WIF.

DATA_PIPELINE_ENABLED=false. Main, cron y despliegue no se modificaron. Falta ejecutar el workflow desde un runner real después de una promoción autorizada; no se ensancha WIF a esta rama para simularlo. Playwright/axe siguen bloqueados por procesos Chromium macOS, como se documentó en la [revisión visual](../snapshot-integration/README.md); no se repitió una prueba de navegador automatizada.

## Evidencia

[Run de nueve etapas](run.json), [summary dbt](dbt-summary.json), [freshness](freshness.json), [rendimiento real](performance.json), [recibo export](export-receipt.json), [contrato frontend](snapshot-check.json), [paridad](snapshot-parity.json). [CLI](../../../../pipeline/CLI.md), [arquitectura](../../../architecture.md), [linaje dbt](../../../lineage/README.md). Los logs locales y bundle quedan en outputs; aquí se conserva metadata revisable, sin registros raw ni credenciales.
