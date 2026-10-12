# Linaje del candidato ejecutado

Generado desde las dependencias del manifest de la corrida real: únicamente los 11 modelos construidos y sus fuentes directas. No contiene metadatos de conexión ni incluye tests/macros. No representa todavía publicación histórica del dashboard.

```mermaid
flowchart LR
  n0["dim_area"]
  n1["dim_company"]
  n2["fct_area_month"]
  n3["fct_company_month"]
  n4["fct_production_rate"]
  n5["fct_reference_valuation_entity_month"]
  n6["fct_reference_valuation_month"]
  n7["fct_well_month"]
  n8["int_produccion_vm_noconv"]
  n9["stg_monthly_reference_price"]
  n10["stg_produccion_pozo_mes"]
  n11["monthly_reference_price"]
  n12["produccion_pozo_mes"]
  n7 --> n0
  n7 --> n1
  n7 --> n2
  n7 --> n3
  n7 --> n4
  n6 --> n5
  n7 --> n6
  n9 --> n6
  n8 --> n7
  n10 --> n8
  n11 --> n9
  n12 --> n10
```
