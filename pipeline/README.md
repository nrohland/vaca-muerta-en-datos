# Pipeline candidato — Vaca Muerta en Datos

Python → BigQuery raw aislado → dbt histórico → snapshot agregado → contrato frontend → build Next.js. El mismo CLI se usa localmente y desde GitHub Actions. El workflow fue verificado en GitHub; el calendario conserva **DATA_PIPELINE_ENABLED=false** y el monitor **SOURCE_MONITOR_ENABLED=false** por conectividad con la fuente. La demo pública en Vercel se despliega por separado y sirve el snapshot incluido en Git. WIF sigue restringido a main, workflow y ambientes autorizados, con identidades separadas de extracción y transformación.

La extracción implementada usa **Python**, cuatro CSV oficiales de Capítulo IV (2023–2026) y HTML oficial EIA para Brent/Henry Hub. El corte aceptado es fijo: enero 2023–agosto 2026; septiembre parcial se excluye. No hay descubrimiento ni aceptación automática de meses nuevos.

## Recorrido

1. Preparar y revisar fuentes públicas, sin autenticación cloud. Esquema, SHA-256 y conciliaciones de cobertura; precios sin interpolación.
2. Autenticar con WIF/ADC y cargar únicamente tablas candidatas. Cargas atómicas por tabla, sin transacción conjunta ni reintento automático de escrituras.
3. Verificar fuente, precios, linaje y frescura; ejecutar dbt source freshness, parse, compile y build/tests.
4. Exportar `fct_dashboard_month` y cotizaciones de la misma carga. Exigir hashes de entrada dbt, anclajes físicos, sumas por entidad, units y valores válidos.
5. Validar el bundle mediante los contratos reales del frontend. GitHub lo consume en su checkout temporal, ejecuta typecheck/tests/build y conserva sólo metadata sanitizada.

Si una etapa falla, no se ejecuta la siguiente. El export se escribe completo en una carpeta temporal y se instala sólo al finalizar; no reemplaza el snapshot del repo ni crea aprobación. El consumidor no calcula USD a partir de volumen/precio. Sólo consulta agregados JSON, sin acceso al warehouse.

## Ejecutar y verificar

Ver [CLI y comandos](CLI.md). Requiere Python 3.12, `transform/requirements.txt`, paquetes dbt resueltos y Node 22.13+. Credenciales ADC sólo para las etapas cloud; ninguna clave permanente en el repositorio. `python -m unittest discover -s pipeline/tests` verifica gates, datos, aislamiento y contrato del workflow.

La fuente conserva sus fechas reales de recuperación. Frescura operativa ≤7 días, con warning dbt desde cinco días que el CLI también rechaza. Eso no vuelve completo el último mes ni significa frescura económica. Presupuesto **1 GiB por consulta**, no por run ni costo total. Histórico fuera de la ventana de expiración del sandbox se conserva con clustering; no se particionan marts por el mes histórico.

WIF usa el archivo ADC externo de la acción oficial, nunca una key. Se instalan dependencias y preparan las descargas antes de autenticar. Las dos identidades se comprobaron en el recorrido real de GitHub; no se amplía IAM ni duración de tokens para simular esa prueba. [Documentación oficial de autenticación](https://github.com/google-github-actions/auth).

## Estado y límites

La carga y los modelos históricos tienen evidencia real previa; la integración del export se registra en [evidencia de orquestación/export](../docs/archive/evidence/orchestration-export/README.md). El snapshot revisado y las capturas están en [integración frontend](../docs/archive/evidence/snapshot-integration/README.md). El árbol conserva la evidencia vigente y la auditoría histórica relevante; las iteraciones superadas permanecen en Git.

[Recorrido real en GitHub con WIF aprobado](../docs/evidence/github-actions/README.md), desde descarga hasta build del consumidor. La detección de nuevos meses y rectificativas tiene [monitor independiente](MONITOR.md). La promoción de nuevos datos sigue requiriendo revisión; no hay ingesta automática operativa. Cron preparado día 5 a las 03:00 Argentina, desactivado. El workflow no sube raw, HTML, perfiles, credenciales, manifest dbt completo, dashboard ni build a artifacts; no publica GitHub Pages ni hace commits/push. Cambios nuevos de volumen/clasificación/área bloquean hasta contar con revisión explícita; no se aceptan automáticamente por actualizar hashes.

En V1 la operación aceptada fue manual local. El objetivo vigente exige un colector remoto; la nueva integración [Meltano Singer](../extraction/MELTANO.md) no programa extracción en la Mac. Aún no hay un runner remoto con acceso comprobado a los CSV oficiales. Ambos workflows de datos están `disabled_manually`, además de los flags en `false`: `workflow_dispatch` requiere rehabilitarlos explícitamente, comprobar conectividad y revisar el claim WIF tras el renombre del repo. CI y seguridad continúan activos. Ver [cierre y operación de V1](../docs/v1-closeout.md).

Antes de warehouse, `resource-preflight` exige billing verificado como desactivado y registra uso/expiración por APIs de metadatos. Una identidad sin visibilidad de todos los jobs informa esa limitación; no fabrica cero. No modifica billing, IAM ni cuotas. El build dbt usa 4 threads y presupuesto agregado de aceptación de 3 GiB. [Spec de rendimiento](../specs/021-performance-optimization.md).

Para investigar acceso del runner se puede ejecutar manualmente el mismo workflow con `resource_check_only=true`: autentica sólo la identidad de extracción y consulta metadatos; omite descargas públicas, cargas y transformación. El valor predeterminado es `false`. Un preflight fallido conserva un JSON con fase, código HTTP y categorías API permitidas, sin mensajes de excepción, respuestas completas ni credenciales. Nunca satisface el gate ni continúa hacia warehouse.

El build verifica primero con dry run que la consulta staging compilada entre en 1 GiB. Si la estimación excede el límite, espera de forma acotada hasta cinco minutos y vuelve a estimar; no reintenta escrituras ni cambia el presupuesto. Se conserva `dbt-build-readiness.json`. Un build fallido genera `dbt-build.diagnostic.json` con estados/categorías numéricas permitidas, sin SQL ni mensajes completos. Una estimación ausente o persistentemente excesiva sigue bloqueando export/frontend.

La visibilidad mensual global se comprueba mediante `testIamPermissions` para `bigquery.jobs.listAll` (sólo verifica permisos existentes). `jobs.list(all_users=True)` puede devolver únicamente jobs propios sin ese permiso; HTTP 200 no demuestra un inventario global. Sin confirmación, el total global queda desconocido y se informa sólo el observado. No se amplían roles.
