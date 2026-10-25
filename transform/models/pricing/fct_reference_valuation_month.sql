{{ config(enabled=target.name == 'candidate' and var('enable_candidate_pricing', false), materialized='table', schema='marts', tags=['pricing']) }}
with unique_prices as (
 select * from {{ ref('stg_monthly_reference_price') }}
 qualify count(*) over (partition by product, periodo) = 1
), joined as (
 select w.*, o.price as oil_price, coalesce(o.price_valid, false) as oil_price_valid,
    o.periodo as oil_price_period, o.benchmark as oil_benchmark,
    o.source_sha256 as oil_source_sha256, o.snapshot_id as oil_snapshot_id,
    o.retrieved_at as oil_retrieved_at, o.source_updated_at as oil_source_updated_at,
    o.accepted_cutoff as oil_cutoff,
    g.price as gas_price, coalesce(g.price_valid, false) as gas_price_valid,
    g.periodo as gas_price_period, g.benchmark as gas_benchmark,
    g.energy_basis as gas_price_energy_basis, g.source_sha256 as gas_source_sha256,
    g.snapshot_id as gas_snapshot_id, g.retrieved_at as gas_retrieved_at,
    g.source_updated_at as gas_source_updated_at, g.accepted_cutoff as gas_cutoff
 from {{ ref('fct_well_month') }} w
 left join unique_prices o
   on w.periodo = o.periodo and o.product = 'oil' and o.benchmark = 'EIA_BRENT_MONTHLY'
 left join unique_prices g
   on w.periodo = g.periodo and g.product = 'gas' and g.benchmark = 'EIA_HENRY_HUB_MONTHLY'
), assessed as (
 select *,
    prod_pet_m3 is not null and not is_nan(prod_pet_m3) and not is_inf(prod_pet_m3) and prod_pet_m3 >= 0 as oil_volume_valid,
    prod_gas_km3 is not null and not is_nan(prod_gas_km3) and not is_inf(prod_gas_km3) and prod_gas_km3 >= 0 as gas_volume_valid,
    coalesce(gas_price_energy_basis = '{{ gas_reference_energy_basis_id() }}', false) as gas_energy_basis_valid
 from joined
)
select
    well_month_id, idpozo, idempresa, idareapermisoconcesion, periodo,
    prod_pet_m3 * {{ var('m3_to_bbl') }} as oil_volume_bbl,
    oil_price as reference_price_usd_per_bbl,
    if(oil_price_valid and oil_volume_valid,
       prod_pet_m3 * {{ var('m3_to_bbl') }} * oil_price, null) as oil_reference_value_usd,
    oil_price_valid as price_valid,
    coalesce(oil_price_valid and oil_volume_valid, false) as oil_valuation_available,
    case when oil_price_period is null then 'missing_price'
         when not oil_price_valid then 'invalid_price'
         when not coalesce(oil_volume_valid, false) then 'invalid_volume'
         else 'available' end as oil_valuation_status,
    oil_benchmark as benchmark, oil_source_sha256 as source_sha256, oil_snapshot_id as snapshot_id,
    oil_retrieved_at as price_retrieved_at, oil_source_updated_at as price_source_updated_at,
    oil_cutoff as price_cutoff,
    prod_gas_km3 * 1000.0 as gas_volume_m3,
    if(gas_volume_valid, prod_gas_km3 * 1000.0 * {{ gas_reference_mmbtu_per_m3() }}, null) as gas_estimated_mmbtu,
    gas_price as gas_reference_price_usd_per_mmbtu,
    if(gas_price_valid and gas_energy_basis_valid and gas_volume_valid,
       prod_gas_km3 * 1000.0 * {{ gas_reference_mmbtu_per_m3() }} * gas_price, null) as gas_reference_value_usd,
    gas_price_valid,
    coalesce(gas_price_valid and gas_energy_basis_valid and gas_volume_valid, false) as gas_valuation_available,
    case when gas_price_period is null then 'missing_price'
         when not gas_energy_basis_valid then 'invalid_energy_basis'
         when not gas_price_valid then 'invalid_price'
         when not coalesce(gas_volume_valid, false) then 'invalid_volume'
         else 'reference_scenario' end as gas_valuation_status,
    gas_benchmark, gas_price_energy_basis,
    '{{ gas_reference_energy_basis_id() }}' as gas_energy_basis,
    {{ gas_reference_mmbtu_per_m3() }} as gas_energy_factor_mmbtu_per_m3,
    true as gas_energy_is_scenario,
    'estimated_reference_scenario' as gas_valuation_method,
    gas_source_sha256, gas_snapshot_id,
    gas_retrieved_at as gas_price_retrieved_at,
    gas_source_updated_at as gas_price_source_updated_at, gas_cutoff as gas_price_cutoff
from assessed
