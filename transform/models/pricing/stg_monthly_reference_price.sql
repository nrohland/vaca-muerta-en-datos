{{ config(enabled=target.name == 'candidate' and var('enable_candidate_pricing', false), materialized='view', schema='stg', tags=['pricing']) }}
select
    product, periodo, benchmark, price, currency, price_unit,
    source_url, source_sha256, source_updated_at, retrieved_at,
    accepted_cutoff, snapshot_id, energy_basis,
    coalesce(price > 0 and not is_nan(price) and not is_inf(price)
      and currency = 'USD' and periodo <= accepted_cutoff
      and ((product = 'oil' and benchmark = 'EIA_BRENT_MONTHLY'
            and price_unit = 'bbl' and energy_basis is null)
        or (product = 'gas' and benchmark = 'EIA_HENRY_HUB_MONTHLY'
            and upper(price_unit) = 'MMBTU'
            and energy_basis = '{{ gas_reference_energy_basis_id() }}')), false) as price_valid
from {{ source('candidate_pricing', 'monthly_reference_price') }}
