# Mapa de producción por concesión

Las geometrías vienen del [portal oficial de Neuquén](https://hidrocarburos.energianeuquen.gob.ar/gis), WFS `Hidrocarburos:Areas`, GeoJSON EPSG:4326 recuperado el 18 de octubre de 2026. El asset local conserva SHA-256, códigos y coordenadas; excluye titulares y operadores.

Cruce estricto de `SIGLA` y `NOMBRE` contra el catálogo, normalizando acentos, espacios y puntuación, sin aproximaciones: **68 de 88 áreas**. Los bloques con el mismo código verificado se combinan como MultiPolygon. Las 20 sin coincidencia permanecen en ranking y detalle. La cobertura de registros y volumen del período se informa separadamente del catálogo histórico.

Geometrías de referencia con vigencia desconocida: no reconstruyen los límites de cada mes ni reemplazan un catastro legal. No se infieren relaciones operador–área. Cada círculo se ancla dentro del polígono de mayor superficie de su concesión; un centroide que caiga fuera o dentro de un hueco se reemplaza por un punto interior obtenido con intersecciones de una línea horizontal. Los tests comprueban que todos los anclajes están dentro de su geometría. No son posiciones de pozos.

**Superficie del círculo proporcional al volumen**, no radio: `radio = 28 × sqrt(valor/máximo)`. Misma escala para todas las áreas ubicadas en el mes; cambia explícitamente al cambiar de período. USD usa el valor estimado del mart, sin calcular precios en el navegador. Cero y ausencia se distinguen con símbolos neutros. Leyenda con tres magnitudes; selección/hover/foco muestran nombre, cifra y mes. El ranking es el acceso equivalente para áreas pequeñas o no ubicadas.

MapLibre se descarga al abrir Áreas, con límites neutrales, controles de zoom, encuadre de Argentina y encuadre de áreas. El [fondo OpenStreetMap](https://operations.osmfoundation.org/policies/tiles/) usa HTTPS, atribución visible, Referer/caché normales del navegador y no tiene prefetch/offline. No hay API key ni facturación configurada. Servicio de mejor esfuerzo, sin garantía de disponibilidad; la caída del fondo conserva polígonos y cifras. La configuración del proveedor deberá revisarse para operación pública de mayor tráfico. Los tests de navegador interceptan las teselas y no recorren el servicio comunitario con automatización.

## Regenerar geometrías

Descargar el GeoJSON desde `https://hidrocarburos.energianeuquen.gob.ar/geoserver/Hidrocarburos/ows` con `service=WFS`, `version=1.0.0`, `request=GetFeature`, `typeName=Hidrocarburos:Areas`, `outputFormat=application/json`, `srsName=EPSG:4326`. Luego:

```sh
python scripts/prepare_area_map.py --source /path/to/source.geojson --release apps/web/public/data/release.json --output apps/web/public/geography/areas.json --retrieved-at YYYY-MM-DD
```

Revisar cobertura, geometrías y anclajes antes de reemplazar el asset. JSON ~155 KB cargado sólo en Áreas; no consulta BigQuery. Se retiró el recuadro estático de Argentina: el contexto nacional se obtiene con el control de encuadre del mapa real.
