# Precios y valorización candidatos

Estado: implementación aislada con build y conciliación real aprobados técnicamente el 12 de octubre de 2026. Integración al frontend pendiente; no constituye aprobación de publicación. Ver docs/evidence/orchestration/README.md.

## Fuente y corte

EIA Europe Brent Spot Price FOB mensual, USD/bbl. Importar HTML oficial retenido como bytes sin modificaciones. Registrar URL, fecha de publicación, recuperación UTC real, SHA-256 de respuesta y NDJSON, snapshot_id igual al hash de respuesta y accepted_cutoff de mes aceptado por pipeline. La descarga no cambia el corte. Octubre no está publicado y septiembre no se incorpora a un candidato de agosto.

`prepare_reference_prices.py` valida parser, fecha de publicación y presencia del precio del corte, produce filas inmutables y manifest. `load_reference_prices.py` vuelve a validar hash, tipos, unicidad, calendario y metadatos; sólo escribe con `--apply` a tabla exacta `vaca-muerta-pulse.raw_cap4_candidate_dev.monthly_reference_price`. WRITE_TRUNCATE reemplaza exclusivamente ese candidato de precio, nunca producción ni tablas históricas. No usar seeds para cotizaciones dinámicas. El archivo de respuesta y manifest se retienen como evidencia del run; no commitear credenciales.

## Transformación

Modelos y tests sólo habilitados si target=candidate y `enable_candidate_pricing: true`. `stg_monthly_reference_price` no selecciona entre revisiones: el raw es un snapshot revisado único. `fct_reference_valuation_month` grano pozo-mes, un join del mismo mes; volumen bbl = prod_pet_m3 × 6.28981077. Precio válido requiere número finito >0, producto oil, benchmark EIA_BRENT_MONTHLY, USD/bbl y mes no posterior al corte. Volumen ausente/negativo → NULL. No aplicar forward fill ni interpolación. Valor = volumen bbl × Brent del mismo mes. Es valor bruto de referencia, no ingreso realizado ni precio efectivo por operador.

`fct_reference_valuation_entity_month` grano tipo-entidad × entidad × mes: basin/company/area, incluyendo grupo explícito de IDs ausentes. Toda agregación exige disponibilidad de todas sus filas. Comparaciones usan joins calendario contra mes anterior/año anterior; huecos no se saltan. YTD exige enero hasta mes actual con todos los meses presentes y todos los valores válidos. Base cero → porcentaje NULL. No suponer que ausencia de una empresa equivale a volumen cero.

## Gas

Gas USD queda NULL y `gas_valuation_available=false`. Ni Brent ni Henry Hub son sustitutos silenciosos. PPP Cuenca Neuquina/TOTAL podría registrarse como benchmark separado cuando se verifique la descarga oficial, pero no hay compatibilidad demostrada entre volúmenes CapIV y gas de venta normalizado a 9300 kcal/m³. Ese bloqueo persiste aunque aparezcan precios de agosto. No cargar factor térmico arbitrario.

## Gates y integración

Tests: unidades/hash/metadatos, unicidad de mes, precio requerido, NULL coherente con flags, multiplicación, gas deshabilitado, conciliación empresa-área-cuenca y tests de transformación de huecos/bases cero. Build candidato no cambia artefactos públicos. Next sigue usando snapshot anterior hasta cierre integrado autorizado; esta implementación no declara migración completa del consumidor.
