{{ config(enabled=target.name == 'candidate' and var('enable_candidate_pricing', false), tags=['pricing']) }}
select * from {{ ref('fct_reference_valuation_month') }}
where gas_reference_value_usd is not null or gas_valuation_available
   or oil_valuation_available != (oil_reference_value_usd is not null)
   or (oil_valuation_available and abs(oil_reference_value_usd - oil_volume_bbl * reference_price_usd_per_bbl) > greatest(0.01, abs(oil_reference_value_usd)*1e-12))
   or (not price_valid and oil_reference_value_usd is not null)
