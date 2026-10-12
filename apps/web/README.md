# Frontend — Vaca Muerta en Datos

Aplicación Next.js de revisión con Resumen como base aprobada y vistas de Producción, Operadores, Áreas y Actividad. Usa agregados reales del snapshot candidato y componentes compartidos; no necesita credenciales del warehouse para ejecutarse. El alcance y los resultados de cada iteración se documentan en `specs/` y `docs/evidence/`.

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

El build estático queda en `out/`. El runner de navegador requiere un entorno compatible y un puerto disponible. `EVIDENCE_DIR` permite dirigir las capturas; los reportes de evidencia deben indicar qué suite y qué inspección visual se ejecutaron realmente. No hay despliegue automático.

## Componentes y navegación

Stack instalado: Next.js 16, React 19, TypeScript 7 y Recharts 3. Tremor pertenece al plan inicial, no al package actual. `app/dashboard-components.tsx` contiene `KpiCard`, `ModuleCard`, `ChartCard`, `RankingCard` y `GlobalFilters`; `app/globals.css` comparte tema, espaciado y responsive. analytics-ui guía jerarquía, componentes comunes y escalas veraces.

El mismo concepto mantiene color y comportamiento entre pestañas: petróleo azul, gas violeta, monetario ámbar. Variaciones positivas verdes y negativas rojas siguen la convención del producto. Rankings de participación usan escala real 0–100%; etiquetas, unidades, tooltips y tablas permiten leer cifras exactas.

`lib/navigation.ts` conserva fluido, período, modo volumen/valor y comparación MoM/YoY, además de vista e ID de entidad en deep links. `lib/i18n.ts` y `lib/locale.tsx` centralizan ES/EN y formatos Intl; la preferencia de idioma tiene fallback español. Las vistas mantienen claro/oscuro, navegación atrás/adelante y responsive.

## Contrato de datos

`lib/contract.ts` verifica release, SHA-256, manifiesto, cobertura y corte antes de mostrar métricas. `public/data/release.json` contiene agregados, nunca registros raw. El candidato acepta **agosto de 2026** como máximo; septiembre parcial queda excluido. Sin un `approval.json` válido se muestra **Preliminar**. Validación técnica no equivale a aprobación de publicación.

Petróleo: bbl y bbl/d; gas: MMm³ y MMm³/d. Tasa = volumen mensual / días calendario. Pozos productivos = IDs únicos con producción positiva del fluido. No hay contador live. Permisos/concesiones y transferencias pueden afectar rankings.

`lib/metrics.ts` separa comparaciones y valorización de la presentación. Brent mensual EIA está en `prices.json`; `valuation-manifest.json` vincula sus bytes con el release. `scripts/import_brent.py` y `scripts/bind_valuation.py` de la raíz permiten importar y ligar artefactos. Cada período usa su precio; faltantes no se rellenan. Gas mantiene métricas físicas y explica la indisponibilidad de USD. Un error de precios no bloquea la lectura de volumen físico.

Producción profundiza en historia, acumulados comparables, años calendario, cambios absolutos y tabla. Operadores y Áreas profundizan ranking y entidad. Actividad usa conteos y promedio por pozo y día calendario sin inferir productividad por día efectivo, altas/bajas o completaciones sin fuentes válidas.

## Evidencia y límites

La [auditoría de datos/precios](../../docs/evidence/data-valuation/README.md) documenta conciliación y corte. La [evidencia de Resumen](../../docs/evidence/resumen/README.md) y [comparaciones/idiomas](../../docs/evidence/comparison-i18n/README.md) conserva resultados históricos; sus checks no prueban automáticamente las nuevas vistas. La integración final debe registrar nuevas capturas desktop/mobile y pruebas actuales.

La capa de datos tiene extracción mensual y transformación reproducible, pero no actualización/promoción end-to-end automática: [arquitectura](../../docs/architecture.md). No afirmar frescura o publicación por una fecha de build del frontend.
