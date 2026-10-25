{{ config(enabled=(target.name == 'candidate')) }}

{% if target.name == 'candidate' %}
with headline as (
    select count(*) as headline_rows,
           countif(periodo = {{ candidate_period_sql() }}) as accepted_rows
    from {{ ref('fct_production_rate') }}
)
select 'unexpected_well_month' as error
from {{ ref('fct_well_month') }}
where periodo not between {{ candidate_start_period_sql() }} and {{ candidate_period_sql() }} or periodo is null
union all
select 'headline_missing_or_wrong_period'
from headline
where headline_rows != 1 or accepted_rows != 1

{% else %}
select 1 where false
{% endif %}
