# Revisión final independiente de las cinco pestañas

Auditoría estática inicial del código integrado del 11 de octubre de 2026, sobre commit `0316dd5`, con revalidación de las correcciones el 12 de octubre de 2026 sobre el árbol integrado actual. Se revisaron las cinco vistas, componentes compartidos, transformaciones, navegación, estilos responsive y suites de pruebas. No se modificó código ni se lanzó otro navegador.

## Resultado verificable

- Suite actual de unidad: **47/47 aprobados**, ejecutada nuevamente tras las correcciones; incluye cuatro casos nuevos de visibilidad de series. La revisión inicial tenía 43/43.
- Typecheck: **aprobado**, ejecutado nuevamente.
- Los agregados de operadores y áreas concilian con el universo. Cuotas mantienen el denominador de cuenca incluso al filtrar. Las bases mensuales/interanuales son exactas; bases ausentes no se sustituyen por meses cercanos y base cero no inventa porcentaje.
- USD usa precio válido propio de cada período; gas retorna volumen físico con explicación. Actividad preserva unidades físicas y separa diferencia neta de altas/bajas. Promedio por pozo usa días calendario, sin prometer productividad por tiempo efectivo.
- Navegación, fluido, modo, comparación, período y ventana se codifican en URL. Resumen mantiene KPIs y estructura aprobados: el diff de componentes compartidos conecta destinos reales, exporta logos/nombres y añade controles de series a los detalles.
- Existe evidencia previa de inspección con navegador integrado y capturas. Esta revisión no repite esa ejecución ni la presenta como aprobación de Playwright/axe. La suite automática de browser/axe sigue pendiente por el bloqueo de Chromium documentado.

## Estado después de las correcciones

Los cuatro hallazgos P2 y el ajuste P3 están **corregidos y verificados por revisión de código**. La revalidación no encontró nuevas fallas introducidas por estos cambios. La suite completa de unidad y typecheck finalizaron con código 0.

| Hallazgo inicial | Reparación verificada | Evidencia actual |
| --- | --- | --- |
| Mensaje falso al ocultar USD | `chartVisibility` separa disponibilidad y selección; el pie usa `unavailable`. | Test «hiding verified USD by choice does not claim missing prices», aprobado. |
| Gráfico vacío sin precios válidos | Ventana sin valores USD usa `activeSeries=physical`, deshabilita Ambas/Valor y conserva explicación de indisponibilidad. | Test de fallback sin precios y pruebas gas/pozos con selección anterior, aprobados. |
| SVG oculto pero enfocable | Evolution fija `accessibilityLayer=false`; conserva región de scroll enfocada y tablas accesibles alternativas. | Verificación estática del componente y contrato de Recharts. Validación runtime/axe pendiente. |
| Encabezado m³ frente a celdas MMm³ | `fullUnit=unit`; encabezado y contexto del delta de gas usan MMm³. | Verificación estática de las celdas y las llamadas a `signed`; tests de unidades/CSV siguen aprobados. |
| Año USD antiguo gris | Tokens antiguos ahora cálidos: `#a99579` claro y `#8f7c60` oscuro. | CSS revisado; inspección visual final a cargo del integrador. |

No se ejecutó Playwright/axe en esta revalidación ni se declara accesibilidad automatizada aprobada. El integrador conserva la responsabilidad del smoke con navegador integrado y sus capturas; unit/typecheck no reemplazan esa inspección.

## Hallazgos iniciales, todos reparados

### P2 — Selector físico anuncia precios ausentes aunque estén disponibles

`apps/web/app/dashboard-components.tsx`, inicialmente líneas 466 y 629. Elegir «Producción física» desactiva la serie monetaria por decisión del usuario; el pie del gráfico interpreta `!monetary` como ausencia de referencia y muestra «Referencia de precios no disponible». Distinguir ocultamiento voluntario de disponibilidad de precios.

### P2 — Selección monetaria puede dejar el gráfico vacío

Mismo componente, inicialmente líneas 421 y 466. Con un objeto de precios cargado, elegir «Valor estimado» y pasar a una ventana sin precios válidos hace que tanto `showPhysical` como `monetary` sean false. La gráfica queda vacía y el título vuelve a producción. Resolver mediante selección monetaria deshabilitada cuando no hay valores, fallback explicado o estado explícito de USD no disponible; conservar nulls y no inventar precios.

### P2 — Gráfico enfocable dentro de `aria-hidden` en Resumen

Mismo componente, inicialmente líneas 537 y 544. El contenedor del gráfico usa `aria-hidden=true`, mientras Resumen habilita `accessibilityLayer={!detailView}`. Confirmado en la biblioteca instalada `recharts/lib/container/RootSurface.js`: esa opción asigna `tabIndex=0` al SVG. El resultado puede recibir foco pero está oculto a lectores de pantalla. Corregir la combinación sin cambiar layout: gráfico no enfocable con tabla accesible alternativa, o gráfico expuesto y correctamente etiquetado. No afirmar axe aprobado sin ejecución efectiva.

### P2 — Unidades divergentes en delta de tabla de gas

`apps/web/app/production-dashboard.tsx`, inicialmente líneas 57 y 448. Header/contexto declara Δ en m³; las celdas calculadas por `signed` muestran MMm³ sin multiplicar por un millón. El texto de la celda hace explícita su magnitud, pero contradice el encabezado. Usar MMm³ en encabezado/contexto o convertir de manera consistente a m³.

### P3 — Año más antiguo de USD usa gris

`apps/web/app/globals.css`, tokens `--monetary-oldest`: `#a6a19a` en claro y `#8d939b` en oscuro. Las series restantes de USD usan ámbar. Ajustar el tono más antiguo a la familia ámbar si se exige que todas las líneas de valor conserven esa identidad; no afecta cálculos.

## Revisión por vista

| Vista | Resultado estático |
| --- | --- |
| Resumen | Arquitectura/KPIs preservados; combinación foco + aria-hidden reparada en el gráfico compartido. |
| Producción | Tres KPIs no redundantes, YTD comparable, años calendario, barras divergentes y CSV correcto; estados del selector y encabezado de gas reparados. |
| Operadores | Ranking completo, búsqueda/dirección/orden; detalle, CSV y procedencia legal; huecos nulos y cuotas reales. Sin nueva falla de cálculo detectada. |
| Áreas | Ranking accesible con ampliación progresiva; detalle, bases exactas y huecos; relación operador–área explícitamente no inferida. Sin nueva falla de cálculo detectada. |
| Actividad | Pozos únicos según contrato, diferencia neta, promedio físico; rangos propios; `kind=wells` fuerza ausencia de línea monetaria. Sin nueva falla de cálculo detectada. |

Los hallazgos detallados reflejan la fotografía inicial y se mantienen como trazabilidad. Sus correcciones están verificadas en el árbol actual, todavía sin un commit nuevo al momento de esta revisión; el integrador debe registrar el commit final y su smoke de navegador. Esta auditoría no valida publicación, despliegue, ejecución de warehouse ni automatización end-to-end del pipeline.

## Verificación del integrador en navegador

Las cuatro regresiones se comprobaron sobre el build final: ocultar USD con precios válidos no anuncia indisponibilidad; la tabla gas declara MMm³ igual a sus celdas; ningún SVG oculto de Resumen queda con tabindex=0; la fixture aislada sin precios anteriores a 2026 conserva una barra física y un aviso correcto al seleccionar enero 2023. Además, los 20 estados responsive (5 vistas × 4 anchos) pasan nuevamente. El release real no fue alterado. [Resultados](regresiones-finales.json). Build estático aprobado en copia con código de app idéntico byte a byte. Axe automatizado sigue pendiente; no se presenta como ejecutado.
