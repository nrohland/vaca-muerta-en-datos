# Demo en Vercel

URL: https://vaca-muerta-en-datos.vercel.app

Proyecto `vaca-muerta-en-datos` en la cuenta Hobby personal. Sólo frontend estático:
sin funciones, BigQuery, credenciales de extracción, compras de dominios ni cron.
Los límites y el consumo se comparten con las otras aplicaciones de la cuenta.

## Configuración

- Repositorio `nrohland/vaca-muerta-en-datos`, rama de producción `feat/dashboard-visual-polish`.
  `main` contiene la versión integrada. La rama de producción se sincroniza por fast-forward después de los controles; sus pushes generan builds.
- Root Directory: `apps/web`.
- Framework Preset: `Other`, para servir únicamente el export estático.
- Install Command: `npm ci`.
- Build Command: `NEXT_PUBLIC_BASE_PATH='' npm run build`.
- Output Directory: `out`.
- Máquina Basic incluida en Hobby; concurrencia de builds bajo demanda desactivada.

La variable vacía de base path evita el prefijo local `/vaca-muerta-pulse` y sirve
assets, logos, datos y geometrías desde la raíz del dominio. El worker de MapLibre
usa `new URL(..., import.meta.url)` y `setWorkerUrl` para que Next emita un asset
versionado; no se busca un worker inexistente al lado del chunk de la aplicación.
Las pruebas de navegador exigen que se descargue y que la geometría esté cargada
antes de mostrar los círculos.

## Datos y operación

Se publica el snapshot incluido en Git. Este despliegue no reanuda la extracción,
no cambia el corte y no convierte un mes parcial en completo. El monitor de fuentes
está pausado (`SOURCE_MONITOR_ENABLED=false`); las cargas periódicas también
(`DATA_PIPELINE_ENABLED=false`). La fecha de deploy no es la fecha de los datos.

Para actualizar, preparar y validar un nuevo snapshot con el pipeline existente,
revisar sus contratos y luego desplegar el commit correspondiente. Nunca añadir
credenciales GCP al frontend o a variables `NEXT_PUBLIC_*`.
