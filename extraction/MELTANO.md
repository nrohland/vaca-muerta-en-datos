# Meltano local sin facturación

Esta integración ejecuta el extractor batch existente como **utility**, no como tap Singer. No necesita servicios nuevos. El plan se puede comprobar sin red ni credenciales; las fases de datos sí requieren acceso a las fuentes y ADC para BigQuery Sandbox. Billing debe seguir deshabilitado: el CLI comprueba ese estado antes de usar warehouse.

Desde la raíz del repo, con Python 3.12 y Node 22.13+:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r extraction/requirements-meltano.txt
npm --prefix apps/web ci
meltano run cap4:plan
```

Las utilities usan las dependencias del entorno activo. No ejecutar `meltano install` para esta utility sin pip_url; el runner es un script local. No hay extracción remota ni carga durante el plan. Para preparar las dependencias dbt antes de una corrida real, seguir [CLI](../pipeline/CLI.md) y su perfil local ADC; `dbt deps --project-dir transform --profiles-dir /ruta/a/perfiles` requiere un profiles.yml local y no versionado.

Corrida candidata completa, con ID nuevo autogenerado:

```sh
meltano run cap4:pipeline
# Equivalente como job nombrado:
meltano run candidate-history
```

Ejecutar una sola de esas dos variantes por actualización. No hay deploy, commit ni promoción implícita. Toda falla detiene las fases siguientes. Directorios por defecto en `.local/runs/<id>/{prepare,scratch,load,transform}`; contienen payloads privados y quedan fuera de Git.

Fases separadas requieren reutilizar el mismo ID y scratch:

```sh
export VM_RUN_ID="candidate-$(date -u +%Y%m%dT%H%M%SZ)"
meltano run cap4:prepare
meltano run cap4:load
meltano run cap4:transform
```

No reutilizar directorios fallidos para fingir una corrida nueva. `VM_RUN_ROOT` permite elegir almacenamiento local fuera del repo. `VM_SOURCE_INBOUND` apunta a CSV retenidos con sus recibos originales; no rejuvenece timestamps ni evita el control de frescura. Todos los procesos deben usar el mismo VM_RUN_ROOT para compartir lock. El lock es de un host; no coordina máquinas distintas.

## Programación local

No se instala ningún scheduler en esta entrega. Se puede ejecutar el siguiente comando mediante launchd en macOS o systemd timer en Linux, usando rutas absolutas reales:

```sh
cd /ruta/al/repositorio
. .venv/bin/activate
unset VM_RUN_ID
meltano run cap4:pipeline
```

Una observación diaria no certifica cierre oficial. La máquina debe estar encendida y conectada; no usar la Mac personal como runner de PRs públicos. El monitor GitHub y el pipeline cloud permanecen deshabilitados. No abrir Issues ni enviar avisos desde este wrapper.

## Límites

El corte sigue siendo agosto de 2026; la política de aceptación dinámica y promoción automática no está implementada. No se desactiva TLS ni se cambia la política existente de redirección pública oficial. Los hashes ligan bytes/versiones, no sustituyen autenticación del origen. El estado Singer no aplica a utilities; recibos/checkpoints siguen en las carpetas del CLI.
