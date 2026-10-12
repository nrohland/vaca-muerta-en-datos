# Referencia USD para gas y arquitectura de precios

Revisión del 11 de octubre de 2026. No se implementó USD para gas ni se cambiaron fuentes o configuración de red.

## Resultado verificable

Hay una referencia oficial útil: precio promedio ponderado de **Cuenca Neuquina, contrato TOTAL**, campo `precio_ppp`, publicado por Secretaría de Energía en el recurso `d87ca6ab-2979-474b-994a-e4ba259bb217`. El [tablero oficial Res. 1/2018](https://estadisticasenergia.mecon.gob.ar/superset/dashboard/175/?standalone=true) documenta USD/MMBTU, ventas de gas normalizado a 9.300 kcal/m³ y origen convencional y no convencional. Corresponde a cobros de productores en PIST o puntos previos; excluye transporte, distribución, subsidios, impuestos y cargos financieros. La información desde octubre de 2022 permanece provisoria según las aclaraciones publicadas. Esa serie de cuenca puede servir como benchmark explícito, no como precio realizado de la formación o de cada operador.

El [catálogo oficial](https://datos.gob.ar/dataset/energia-precios-gas-natural) declara actualización mensual. La copia del CSV oficial retenida el 9 de octubre tiene 1.602 filas y hash SHA-256 `1bd11d294573d30c8f366dfab302ee8bd4b5a19925358263b8f6f608e3576ae4`. Se volvió a perfilar independientemente: 89 registros Neuquina/TOTAL, enero de 2019–mayo de 2026, cobertura completa enero de 2023–mayo de 2026; junio, julio y agosto de 2026 ausentes. Mayo de 2026: `precio_ppp=4.01`, exportación `precio_expo=4.66`, ambos distintos. No mezclar ambos ni promediar TOTAL, FIRME e INTERRUMPIBLE: TOTAL ya es la categoría agregada publicada.

Campos CSV: `id_pub`, `anio`, `mes`, `cuenca`, `contrato`, `precio_distribuidora`, `precio_gnc`, `precio_usina`, `precio_industria`, `precio_otros`, `precio_ppp`, `precio_expo`, `indice_tiempo`, `fecha`. Sin volúmenes de venta, ponderadores, formación, empresa o calorificidad de pozo. No se puede reconstruir un promedio propio ponderado por destinos ni demostrar representatividad exclusiva de Vaca Muerta a partir de ese archivo. Las categorías de cuenca incluyen Neuquina y Total Cuenca; no intercambiarlas.

## Qué queda abierto

La descarga/API actual no pudo comprobarse: herramienta web inaccesible, Superset directo con timeout y DNS del entorno bloqueado. El texto metodológico oficial sí se recuperó por búsqueda primaria; el perfil numérico corresponde a la copia retenida, no a una descarga nueva. La fecha de modificación de metadata 9 de octubre no prueba cobertura a agosto. No afirmar que agosto tiene precio ni extender mayo a meses posteriores.

La documentación recuperada de Capítulo IV identifica volumen gas en miles de m³, pero no demuestra en esta revisión que cada volumen de producción sea equivalente comercial de 9.300 kcal/m³. Falta verificar base térmica, condiciones de referencia y/o poder calorífico. Una conversión universal m³→MMBTU supondría calidad no medida. [NIST](https://nvlpubs.nist.gov/nistpubs/Legacy/IR/nbsir82-2401.pdf) documenta las convenciones de caloría y Btu; elegir la convención explícita de las fuentes es necesario antes de fijar un factor.

## Definición recomendada

Separar precio benchmark de valorización. Se puede cargar y mostrar **Referencia Neuquina PPP — USD/MMBTU** para los meses comprobados. Una estimación de volumen comercial normalizado requiere `valor_usd = volumen_m3_normalizado_9300 × energía_MMBTU_por_m3_9300 × precio_ppp_del_mismo_mes`. Si Capítulo IV no acredita esa normalización, presentar eventualmente un escenario de referencia a 9.300 kcal/m³ como supuesto explícito versionado; no describirlo como conversión física medida ni facturación. No activarlo silenciosamente como valor real del producto. Para estimación física medida, usar poder calorífico trazable compatible con el grano y la fuente.

Una referencia monetaria robusta para agosto sigue bloqueada por precio mensual no comprobado y contrato térmico no resuelto. Los meses sin precio quedan nulos; YoY/MoM exige precios de ambos meses; YTD exige cobertura completa. No forward fill, precio fijo, Henry Hub sustituto ni promedio de precios sin pesos. Ningún valor monetario de gas fue implementado en esta investigación.

## Arquitectura recomendada

Para producto final, precios como **fuente dinámica**: extracción trazable → raw con snapshot/hash/fechas → staging dbt con unidades y claves → mart de referencia por producto/mes/benchmark → mart de valorización junto a volúmenes aceptados → release/API cache → Next para presentación. Esto aplica también a Brent. Las reglas de negocio, conversiones, comparadores y gates de cobertura pertenecen a dbt y contrato compartido; no duplicarlas como cálculo principal en navegador.

Seeds dbt sólo para catálogos/conversiones/metodologías estables o una copia histórica temporal y reproducible con hash/cutoff explícitos. Un precio mensual revisable no debería mantenerse manualmente como seed permanente. El CSV retenido puede servir como fixture o respaldo histórico mientras se cierra la ingesta; no constituye actualización automatizada.

Tests necesarios: unicidad mes/cuenca/contrato, precios válidos con política explícita para cero, ausencia de mezcla de categorías agregadas, unidades y base térmica, cobertura mensual, frescura por extracción y período económico, revisiones de snapshots, conciliación de valores entidad/total, y pruebas de huecos/precios ausentes/bases cero. El frontend conserva estado de indisponibilidad y muestra fuente, benchmark y carácter provisorio. No se ha desplegado esta arquitectura.

## Alternativa de regalías

El [catálogo oficial de regalías y precios](https://datos.gob.ar/ne/dataset/energia-regalias-petroleo-crudo-gas-natural-glp-gasolina-condensado) ofrece ZIP de gas y advierte provisionalidad de los dos últimos períodos. El índice consultado conserva una descripción de agosto de 2023: no demuestra archivo ni precio a agosto de 2026. Las búsquedas provinciales no verificaron una serie mensual descargable USD/dam³ hasta agosto. Sin inspección del ZIP y definición de denominador no corresponde usar una cotización de regalías como sustituto. Provincia de Neuquén tampoco equivale a toda Cuenca Neuquina ni a formación Vaca Muerta. Si aparece un precio USD/dam³ se evita la conversión a energía, pero sigue siendo necesario confirmar base volumétrica, normalización, universo y fecha antes de aplicarlo a Capítulo IV.

Se repitió la descarga shell después de la notificación de acceso de red del coordinador: esta subejecución siguió recibiendo fallo DNS. Por eso el corte mayo conserva estatus de copia retenida; el coordinador puede cerrar una descarga nueva y actualizar este hallazgo con checksum/perfil real.
