# Experimento de conectividad con curl-cffi

Compara libcurl sin impersonación y perfiles Chrome 110/142 de `curl_cffi==0.17.0` en runners estándar x64/ARM. Los destinos son los endpoints reales de metadata/CSV 2026 de Energía y una referencia EIA de control.

No sigue redirecciones, modifica TLS, usa proxies ni autentica contra cloud. Verificación TLS permanece activada. El CSV sólo se prueba mediante Range y un límite local de 64 KiB; no se certifica una descarga completa, integridad, frescura ni publicación. Se reportan tiempos de DNS/TCP/TLS y prefijo esperado, nunca cuerpos de respuesta. Un job verde significa diagnóstico terminado, no fuente disponible.

La biblioteca permite imitar perfiles TLS/HTTP; no garantiza que el servidor acepte la conexión ni cambia la IP del runner. Un timeout anterior a TCP impide que la huella TLS llegue al servidor. Este experimento no sustituye el tap revisado por tap-csv ni introduce un extractor paralelo en producción.
