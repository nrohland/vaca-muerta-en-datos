# Calidad, arquitectura y rendimiento

La validación se separa en tres resultados: datos/cálculos, arquitectura del proyecto y ejecución real en BigQuery. Instalar un paquete no demuestra que sus controles hayan corrido.

## Herramientas activas

- **dbt_utils / dbt_expectations:** macros y tests declarados del proyecto. No sustituyen contratos de fuente, conciliaciones ni tests unitarios.
- **audit_helper 0.14.0:** `analyses/audit_history_before_merge.sql` compara claves y volúmenes por pozo/mes contra el raw retenido. Sólo sale un resumen por clasificación, sin muestras raw. La discrepancia oficial de clasificación documentada explica las 24 incorporaciones; cualquier diferencia adicional debe revisarse.
- **dbt_project_evaluator 1.3.5:** auditoría de estructura, documentación, claves y materializaciones. Se ejecuta localmente con DuckDB sobre el grafo, sin copiar datos productivos. Está desactivado por defecto y bloqueado para BigQuery: sus hooks usan INSERT, no permitido en el sandbox sin facturación.
- **Reporte de rendimiento:** `pipeline/report_dbt_performance.py` lee run_results reales. Guarda duración por nodo, bytes procesados/facturables, slot-ms y job IDs. El CLI lo genera después de un build aceptado; no exporta SQL ni credenciales.

## Arquitectura local

En un entorno aislado con las dependencias de dbt Core:

```sh
python -m pip install -r transform/requirements.txt -r transform/requirements-audit.txt
mkdir -p /tmp/vm-audit-profile
cp transform/profiles-audit.yml.example /tmp/vm-audit-profile/profiles.yml
dbt deps --project-dir transform --profiles-dir /tmp/vm-audit-profile --target candidate
dbt build --project-dir transform --profiles-dir /tmp/vm-audit-profile --target candidate \
  --vars '{"candidate_period":"2026-08-01","candidate_start_period":"2023-01-01","enable_candidate_pricing":true,"enable_dashboard_export":true,"enable_project_evaluator":true}' \
  --select package:dbt_project_evaluator
```

Los resultados son recomendaciones del paquete, no una medición de velocidad en BigQuery. La auditoría ejecutada produjo 75 resultados aprobados y tres advertencias: organización de archivos de fuentes/modelos y fanout del hecho compartido por seis consumidores. Se conservaron las reglas y los hallazgos; no se ocultaron ni elevó el umbral para obtener verde. La reutilización del hecho materializado es deliberada; el layout de carpetas puede revisarse sin cambiar cálculos.

## Freshness

Fuentes de producción y precios declaran warning a cinco días y error a siete días usando el timestamp de llegada/recuperación. Se ejecuta antes del build con `dbt source freshness`, además de los gates estrictos de hashes, cronología y recuperación independiente por producto. Un warning no acepta el candidato.

Freshness técnica no implica que el mes económico sea reciente ni completo. El corte aceptado sigue siendo agosto de 2026; no se publica septiembre por ser el máximo raw. Completaciones/Adjunto IV están fuera de V1; los prototipos se retiraron y una incorporación futura requiere contrato y validación propios.

## Rendimiento y límites

El reporte conserva NULL cuando el adaptador no informa una métrica; no fabrica ceros. Slot-ms mide uso de cómputo, no tiempo de pared. CREATE VIEW con cero bytes no mide el costo de consultar esa vista. Los bytes facturables no son una factura monetaria.

La primera corrida histórica reportó 1.549 GiB procesados entre todos sus nodos; incluye el intento inicial fallido del modelo de publicación. La reparación y los tests adicionales tienen reportes independientes. No es un benchmark comparativo ni una prueba de regresión: faltan varias ejecuciones del mismo código/datos y condiciones. Límite existente: 1 GiB por consulta, distinto del costo total de una corrida.

Elementary/Recce y servicios comerciales no se instalaron en esta entrega. La observabilidad continua se decide al activar la operación; no se habilita facturación ni se envían datos a terceros para estos controles.
