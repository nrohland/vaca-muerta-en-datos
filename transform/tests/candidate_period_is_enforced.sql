{{ config(enabled=(target.name == 'candidate')) }}

{% if target.name == 'candidate' %}
select 'unexpected_well_month' as error
from {{ ref('fct_well_month') }}
where periodo != {{ candidate_period_sql() }} or periodo is null
union all
select 'headline_missing_or_wrong_period'
from {{ ref('fct_production_rate') }}
having count(*) != 1 or countif(periodo = {{ candidate_period_sql() }}) != 1

{% else %}
select 1 where false
{% endif %}
