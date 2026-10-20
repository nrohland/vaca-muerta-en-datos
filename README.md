# Vaca Muerta en Datos

**Un producto analítico para entender cómo evoluciona la producción no convencional de Vaca Muerta, quién la impulsa y dónde se concentra.** Transforma declaraciones mensuales oficiales en métricas comparables, rankings y exploración interactiva, con trazabilidad desde la fuente hasta la pantalla.

Pensado para analistas, equipos de energía y periodistas. Como portfolio, muestra un recorrido completo de ingeniería de datos, modelado analítico y diseño de producto.

![Resumen de Vaca Muerta en Datos](docs/screenshots/resumen.jpg)

**Estado:** V1 preliminar con 44 meses de enero de 2023 a agosto de 2026. Septiembre parcial queda excluido; las declaraciones oficiales pueden rectificarse.

**[Abrir demo pública en Vercel](https://vaca-muerta-en-datos.vercel.app)**. El sitio sirve el snapshot revisado; la extracción automática está pausada por problemas de conectividad con Energía. Publicar el frontend no actualiza los datos. [Configuración del despliegue](docs/vercel.md).

## Qué preguntas responde

| Vista | Preguntas y herramientas |
| --- | --- |
| Resumen | ¿Cuál es el nivel actual y qué cambió? KPIs, evolución y concentración. |
| Producción | ¿Cómo evoluciona cada fluido? Comparación entre años, cambio absoluto, acumulados y tabla descargable. |
| Operadores | ¿Quién produce y cómo cambia su participación? Ranking completo, búsqueda y evolución por operador. |
| Áreas | ¿Dónde se concentra la producción? Mapa con círculos proporcionales sobre concesiones de referencia, ranking y evolución por área. |
| Actividad | ¿Cuántos pozos tienen producción y cómo cambia el promedio por pozo? Historia, cambio neto y tasa por día calendario. |

Las cinco vistas comparten componentes, filtros y contexto persistente: petróleo/gas, período, volumen/valor USD, comparación mensual/interanual, ES/EN, light/dark y enlaces a detalles. Petróleo azul, gas violeta, dinero ámbar y variaciones verde/rojo conservan su significado en todo el dashboard. [Capturas desktop y mobile](docs/screenshots/README.md).

## Datos, precios y definiciones

La fuente principal es [Capítulo IV de la Secretaría de Energía](https://datos.gob.ar/dataset/energia-produccion-petroleo-gas-por-pozo-capitulo-iv). El universo combina **formación Vaca Muerta y recurso no convencional**; no representa toda la Cuenca Neuquina. Cuatro CSV oficiales anuales contienen 3.614.213 registros nacionales, de los que dbt obtiene el universo y los agregados del producto.

- **Petróleo:** m³ × 6,28981077 → barriles. **Gas:** miles de m³ → MMm³. Tasa diaria equivalente = volumen mensual / días calendario.
- **Pozos productivos:** IDs únicos con volumen positivo del fluido en cada mes. Los conteos petróleo/gas no se suman.
- **USD de petróleo:** producción × [Brent mensual EIA](https://www.eia.gov/dnav/pet/hist/leafhandler.ashx?f=m&n=pet&s=rbrte).
- **USD de gas:** volumen × equivalencia energética × [Henry Hub mensual EIA](https://www.eia.gov/dnav/ng/hist/rngwhhdm.htm). El escenario usa 1.036 BTU/pie³, equivalente a 0,03658599472346218 MMBtu/m³; es un supuesto de referencia estadounidense, no calorificidad medida de Vaca Muerta. [Metodología](specs/017-international-gas-reference.md).

USD representa **valor bruto estimado con referencias internacionales**, no ingresos realizados, márgenes ni precios locales. Los precios cambiantes se extraen y cargan a BigQuery; dbt calcula la valorización. No son seeds ni se calculan en Next.js. Sin precio válido → valor indisponible; no hay relleno silencioso. Los seeds contienen catálogos estables.

Actividad muestra producción media por pozo y día calendario, no productividad por día efectivo. El cambio neto de conteos no identifica altas o bajas. No se presentan completaciones ni relaciones operador–área actuales sin respaldo suficiente. El [mapa de referencia](docs/geography/README.md) usa geometrías oficiales de Neuquén con cruce verificado de 68/88 áreas y límites de cobertura explícitos. [Contrato histórico](specs/019-historical-source-candidate.md).

## Arquitectura y razones

```mermaid
flowchart LR
  SE["CSV oficiales · Capítulo IV"] --> PY["Python · extracción y contratos"]
  EIA["EIA · Brent y Henry Hub"] --> PY
  PY --> PQ["Parquet tipado · producción histórica"]
  PQ --> RAW["BigQuery · raw candidato aislado"]
  PY -->|Precios| RAW
  RAW --> DBT["dbt · staging / intermediate / marts"]
  DBT --> QA["Tests · freshness · conciliación"]
  QA --> JSON["Snapshot agregado + manifiestos SHA-256"]
  JSON --> UI["Next.js / React / Recharts / MapLibre"]
  UI --> HOST["Vercel · sitio estático"]
```

| Capa | Elección | Motivo |
| --- | --- | --- |
| Extracción | Python 3.12, CSV oficiales → Parquet y HTML EIA | Esquema explícito, cobertura, rectificativas y hashes; Parquet tipado y comprimido para la ingesta histórica. El CSV comprobado tiene mayor cobertura que DataStore. |
| Warehouse | BigQuery | Consultas analíticas sin administrar servidores, aislamiento de permisos y medición de bytes. Raw particionado por ingesta; marts con clustering para conservar historia en el sandbox. |
| Modelado | dbt Core + SQL | Granos y unidades únicos, linaje, tests y conciliación. Intermediate se usa para reglas reutilizadas; staging puede alimentar directamente un mart. |
| Entrega | JSON agregado por vista y manifiestos | El browser carga Resumen y descarga detalles por fluido/dimensión cuando los necesita, con hashes y límites de tamaño. Construcción y promoción se separan. |
| Aplicación | Next.js 16, React 19, TypeScript 7, Recharts 3 y MapLibre 6 | Componentes tipados, navegación persistente, export estático, mapas navegables y semántica visual compartida. |
| Automatización | CLI Python + GitHub Actions con WIF | Mismos controles localmente y en runner, identidades por etapa y sin claves permanentes. |
| Calidad | dbt tests, audit_helper, dbt_project_evaluator, Python, Node y Playwright | Validar datos, arquitectura, contratos y UI; rendimiento medido con tiempos, bytes y slot-ms reales. |

[Arquitectura detallada](docs/architecture.md) · [Decisiones](docs/adrs/README.md) · [Calidad y rendimiento](transform/docs/quality-and-performance.md).

## Linaje real de dbt

![Linaje dbt](docs/lineage/linaje-dbt.svg)

Generado desde el manifest de la ejecución aceptada: **12 modelos, 2 fuentes, 1 seed y 15 dependencias**. Se exportan nombres lógicos y relaciones, sin conexiones ni credenciales. [Procedencia y regeneración](docs/lineage/README.md).

## Orquestación, frecuencia y freshness

El [CLI compartido](pipeline/CLI.md) prepara fuentes públicas, carga tablas candidatas, verifica linaje y frescura, ejecuta dbt y exporta/valida el snapshot. Cada fallo bloquea las etapas posteriores. El export se instala completo en una carpeta separada; no promueve automáticamente datos al repo o al sitio.

La fuente es mensual. GitHub tiene preparado el día 5 a las 03:00 Argentina, con **`DATA_PIPELINE_ENABLED=false`**. No se presupone que la fuente publique ese día. Frescura operativa máxima de siete días; el warning dbt desde cinco días también detiene el pipeline. Se distinguen recuperación, ingesta, mes de negocio y cobertura: descargar hoy no vuelve completo el último mes.

La validación histórica documentó nueve etapas, **106/106 nodos dbt aprobados, sin warnings, errores ni skips**, 59 tests frontend y 10.296 agregados conciliados. Es evidencia de esa ejecución, no un contador de pruebas de la versión actual. [Evidencia del recorrido](docs/evidence/orchestration-export/README.md) · [Revisión visual](docs/evidence/snapshot-integration/README.md).

**Ejecución real:** extracción, WIF, dbt, export y frontend aprobados en la validación histórica de [GitHub Actions](docs/evidence/github-actions/README.md). La demo está publicada en Vercel y conserva el snapshot preliminar. La extracción y el monitor automático permanecen pausados por problemas de conectividad de los runners con Energía; publicar el frontend no reanuda la ingesta. Playwright corre en CI. El [monitor de fuentes](pipeline/MONITOR.md), actualmente pausado, está preparado para detectar nuevos meses y rectificativas; sus avisos no certifican cierre oficial. [Configuración y operación del sitio](docs/vercel.md).

## Ejecutar la aplicación

Node.js 22.13+ y npm. El snapshot está incluido; no hace falta acceso a GCP para abrirlo.

```sh
cd apps/web
npm ci
npm run dev
```

Abrir `http://localhost:3000/vaca-muerta-pulse/`.

```sh
npm run typecheck
npm test
npm run build
npm run test:browser
```

Para navegador, instalar Chromium con `npx playwright install chromium`. Para capas de datos, ver [extracción](extraction/README.md), [dbt](transform/README.md) y [pipeline](pipeline/README.md). Las etapas cloud requieren ADC/WIF; nunca keys en Git.

## Recorrer el repo

| Ruta | Responsabilidad |
| --- | --- |
| `apps/web/` | Producto, componentes comunes, contratos y pruebas frontend. |
| `extraction/` | Contratos, extracción Python y carga candidata. |
| `transform/` | Modelos, seeds, tests, calidad y linaje dbt. |
| `pipeline/` | Coordinación, gates, export y pruebas de integración. |
| `scripts/` | Extracción y carga de referencias de precio. |
| `specs/` | Alcance, preguntas, definiciones y contratos vigentes. |
| `docs/` | Arquitectura, decisiones, evidencia y capturas de V1. |

Nombre de producto: **Vaca Muerta en Datos**. Identificador técnico: `vaca-muerta-pulse`. [Contribución y seguridad](AGENTS.md). Los prototipos y la evidencia superada se retiraron del árbol vigente; las versiones previas permanecen en el historial Git. No se versionan secretos ni dumps raw.

La validación manual del workflow de datos está permitida únicamente en `main`, independientemente del opt-in del calendario. `DATA_PIPELINE_ENABLED=false` mantiene el cron desactivado; `workflow_dispatch` ejecuta una corrida puntual con los mismos permisos y gates.

El monitor de disponibilidad y rectificativas es independiente y está pausado (`SOURCE_MONITOR_ENABLED=false`). Su calendario previsto contempla revisiones diarias, histórico completo semanal y avisos deduplicados mediante Issues asignadas al propietario. `SOURCE_MONITOR_ENABLED` controla este calendario sin activar las cargas de `DATA_PIPELINE_ENABLED`. [Criterios, fallos y operación](pipeline/MONITOR.md).

La [iteración de rendimiento](specs/021-performance-optimization.md) incorpora Parquet en la ingesta histórica, cuatro threads en el CLI dbt, staging candidato materializado, preflight de recursos sin facturación, presupuestos de bytes y entrega de datos por vista. Los cambios mantienen el snapshot canónico y los cálculos. El preflight no modifica IAM ni habilita facturación.

## Alcance de esta versión

V1 permite explorar datos públicos agregados; no consulta BigQuery desde el navegador ni expone credenciales del pipeline. No incluye un chat de datos: esa integración está planificada para una etapa posterior. La demo es preliminar y no ofrece actualización automática mientras la extracción y el monitor permanezcan pausados.
