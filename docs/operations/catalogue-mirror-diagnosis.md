# Diagnóstico: catálogo nacional y espejos públicos

Pruebas desde GitHub Actions Ubuntu estándar en repositorio público, sin GCP, billing, secretos, cron ni promoción. No se ejecutó extracción desde la Mac.

## Catálogo nacional

La URL propuesta con ID `energia_produccion-de-petroleo-y-gas-por-pozo` respondió404 CKAN (Not Found Error). La variante basada en el slug de la página también respondió404. La página HTML devolvió 502 en esta corrida.

La búsqueda oficial `https://datos.gob.ar/api/3/action/package_search?q=pozo&rows=20` respondió200, success=true, 13 datasets. Identificó Capítulo IV con:

- ID: `7a388cf4-b266-54ac-865a-732996c2d1d7`.
- Nombre: `produccion-de-petroleo-y-gas-por-pozo`.
- 53 recursos; todos apuntan a `datos.energia.gob.ar`.
- Los CSV anuales 2023–2026 apuntan al mismo packageUUID y resourceUUID usados por el extractor del proyecto.

Consulta por ID descubierta:

```text
https://datos.gob.ar/api/3/action/package_show?id=7a388cf4-b266-54ac-865a-732996c2d1d7
```

La consulta por ID devolvió 502 en el [tercer diagnóstico](https://github.com/nrohland/vaca-muerta-en-datos/actions/runs/40261906797); el ID y los 53 recursos fueron obtenidos mediante package_search HTTP 200. No se afirma disponibilidad constante de package_show.

El catálogo permite descubrir recursos remotamente; no aloja aquí un espejo de los CSV. El timestamp del catálogo cosechado no certifica frescura de bytes del origen. No cambiar la fuente de descarga ni avanzar frescura basándose sólo en metadata accesible.

## Hugging Face: copia real, universo distinto

Se descargó en el runner remoto `contepablod/vm_app/data/well_prod_data.csv`, fijado al commit `a53f0fdca86d585edfebee68ff87e73672bfbd11`:

- HTTP 200; 21.847.744 bytes; 109.185 filas; 2.190 pozos distintos.
- Cobertura observada: enero 2006–febrero 2026.
- SHA256 `40f56220b48bb71e8f6730432aa25cce14d94b3cbc8ad6b3e02a403a04ea84dd`, coincide con el LFS publicado para el archivo.

El hash demuestra coincidencia con la copia del commit, no autenticidad ni equivalencia con el CSV oficial. El script `scripts/refresh_data.py` de ese Space renombra columnas, agrega acumulados, selecciona Vaca Muerta/no convencional/shale/profundidad positiva y después conserva sólo IDs presentes en su dataframe de fracturas, que tiene filtros adicionales y exclusiones explícitas. Faltan columnas raw del contrato del proyecto. No es un fallback intercambiable para el universo del dashboard y su corte está por detrás del snapshot aceptado de agosto 2026. No se incorporó a datos productivos.

Fuentes públicas inspeccionadas:

- [Space y archivos](https://huggingface.co/spaces/contepablod/vm_app/tree/a53f0fdca86d585edfebee68ff87e73672bfbd11).
- [Transformación del Space](https://huggingface.co/spaces/contepablod/vm_app/blob/a53f0fdca86d585edfebee68ff87e73672bfbd11/scripts/refresh_data.py).
- [README del Space](https://huggingface.co/spaces/contepablod/vm_app/blob/a53f0fdca86d585edfebee68ff87e73672bfbd11/README.md).

## GitHub y API de series

El árbol de [datosenergia/produccion-de-petroleo-y-gas-por-pozo](https://github.com/datosenergia/produccion-de-petroleo-y-gas-por-pozo) sólo contiene README.md; no replica CSV. Se revisaron otros proyectos públicos: se encontraron aplicaciones y agregados derivados, sin un raw actual equivalente verificado. Esto no prueba inexistencia global de un espejo.

[apis.datos.gob.ar/series](https://datosgobar.github.io/series-tiempo-ar-api/) documenta indicadores cronológicos. No se identificó en esta revisión un recurso de esa API equivalente al grano pozo–mes y columnas del contrato. Una serie agregada no reemplaza las fuentes de rankings de área/operadora ni los conteos de pozos.

## Evidencia reproducible

- [Diagnóstico inicial y CSV HF](https://github.com/nrohland/vaca-muerta-en-datos/actions/runs/40261556161).
- [Descubrimiento nacional 200 y hosts de recursos](https://github.com/nrohland/vaca-muerta-en-datos/actions/runs/40261754283).
- `pipeline/check_catalogue_mirrors.py`: sin dependencias externas; límites de bytes/tiempo, TLS estricto, destinos revisados y sin ejecución de código del mirror.
- `.github/workflows/catalogue-mirror-diagnostic.yml`: job de diagnóstico, sin artifacts/caches ni promoción. Verde indica diagnóstico terminado; el resumen conserva official_mirror_verified=false.

Conclusión: datos.gob.ar es viable para metadata remota; los archivos del dataset siguen en Energía. HF permite descargar una copia estática pero sesgada/antigua para este contrato. No se encontró un espejo actual equivalente que cierre todavía la extracción autónoma de costo cero.
