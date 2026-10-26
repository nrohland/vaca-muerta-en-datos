# CLI downstream: transformación y export

La ingesta batch anterior está retirada. `prepare`, `load`, `extract` y `all` fallan; los subcomandos internos tampoco permiten saltar esa baja. No ejecutar los antiguos scripts CSV/precios. La única entrada de ingesta es [Meltano](../extraction/MELTANO.md):

```sh
meltano run candidate-history
python pipeline/singer_completion.py
```

Estos comandos se reservan a un runner remoto habilitado y generan candidatos aislados; hoy la conectividad oficial mantiene la operación bloqueada. No programarlos en la Mac.

## Contrato downstream conservado

`pipeline/run_candidate.py transform|export` sigue disponible para artefactos canónicos previamente aceptados. Conserva la verificación de hashes, fuentes/precios, freshness, presupuestos dbt y contrato frontend. No acepta automáticamente los nuevos recibos Singer ni sustituye una promoción de tablas.

Ejemplo exclusivamente para una extracción canónica aceptada, con ADC autorizado y billing deshabilitado:

```sh
python pipeline/run_candidate.py transform --history \
  --extract-artifact /ruta/a/artefactos-canonicos-aceptados --run-dir /tmp/vm-transform
```

La metadata histórica exigida sigue siendo `source-evidence`, `source-manifest`, `source-load`, `price-manifest` y `price-load`. El gate requiere destinos canónicos, corte 2023-01 a 2026-08 y hashes/frescura coincidentes; una tabla Singer con TTL de un día no satisface ese contrato.

La conexión de candidatos Singer a dbt requiere una promoción y contrato explícitos aún pendientes. Por eso el nuevo workflow de ingesta no encadena transformación/export ni publica un dashboard. No se aprueban datos nuevos por tener STATE o `target-complete.json`.
