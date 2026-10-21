# Documentación — Vaca Muerta en Datos

| Documento | Propósito |
| --- | --- |
| [Demo pública](https://vaca-muerta-en-datos.vercel.app) | Dashboard estático con snapshot preliminar hasta agosto de 2026 |
| [Despliegue Vercel](vercel.md) | Configuración real, base path y separación de datos/despliegue |
| [Arquitectura](architecture.md) | Flujo, decisiones, contratos y freshness |
| [ADRs](adrs/README.md) | Motivos y compromisos técnicos |
| [Linaje dbt](lineage/README.md) | Grafo generado y procedencia |
| [Capturas V1](screenshots/README.md) | Las cinco vistas desktop/mobile |
| [GitHub y seguridad](evidence/github-actions/README.md) | Recorrido cloud real y revisión de credenciales |
| [Ejecución integrada](evidence/orchestration-export/README.md) | dbt, export, consumidor y límites |
| [Revisión frontend](evidence/snapshot-integration/README.md) | Cálculos, navegación y capturas |
| [Fuente histórica](evidence/historical-source/README.md) | Cobertura y rectificativas |
| [Calidad dbt](evidence/historical-dbt/README.md) | Auditoría física, arquitectura y rendimiento |
| [Acceso](evidence/pipeline-access/README.md) | Permisos y tamaño de raw |
| [Contratos](../specs/README.md) | Alcance y definiciones |

El árbol vigente conserva documentación de V1 y evidencia necesaria para auditarla. Prototipos y evidencia superada permanecen en el historial, con copia local previa a la limpieza fuera del repo. La demo está publicada en Vercel. Extracción y monitor permanecen pausados por conectividad con Energía; un despliegue no implica datos nuevos. Nuevas promociones de datos y despliegues requieren aprobación. Las cifras de pruebas en las carpetas de evidencia corresponden a sus ejecuciones históricas.
