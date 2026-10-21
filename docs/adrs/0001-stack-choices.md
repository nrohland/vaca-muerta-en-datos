# ADR 0001 — Stack de V1

**Estado:** implementado en el candidato integrado. Actualizado el 20 de octubre de 2026; reemplaza la elección inicial de extracción. Las versiones anteriores permanecen en Git.

## Contexto y decisión

El producto necesita declaraciones oficiales reproducibles, reglas de negocio auditables y una UI accesible sin credenciales cloud. Se eligió Python → BigQuery → dbt → snapshot agregado → Next.js/React/Recharts.

**Python:** CSV oficiales comprobados con mayor cobertura que DataStore, contratos estrictos y conciliación de rectificativas. La ruta inicial Meltano/Singer se retiró: mantener dos recorridos aumentaba complejidad y ambigüedad sin aportar cobertura al producto actual. El CLI compartido ofrece etapas, recibos y gates versionados.

**BigQuery:** almacén analítico sin administrar servidores, aislamiento por dataset y medición de bytes. Raw particionado por ingesta y con clustering; marts con clustering, sin partición histórica que expire datos en el sandbox. La elección exige presupuestos por consulta y atención a cuotas; no garantiza costo cero.

**dbt Core:** staging para normalización, intermediate para reglas reutilizadas y marts para hechos y agregados. No se fuerza una capa intermedia sin transformación útil. Tests, paquetes fijados y linaje acompañan SQL revisable. Los precios dinámicos viven en raw; los seeds reservan catálogos estables.

**Next.js y Recharts:** export estático, componentes tipados, filtros y navegación persistentes. El snapshot agregado evita credenciales en el cliente y consultas raw. El costo es generar y validar un bundle antes de promoción; el dashboard no es tiempo real.

**GitHub Actions con WIF:** CLI idéntico local/runner, identidades por etapa y sin claves permanentes. Automatización preparada y desactivada; la prueba histórica en runner real está registrada. Los calendarios de carga/monitor están pausados por conectividad de los runners con la fuente; publicar la interfaz no los activa.

## Alternativas y consecuencias

Un notebook aceleró exploración, pero la versión de producto necesita navegación, responsive y componentes compartidos. Airflow/Composer añadiría operación para una cadencia mensual; el pipeline actual no requiere ese scheduler. La separación warehouse/transformación/presentación permite revisar y probar contratos, a costa de más piezas que una app sobre CSV.

[Arquitectura](../architecture.md), [pipeline](../../pipeline/README.md) y [decisiones de UI](0003-resumen-ui.md). La interfaz está publicada como export estático en Vercel, sin funciones ni credenciales BigQuery. La actualización desatendida de datos sigue pausada; construir o desplegar la interfaz no promueve nuevos snapshots. [Configuración vigente](../vercel.md).
