# Vaca Muerta en Datos

**Un producto analítico para entender cómo evoluciona la producción no convencional de Vaca Muerta, quién la impulsa y dónde se concentra.** Transforma declaraciones mensuales oficiales en métricas comparables, rankings y exploración interactiva, con trazabilidad desde la fuente hasta la pantalla.

Pensado para analistas, equipos de energía y periodistas. Como portfolio, muestra un recorrido completo de ingeniería de datos, modelado analítico y diseño de producto.

![Resumen de Vaca Muerta en Datos](docs/screenshots/resumen.jpg)

**Estado:** V1 integrada y validada localmente y en GitHub, con 44 meses de enero de 2023 a agosto de 2026. Versión preliminar sin promoción pública aprobada. Septiembre parcial queda excluido; las declaraciones oficiales pueden rectificarse.

## Qué preguntas responde

| Vista | Preguntas y herramientas |
| --- | --- |
| Resumen | ¿Cuál es el nivel actual y qué cambió? KPIs, evolución y concentración. |
| Producción | ¿Cómo evoluciona cada fluido? Comparación entre años, cambio absoluto, acumulados y tabla descargable. |
| Operadores | ¿Quién produce y cómo cambia su participación? Ranking completo, búsqueda y evolución por operador. |
| Áreas | ¿Dónde se concentra la producción? Ranking y evolución por permiso o concesión. |
| Actividad | ¿Cuántos pozos tienen producción y cómo cambia el promedio por pozo? Historia, cambio neto y tasa por día calendario. |

Las cinco vistas comparten componentes, filtros y contexto persistente: petróleo/gas, período, volumen/valor USD, comparación mensual/interanual, ES/EN, light/dark y enlaces a detalles. Petróleo azul, gas violeta, dinero ámbar y variaciones verde/rojo conservan su significado en todo el dashboard. [Capturas desktop y mobile](docs/screenshots/README.md).

## Datos, precios y definiciones

La fuente principal es [Capítulo IV de la Secretaría de Energía](https://datos.gob.ar/dataset/energia-produccion-petroleo-gas-por-pozo-capitulo-iv). El universo combina **formación Vaca Muerta y recurso no convencional**; no representa toda la Cuenca Neuquina. Cuatro CSV oficiales anuales contienen 3.614.213 registros nacionales, de los que dbt obtiene el universo y los agregados del producto.

- **Petróleo:** m³ × 6,28981077 → barriles. **Gas:** miles de m³ → MMm³. Tasa diaria equivalente = volumen mensual / días calendario.
- **Pozos productivos:** IDs únicos con volumen positivo del fluido en cada mes. Los conteos petróleo/gas no se suman.
- **USD de petróleo:** producción × [Brent mensual EIA](https://www.eia.gov/dnav/pet/hist/leafhandler.ashx?f=m&n=pet&s=rbrte).
- **USD de gas:** volumen × equivalencia energética × [Henry Hub mensual EIA](https://www.eia.gov/dnav/ng/hist/rngwhhdm.htm). El escenario usa 1.036 BTU/pie³, equivalente a 0,03658599472346218 MMBtu/m³; es un supuesto de referencia estadounidense, no calorificidad medida de Vaca Muerta. [Metodología](specs/017-international-gas-reference.md).

USD representa **valor bruto estimado con referencias internacionales**, no ingresos realizados, márgenes ni precios locales. Los precios cambiantes se extraen y cargan a BigQuery; dbt calcula la valorización. No son seeds ni se calculan en Next.js. Sin precio válido → valor indisponible; no hay relleno silencioso. Los seeds contienen catálogos estables.

Actividad muestra producción media por pozo y día calendario, no productividad por día efectivo. El cambio neto de conteos no identifica altas o bajas. No se presentan completaciones, mapa ni relaciones operador–área actuales sin respaldo suficiente. [Contrato histórico](specs/019-historical-source-candidate.md).

## Arquitectura y razones

```mermaid
flowchart LR
  SE["CSV oficiales · Capítulo IV"] --> PY["Python · extracción y contratos"]
  EIA["EIA · Brent y Henry Hub"] --> PY
  PY --> RAW["BigQuery · raw candidato aislado"]
  RAW --> DBT["dbt · staging / intermediate / marts"]
  DBT --> QA["Tests · freshness · conciliación"]
  QA --> JSON["Snapshot agregado + manifiestos SHA-256"]
  JSON --> UI["Next.js / React / Recharts"]
```

| Capa | Elección | Motivo |
| --- | --- | --- |
| Extracción | Python 3.12, CSV oficiales y HTML EIA | Control explícito de esquema, cobertura, rectificativas y hashes. El CSV comprobado tiene mayor cobertura que DataStore. |
| Warehouse | BigQuery | Consultas analíticas sin administrar servidores, aislamiento de permisos y medición de bytes. Raw particionado por ingesta; marts con clustering para conservar historia en el sandbox. |
| Modelado | dbt Core + SQL | Granos y unidades únicos, linaje, tests y conciliación. Intermediate se usa para reglas reutilizadas; staging puede alimentar directamente un mart. |
| Entrega | JSON agregado y manifiestos | El browser recibe un snapshot consistente sin credenciales ni consultas al warehouse. Construcción y promoción se separan. |
| Aplicación | Next.js 16, React 19, TypeScript 7, Recharts 3 | Componentes tipados, navegación persistente, export estático y semántica visual compartida. |
| Automatización | CLI Python + GitHub Actions con WIF | Mismos controles localmente y en runner, identidades por etapa y sin claves permanentes. |
| Calidad | dbt tests, audit_helper, dbt_project_evaluator, Python, Node y Playwright | Validar datos, arquitectura, contratos y UI; rendimiento medido con tiempos, bytes y slot-ms reales. |

[Arquitectura detallada](docs/architecture.md) · [Decisiones](docs/adrs/README.md) · [Calidad y rendimiento](transform/docs/quality-and-performance.md).

## Linaje real de dbt

![Linaje dbt](docs/lineage/linaje-dbt.svg)

Generado desde el manifest de la ejecución aceptada: **12 modelos, 2 fuentes, 1 seed y 15 dependencias**. Se exportan nombres lógicos y relaciones, sin conexiones ni credenciales. [Procedencia y regeneración](docs/lineage/README.md).

## Orquestación, frecuencia y freshness

El [CLI compartido](pipeline/CLI.md) prepara fuentes públicas, carga tablas candidatas, verifica linaje y frescura, ejecuta dbt y exporta/valida el snapshot. Cada fallo bloquea las etapas posteriores. El export se instala completo en una carpeta separada; no promueve automáticamente datos al repo o al sitio.

La fuente es mensual. GitHub tiene preparado el día 5 a las 03:00 Argentina, con **`DATA_PIPELINE_ENABLED=false`**. No se presupone que la fuente publique ese día. Frescura operativa máxima de siete días; el warning dbt desde cinco días también detiene el pipeline. Se distinguen recuperación, ingesta, mes de negocio y cobertura: descargar hoy no vuelve completo el último mes.

La integración local pasó nueve etapas en una corrida, con **106/106 nodos dbt aprobados, sin warnings, errores ni skips**. El frontend pasó 59 tests, typecheck y build sobre el bundle exportado; 10.296 agregados conciliados. [Evidencia del recorrido](docs/evidence/orchestration-export/README.md) · [Revisión visual](docs/evidence/snapshot-integration/README.md).

**Ejecución real:** extracción, WIF, dbt, export y frontend aprobados en [GitHub Actions](docs/evidence/github-actions/README.md). **Pendientes:** detección/aviso de nuevos meses, promoción del snapshot, hosting y operación pública. Playwright local está bloqueado por permisos de Chromium en macOS; la inspección desktop/mobile se documenta separadamente. No se habilitaron cron, despliegue ni facturación.

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
