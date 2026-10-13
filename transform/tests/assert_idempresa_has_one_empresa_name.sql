-- Legal/area names can change over history. Multiple names within the same
-- ID/month are ambiguous and must fail rather than be silently chosen.
select idempresa, periodo
from {{ ref("fct_well_month") }}
group by 1,2
having count(distinct empresa) > 1
