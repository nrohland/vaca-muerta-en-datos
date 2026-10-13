{{ config(enabled=target.name == 'candidate' and var('enable_candidate_pricing', false), tags=['pricing']) }}
select * from {{ ref('fct_reference_valuation_month') }}
where oil_valuation_available != (oil_reference_value_usd is not null)
   or (oil_valuation_available and abs(oil_reference_value_usd - oil_volume_bbl * reference_price_usd_per_bbl) > greatest(0.01, abs(oil_reference_value_usd)*1e-12))
   or (not price_valid and oil_reference_value_usd is not null)
   or gas_valuation_available != (gas_reference_value_usd is not null)
   or gas_energy_basis != '{{ gas_reference_energy_basis_id() }}'
   or gas_valuation_method != 'estimated_reference_scenario'
   or not gas_energy_is_scenario
   or abs(gas_energy_factor_mmbtu_per_m3 - {{ gas_reference_mmbtu_per_m3() }})>1e-15
   or (gas_valuation_available and (
       gas_valuation_status != 'reference_scenario'
       or gas_benchmark != 'EIA_HENRY_HUB_MONTHLY'
       or gas_price_energy_basis != gas_energy_basis
       or abs(gas_estimated_mmbtu-gas_volume_m3*gas_energy_factor_mmbtu_per_m3)>greatest(1e-9,abs(gas_estimated_mmbtu)*1e-12)
       or abs(gas_reference_value_usd-gas_estimated_mmbtu*gas_reference_price_usd_per_mmbtu)>greatest(0.01,abs(gas_reference_value_usd)*1e-12)))
   or (not gas_price_valid and gas_reference_value_usd is not null)
