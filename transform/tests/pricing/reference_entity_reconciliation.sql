{{ config(enabled=target.name == 'candidate' and var('enable_candidate_pricing', false), tags=['pricing']) }}
with sums as (
    select periodo, entity_type,
        sum(oil_volume_bbl) as volume,
        if(countif(not oil_valuation_available)=0,sum(oil_reference_value_usd),null) as value
    from {{ ref('fct_reference_valuation_entity_month') }}
    group by 1,2
)
select s.* from sums s join sums b using(periodo)
where b.entity_type='basin' and s.entity_type!='basin'
 and (abs(s.volume-b.volume)>greatest(0.000001,abs(b.volume)*1e-12)
      or (s.value is null)!=(b.value is null)
      or abs(s.value-b.value)>greatest(0.01,abs(b.value)*1e-12))
