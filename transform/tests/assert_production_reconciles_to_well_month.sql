-- Fails (returns rows) if Vaca Muerta en Datos oil does not match fct_well_month
-- for the same latest periodo and Pulse cut.
-- Grain of the mart is one row; this is the Hito 2 reconciliation test.

select
    production.periodo,
    production.prod_pet_m3 as production_prod_pet_m3,
    well_month.prod_pet_m3 as well_month_prod_pet_m3
from {{ ref("fct_production_rate") }} as production
inner join
    (
        select periodo, sum(prod_pet_m3) as prod_pet_m3
        from {{ ref("fct_well_month") }}
        group by 1
    ) as well_month
    on production.periodo = well_month.periodo
where abs(production.prod_pet_m3 - well_month.prod_pet_m3) > 0.0001
