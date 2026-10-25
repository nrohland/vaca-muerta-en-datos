# Precios y valorización candidatos

Estado: implementación aislada con build y conciliación real aprobados técnicamente el 12 de octubre de 2026. Integración al frontend pendiente; no constituye aprobación de publicación. Ver docs/evidence/orchestration/README.md.

## Fuente y corte

EIA Europe Brent Spot Price FOB mensual, USD/bbl. Importar HTML oficial retenido como bytes sin modificaciones. Registrar URL, fecha de publicación, recuperación UTC real, SHA-256 de respuesta y NDJSON, snapshot_id igual al hash de respuesta y accepted_cutoff de mes aceptado por pipeline. La descarga no cambia el corte. Octubre no está publicado y septiembre no se incorpora a un candidato de agosto.

`prepare_reference_prices.py` valida parser, fecha de publicación y presencia del precio del corte, produce filas inmutables y manifest. `load_reference_prices.py` vuelve a validar hash, tipos, unicidad, calendario y metadatos; sólo escribe con `--apply` a tabla exacta `vaca-muerta-pulse.raw_cap4_candidate_dev.monthly_reference_price`. WRITE_TRUNCATE reemplaza exclusivamente ese candidato de precio, nunca producción ni tablas históricas. No usar seeds para cotizaciones dinámicas. El archivo de respuesta y manifest se retienen como evidencia del run; no commitear credenciales.

## Transformación

Modelos y tests sólo habilitados si target=candidate y `enable_candidate_pricing: true`. `stg_monthly_reference_price` no selecciona entre revisiones: el raw es un snapshot revisado único. `fct_reference_valuation_month` grano pozo-mes, un join del mismo mes; volumen bbl = prod_pet_m3 × 6.28981077. Precio válido requiere número finito >0, producto oil, benchmark EIA_BRENT_MONTHLY, USD/bbl y mes no posterior al corte. Volumen ausente/negativo → NULL. No aplicar forward fill ni interpolación. Valor = volumen bbl × Brent del mismo mes. Es valor bruto de referencia, no ingreso realizado ni precio efectivo por operador.

`fct_reference_valuation_entity_month` grano tipo-entidad × entidad × mes: basin/company/area, incluyendo grupo explícito de IDs ausentes. Toda agregación exige disponibilidad de todas sus filas. Comparaciones usan joins calendario contra mes anterior/año anterior; huecos no se saltan. YTD exige enero hasta mes actual con todos los meses presentes y todos los valores válidos. Base cero → porcentaje NULL. No suponer que ausencia de una empresa equivale a volumen cero.

## Gas

La decisión anterior de conservar gas NULL fue reemplazada por autorización de referencia internacional Henry Hub y escenario energético explícito el 12 de octubre de 2026. Ver [spec 017](017-international-gas-reference.md). El nuevo manifest v2 incluye ambos productos, con hashes y fechas propios; gas usa USD/MMBTU y basis versionado, y dbt calcula valor estimado del mismo mes. No se presenta como poder calorífico medido ni ingreso realizado.

## Gates y integración

Tests: unidades/hash/metadatos, unicidad de producto × mes, precio requerido, NULL coherente con flags, multiplicación, gas de referencia y basis explícito, conciliación empresa-área-cuenca y tests de transformación de huecos/bases cero. Build candidato no cambia artefactos públicos. Next conserva los volúmenes del snapshot multianual revisado y usa ambos benchmarks frescos con el helper compartido; migrar todos los exportadores a marts sigue siendo parte del cierre integrado; esta implementación no declara migración completa del consumidor.
