# Spec 001 — Vaca Muerta en Datos

- **Estado:** Fundación de producto; actualizada al alcance autorizado del Hito 3.
- **Marca:** Vaca Muerta en Datos. **Repo:** `vaca-muerta-pulse`.
- **Detalle de iteraciones:** specs 004 (datos/valor), 005 (comparaciones/idiomas), 010 (Producción) y specs de Operadores/Áreas/Actividad.
- **Contratos:** [modelo de datos](data-model.md), [arquitectura](../../docs/architecture.md), [plan](plan.md), [evidencia](../../docs/evidence/data-valuation/README.md).

## Problema y objetivo

Los archivos mensuales oficiales de producción por pozo contienen información útil pero requieren conocer grano, unidades, rectificativas y fuentes separadas. Vaca Muerta en Datos convierte esa materia prima en un producto que explica nivel, evolución, concentración y actividad del recorte formación Vaca Muerta + recurso no convencional.

La audiencia incluye analistas energéticos, periodistas, estudiantes y equipos que necesitan preguntas de negocio respondidas con fuentes y límites claros. El repositorio también demuestra ingeniería de datos, analytics engineering, diseño de producto y verificación ante clientes o empleadores.

## Preguntas y alcance actual

| Vista | Pregunta principal | Alcance |
| --- | --- | --- |
| Resumen | ¿Qué ocurre y dónde profundizar? | KPIs distintos, evolución y concentración; base visual aprobada |
| Producción | ¿Cómo cambia el volumen o valor en el tiempo? | Historia, años comparables, acumulados con cobertura completa, cambio absoluto y tabla |
| Operadores | ¿Quién produce y cómo cambia? | Ranking completo, filtros y detalle temporal |
| Áreas | ¿Dónde se produce y cómo evoluciona? | Permiso/concesión, ranking, detalle y relaciones sólo con fuente confiable |
| Actividad | ¿Cómo evoluciona la cantidad de pozos que producen? | Conteos por fluido y promedio por pozo/día calendario; dinámica sólo con datos suficientes |

## Requisitos de datos

1. Extraer Capítulo IV reproduciblemente a BigQuery mediante Meltano, con lectura anual para rectificativas y cadencia mensual.
2. Separar raw, staging, intermediate y marts, con granos y claves explícitos y tests dbt.
3. Aplicar el universo `formacion = 'vaca muerta'` y `tipo_de_recurso = 'NO CONVENCIONAL'`. No equivale a toda la Cuenca Neuquina.
4. Convertir petróleo m³ × 6,28981077; gas de miles de m³ a MMm³. Tasa diaria equivalente = volumen / días calendario.
5. Contar pozos únicos con producción positiva por fluido y mes. No sumar petróleo + gas como pozos únicos.
6. Separar el último período raw del último período aceptado. El candidato actual acepta agosto de 2026, excluye septiembre parcial y mantiene estado Preliminar hasta aprobación válida.
7. Validar contrato, cobertura, conciliación y hashes del export; no consultar raw desde el browser.
8. Valor de petróleo = barriles × Brent mensual EIA del mismo mes. Precio faltante → no disponible. Gas USD pendiente de referencia y conversión energética robustas.
9. Mantener fuente, actualización de recurso, extracción, ingesta, generación y publicación como fechas distintas.

## Requisitos de producto

- Componentes comunes y analytics-ui: un sistema de KPIs, cards, rankings, gráficos, filtros y estados. No crear una estética por pestaña.
- Petróleo azul, gas violeta, monetario ámbar; positivo verde y negativo rojo por convención explícita. Escalas de participación 0–100% y gráficos sin proporciones engañosas.
- ES/EN, light/dark, responsive, selector fluido, período, volumen/valor, mensual/interanual y contexto persistente.
- Deep links de vista y entidad, atrás/adelante; períodos base y unidades visibles; tabla/tooltips para cifras exactas.
- Resumen mantiene la base aprobada. Las vistas de detalle explican preguntas nuevas, sin duplicar toda la portada.
- Datos mensuales sin telemetría ni contador live. El contador interpolado previsto originalmente fue reemplazado por tasas equivalentes y comparaciones explícitas en la UI actual.
- Valor estimado no representa ingresos realizados ni rentabilidad. Promedio por pozo/día calendario no representa productividad por día efectivo.

## Fuentes y no objetivos

Capítulo IV alimenta producción, entidades y pozos productivos. Adjunto IV es una fuente separada de fracturas; no se atribuye a Capítulo IV ni se fuerza su join con producción. Brent EIA es contexto económico separado. Perforación, comercio exterior, capacidades/ductos y mapas requieren contratos propios antes de agregar métricas.

No incluye telemetría, rigs live, breakeven, reservas, margen/beneficio, API pública estable, app nativa ni nuevos datos privados. No inferir altas/bajas/completaciones a partir del cambio neto de pozos agregados. No inventar relaciones o factores energéticos.

## Aceptación y operación

Cálculos y transformaciones, contratos y navegación requieren pruebas; las pantallas requieren inspección desktop/mobile con evidencia. Los resultados históricos no cierran la integración actual. Sin secretos en Git, sin merges/promoción/deploy por agentes sin autorización.

La meta de freshness es ingestar dentro de siete días de una publicación oficial, todavía sin SLA/alertas automáticas demostrado. La extracción programada default sigue en dev/recurso 2025 y condicionada por guard/secretos. CI dbt sólo deps/parse; el pipeline de extracción → build/tests → gates → export → aprobación no está orquestado end-to-end. Ver [operación](../../docs/architecture.md).
