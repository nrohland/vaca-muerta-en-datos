# Instrucciones de contribución — Vaca Muerta en Datos

## Estado y alcance

El repositorio contiene extracción candidata Python (ruta Meltano/Singer histórica conservada), modelos dbt y una aplicación Next.js funcional en `apps/web/`. El Hito 3 está activo: Resumen está aprobado como base visual y la iteración autorizada completa Producción, Operadores, Áreas y Actividad. No usar las restricciones del antiguo scaffold para bloquear este trabajo.

El snapshot es candidato de revisión, con corte aceptado hasta agosto de 2026. No inventar aprobación, publicación ni ejecución de pruebas. Ver [README](README.md), [arquitectura](docs/architecture.md) y specs de cada iteración. Documentos de hitos anteriores conservan evidencia histórica; no son el estado de aceptación de la integración actual.

## Antes de cambiar

1. Leer este archivo y el README.
2. Leer la spec de la vista/capa afectada y el [modelo de datos](specs/001-vaca-muerta-pulse/data-model.md).
3. Leer el README de la carpeta y los ADRs relevantes.
4. Ante nuevo origen, grano, métrica o cambio de arquitectura, actualizar contrato/spec/ADR. Los cambios de copy o presentación no requieren inventar una spec nueva.

La autorización y las preferencias explícitas del usuario prevalecen. Trabajar autónomamente en lo autorizado; solicitar una decisión sólo ante un bloqueo material que no pueda resolverse con evidencia.

## Responsabilidades

| Ámbito | Rol | Responsabilidad |
| --- | --- | --- |
| `extraction/` | Data Engineer | Recursos, taps, cargas, reemisión y raw fiel a la fuente |
| `transform/` | Analytics Engineer | Granos, conversiones, staging/intermediate/marts, tests y conciliación |
| `apps/web/` | Frontend | Next.js/React/Recharts, componentes comunes, filtros y accesibilidad |
| `specs/`, `docs/` | Roles pertinentes | Definiciones, decisiones y evidencia verificable |
| Aceptación | QA | Cálculos, contrato, navegación y capturas desktop/mobile |

Mantener tareas de agentes en ramas o worktrees aislados; integración controlada. Un cambio de contrato entre capas debe coordinarse, no resolverse duplicando lógica en el frontend. No leer raw desde el browser.

## Sistema visual y datos

Aplicar analytics-ui en las vistas analíticas: jerarquía, componentes reutilizados, escalas veraces y significado consistente entre overview y detalle. Extender `KpiCard`, `ModuleCard`, `ChartCard`, rankings y filtros existentes antes de crear componentes propios de una pestaña.

- Petróleo azul; gas violeta; valor monetario ámbar. Variaciones positivas verdes y negativas rojas según convención explícita del usuario.
- Mantener Resumen como base aprobada, ES/EN, temas claro/oscuro, responsive, deep links y contexto persistente.
- Precio ausente o inválido → valor indisponible; no inventar precios de gas ni factores energéticos.
- No confundir tasa diaria equivalente con telemetría o productividad por día efectivo. No inventar relaciones operador–área, altas/bajas o completaciones.
- Mantener snapshot, cobertura, manifiestos y hashes consistentes. Un período parcial no se publica por ser el máximo raw.

## Verificación y entrega

Ejecutar pruebas proporcionales a los cambios: cálculos/transformaciones, contratos y navegación, typecheck/build y pruebas de navegador cuando estén disponibles. Inspeccionar capturas desktop/mobile, corregir problemas y registrar resultados reales con sus límites. No afirmar éxito de Playwright por una inspección manual.

Actualizar documentación operativa si cambia cómo se ejecuta una pieza. Markdown, enlaces y Mermaid deben ser coherentes; nombres técnicos en inglés, narrativa de producto en español. Nombre oficial: **Vaca Muerta en Datos**; identificador de repositorio: `vaca-muerta-pulse`.

## Secretos y aprobación

Nunca commitear `.env`, JSON de service accounts, tokens, keys ni dumps raw pesados. Nunca incluir secretos en logs, chat o cuerpos de PR. Configuración real en entorno/secret manager; ejemplos sin credenciales.

Flujo de revisión: autor → QA → Security Analyst → Nicolás decide el merge. **Agentes no aprueban ni mergean a main, publican, despliegan ni comparten externamente sin aprobación explícita.** Preparar resultados concretos y revisables antes de pedirla.
