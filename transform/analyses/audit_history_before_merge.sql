-- Read-only physical data diff. Only aggregate classifications leave the warehouse.
-- Retained baseline and candidate are explicit; neither relation is modified.
{% set before %}
select cast(idpozo as int64) as idpozo, cast(anio as int64) as anio,
 cast(mes as int64) as mes, cast(prod_pet as float64) as prod_pet_m3,
 cast(prod_gas as float64) as prod_gas_km3
from `vaca-muerta-pulse.raw_cap4_candidate_20261009.produccion_pozo_mes`
where formacion='vaca muerta' and tipo_de_recurso='NO CONVENCIONAL'
 and anio between 2023 and 2026 and (anio<2026 or mes<=8)
{% endset %}
{% set after %}
select idpozo,anio,mes,prod_pet_m3,prod_gas_km3
from {{ ref('fct_well_month') }}
{% endset %}
with comparison as (
 {{ audit_helper.compare_and_classify_query_results(before, after,
      primary_key_columns=['idpozo','anio','mes'],
      columns=['idpozo','anio','mes','prod_pet_m3','prod_gas_km3'],sample_limit=None) }}
)
select dbt_audit_row_status as classification,count(*) as `rows`,
 countif(classification_check) as explained_reclassification_rows
from (select *,idpozo=164323 and anio in (2024,2025) as classification_check from comparison)
group by classification
