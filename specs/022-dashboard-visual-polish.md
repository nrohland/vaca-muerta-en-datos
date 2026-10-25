# Iteración visual integrada

Reutilizar KpiCard, ChartCard, Change y filtros globales. Separar escalas K/M y unidades en tipografía secundaria, sin recalcular métricas. Verde positivo, rojo negativo y ausencia/cero neutral. Preservar ES/EN, tema y contexto de navegación.

La metodología Henry Hub aparece dentro del KPI monetario mediante el mecanismo de información existente. Quitar el banner general; conservar los avisos materiales de datos/precios ausentes.

Actividad: conteo mensual en columnas desde cero y referencia al mes base exacto; cambio neto divergente; promedio por pozo en dos barras horizontales (mes base y actual) desde cero. Un promedio ausente no es cero. No afirmar eficiencia individual, altas/bajas ni tiempo efectivo. Tabla compacta con expansión y CSV completo.

Áreas: mapa de referencia de Neuquén junto al ranking, con datos productivos existentes y polígonos oficiales verificados; ver [proveniencia y límites](../docs/geography/README.md). Nuevo origen geográfico separado del snapshot de producción. No agrega relaciones operador–área ni modifica cortes/precios. Área sin geometría permanece en ranking/detalle. Cobertura y vigencia desconocida explícitas.

Optimizar sólo logos raster usados a tamaños de UI, manteniendo originales y procedencia. Ningún logo faltante se inventa. Revisar desktop/mobile, temas, idiomas, filtros y navegación; tests de cálculo/contrato y suite de navegador.

## Dirección elegida después de la revisión editorial independiente

El usuario eligió símbolos proporcionales sobre concesiones neutras. El mapa pasa a ser una vista navegable MapLibre; radio = radio máximo × raíz(valor / máximo), sin mínimo artificial para valores positivos. La superficie representa magnitud física o USD estimados. Tres referencias numéricas visibles, estados cero/sin dato separados y anclajes interiores verificables en el polígono de mayor superficie de cada concesión. No representan pozos.

Mapa y ranking preceden a las tarjetas, cuyo alcance de área seleccionada se anuncia. Se distinguen registros del mes, catálogo histórico y geometrías disponibles. Cámara y controles Argentina/áreas conservan contexto al cambiar selección, idioma, fluido o modo. Sin agrupaciones que sumen o inventen pozos. El zoom permite separar áreas cercanas.

MapLibre se importa al entrar a Áreas; no se agrega al JS inicial de Resumen. Fondo OpenStreetMap raster sobre HTTPS, atribución visible, caché estándar y sin prefetch masivo. CI intercepta teselas para comprobar geometría/interacción sin tráfico automatizado al servicio comunitario. La revisión humana inspecciona el fondo real. No requiere API key ni una cuenta de facturación; el proveedor de teselas ofrece disponibilidad de mejor esfuerzo y puede sustituirse si la operación pública exige otro SLA.

## Revisión de auditoría

El resumen sigue el modo global volumen/valor con una sola magnitud y eje visible. Detalle permite seleccionar producción o USD sin superponer escalas. Pozos sólo presenta magnitud física. Metodología expandida libera la altura del shell para no recortar rankings. Fecha de producción e ingesta se muestran junto a filtros; validación de integridad no certifica frescura upstream.
