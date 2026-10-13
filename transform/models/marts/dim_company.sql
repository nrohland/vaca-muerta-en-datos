{# Dimension name uses latest observed period; conflicting names inside one ID/month remain a test failure. #}
{{
    config(
        materialized="table",
        cluster_by=["idempresa"],
    )
}}

select
    idempresa,
    array_agg(empresa ignore nulls order by periodo desc, empresa limit 1)[safe_offset(0)] as empresa,
    count(distinct idpozo) as well_count,
    min(periodo) as first_periodo,
    max(periodo) as last_periodo
from {{ ref("fct_well_month") }}
group by 1
