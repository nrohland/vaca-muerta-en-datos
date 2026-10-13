{{ config(enabled=target.name == 'candidate' and var('enable_dashboard_export', false)) }}
select dimension,entity_id,fluid,periodo,'invalid_row' as error
from {{ ref('fct_dashboard_month') }}
where volume < 0 or is_nan(volume) or is_inf(volume)
 or valid_volume_rows != reported_well_rows or source_loaded_at is null
 or periodo not between {{ candidate_start_period_sql() }} and {{ candidate_period_sql() }}
 or estimated_value_usd < 0 or (estimated_value_usd is null and estimated_daily_value_usd is not null)
 or (fluid='gas' and energy_basis != '{{ gas_reference_energy_basis_id() }}')
union all
select dimension,entity_id,fluid,periodo,'duplicate_row'
from {{ ref('fct_dashboard_month') }} group by 1,2,3,4 having count(*) != 1
