{{ config(enabled=target.name == 'candidate' and var('enable_candidate_pricing', false), tags=['pricing']) }}
-- Independent 45-digit decimal derivation of 1036 / exact m3-per-ft3 / 1e6.
-- Tolerance covers native FLOAT64 evaluation, not another energy assumption.
select * from {{ ref('fct_reference_valuation_month') }}
where abs(gas_energy_factor_mmbtu_per_m3-0.03658599472346217949945377872674672)>1e-15
   or (gas_estimated_mmbtu is not null and
       abs(gas_estimated_mmbtu-gas_volume_m3*0.03658599472346217949945377872674672)
       >greatest(1e-9,abs(gas_estimated_mmbtu)*1e-12))
