# Pipeline candidato de desarrollo

Estado: código preparado, controles offline probados y consulta de raw validada
con dry-run en BigQuery. **No está activado ni ejecutado de punta a punta.**

`data-pipeline.yml` encadena medición CKAN antes de cargar → extracción Meltano a
raw aislado → medición CKAN después de cargar → gate raw → dbt build/tests del
mes técnicamente validado. Cada etapa falla cerrada y transformación depende del
éxito de extracción. El workflow no exporta un release ni publica la aplicación.

## Configuración

1. Revisar `transform/scripts/configure_pipeline_identity.py` (sin `--apply`
   imprime el plan). Propone dos identidades y cuatro datasets candidatos nuevos.
   Aplicarlo requiere aprobación de los cambios persistentes de infraestructura.
2. Configurar ambientes GitHub `data-dev-extract` y `data-dev-dbt`. WIF valida
   repositorio/propietario numéricos, rama main, workflow y ambiente; cada token
   sólo puede usar la identidad correspondiente a su etapa.
3. Agregar bajo `pipeline/contracts/` evidencia técnica CKAN revisada con recurso,
   año, conteos y mes completo. No hay una evidencia real agregada por este cambio:
   no se fabrica aceptación usando el snapshot UI ni datos de un CSV distinto.
4. Validar manualmente en desarrollo antes de activar `DATA_PIPELINE_ENABLED`.
   Esa variable queda en `false` en el plan. El cron sólo existe en main después
   de un merge aprobado: día 5 a las 03:00 Argentina.

Inputs manuales: `resource_id`, `year`, `month`, `evidence`. Para cron, equivalentes
`DATA_RESOURCE_ID`, `DATA_SOURCE_YEAR`, `DATA_REQUIRED_MONTH`,
`DATA_REVIEWED_EVIDENCE`. Ninguno tiene fallback al recurso 2025. El candidato
está limitado a dos millones de filas y un presupuesto de consulta de 1 GiB.
Estos límites no son una estimación del costo total de toda la ejecución.

## Freshness e integridad

- Timestamp de producción: año/mes de la declaración; no indica cuándo extrajimos.
- Observación de fuente: hora del preflight CKAN; comprueba que la medición es
  reciente, no cuándo se revisó por última vez cada registro de la fuente.
- Ingesta: todos los timestamps raw deben existir, quedar después del preflight,
  no estar en el futuro y tener antigüedad máxima de siete días al validar.
- Cobertura: mes requerido explícitamente validado en evidencia; no se acepta
  automáticamente el mes máximo por existir filas.
- Estabilidad CKAN: huella de metadata/schema/conteos antes/después y contra
  evidencia revisada. **No es hash del contenido de los registros**. No detecta
  una modificación de valores que conserve metadata y conteos; la conciliación
  exacta de valores requiere un snapshot inmutable o digest de contenido.

El raw retiene el recurso anual candidato; los marts sólo incluyen el mes
requerido mediante `candidate_period`. Un test dbt exige que el headline tenga
una fila de ese período y que el pozo-mes no lo exceda. Esto evita que septiembre
parcial desplace agosto validado. Todavía no es la publicación multianual del
dashboard: faltan integrar sus modelos originales y migrar la valorización.

`--recreate` sólo afecta raw candidato, nunca el histórico actual. Si una carga
falla puede perderse el candidato previo y quedar uno parcial; el gate falla,
no se transforma ni se publica. La evidencia de cada run se conserva siete días.
El reemplazo por candidato por ejecución y digest de contenido quedan pendientes
antes de ampliar este flujo a publicación.

WIF emite credenciales temporales; su duración/renovación durante la carga anual
debe verificarse en la primera ejecución real. Instalar dependencias antes de
autenticar evita gastar su vigencia durante instalación. No se habilita facturación.

## Pruebas locales

```bash
python3.12 -m unittest discover -s extraction/tests -p 'test_*snapshot_gate.py'
python3.12 -m unittest discover -s transform/tests_python -p 'test_candidate_gate.py'
python3.12 -m unittest discover -s pipeline/tests
```

Las pruebas no usan una fuente real ni conceden aprobación de publicación.
Consultar [ADR 0006](../docs/adrs/0006-candidate-pipeline.md) y
[contrato de gates](../specs/015-dev-pipeline-gates.md).

Auditoría de warehouse: raw_cap4_dev contiene 3.511.366 filas, de las que 991.844
son 2025; su ingesta consultada data del 14 de septiembre de 2026. No es un raw
monoanual reemplazable. Se retira el cron legacy del código preparado y se bloquea
reemit de dev compartido y --recreate fuera del candidato. Hasta merge aprobado,
el workflow remoto histórico conserva su estado anterior.
