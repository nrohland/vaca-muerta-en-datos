{{ config(enabled=target.name == 'candidate' and var('enable_candidate_pricing', false), tags=['pricing']) }}
{% if var('candidate_period', none) is not none %}
select date('{{ var("candidate_period") }}') as missing_required_period
from (select 1 as candidate_run)
where not exists (
    select 1 from {{ ref('stg_monthly_reference_price') }}
    where periodo=date('{{ var("candidate_period") }}') and price_valid
)
{% else %}
select periodo from {{ ref('stg_monthly_reference_price') }} where false
{% endif %}
