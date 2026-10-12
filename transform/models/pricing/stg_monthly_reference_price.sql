{{ config(enabled=target.name == 'candidate' and var('enable_candidate_pricing', false), materialized='view', schema='stg', tags=['pricing']) }}
select
    product, periodo, benchmark, price, currency, price_unit,
    source_url, source_sha256, source_updated_at, retrieved_at,
    accepted_cutoff, snapshot_id, energy_basis,
    price > 0 and not is_nan(price) and not is_inf(price)
      and currency = 'USD' and price_unit = 'bbl'
      and product = 'oil' and benchmark = 'EIA_BRENT_MONTHLY'
      and periodo <= accepted_cutoff as price_valid
from {{ source('candidate_pricing', 'monthly_reference_price') }}
