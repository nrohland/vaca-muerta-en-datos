# Observación de fuentes y avisos

[Contrato y criterios](../specs/020-source-monitor.md). Monitor independiente del pipeline de carga, sin autenticación cloud. [Workflow](../.github/workflows/source-monitor.yml).

```sh
python pipeline/source_monitor.py --output /tmp/vm-monitor
# Reusar explícitamente estado observado, forzando lectura completa:
python pipeline/source_monitor.py --previous /ruta/state.json --output /tmp/vm-monitor-full --full
```

Genera `state.json`, `report.json` y `summary.md`. La línea base en `contracts/monitor-baseline.json` se obtuvo de fuentes retenidas verificadas contra el snapshot; no renueva fechas. `--inbound` conserva recuperación original. `--bootstrap` valida el grano/volúmenes/pozos de todas las filas de cuenca antes de generar una nueva línea base; ese cambio requiere revisión, no se ejecuta en el scheduler.

GitHub restaura el estado con `monitor_github.py restore`, observa fuentes y entrega Issues con `notify`. Sólo la restauración y entrega necesitan el token efímero GitHub. El estado no tiene filas de pozo, datos raw ni credenciales. No ejecutar `notify` durante pruebas: los tests usan API simulada.

«Nuevo mes observado» puede ser parcial. «Listo para revisión» es una señal de cobertura/estabilidad/precios, no cierre oficial. «Mes aceptado revisado» identifica cambios de campos, incluso con volúmenes iguales; cotizaciones revisadas tienen su propio aviso. Nada modifica dbt, el corte aceptado o el frontend automáticamente.

Monitor diario a las 03:00 Argentina, histórico completo al menos semanal y al concluir la ingesta. Verificar estado/Issue asignada; para recibir correo/push, usar las preferencias de notificaciones de GitHub. Los avisos llevan enlace a evidencia y no instrucciones para incorporar datos sin revisión.

Los GET públicos del monitor tienen hasta tres intentos (esperas de 1 y 2 segundos) ante fallos de conexión, timeout, respuesta incompleta o HTTP 429/500/502/503/504. No se reintentan errores de contrato, redirects fuera del origen revisado, certificados TLS ni HTTP 401/403. Un CSV parcial se elimina únicamente en el directorio temporal propio antes de reiniciar su descarga; no se reutilizan bytes truncados ni se altera un archivo inbound. Las escrituras cloud no participan de estos reintentos.

Las alertas identifican la fuente (año de Capítulo IV, catálogo o serie EIA) y una categoría técnica permitida, con HTTP cuando corresponde. No incluyen mensajes de excepción, cuerpos de respuesta, credenciales ni URLs de error. El resumen de Actions conserva el mismo diagnóstico. Si se agotan los intentos, el monitor sigue fallando y conserva la última fecha de observación válida. Un fallo de conexión no demuestra que la fuente no haya publicado novedades.
