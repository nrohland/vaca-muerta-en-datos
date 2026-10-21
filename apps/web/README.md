# Frontend — Vaca Muerta en Datos

Aplicación Next.js estática publicada en [Vercel](https://vaca-muerta-en-datos.vercel.app), con Resumen, Producción, Operadores, Áreas y Actividad. Usa agregados reales del snapshot candidato y componentes compartidos; no necesita credenciales del warehouse para ejecutarse. El alcance y los resultados de cada iteración se documentan en `specs/` y `docs/evidence/`.

## Ejecutar

Node.js 22.13+ y npm. Desde `apps/web`:

```sh
npm ci
npm run dev
```

Abrir `http://localhost:3000/vaca-muerta-pulse/`.

```sh
npm run typecheck
npm test
npm run build
npx playwright install chromium
npm run test:browser
```

El build estático queda en `out/`. El runner de navegador requiere un entorno compatible y un puerto disponible. `EVIDENCE_DIR` permite dirigir las capturas; los reportes de evidencia deben indicar qué suite y qué inspección visual se ejecutaron realmente. La rama de despliegue configurada en Vercel actualiza la demo pública; las ramas de trabajo generan previews protegidas. Ver [configuración](../../docs/vercel.md).

## Componentes y navegación

Stack instalado: Next.js 16, React 19, TypeScript 7, Recharts 3 y MapLibre 6. `app/dashboard-components.tsx` contiene `KpiCard`, `ModuleCard`, `ChartCard`, `RankingCard`; `app/global-filters.tsx` contiene `GlobalFilters`; `app/globals.css` comparte tema, espaciado y responsive. analytics-ui guía jerarquía, componentes comunes y escalas veraces.

El mismo concepto mantiene color y comportamiento entre pestañas: petróleo azul, gas violeta, monetario ámbar. Variaciones positivas verdes y negativas rojas siguen la convención del producto. Rankings de participación usan escala real 0–100%; etiquetas, unidades, tooltips y tablas permiten leer cifras exactas.

`lib/navigation.ts` conserva fluido, período, modo volumen/valor y comparación MoM/YoY, además de vista e ID de entidad en deep links. `lib/i18n.ts` y `lib/locale.tsx` centralizan ES/EN y formatos Intl; la preferencia de idioma tiene fallback español. Las vistas mantienen claro/oscuro, navegación atrás/adelante y responsive.

## Contrato de datos

`lib/contract.ts` verifica release, SHA-256, manifiesto, cobertura y corte antes de mostrar métricas. `public/data/release.json` contiene agregados, nunca registros raw. El candidato acepta **agosto de 2026** como máximo; septiembre parcial queda excluido. Sin un `approval.json` válido se muestra **Preliminar**. Validación técnica no equivale a aprobación de publicación.

Petróleo: bbl y bbl/d; gas: MMm³ y MMm³/d. Tasa = volumen mensual / días calendario. Pozos productivos = IDs únicos con producción positiva del fluido. No hay contador live. Permisos/concesiones y transferencias pueden afectar rankings.

`lib/metrics.ts` lee los valores USD ya calculados por dbt: mensual, diario, bases exactas MoM/YoY y YTD de calendario completo. El release declara productor `dbt` y modelo `fct_dashboard_month`; la UI no multiplica volumen por precio. `prices.json` contiene Brent y Henry Hub oficiales para mostrar las cotizaciones y metodología; `valuation-manifest.json` liga sus bytes con el release. Gas USD explicita el escenario energético EIA de 1.036 BTU/pie³, no calorificidad medida de Vaca Muerta ni ingresos realizados. Sin valor persistido válido se muestra indisponibilidad; un fallo del archivo auxiliar de cotizaciones no borra valores ya validados en el snapshot.

Producción profundiza en historia, acumulados comparables, años calendario, cambios absolutos y tabla. Operadores y Áreas profundizan ranking y entidad. Actividad usa conteos y promedio por pozo y día calendario sin inferir productividad por día efectivo, altas/bajas o completaciones sin fuentes válidas.

## Evidencia y límites

La [revisión histórica del snapshot](../../docs/evidence/snapshot-integration/README.md) registra cálculos, navegación, capturas desktop/mobile y restricciones de Playwright. La [orquestación/export](../../docs/evidence/orchestration-export/README.md) valida el consumidor sobre el bundle generado. [Capturas de las cinco vistas](../../docs/screenshots/README.md).

La extracción y transformación son reproducibles. La demo pública sirve el snapshot incluido en Git; la extracción automática permanece pausada por conectividad con la fuente. [Arquitectura](../../docs/architecture.md). No afirmar frescura o publicación por una fecha de build.

## Conexión histórica validada

El snapshot actual tiene 44 meses (enero 2023–agosto 2026), 88 filas de cuenca y 10.208 de entidades; pesa 16,75 MiB sin comprimir. Se conserva el grano ID × fluido × mes y los ceros explícitos de entidades ausentes dentro de meses técnicamente aceptados. “Áreas reportadas” cuenta sólo áreas con registros del mes, aunque el ranking conserve todo el catálogo histórico. [Resultados actuales y límites](../../docs/evidence/snapshot-integration/README.md).

`apps/web/scripts/check_snapshot.mjs --data-dir ...` valida bundles generados con los contratos del consumidor y sus hashes antes de copiar assets a un checkout temporal de CI. El pipeline histórico ejecuta ese checker después de exportar; el workflow continúa con typecheck/tests/build sin despliegue.

## Rendimiento y superficie de acceso

Los filtros globales se definen en `app/global-filters.tsx`, separados del módulo de gráficos. Cada vista se descarga cuando se necesita; el build limita el JavaScript moderno inicial a 200 KiB gzip. El build genera shards comprimidos y direccionados por hash para cargar el resumen primero y el detalle por fluido/dimensión cuando se necesita. `lib/delivery.ts` valida tamaños y hashes; `scripts/check_performance.mjs` controla presupuestos. [Mediciones, decisiones y límites](PERFORMANCE.md).

La configuración propuesta de Vercel asigna caché inmutable a shards con hash y revalidación a manifiestos/precios de nombre estable; sus headers efectivos requieren verificar el despliegue. El render no ejecuta SQL ni realiza requests a BigQuery: las consultas analíticas y la valorización se resuelven antes de exportar. El mapa consume geometrías públicas de referencia; los logos se sirven como assets del sitio.

El chat de datos no está implementado: su diseño es una etapa futura. Ninguna clave de modelo, GCP o extracción es necesaria para usar este frontend.

