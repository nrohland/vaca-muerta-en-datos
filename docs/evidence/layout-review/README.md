# Revisión de composición e interacción — 20 de octubre de 2026

La revisión independiente de las cinco pestañas encontró tres fallos en la versión pública anterior: selección ambigua de concesiones superpuestas, espacio vacío después del footer de Operadores y filas que invadían la nota final del ranking móvil.

Esta iteración conserva datos y cálculos. Operadores usa dos paneles de igual altura en desktop con ranking internamente desplazable. Áreas adelanta los indicadores, alinea mapa y ranking, integra una leyenda compacta al mapa y conserva las 88 áreas en la lista. La selección destaca el límite de la concesión y mantiene el nombre elegido; cuando varios símbolos coinciden bajo el puntero aparece un selector nominal. Enter sobre un marcador conserva selección directa por nombre. Las geometrías siguen siendo referencia, no límites históricos ni ubicaciones de pozos.

Actividad reemplaza la comparación aislada de dos barras por historia mensual del promedio físico con escala desde cero, valor base exacto, delta y referencia. Mantiene huecos y definiciones: volumen / días calendario / pozos productivos; no mide eficiencia individual.

Resumen mantiene su composición aprobada. La revisión editorial señala como posible mejora futura explicitar las escalas independientes del gráfico combinado volumen/USD; no cambia sus cálculos ni la composición en esta iteración.

Verificación local: typecheck, build estático, presupuesto de JavaScript y 66 tests frontend. La suite de 37 pruebas de navegador cubre alturas, scroll interno, selección superpuesta, filtros, deep links, export y mobile; corre en GitHub Actions porque Chromium local no inicia en este entorno. Los resultados y el commit comprobado quedan en los [checks de la integración](https://github.com/nrohland/vaca-muerta-pulse/pull/54/checks). Las capturas finales se inspeccionan además en el navegador integrado contra Vercel. La evaluación móvil es emulada, no en un teléfono físico. No hay cambios de extracción, precios o warehouse.
