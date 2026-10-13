# Monitor de disponibilidad y rectificativas

## Objetivo

Avisar al propietario del repo cuando aparezca un nuevo mes, alcance condiciones para revisar su cobertura, cambien meses aceptados o se revisen referencias de precio. No cargar BigQuery, aceptar períodos ni publicar snapshots desde el monitor.

## Evidencia y grano

CSV oficiales anuales 2023–2026, contrato de extracción vigente y EIA Brent/Henry Hub mensual. Cada período conserva conteos nacionales/VM, pozos productivos por fluido, volúmenes VM y fingerprints de contenido. SQLite temporal ordena hashes de filas y obtiene pozos únicos con memoria acotada. No se conservan filas ni IDs de pozos en estado/artifacts.

Fingerprint semántico, independiente del orden de filas y representación numérica equivalente. Excluye `fecha_data`, `idusuario` y el `id` sustituto opcional: cambios de metadatos de recuperación no son rectificativas productivas. Incluye clasificación, operador, área, producción y demás atributos oficiales. Reasignaciones se detectan aunque los totales coincidan. Negativos fuera de VM no convencional se preservan y cuentan, como en el contrato histórico; cualquier negativo en el producto falla.

La línea base durable concilia las 88 filas físicas del snapshot revisado. Estado observado y referencia aceptada son conceptos distintos: observar una rectificativa no cambia los perfiles usados como referencia aceptada. Cambiar el corte requiere actualizar snapshot/contrato/línea base con revisión.

## Señal «listo para revisión»

- Mes transcurrido en Argentina; recuperación no futura y ≤36 horas.
- Sin duplicados de pozo × mes, campos inválidos ni valores no finitos.
- Registros nacionales, VM y pozos positivos de ambos fluidos ≥98% de la mediana de los tres meses aceptados anteriores.
- Volumen físico entre 0,5 y 2 veces esa mediana; extremos requieren revisión aunque sean reales.
- Dos recuperaciones distintas sin cambio semántico durante ≥48 horas. Reusar un archivo retenido no aumenta observaciones ni renueva su fecha.
- Brent y Henry Hub mensuales disponibles, sin sustitutos ni relleno.

Estos umbrales son heurísticas conservadoras de revisión, **no prueban completitud oficial**. Un mes puede recibir rectificativas posteriores. Nunca se escribe `is_complete=true` ni se amplía el corte automáticamente. Si desaparecen condiciones se avisa que el mes vuelve a requerir observación.

## Cadencia y avisos

Monitor diario a las 03:00 Argentina. Año más reciente revisado: descarga diaria; años anteriores: metadatos diarios y descarga completa al menos cada siete días o ante cambios declarados. Precios diarios. Después de una ejecución de ingesta, exitosa o fallida, se fuerza revisión completa del histórico. Descubre recursos anuales fuera del contrato y avisa antes de incorporar su esquema/identidad.

GitHub Issues con etiqueta `data-monitor`, asignadas al propietario. La notificación personal depende de sus preferencias de GitHub. Marcador derivado del tipo/mes/transición identifica cada novedad; se consulta estado e issues abiertas/cerradas para evitar repetir incluso si se pierde el artifact. Nueva rectificativa genera nueva evidencia/aviso.

## Persistencia, seguridad y fallos

Estado/report/summary JSON-Markdown, artifacts 90 días, sin CSV, SQLite, perfiles, raw ni credenciales. Última ejecución del mismo workflow/repositorio/main, eventos autorizados; no artifacts PR/fork. Concurrencia serial. La línea base del repo permite recuperar contexto si expira el estado.

Permisos `contents:read`, `actions:read`, `issues:write`; sin WIF, id-token, IAM ni acceso BigQuery. Token GitHub sólo en restauración/avisos al API oficial. No se reenvía Authorization a destinos de descarga firmada. Las fuentes públicas no reciben el token. Un error de fuente conserva observaciones previas, no declara ausencia de cambios y genera aviso de fallo. Si falla GitHub, la entrega puede fallar y queda visible en Actions; no se simula recepción de avisos.

`SOURCE_MONITOR_ENABLED` controla este calendario. `DATA_PIPELINE_ENABLED` sigue controlando el calendario de carga por separado. Ejecución manual disponible sólo en main.
