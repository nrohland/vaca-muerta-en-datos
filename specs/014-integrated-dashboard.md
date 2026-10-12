# 014 — Pestañas integradas y validación final

Autorización de Hito 3: petición del usuario del 11 octubre 2026. Mantener arquitectura, layout y KPIs de Resumen; conectar únicamente tokens de producto y destinos funcionales.

Producción: tres KPIs distintos (mensual, delta absoluto calendario, acumulado enero–mes con variación vs igual acumulado anterior). Sin KPI duplicado de récord/crecimiento. Petróleo #27627C, gas #7954A1; secundarios #8AB5C5/#B5A0D2, monetario #B47B32. Variantes legibles dark. Históricos mantienen nulls, cero como origen físico/monetario independiente, años distinguibles dentro del tema. Delta positivo/negativo divergente con línea cero y codificación de dirección, no juicio causal. Tabla compacta, primera columna fija, CSV con precisión original.

Operadores, Áreas y Actividad se implementan con specs 011–013, ámbitos aislados y componentes compartidos. Actividad muestra conteos históricos y cambios netos; no inferir altas/bajas, perforación ni completaciones desde agregados. Relaciones operador–área sólo cuando hay fuente verificada; no reconstruir desde marginales.

Contexto fluid/month/mode/comparison/range e identificadores vive en URL y atrás/adelante. Preferencias ES/EN y tema persistentes localmente. Gas USD: aviso y valores físicos; precios ausentes USD petróleo = indisponible, nunca cero/interpolación.

Validación: cálculos y transformaciones, navegación, descarga, disponibilidad de precios, ES/EN, oil/gas, light/dark y anchos 320/390/768/1440. Capturas integradas desktop/mobile y revisión visual. No merge, publicación ni despliegue. Entrega local primero; PRs sólo sin violar límite de compartir externamente.
