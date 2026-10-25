# Mejoras implementadas de la auditoría

Rama local: feat/audit-improvements. Base: 27912a04cdfce43aa32b877ccdd4133d6d4f9be6. Facturación GCP deshabilitada; sin cambios remotos.

## Cambios

- Evidencia histórica archivada y enlaces actualizados; se conservan anclajes y baselines operativos.
- Descarga anual con hasta tres intentos, un worker, archivos parciales y renombrado sólo al completar; errores permanentes y TLS bloquean sin downgrade.
- Meltano 4.4.1 ejecuta las fases del CLI como utilities, con ID compartido, plan offline y lock de host. No es un tap Singer ni restaura el extractor CKAN retirado.
- Terraform optativo adopta datasets existentes tras importación. Por defecto cero recursos administrados, estado local y sin servicios facturables, APIs o IAM nuevos.
- Actions instala el bundle completo; no conserva shards/aprobaciones viejas. El recibo técnico de export no se copia a public. Fallo de swap restaura last-good. Se agrega smoke de Meltano Linux sin consultas a fuentes/GCP, y concurrency/timeout en V1 checks.
- Page Server Component valida los archivos locales en build y prerenderiza KPIs/rankings. Charts y detalle siguen diferidos.
- Gráfico con una magnitud por vez y eje visible; estados de producción/ingesta e integridad separados de frescura.
- Metodología abierta no recorta ranking; se mantiene ranking con scroll y altura de 430 px en escritorio.
- Presupuestos explícitos para HTML y HTML+JS inicial, además de JS y overview existentes.

## Verificación real

- Extracción: 54 tests PASS.
- Pipeline: 128 tests PASS, incluyendo lock, secuencia, recuperación y rollback de bundle.
- Frontend Node: 75 tests PASS; typecheck PASS.
- Seguridad HTML: 5 tests PASS.
- Build aislado del mismo código: PASS, export estático, cuatro documentos endurecidos con CSP.
- JS inicial: 154.431 bytes gzip / 204.800 permitidos.
- HTML: 266.960 bytes gzip / 307.200 permitidos.
- HTML+JS inicial: 421.391 bytes gzip / 460.800 permitidos. Excluye CSS/chunks dinámicos; no es Web Vitals.
- Enlaces Markdown locales: 209 comprobados, ninguno roto antes de agregar este reporte.
- Terraform 1.17.0 + provider Google 7.46.2: init -backend=false, fmt y validate PASS; sin import/plan/apply contra GCP.
- Browser real local: resumen, cambio USD, ranking/metodología a1280×720 y responsive390×844. Ranking430px, footer sin superposición; USD1línea/0barras/1eje; ancho de documento390px. Es revisión manual mediante CUA, no Playwright ni axe.
- SHA canónico conservado: e6daf853a62638d93a25395aed1f937c0005c21032b2029f63024fc7afb28dbd.

## Límites y siguiente integración

Playwright completo no acreditado en este sandbox macOS; se conservan/actualizan tests y se añade regresión de metodología para CI Linux. Meltano nativo se instaló pero falló al consultar procesos del host mediante psutil por restricciones del sandbox; el adaptador y plan directo sí pasaron. El nuevo smoke CI aún no se ejecutó remotamente.

La facturación permanece deshabilitada. No se hicieron llamadas BigQuery de carga, cambios IAM, import/apply Terraform, promociones, pushes ni despliegues. No se instaló programación local. La máquina de ingesta deberá estar encendida y conectada.

El corte y anclajes siguen en agosto de 2026. Aceptación dinámica de meses/rectificativas, promoción automática, rutas SSG específicas para deeplinks y reducción del overview serializado son trabajos separados; no se afirma cierre autónomo100%. El HTML estático inicial corresponde al resumen petróleo; query params se restauran al hidratar. El snapshot no cambió ni recibió aprobación nueva.
