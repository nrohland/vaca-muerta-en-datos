# Extracción — Vaca Muerta en Datos

La ruta vigente usa **Python** para cuatro CSV anuales oficiales de Capítulo IV (2023–2026) y referencias mensuales EIA. Los contratos, hashes y controles preceden cualquier carga. No requiere Meltano/Singer.

## Componentes

- `contracts/production_csv.json`: esquema y alcance de producción.
- `scripts/prepare_csv_candidate.py`: tipado estricto y preparación NDJSON para BigQuery.
- `scripts/source_history_pipeline.py`: descarga, revisión, conciliación y carga histórica aislada.
- `scripts/source_csv_pipeline.py`: helpers compartidos y ruta candidata de un año.
- `scripts/check_raw_snapshot.py`: verificación de raw para la ruta de un año.
- `../scripts/prepare_reference_prices.py` y `load_reference_prices.py`: preparación/carga de Brent y Henry Hub.

CSV es el formato publicado por la fuente; NDJSON es el formato transitorio de carga, fuera de Git. El consumidor usa JSON agregado, no raw. No se incorporó Parquet a esta versión.

## Operación

Usar el [CLI compartido](../pipeline/CLI.md), que coordina ambas fuentes. `prepare` no necesita identidad cloud; `load` requiere ADC/WIF y escribe sólo en el proyecto/dataset candidato autorizado. Los helpers rechazan destinos compartidos antes de crear el cliente BigQuery. Cargas atómicas por tabla, sin transacción conjunta producción/precios.

Corte fijo enero 2023–agosto 2026. Septiembre parcial excluido. Cambios de esquema, hash, volumen, clasificación o área requieren conciliación y bloquean aceptación automática. [Contrato histórico](../specs/019-historical-source-candidate.md) y [evidencia fuente](../docs/evidence/historical-source/README.md).

```sh
python -m unittest discover -s extraction/tests
```

Dependencias cloud: `transform/requirements.txt`. Nunca guardar credenciales o descargas raw en Git. Los scripts antiguos de CKAN, claves permanentes y completaciones se retiraron del árbol actual.

## Formato histórico

El workflow activo histórico usa CSV → Parquet Zstandard directamente, en lotes de 32.768 filas y con esquema explícito. Dependencias: `pip install -r extraction/requirements.txt`. Fuente CSV y payload Parquet llevan hashes independientes. El helper monoanual anterior conserva su contrato NDJSON; los precios pequeños conservan el suyo. [Contrato de rendimiento](../specs/021-performance-optimization.md).
