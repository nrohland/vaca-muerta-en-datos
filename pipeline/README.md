# Pipeline candidato — Vaca Muerta en Datos

Python → BigQuery raw aislado → dbt histórico → snapshot agregado → contrato frontend → build Next.js. El mismo CLI se usa localmente y desde GitHub Actions. El workflow está preparado pero **DATA_PIPELINE_ENABLED=false**: no se activó cron, publicó ni desplegó. WIF sigue restringido a main, workflow y ambientes autorizados, con identidades separadas de extracción y transformación.

La extracción activa usa **Python**, cuatro CSV oficiales de Capítulo IV (2023–2026) y HTML oficial EIA para Brent/Henry Hub. El corte aceptado es fijo: enero 2023–agosto 2026; septiembre parcial se excluye. No hay descubrimiento ni aceptación automática de meses nuevos.

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

WIF usa el archivo ADC externo de la acción oficial, nunca una key. Se instalan dependencias y preparan las descargas antes de autenticar. Duración/renovación e identidad efectiva deben comprobarse en el primer runner real; no se amplía IAM ni duración de tokens para simular esa prueba. [Documentación oficial de autenticación](https://github.com/google-github-actions/auth).

## Estado y límites

La carga y los modelos históricos tienen evidencia real previa; la integración del export se registra en [evidencia de orquestación/export](../docs/evidence/orchestration-export/README.md). El snapshot revisado y las capturas están en [integración frontend](../docs/evidence/snapshot-integration/README.md). El árbol conserva la evidencia vigente y la auditoría histórica relevante; las iteraciones superadas permanecen en Git.

Pendiente: ejecutar desde GitHub con WIF tras promoción autorizada a main. Cron preparado día 5 a las 03:00 Argentina, desactivado. El workflow no sube raw, HTML, perfiles, credenciales, manifest dbt completo, dashboard ni build a artifacts; no publica GitHub Pages ni hace commits/push. Cambios nuevos de volumen/clasificación/área bloquean hasta contar con revisión explícita; no se aceptan automáticamente por actualizar hashes.

La validación manual del workflow de datos está permitida únicamente en `main`, independientemente del opt-in del calendario. `DATA_PIPELINE_ENABLED=false` mantiene el cron desactivado; `workflow_dispatch` ejecuta una corrida puntual con los mismos permisos y gates.
