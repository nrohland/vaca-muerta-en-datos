{{ config(enabled=target.name == 'candidate' and var('enable_candidate_pricing', false), tags=['pricing']) }}
with sums as (
 select periodo, entity_type,
   sum(oil_volume_bbl) as oil_volume,
   if(countif(not oil_valuation_available)=0,sum(oil_reference_value_usd),null) as oil_value,
   sum(gas_volume_m3) as gas_volume,
   if(countif(not gas_valuation_available)=0,sum(gas_reference_value_usd),null) as gas_value
 from {{ ref('fct_reference_valuation_entity_month') }} group by 1,2
)
select s.* from sums s join sums b using(periodo)
where b.entity_type='basin' and s.entity_type!='basin' and (
 abs(s.oil_volume-b.oil_volume)>greatest(0.000001,abs(b.oil_volume)*1e-12)
 or (s.oil_value is null)!=(b.oil_value is null)
 or abs(s.oil_value-b.oil_value)>greatest(0.01,abs(b.oil_value)*1e-12)
 or abs(s.gas_volume-b.gas_volume)>greatest(0.000001,abs(b.gas_volume)*1e-12)
 or (s.gas_value is null)!=(b.gas_value is null)
 or abs(s.gas_value-b.gas_value)>greatest(0.01,abs(b.gas_value)*1e-12))
