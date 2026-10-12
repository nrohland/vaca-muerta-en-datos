{{ config(enabled=target.name == 'candidate' and var('enable_candidate_pricing', false), tags=['pricing']) }}
select * from {{ ref('stg_monthly_reference_price') }}
where not coalesce(price_valid, false)
   or source_sha256 is null or not regexp_contains(source_sha256, r'^[a-f0-9]{64}$')
   or snapshot_id != source_sha256
   or source_url != 'https://www.eia.gov/dnav/pet/hist/leafhandler.ashx?f=m&n=pet&s=rbrte'
   or extract(day from periodo) != 1
   or source_updated_at is null or retrieved_at is null
   or source_updated_at > date(retrieved_at)
   or retrieved_at > current_timestamp()
   or energy_basis is not null
