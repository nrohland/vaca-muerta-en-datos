{# Dimension name uses latest observed period; conflicting names inside one ID/month remain a test failure. #}
{{
    config(
        materialized="table",
        cluster_by=["idareapermisoconcesion"],
    )
}}

select
    idareapermisoconcesion,
    array_agg(areapermisoconcesion ignore nulls order by periodo desc, areapermisoconcesion limit 1)[safe_offset(0)] as areapermisoconcesion,
    count(distinct idpozo) as well_count,
    count(distinct idempresa) as company_count,
    min(periodo) as first_periodo,
    max(periodo) as last_periodo
from {{ ref("fct_well_month") }}
group by 1
