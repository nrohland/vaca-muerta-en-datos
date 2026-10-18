# Geometrías de áreas de Neuquén

Fuente: [Ministerio de Energía y Recursos Naturales de Neuquén](https://hidrocarburos.energianeuquen.gob.ar/gis), WFS `Hidrocarburos:Areas`. GeoJSON EPSG:4326 recuperado el 18 de octubre de 2026. El asset conserva SHA-256 del origen y paths derivados con proyección Web Mercator. No se guarda información de titulares u operadores.

Cruce estricto de `SIGLA` y `NOMBRE` contra código y nombre del catálogo (normalización de acentos, espacios y puntuación, sin matching aproximado): **68 de 88 áreas**. Se combinan bloques poligonales que tienen el mismo código/nombre verificado. Las 20 sin coincidencia permanecen en rankings y detalle. El mapa indica cobertura del período y del volumen; no representa toda Vaca Muerta ni todas las jurisdicciones.

La fecha de vigencia de los polígonos no está informada. Son geometrías de referencia, no límites reconstruidos para cada mes histórico ni un catastro legal. No se infieren relaciones operador–área desde los atributos actuales del WFS.

Para regenerar, descargar públicamente GeoJSON del endpoint `https://hidrocarburos.energianeuquen.gob.ar/geoserver/Hidrocarburos/ows` con `service=WFS`, `version=1.0.0`, `request=GetFeature`, `typeName=Hidrocarburos:Areas`, `outputFormat=application/json`, `srsName=EPSG:4326`; luego:

```sh
python scripts/prepare_area_map.py --source /path/to/source.geojson --release apps/web/public/data/release.json --output apps/web/public/geography/areas.json --retrieved-at YYYY-MM-DD
```

Revisar cambios de código/nombre, cobertura y geometría antes de reemplazar el asset. El navegador sólo descarga el JSON local (~85 KB), sin basemap externo, API key ni consultas BigQuery. Intensidad según volumen/valor del período; valor faltante usa neutral, nunca cero. Hover y foco muestran nombre, cifra y mes; click/Enter/Space abren el detalle existente.

Contexto nacional: geometría de Argentina del [dataset Natural Earth, países 1:110m](https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-countries/) (campo ADM0_A3=ARG). Recuadro geográfico proyectado a partir del extent real de las áreas, sin ubicar puntos aproximados. La vista de contexto no es un catastro. El compilador recibe `--context-source` con `geojson/ne_110m_admin_0_countries.geojson` del repositorio público de Natural Earth; su SHA-256 queda en el asset. Se usa exclusivamente como referencia nacional, sin datos productivos adicionales.
