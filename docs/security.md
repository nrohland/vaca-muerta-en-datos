# Seguridad de Vaca Muerta en Datos

## Controles

El frontend estático consume agregados públicos y no recibe credenciales del warehouse. El pipeline mantiene WIF por etapa; no se habilitan cargas ni se reanuda el monitor por estos cambios. Secret Scanning y push protection siguen activos. Dependabot alerts y security updates se habilitaron con autorización del propietario: puede proponer PRs de parches; no hace merge automático.

`.github/workflows/security.yml` ejecuta en PR, main y revisión semanal:

- Gitleaks 8.30.1 con checksum SHA-256 fijado, historia completa disponible, decodificación acotada y salida redactada. No se publican reportes de posibles secretos como artefactos.
- Auditoría del lockfile JavaScript; severidad alta bloquea la comprobación. Dependabot mantiene avisos para dependencias reconocidas por el grafo, incluidas las de Python. No se afirma que npm cubra Python ni que CodeQL sea auditoría de librerías.
- CodeQL security-extended para Python y JavaScript/TypeScript, sin ejecutar cargas cloud. Únicamente el job CodeQL recibe `security-events:write` para sus resultados. No usa credenciales GCP ni secretos de despliegue.

Las actions externas de todos los workflows están fijadas por SHA completo, con versión anotada; checkout no persiste el token. Actualizar los pins mediante PR revisado, resolviendo el SHA de la release oficial y comprobando compatibilidad. No reemplazar hashes por tags móviles.

## Dos falsos positivos históricos

`.gitleaksignore` incluye exclusivamente fingerprints de `provision_hito2_bq.py:418` en commits `96ab1378d183` y `5c21e57222b2`. La auditoría verificó que son enums públicos IAM (`TYPE_GOOGLE_CREDENTIALS_FILE` y `KEY_ALG_RSA_2048`), no claves. No hay exclusión global por archivo ni regla de secreto desactivada. Nuevas coincidencias requieren revisión; nunca añadir un secreto real al ignore para pasar CI.

## Headers y CSP

`apps/web/vercel.json` conserva la caché por hash y añade `nosniff`, `X-Frame-Options: DENY`, referrer policy y permisos de navegador restrictivos. La CSP aplicada bloquea objetos, framing, base ajena y formularios a destinos externos.

La política completa de recursos comienza en **Report-Only**: enumera mismo origen y tiles OSM, workers del mapa y recursos data/blob necesarios. No es bloqueo efectivo de scripts o conexiones. Permite inline script/style por la hidratación de Next estático y estilos de React/Recharts/MapLibre; no agrega unsafe-eval. No se envían informes a un tercero ni se creó endpoint de telemetría. Una política de scripts más estricta requiere hashes/nonce compatibles con el export y otra validación.

El servidor de tests reproduce estos headers de Vercel para que las pruebas de las cinco vistas se ejecuten con las restricciones aplicadas. La política Report-Only y los headers HTTP efectivos se verifican también después de publicar.

## Alcance y respuesta

La auditoría original no encontró exposición confirmada: 140 commits, 104 logs, 50 artefactos y build/recursos públicos. No es garantía absoluta, prueba de penetración ni auditoría de cuentas cloud. Capturas no tuvieron OCR exhaustivo. No guardar secretos, raw o service account JSON en Git, logs, artefactos públicos, NEXT_PUBLIC ni prompts.

Ante una exposición confirmada, revocar/rotar primero, después sanear registros y evaluar historial. Nunca enviar la credencial en un issue público. La reescritura de atribución de commits es otra tarea y no forma parte de estos refuerzos. No se activaron servicios de IA pagos ni planes nuevos.

## Revisión del baseline CodeQL (20 de octubre de 2026)

El primer análisis completo de main detectó tres alertas que el análisis diferencial del PR no mostraba. Se revisaron individualmente:

- `js/bad-tag-filter` (#2): el inventario de JavaScript del build sólo reconocía etiquetas minúsculas. Se corrigió para reconocer SCRIPT y src sin distinguir mayúsculas y delimitar el nombre de etiqueta. Este código mide el presupuesto del build; no se usa como sanitizador HTML.
- `py/jinja2/autoescape-false` (#1): falso positivo en `pipeline/tests/test_dbt_isolation.py`. Jinja compila macros SQL locales para comprobar aislamiento de schemas y validación del período. No genera HTML ni recibe solicitudes web; aplicar escape HTML alteraría el SQL. Se conserva el análisis de la regla y se documenta la excepción en esta alerta concreta.
- `js/file-access-to-http` (#3): falso positivo cuyo origen es la lectura del manifiesto público en `apps/web/tests/delivery.test.ts`. El test reemplaza fetch por una respuesta local para probar rechazo de cuerpos alterados; no envía archivos a la red. En la aplicación estática, validateDelivery restringe cada ruta al snapshot público por hash y nombre de shard antes de cargarla. No hay lectura de credenciales ni exfiltración. Se documenta la excepción sólo en esta alerta; no se excluyen archivos ni reglas.

Las excepciones no significan que futuros hallazgos de esas reglas deban descartarse. Cada nueva alerta requiere revisar su origen, destino y contexto.
