# Linaje dbt — Vaca Muerta en Datos

Diagrama generado con `pipeline/render_dbt_lineage.py` a partir del `parent_map` del manifest real del candidato histórico. Incluye **12 modelos, 2 fuentes y 1 seed**, con 15 dependencias. Excluye tests/macros/paquetes y no exporta SQL, conexiones, credenciales ni el manifest completo.

![Linaje del candidato histórico](linaje-dbt.svg)

Fuentes activas: producción mensual y cotizaciones Brent/Henry Hub. Staging normaliza tipos/claves; intermediate recorta el universo; marts persisten hechos físicos y USD. `operator_groups` contiene el mapping estable de presentación; `fct_dashboard_month` es la salida del consumidor. Completaciones están fuera de V1.

Manifest dbt 1.12.5, generado 2026-10-13T18:42:56.258554Z; SHA-256 `e90087f8c9c0aee0602f158993e6115b0e4136a78edaf0ef942737c114ac3a6a`. [Nodos/relaciones sanitizados](lineage.json) y [ejecución integrada](../archive/evidence/orchestration-export/README.md). El grafo representa dependencias declaradas; los resultados del build se registran aparte y no se infieren por dibujar el diagrama.

Regenerar desde el manifest de un run real:

```bash
python pipeline/render_dbt_lineage.py --manifest /ruta/run/dbt-target/manifest.json --output docs/lineage
```
