# Primera ejecución real en GitHub — 13 de octubre de 2026

[Pipeline manual completo](https://github.com/nrohland/vaca-muerta-en-datos/actions/runs/38456258503) aprobado sobre main, commit `7dbc1d9`: extracción 8m17s, transformación 5m43s. Fuentes descargadas nuevamente, 3.614.213 registros y 828 cotizaciones cargadas; controles raw, linaje y freshness aprobados. Autenticación WIF real con identidades separadas en ambas etapas, sin modificar IAM.

**dbt: 106 nodos aprobados, sin error/warn/skip**. Export de 44 meses y 10.296 agregados, contrato del consumidor, 59 tests frontend, typecheck y build aprobados. El bundle generado queda candidato y no reemplaza automáticamente el snapshot del repo. No se publicó una app ni se habilitó el cron.

[Checks previos del PR](https://github.com/nrohland/vaca-muerta-en-datos/actions/runs/38455837901) y [checks de main](https://github.com/nrohland/vaca-muerta-en-datos/actions/runs/38456228316) aprobados: 112 tests Python y frontend/parse/build. Primera corrida del PR falló por faltar `--experimental-strip-types` bajo Node 22; corregido antes del merge. No fue un fallo de datos.

## Seguridad

Gitleaks 8.30.1 con checksum oficial: árbol main sin secretos, 132 commits alcanzables revisados, 39 logs completos y ambos artifacts sin credenciales. Dos coincidencias históricas son enums constantes de Google, no claves; revisión explícita sin ocultarlas con baseline. GitHub secret scanning y push protection activos, cero alertas. [Alcance](security-audit.json). No se publican logs completos, ADC, perfiles, credenciales, raw ni bundle.

## Evidencia y pendientes

[Resumen](run-summary.json), [dbt](dbt-summary.json), [performance](performance.json), [export](dashboard-export.gate.json), [contrato](snapshot-check.gate.json).

`DATA_PIPELINE_ENABLED=false`: sólo ejecución manual en main; cron preparado día5 a las 03:00 Argentina. Corte aceptado agosto. Detección/aviso de nuevos meses, criterio de aceptación de septiembre, promoción y hosting/operación pública pendientes. Playwright no se ejecutó en este CI; se conserva la revisión visual documentada aparte.
