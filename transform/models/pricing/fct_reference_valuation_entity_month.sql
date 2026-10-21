{{ config(enabled=target.name == 'candidate' and var('enable_candidate_pricing', false), materialized='table', schema='marts', tags=['pricing']) }}
with entities as (
    select 'basin' as entity_type, 'vaca_muerta' as entity_id, *
    from {{ ref('fct_reference_valuation_month') }}
    union all
    select 'company', coalesce(cast(idempresa as string), '__missing__'), *
    from {{ ref('fct_reference_valuation_month') }}
    union all
    select 'area', coalesce(cast(idareapermisoconcesion as string), '__missing__'), *
    from {{ ref('fct_reference_valuation_month') }}
), monthly as (
    select entity_type, entity_id, periodo,
        sum(oil_volume_bbl) as oil_volume_bbl,
        if(countif(not oil_valuation_available) = 0,
           sum(oil_reference_value_usd), null) as oil_reference_value_usd,
        countif(not oil_valuation_available) = 0 as oil_valuation_available,
        any_value(reference_price_usd_per_bbl) as reference_price_usd_per_bbl,
        any_value(snapshot_id) as price_snapshot_id,
        sum(gas_volume_m3) as gas_volume_m3,
        if(countif(gas_estimated_mmbtu is null) = 0,
           sum(gas_estimated_mmbtu), null) as gas_estimated_mmbtu,
        if(countif(not coalesce(gas_valuation_available, false)) = 0,
           sum(gas_reference_value_usd), null) as gas_reference_value_usd,
        countif(not coalesce(gas_valuation_available, false)) = 0 as gas_valuation_available,
        any_value(gas_reference_price_usd_per_mmbtu) as gas_reference_price_usd_per_mmbtu,
        any_value(gas_benchmark) as gas_benchmark,
        any_value(gas_energy_basis) as gas_energy_basis,
        any_value(gas_energy_factor_mmbtu_per_m3) as gas_energy_factor_mmbtu_per_m3,
        any_value(gas_valuation_method) as gas_valuation_method,
        any_value(gas_snapshot_id) as gas_price_snapshot_id
    from entities group by entity_type, entity_id, periodo
), accumulated as (
    select *,
        if(count(*) over ytd = extract(month from periodo)
           and countif(not oil_valuation_available) over ytd = 0,
           sum(oil_reference_value_usd) over ytd, null) as oil_reference_ytd_usd,
        if(count(*) over ytd = extract(month from periodo)
           and countif(not coalesce(gas_valuation_available, false)) over ytd = 0,
           sum(gas_reference_value_usd) over ytd, null) as gas_reference_ytd_usd
    from monthly
    window ytd as (partition by entity_type, entity_id, extract(year from periodo)
                   order by periodo rows between unbounded preceding and current row)
)
select c.*,
    pm.oil_reference_value_usd as oil_reference_previous_month_usd,
    py.oil_reference_value_usd as oil_reference_previous_year_usd,
    c.oil_reference_value_usd - pm.oil_reference_value_usd as oil_reference_mom_change_usd,
    c.oil_reference_value_usd - py.oil_reference_value_usd as oil_reference_yoy_change_usd,
    safe_divide(c.oil_reference_value_usd - pm.oil_reference_value_usd,
                pm.oil_reference_value_usd) * 100 as oil_reference_mom_change_pct,
    safe_divide(c.oil_reference_value_usd - py.oil_reference_value_usd,
                py.oil_reference_value_usd) * 100 as oil_reference_yoy_change_pct,
    py.oil_reference_ytd_usd as oil_reference_previous_year_ytd_usd,
    safe_divide(c.oil_reference_ytd_usd - py.oil_reference_ytd_usd,
                py.oil_reference_ytd_usd) * 100 as oil_reference_ytd_change_pct,
    pm.gas_reference_value_usd as gas_reference_previous_month_usd,
    py.gas_reference_value_usd as gas_reference_previous_year_usd,
    c.gas_reference_value_usd - pm.gas_reference_value_usd as gas_reference_mom_change_usd,
    c.gas_reference_value_usd - py.gas_reference_value_usd as gas_reference_yoy_change_usd,
    safe_divide(c.gas_reference_value_usd - pm.gas_reference_value_usd,
                pm.gas_reference_value_usd) * 100 as gas_reference_mom_change_pct,
    safe_divide(c.gas_reference_value_usd - py.gas_reference_value_usd,
                py.gas_reference_value_usd) * 100 as gas_reference_yoy_change_pct,
    py.gas_reference_ytd_usd as gas_reference_previous_year_ytd_usd,
    safe_divide(c.gas_reference_ytd_usd - py.gas_reference_ytd_usd,
                py.gas_reference_ytd_usd) * 100 as gas_reference_ytd_change_pct
from accumulated c
left join accumulated pm on c.entity_type = pm.entity_type and c.entity_id = pm.entity_id
    and pm.periodo = date_sub(c.periodo, interval 1 month)
left join accumulated py on c.entity_type = py.entity_type and c.entity_id = py.entity_id
    and py.periodo = date_sub(c.periodo, interval 1 year)
