{{ config(enabled=target.name == 'candidate' and var('enable_dashboard_export', false)) }}
with basin as (select * from {{ ref('fct_dashboard_month') }} where dimension='basin'),
 entities as (select fluid,periodo,dimension,sum(volume) as volume,
 if(countif(estimated_value_usd is null)=0,sum(estimated_value_usd),null) as estimated_value_usd
 from {{ ref('fct_dashboard_month') }} where dimension!='basin' group by 1,2,3)
select e.fluid,e.periodo,e.dimension from entities e join basin b using(fluid,periodo)
where abs(e.volume-b.volume)>greatest(1e-8,abs(b.volume)*1e-10)
 or (e.estimated_value_usd is null)!=(b.estimated_value_usd is null)
 or abs(e.estimated_value_usd-b.estimated_value_usd)>greatest(1e-6,abs(b.estimated_value_usd)*1e-10)
