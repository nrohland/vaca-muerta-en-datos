{{ config(enabled=target.name == 'candidate' and var('enable_dashboard_export', false)) }}
with expected as(select periodo,fluid from unnest(generate_date_array({{ candidate_start_period_sql() }},{{ candidate_period_sql() }},interval 1 month)) as periodo
 cross join (select 'oil' as fluid union all select 'gas'))
select e.* from expected e left join {{ ref('fct_dashboard_month') }} d
on d.dimension='basin' and d.periodo=e.periodo and d.fluid=e.fluid
where d.periodo is null or d.reported_well_rows=0
