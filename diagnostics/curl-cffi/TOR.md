# Experimento Tor/SOCKS5

Un cliente Tor corre exclusivamente en un runner estándar efímero de GitHub. SOCKS5h resuelve DNS por Tor; sólo las peticiones explícitas del diagnóstico usan esa ruta. Se prueban dos contextos aislados mediante SOCKSAuth: no implican necesariamente dos IPs diferentes ni salidas argentinas.

El control oficial `check.torproject.org` confirma IsTor y EIA verifica otro origen. No se imprimen IPs, cuerpos ni logs de circuitos. Las consultas a Energía usan metadata y prefijos de CSV limitados a 64 KiB. TLS sigue verificado, sin cookies de autenticación, credenciales cloud, cargas, cambios de frescura ni procesamiento Singer.

Se instala Tor desde los paquetes de Ubuntu y se usa su servicio con configuración cliente; no se crea un relay o exit. El proceso se detiene al terminar. No se ejecuta Tor en la Mac ni se configura proxy global para Meltano/Google Cloud. La disponibilidad de salidas y la respuesta de la fuente deben observarse: no se afirma que sean residenciales o no bloqueadas. No se escanean ni usan proxies abiertos de terceros no autorizados.
