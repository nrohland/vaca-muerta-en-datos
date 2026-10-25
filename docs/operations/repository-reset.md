# Reinicio del repositorio

El nuevo historial empieza con una importación del baseline público revisado; los commits posteriores agrupan cambios coherentes. No reproduce fechas ni secuencias de desarrollo anteriores. Todos los nuevos autores pertenecen al propietario.

## Credenciales y publicación

No se importan .git antiguo, .env reales, tokens, service accounts, perfiles ADC, estado Terraform ni dependencias locales. Sólo se conservan .env.example sanitizados. Gitignore, el guard de rutas, hook pre-commit y Gitleaks sobre todos los commits protegen la publicación.

```sh
git config core.hooksPath .githooks
python3 scripts/test_check_publication.py
python3 scripts/check_publication.py --history
# Gitleaks debe estar instalado y fijado a una versión revisada.
gitleaks git . --log-opts='--all --full-history' --ignore-gitleaks-allow --redact=100 --no-banner
```

No subir archivos .env aunque se haya pasado un escaneo anterior. El hook no sustituye CI y no se instala automáticamente en clones.

## Operación

GCP mantiene facturación deshabilitada. No se copian secrets/variables/entornos de GitHub. Los workflows de datos deben permanecer deshabilitados y sus flags false. El pipeline local Meltano conserva corte, contratos, preflights y promoción manual. No hay nueva ingesta por reiniciar Git.

Un repositorio recreado tiene un ID nuevo aunque conserve el nombre: la confianza WIF anterior y el enlace Vercel deben revisarse antes de reactivar despliegues. No se cambia IAM ni se habilitan servicios facturables. El sitio Vercel existente es independiente del borrado del repositorio; no se borra su proyecto.

Usar ramas pequeñas y squash al integrar un PR coherente; conservar main protegida y los checks requeridos. No habilitar auto-merge. Los documentos de evidencia archivados describen ejecuciones del proyecto anterior, no validaciones nuevas del repositorio recreado.
