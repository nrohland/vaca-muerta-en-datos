# Rendimiento y operación sin facturación

## Contratos

El flujo histórico activo conserva CSV originales y hashes; genera directamente `history.raw.parquet`, con esquema Arrow explícito (INT64, FLOAT64, STRING, DATE, TIMESTAMP UTC microsegundos), lotes de 32.768 filas, Zstandard y diccionario. `id` de 2024 se conserva nullable. Los negativos ajenos al producto y strings vacíos permanecen intactos. El manifiesto identifica formato, tamaño y SHA-256 del payload, separado de los hashes oficiales. No cambia el grano ni los anclajes, no convierte precios en seeds ni altera el corte aceptado.

La revisión de schema/cobertura precede la escritura. Antes del load: bytes, esquema físico Parquet, conteos, meses, hashes anuales y cronología deben coincidir. La unicidad anual usa un mapa de bits por pozo/mes, sin guardar una clave por fila. El helper legado monoanual conserva su contrato; no es el workflow histórico activo. Cotizaciones pequeñas siguen usando el formato de su contrato existente.

## Warehouse y dbt

El CLI comprueba facturación desactivada antes de las etapas warehouse. Es una lectura de Cloud Billing/BigQuery y no cambia facturación, IAM ni cuotas. Falta de acceso a billing bloquea; falta de inventario global de jobs se informa sin inventar saldo. Almacenamiento lógico accesible >8 GiB y consumo mensual global >80% de 1 TiB bloquean aceptación. No se interpreta almacenamiento actual como cuota vitalicia restante del sandbox.

El perfil generado usa cuatro threads. dbt gestiona el paralelismo del DAG y respeta dependencias; no se ejecutan builds simultáneos escribiendo las mismas tablas. Staging candidato se materializa una vez para compartir deduplicación/filtros entre tests y modelos. Dev/prod retenidos mantienen su configuración. No se cambia el particionado histórico ni se introduce MERGE/DML en sandbox.

El run conserva entradas de fuente/precios y métricas reales. Presupuesto de aceptación dbt: 3 GiB bytes facturables agregados, 1 GiB por query; métricas query ausentes bloquean. Es un chequeo posterior al build y no un límite transaccional previo de toda la corrida. El límite por query existente protege cada ejecución. Tiempos >300 s generan advisory; no se afirma regresión estadística desde una sola baseline. El preflight enumera vencimientos cercanos; no borra tablas.

## Entrega estática

`release.json` sigue siendo el snapshot canónico íntegro y verificable. El build genera un overview con todas las métricas de cuenca y rankings top 5, más cuatro shards completos por fluido/dimensión. Los paths incluyen el hash canónico y el hash del archivo comprimido. SHA-256, tamaños y counts están vinculados en `manifest.delivery`; una aprobación sigue cubriendo el hash exacto del manifiesto. Si una generación necesita cambiar un manifiesto con aprobación existente, se detiene y exige un nuevo candidato; no renueva aprobaciones.

Overview ≤250 KiB gzip. El browser comprueba bytes/hash antes de descomprimir, limita también el tamaño descomprimido, valida contratos y muestra un estado de carga/error hasta tener detalle completo. Cache de detalle por versión/fluido/dimensión; no se mezcla un top 5 con ranking completo. Producción/Actividad no necesitan shards de entidades. Módulos de pestañas se importan de forma diferida. Los precios descargan en paralelo, y se usan sólo después de comprobar su vínculo de versión. Áreas memoiza rankings.

Los `.json.gz` son blobs gzip verificados y descomprimidos por el cliente: el host debe servirlos como `application/gzip` **sin** `Content-Encoding: gzip` aplicado al mismo blob. No dependemos de la compresión automática del hosting. Los assets con hash admiten cache largo/inmutable; manifest/approval necesitan revalidación. No se eligió ni desplegó hosting.

CI Linux ejecuta Chromium, toda la suite de pestañas, deeplinks, corrupción/reintento, budgets de entrega y capturas desktop/mobile. Las mediciones locales del browser son laboratorio; no equivalen a Web Vitals de usuarios en un hosting público.

## Evaluaciones que no se aplican a ciegas

El clustering actual no se altera sin benchmark controlado de filtros representativos. Las tablas pequeñas no ganan por añadirlo. El raw particionado por ingesta conserva historia sin crear particiones por meses vencidos. Las copias antiguas requieren inventario/dependencias y respaldo antes de una eliminación explícita. No habilitar billing para eliminar expiraciones. Mantener fuentes reproducibles y monitor de vencimientos; el snapshot estático no depende de que BigQuery conserve tablas más de 60 días.

La preparación pública solapa descargas/revisión de dos años independientes, con dos workers y un único writer Parquet ordenado. Conserva checkpoints atómicos por fase/año (tiempo, estado, conteo y clase de error, sin payload/credenciales). El timeout de source-prepare es 20 minutos; 10 minutos resultó insuficiente en el runner real y se detuvo antes de autenticación. Su diagnóstico se conserva separado del artifact que consume dbt; no altera su layout ni los gates. El timeout no se presenta como una mejora de velocidad.
