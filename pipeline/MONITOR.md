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
