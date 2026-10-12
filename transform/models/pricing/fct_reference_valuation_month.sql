{{ config(enabled=target.name == 'candidate' and var('enable_candidate_pricing', false), materialized='table', schema='marts', tags=['pricing']) }}
select
    w.well_month_id, w.idpozo, w.idempresa, w.idareapermisoconcesion,
    w.periodo, w.prod_pet_m3 * {{ var('m3_to_bbl') }} as oil_volume_bbl,
    p.price as reference_price_usd_per_bbl,
    if(p.price_valid and w.prod_pet_m3 is not null and w.prod_pet_m3 >= 0,
       w.prod_pet_m3 * {{ var('m3_to_bbl') }} * p.price, null) as oil_reference_value_usd,
    coalesce(p.price_valid, false) as price_valid,
    coalesce(p.price_valid and w.prod_pet_m3 is not null and w.prod_pet_m3 >= 0, false) as oil_valuation_available,
    case when p.periodo is null then 'missing_price'
         when not coalesce(p.price_valid, false) then 'invalid_price'
         when w.prod_pet_m3 is null or w.prod_pet_m3 < 0 then 'invalid_volume'
         else 'available' end as oil_valuation_status,
    cast(null as float64) as gas_reference_value_usd,
    false as gas_valuation_available,
    'unverified_energy_basis_and_price_coverage' as gas_valuation_status,
    p.benchmark, p.source_sha256, p.snapshot_id, p.retrieved_at as price_retrieved_at,
    p.source_updated_at as price_source_updated_at, p.accepted_cutoff as price_cutoff
from {{ ref('fct_well_month') }} w
left join {{ ref('stg_monthly_reference_price') }} p
  on w.periodo = p.periodo and p.product = 'oil' and p.benchmark = 'EIA_BRENT_MONTHLY'
