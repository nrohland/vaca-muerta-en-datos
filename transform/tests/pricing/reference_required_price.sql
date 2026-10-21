{{ config(enabled=target.name == 'candidate' and var('enable_candidate_pricing', false), tags=['pricing']) }}
with required as (
 select product, {{ candidate_period_sql() }} as periodo
 from unnest(['oil','gas']) product
)
select r.* from required r
where not exists (
 select 1 from {{ ref('stg_monthly_reference_price') }} p
 where p.product=r.product and p.periodo=r.periodo and p.price_valid
)
