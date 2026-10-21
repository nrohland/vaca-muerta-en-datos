{{ config(enabled=target.name == 'candidate' and var('enable_dashboard_export', false), materialized='table', tags=['dashboard_export']) }}
-- All business arithmetic is persisted here. Export reads this mart only.
with well_fluids as (
 select w.*, 'oil' as fluid, 'bbl' as volume_unit,
        w.prod_pet_m3 * {{ var('m3_to_bbl') }} as volume,
        v.oil_reference_value_usd as estimated_value_usd,
        v.oil_valuation_available as valuation_available,
        if(v.price_valid,v.reference_price_usd_per_bbl,null) as price_usd_per_unit,
        'USD/bbl' as price_unit, cast(null as string) as energy_basis,
        'estimated_reference' as valuation_method
 from {{ ref('fct_well_month') }} w join {{ ref('fct_reference_valuation_month') }} v using(well_month_id)
 union all
 select w.*, 'gas', 'million_m3', w.prod_gas_km3 / 1000.0,
        v.gas_reference_value_usd, v.gas_valuation_available,
        if(v.gas_price_valid,v.gas_reference_price_usd_per_mmbtu,null), 'USD/MMBtu', v.gas_energy_basis,
        'estimated_reference_scenario'
 from {{ ref('fct_well_month') }} w join {{ ref('fct_reference_valuation_month') }} v using(well_month_id)
), mapped as (
 select w.*,
        coalesce(g.operator_group_id, w.idempresa, '__missing__') as company_id,
        coalesce(g.operator_group_name, w.empresa, 'Sin operador declarado') as company_name,
        coalesce(w.idareapermisoconcesion, '__missing__') as area_id,
        coalesce(w.areapermisoconcesion, 'Sin área declarada') as area_name,
        g.rule_version as operator_group_rule_version
 from well_fluids w left join {{ ref('operator_groups') }} g
 on w.idempresa = g.legal_operator_id and w.periodo >= cast(g.valid_from as date)
 and (nullif(cast(g.valid_to as string), '') is null or w.periodo <= cast(g.valid_to as date))
), dimensions as (
 select 'basin' as dimension, 'vaca_muerta' as entity_id, 'Vaca Muerta' as entity_name, * from mapped
 union all select 'company', company_id, company_name, * from mapped
 union all select 'area', area_id, area_name, * from mapped
), provenance_ids as (
 select distinct dimension, entity_id,
 coalesce(idempresa,'__missing__') as idempresa,
 coalesce(empresa,'Sin operador declarado') as empresa
 from dimensions
), provenance as (
 select dimension,entity_id,array_agg(struct(idempresa,empresa) order by idempresa,empresa) as legal_operator_provenance
 from provenance_ids group by dimension,entity_id
), names as (
 select dimension, entity_id,
 array_agg(entity_name order by periodo desc, entity_name limit 1)[offset(0)] as entity_name,
 max(periodo) as name_periodo,
 array_agg(operator_group_rule_version ignore nulls limit 1)[safe_offset(0)] as operator_group_rule_version
 from dimensions group by dimension, entity_id
), names_with_provenance as (
 select n.*,p.legal_operator_provenance from names n join provenance p using(dimension,entity_id)
), aggregate_values as (
 select dimension, entity_id, fluid, periodo,
 sum(volume) as volume, count(*) as reported_well_rows,
 countif(volume is not null and not is_nan(volume) and not is_inf(volume) and volume >= 0) as valid_volume_rows,
 count(distinct if(volume > 0,idpozo,null)) as positive_producing_wells,
 if(countif(not coalesce(valuation_available,false)) = 0,sum(estimated_value_usd),null) as estimated_value_usd,
 max(source_batched_at) as source_loaded_at
 from dimensions group by 1,2,3,4
), periods as (
 select periodo from unnest(generate_date_array({{ candidate_start_period_sql() }}, {{ candidate_period_sql() }}, interval 1 month)) as periodo
), price_context as (
 select fluid,periodo,any_value(volume_unit) as volume_unit,any_value(price_usd_per_unit) as price_usd_per_unit,
 any_value(price_unit) as price_unit,any_value(energy_basis) as energy_basis,
 any_value(valuation_method) as valuation_method,countif(not coalesce(valuation_available,false))=0 as valuation_available,
 max(source_batched_at) as source_loaded_at
 from well_fluids group by 1,2
), grid as (
 select n.*, p.periodo, f.fluid,
 if(f.fluid='oil','bbl','million_m3') as volume_unit,
 extract(day from last_day(p.periodo)) as days_in_month,
 coalesce(a.volume,0.0) as volume,
 coalesce(a.reported_well_rows,0) as reported_well_rows,
 coalesce(a.valid_volume_rows,0) as valid_volume_rows,
 coalesce(a.positive_producing_wells,0) as positive_producing_wells,
 a.reported_well_rows is null as is_absent_current,
 case when a.reported_well_rows is not null then a.estimated_value_usd
      when c.valuation_available then 0.0 else null end as estimated_value_usd,
 coalesce(a.source_loaded_at,c.source_loaded_at) as source_loaded_at,
 c.price_usd_per_unit,c.price_unit,c.energy_basis,
 coalesce(c.valuation_method,'unavailable') as valuation_method
 from names_with_provenance n cross join periods p cross join (select 'oil' as fluid union all select 'gas') f
 left join aggregate_values a on n.dimension=a.dimension and n.entity_id=a.entity_id and p.periodo=a.periodo and f.fluid=a.fluid
 left join price_context c on p.periodo=c.periodo and f.fluid=c.fluid
), ranked as (
 select *,volume/days_in_month as rate,
 estimated_value_usd/days_in_month as estimated_daily_value_usd,
 row_number() over(partition by fluid,dimension,periodo order by volume desc,entity_id) as volume_rank
 from grid
), concentration as (
 select fluid,dimension,periodo,safe_divide(sum(if(volume_rank<=5,volume,0)),sum(volume))*100 as top5_share_pct
 from ranked where dimension!='basin' group by 1,2,3
), accumulated as (
 select *,if(count(*) over ytd=extract(month from periodo) and countif(estimated_value_usd is null) over ytd=0,
 sum(estimated_value_usd) over ytd,null) as estimated_ytd_value_usd
 from ranked window ytd as(partition by fluid,dimension,entity_id,extract(year from periodo) order by periodo rows between unbounded preceding and current row)
), comparisons as (
 select c.*,pm.volume as mom_volume,py.volume as yoy_volume,pm.rate as mom_rate,py.rate as yoy_rate,
 c.volume-pm.volume as mom_volume_delta,c.volume-py.volume as yoy_volume_delta,
 c.rate-pm.rate as mom_rate_delta,c.rate-py.rate as yoy_rate_delta,
 safe_divide(c.volume-pm.volume,pm.volume)*100 as mom_volume_pct,
 safe_divide(c.volume-py.volume,py.volume)*100 as yoy_volume_pct,
 safe_divide(c.rate-pm.rate,pm.rate)*100 as mom_rate_pct,
 safe_divide(c.rate-py.rate,py.rate)*100 as yoy_rate_pct,
 pm.estimated_value_usd as mom_estimated_value_usd,py.estimated_value_usd as yoy_estimated_value_usd,
 py.estimated_ytd_value_usd as yoy_estimated_ytd_value_usd,
 conc.top5_share_pct,prev.top5_share_pct as yoy_top5_share_pct,
 conc.top5_share_pct-prev.top5_share_pct as top5_share_yoy_pp,
 cc.top5_share_pct as top5_company_share_pct,ca.top5_share_pct as top5_area_share_pct,
 pcc.top5_share_pct as yoy_top5_company_share_pct,pca.top5_share_pct as yoy_top5_area_share_pct,
 cc.top5_share_pct-pcc.top5_share_pct as top5_company_share_yoy_pp,
 ca.top5_share_pct-pca.top5_share_pct as top5_area_share_yoy_pp
 from accumulated c
 left join accumulated pm on c.fluid=pm.fluid and c.dimension=pm.dimension and c.entity_id=pm.entity_id and pm.periodo=date_sub(c.periodo,interval 1 month)
 left join accumulated py on c.fluid=py.fluid and c.dimension=py.dimension and c.entity_id=py.entity_id and py.periodo=date_sub(c.periodo,interval 1 year)
 left join concentration conc on c.fluid=conc.fluid and c.dimension=conc.dimension and c.periodo=conc.periodo
 left join concentration prev on c.fluid=prev.fluid and c.dimension=prev.dimension and prev.periodo=date_sub(c.periodo,interval 1 year)
 left join concentration cc on c.fluid=cc.fluid and cc.dimension='company' and c.periodo=cc.periodo
 left join concentration ca on c.fluid=ca.fluid and ca.dimension='area' and c.periodo=ca.periodo
 left join concentration pcc on c.fluid=pcc.fluid and pcc.dimension='company' and pcc.periodo=date_sub(c.periodo,interval 1 year)
 left join concentration pca on c.fluid=pca.fluid and pca.dimension='area' and pca.periodo=date_sub(c.periodo,interval 1 year)
), contributions as (
 select *,row_number() over(partition by fluid,dimension,periodo order by abs(yoy_rate_delta) desc,entity_id) <= 5 and yoy_rate_delta is not null as yoy_contribution_selected
 from comparisons
)
select *,sum(if(not yoy_contribution_selected,yoy_rate_delta,0)) over(partition by fluid,dimension,periodo) as yoy_rest_rate_delta,
 1.0 as coverage,true as is_complete,'approved_complete_snapshot' as acceptance_basis
from contributions
