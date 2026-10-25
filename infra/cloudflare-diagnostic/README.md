# Diagnóstico de transporte — Workers Free

Prueba autorizada de acceso remoto, no colector productivo. Únicamente GET /health, /probe/resource y /probe/catalogue con destinos HTTPS fijos, timeout20s y redirects sin seguir. El body oficial se cancela al recibir headers. No acepta destinos/query arbitrarios, no lee secretos ni tiene almacenamiento, cron o bindings.

Workers Free comprobado en dashboard el25/10/2026 ($0). Worker `vm-source-diagnostic.nicolas-rohland.workers.dev` creado; Placement Region/GCP/southamerica-east1 guardado sin recursos GCP. El editor web quedó cargando; la prueba de código se desplegó mediante Wrangler4.152.0 en una cuenta temporal de vista previa (caduca60min), en https://vm-source-diagnostic.booming-mantis.workers.dev. La invocación Actions está pendiente. El Worker de la cuenta del usuario conserva Hello World y no es evidencia de acceso a Energía. La vista previa temporal no es un colector permanente.

`wrangler.toml` reproduce la configuración propuesta con observability deshabilitado. El alta inicial por dashboard habilita logs por defecto; esa configuración todavía difiere del archivo. No se registran credenciales ni raw. No activar Workers Paid, R2 ni servicios adicionales.

`ingress_colo` indica el punto de entrada, no demuestra dónde ejecutó el Worker colocado. Registrar `cf-placement` cuando esté disponible. El hint no garantiza país/IP de salida ni evita bloqueos del origen.

Workflow `.github/workflows/cloudflare-diagnostic.yml`: Ubuntu estándar, repo público, sin secretos ni permisos GitHub, tres llamadas acotadas al Worker. Se ejecuta al publicar la rama test/cloudflare-source-connectivity o manualmente. HTTP200 sólo confirma headers; metadata válida y CSV completo son pruebas posteriores. No cambia snapshot ni timestamps de frescura.

Verificaciones locales: sintaxis Node correcta y seis casos con fetch simulado (health, dos destinos, queryrechazada, POSTrechazado y ruta desconocida). Sin acceso real a la fuente durante estas verificaciones.
