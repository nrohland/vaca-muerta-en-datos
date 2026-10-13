-- Read-only historical dimension revision audit; retained baseline vs candidate.
-- Exact contractual oil conversion. Only grouped transitions leave the warehouse.
WITH old AS (
 SELECT CAST(idpozo AS INT64) idpozo,CAST(anio AS INT64) anio,CAST(mes AS INT64) mes,idempresa company_id,idareapermisoconcesion area_id,CAST(prod_pet AS FLOAT64)*6.28981077 oil_volume,CAST(prod_gas AS FLOAT64)/1000 gas_volume
 FROM `vaca-muerta-pulse.raw_cap4_candidate_20261009.produccion_pozo_mes`
 WHERE formacion='vaca muerta' AND tipo_de_recurso='NO CONVENCIONAL' AND anio BETWEEN 2023 AND 2026 AND (anio<2026 OR mes<=8)
), current_rows AS (
 SELECT idpozo,anio,mes,idempresa company_id,idareapermisoconcesion area_id,prod_pet_m3*6.28981077 oil_volume,prod_gas_km3/1000 gas_volume
 FROM `vaca-muerta-pulse.marts_cap4_candidate_dev.fct_well_month`
) SELECT FORMAT('%04d-%02d-01',o.anio,o.mes) periodo,
 COALESCE(o.company_id,'__missing__') old_company_id,COALESCE(n.company_id,'__missing__') new_company_id,
 COALESCE(o.area_id,'__missing__') old_area_id,COALESCE(n.area_id,'__missing__') new_area_id,
 COUNT(*) well_months,SUM(n.oil_volume) oil_volume,SUM(n.gas_volume) gas_volume,
 COUNTIF(n.oil_volume>0) oil_positive_wells,COUNTIF(n.gas_volume>0) gas_positive_wells,
 COUNTIF(o.oil_volume!=n.oil_volume OR o.gas_volume!=n.gas_volume) changed_volumes
 FROM old o JOIN current_rows n USING(idpozo,anio,mes)
 WHERE COALESCE(o.company_id,'__missing__')!=COALESCE(n.company_id,'__missing__') OR COALESCE(o.area_id,'__missing__')!=COALESCE(n.area_id,'__missing__')
 GROUP BY 1,2,3,4,5 ORDER BY 1,2,4
