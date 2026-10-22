# Revisión documental previa a compartir — 20 de octubre de 2026

## Alcance y correcciones

Se revisaron README principal, índice de documentación, frontend, extracción, pipeline, despliegue y galería. Arquitectura y ADRs tienen una revisión separada. La documentación describe **Vaca Muerta en Datos**, las cinco vistas, preguntas de negocio, tecnologías y decisiones del flujo Python → Parquet → BigQuery → dbt → snapshot → Next.js/React/Recharts/MapLibre → Vercel estático.

Se corrigió una contradicción en extracción: el histórico vigente sí usa Parquet; NDJSON sólo se conserva en el helper monoanual y contratos pequeños. Se separó el despliegue público del frontend de la ejecución del pipeline. Extracción y monitor están pausados; el corte sigue siendo agosto de 2026 y el snapshot es preliminar. El chat de datos sigue siendo una etapa futura. Las cifras de tests de las evidencias anteriores se identifican como históricas, sin presentarlas como una ejecución de hoy.

La portada y la galería desktop se renovaron con las capturas públicas de la revisión del 20 de octubre, commit `cb62ef645d6ffeac4943afa65c5b267203d7f090`. También se renovaron Operadores, Áreas y Actividad mobile. Las otras dos capturas mobile conservan procedencia histórica explícita. Conversión PNG → JPEG a calidad 85 mediante `sips`; imágenes entre 155 y 334 KiB aproximadamente, sin modificar contenido visual.

## Verificaciones realizadas

- **62 enlaces relativos** en los siete documentos de entrada revisados: todos resuelven a archivos existentes. No se verificaron automáticamente destinos externos ni anclas Markdown.
- `git diff --check`: correcto.
- Stack contrastado con `apps/web/package.json`, formatos con `source_history_pipeline.py` y entrega con `lib/delivery.ts`/`next.config.ts`.
- Revisión acotada de credenciales sobre **290 archivos de texto versionados de hasta 2 MB**: sin coincidencias de claves privadas, tokens GitHub, claves API Google, accesos AWS ni documentos service account; sin nombres de archivo sensibles versionados. Se imprimieron sólo rutas/categorías, nunca valores. No equivale a una auditoría del historial completo ni cubre cualquier secreto posible.
- No se ejecutó ingesta cloud, no se alteraron datos, permisos, facturación ni configuración del sitio. Cambios documentales e imágenes; los checks funcionales del producto corresponden a la integración de esta auditoría.

## Texto breve para compartir

Construí **Vaca Muerta en Datos**, un producto analítico que transforma declaraciones oficiales de producción en una experiencia interactiva para explorar petróleo y gas: evolución histórica, operadores, áreas geográficas y pozos productivos. Incluye cinco vistas, filtros persistentes, comparaciones mensuales e interanuales, referencias internacionales de valor, mapa, ES/EN y tema claro/oscuro.

La solución combina Python y Parquet para extracción, BigQuery como warehouse, dbt para modelado y controles, y Next.js/React/TypeScript con Recharts y MapLibre en el frontend estático de Vercel. El navegador consume agregados validados y no requiere credenciales del warehouse. La demo es preliminar, con datos de enero de 2023 a agosto de 2026; la actualización automática está pausada.

[Dashboard](https://vaca-muerta-en-datos.vercel.app) · [Repositorio](https://github.com/nrohland/vaca-muerta-en-datos) · [README](../../../README.md) · [Arquitectura](../../architecture.md) · [Capturas](../../screenshots/README.md)
