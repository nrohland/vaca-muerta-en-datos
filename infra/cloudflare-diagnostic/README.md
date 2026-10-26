# Diagnóstico remoto — Workers Free

Ejecutado el25/10/2026, sin upgrades ni medios de pago agregados. Prueba de transporte, no colector productivo.

## Resultado desde GitHub Actions

[Run40253478821](https://github.com/nrohland/vaca-muerta-en-datos/actions/runs/40253478821), runner Ubuntu estándar del repositorio público:

| Ruta | Respuesta del Worker | Resultado upstream | Placement |
| --- | --- | --- | --- |
| /health |200| Diagnóstico activo |remote-GRU|
| /probe/resource |502| Energía522,19,612s |remote-GRU|
| /probe/catalogue |502| Timeout20s |remote-GRU|

Entrada del request: LAX. Ejecución confirmada por `cf-placement: remote-GRU`, São Paulo. Esto demuestra que el Placement Hint se aplicó aunque la llamada provino de Actions. No resolvió la comunicación con Energía. No se puede inferir un fallo TLS ni bloqueo por país; GRU tampoco prueba una IP argentina.

Worker de la cuenta: `https://vm-source-diagnostic.nicolas-rohland.workers.dev`, versión6db06b68-a691-434d-a448-0c3b681a82a0. Plan Workers Free ($0) comprobado en dashboard. Sin bindings, cron ni almacenamiento de datos. Logs de invocación gratuitos del dashboard conservados; el código no registra raw ni credenciales. La sesión OAuth de Wrangler fue revocada mediante `wrangler logout` después de la prueba. No hay token Cloudflare en Actions.

## Alcance

Sólo GET /health, /probe/resource y /probe/catalogue; destinos HTTPS fijos, timeout20s, sin redirects automáticos. Se cancela el body después de recibir headers. No acepta URLs arbitrarias ni query del llamante. HTTP200 no certifica metadata válida ni un CSV completo. No cambia snapshot ni timestamps de frescura.

El hint gcp:southamerica-east1 orienta la ejecución dentro de Cloudflare; no crea recursos GCP. La extracción no depende de la Mac. Sigue sin colector remoto con acceso verificado a la fuente.

## Configuración y pruebas

`wrangler.toml` reproduce Free Worker sin previews adicionales ni bindings. Publicación por CLI oficial, con autorización temporal del usuario para escritura de scripts, lectura de cuenta/usuario y offline_access; sesión cerrada al terminar.

Workflow `.github/workflows/cloudflare-diagnostic.yml`: sin permisos GitHub, secretos, checkout ni artifacts; llamadas acotadas al Worker desde Ubuntu estándar. Corre en push a la rama test/cloudflare-source-connectivity o manualmente. No está integrado a main.

Verificaciones locales: sintaxis Node y seis casos con fetch simulado (health, dos destinos, query rechazada, POST rechazado y ruta desconocida). Prueba real en Actions: falló correctamente porque el origen no respondió.

## Ensayo temporal previo

La vista previa temporal de60min respondió /health desde navegador con ingreso EZE, pero Actions recibió403 de Cloudflare con HTML “Just a moment…” incluso en /health (runs40234834847 y40235054573). Ese resultado no evaluó Cloudflare→Energía. No se reclamó la cuenta temporal. La prueba final en la cuenta del usuario sí alcanzó el código del Worker y confirmó remote-GRU.
