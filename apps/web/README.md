# Vaca Muerta en datos — Resumen

Iteración de Hito 3 autorizada el 9 de octubre de 2026: solo Resumen. El frontend local editorial del 6 de octubre se incorpora por primera vez al repositorio con una nueva composición modular, usando la skill analytics-ui del ZIP adjunto (leída en el entorno de trabajo; sin modificar el harness).

## Ejecutar y verificar

Node.js 22.13+; validado con Node 25.8.1. Desde `apps/web`:

```sh
npm ci
npm run dev
```

Abrir http://localhost:3000/vaca-muerta-pulse/.

```sh
npm run typecheck
npm test
npm run build
npx playwright install chromium
npm run test:browser
```

El build estático queda en `out/`. Las pruebas de navegador sirven ese build localmente y generan capturas en `docs/evidence/resumen`. `EVIDENCE_DIR` permite cambiar la carpeta. No hay despliegue automático en esta entrega.

## Sistema de componentes

`app/dashboard-components.tsx` contiene KpiCard (principal/secundaria, contexto, unidad, estado, tooltip opcional), ModuleCard común, ChartCard, RankingCard y GlobalFilters. El tema está en `app/globals.css`. Producción diaria ocupa el doble que cada KPI secundario en desktop e incluye YoY/MoM en su propia card. Las otras tres cards muestran pozos productivos, volumen mensual y cuota Top 5 (campos existentes). Variaciones positivas verdes y negativas rojas por instrucción del usuario. Logos oficiales locales y nombres cortos por ID; razones sociales en tooltip. Overview cerrado sin scroll a 1440×900 y 1366×768; mobile apila módulos. Evolución usa Recharts, un trazo, tooltip y tabla accesible. Ver [ADR 0003](../../docs/adrs/0003-resumen-ui.md).

## Contrato de datos conservado

`lib/contract.ts`, `lib/operators.ts`, `public/data/release.json` y `manifest.json` son copias exactas de la entrega local del 6 de octubre. El release contiene agregados, no registros raw. Los cálculos de tasas, variaciones, ranking y pozos provienen de marts/export candidatos de #27, #29 y #31; no se cambian en este PR. El cliente verifica contrato, SHA-256 y manifiesto antes de mostrar métricas. La participación mostrada es volumen de entidad / volumen total; las barras usan escala real 0–100%. KPIs comparan tasas; YoY de ranking compara volumen mensual.

No se inventa aprobación: mientras no exista un `approval.json` válido se muestra Preliminar. Esto es una revisión del frontend sobre el snapshot oficial candidato, no promoción a producción. Petróleo: bbl/d y bbl mensuales; gas: MMm³/d y MMm³ mensuales. No hay contador live. Recorte: formación Vaca Muerta, no convencional. Área: permiso/concesión. Las transferencias de activos pueden cambiar rankings.

## Navegación progresiva

`lib/navigation.ts` define Resumen → Producción/Operadores/Áreas/Actividad → operador/área. Filtros e IDs se conservan en la URL, con atrás/adelante. Los destinos solo muestran Próximamente; no se incorporan las vistas locales de operadores o mapa ni se construyen drill-downs.

Alcance/aceptación: [resumen-ui.md](../../specs/001-vaca-muerta-pulse/resumen-ui.md). Hito 3 completo queda pendiente; sin cambios en extracción, dbt o harness.
