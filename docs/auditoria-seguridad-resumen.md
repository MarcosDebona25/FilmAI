# Auditoría de seguridad: resumen

Resumen para el equipo de la auditoría `standard` de `security-audit` (commit `f7bbb6b`, 18/10/2026). Contiene solo títulos, módulos, estado y prioridad. Los informes completos con la reproducción siguen locales (`security-audit/`, ignorado por git) y se comparten por otro canal si hace falta.

## Cómo se hizo

1. **run-1:** lectura de código. Dejó 11 pistas por validar y 1 rechazada.
2. **run-2:** las 11 pistas se probaron en un sandbox Docker sin acceso a internet (repositorio en solo lectura, TMDB simulado, correo en memoria, Postgres y Redis efímeros, solo datos ficticios). Cada pista la reprodujo un agente validador y la repitió un verificador independiente.

## Resultado

- **11 pistas confirmadas** (ninguna alta ni crítica), **1 rechazada**, 0 pendientes.
- Hay factores de despliegue que el repositorio no muestra y que cambian la probabilidad real: proxy o WAF delante, límites de Resend y de TMDB, quién lee los logs, exposición real del puerto de Redis y permisos de staff concedidos.

## Hallazgos

| # | Módulo | Hallazgo | Estado | Severidad | Prioridad |
|---|---|---|---|---|---|
| ~~F1~~ | ~~infra / settings~~ | ~~Redis sin contraseña y publicado, con caché que deserializa pickle~~ | **Resuelto** (20/10/2026) | ~~Media~~ | ~~1~~ |
| ~~F2a~~ | ~~usuarios~~ | ~~Login sin límite de intentos~~ | **Resuelto** (20/10/2026) | ~~Media~~ | ~~1~~ |
| ~~F2b~~ | ~~usuarios~~ | ~~Reenvío de confirmación y registro sin límite (correo masivo)~~ | **Resuelto** (20/10/2026) | ~~Media~~ | ~~1~~ |
| ~~F3~~ | ~~catálogo / settings~~ | ~~Límite del catálogo eludible con `X-Forwarded-For`, con amplificación a TMDB y Redis~~ | **Resuelto** (20/10/2026) | ~~Media~~ | ~~1~~ |
| ~~F4~~ | ~~usuarios~~ | ~~Cuenta pendiente sin vencimiento reserva el correo (pre-secuestro)~~ | **Resuelto** (20/10/2026); riesgo residual y mejora para el despliegue en `docs/decisiones.md` | ~~Media~~ | ~~2~~ |
| ~~F5~~ | ~~usuarios (admin)~~ | ~~Staff con permiso parcial puede escalar privilegios~~ | **Resuelto** (20/10/2026) | ~~Media~~ | ~~2~~ |
| ~~F6~~ | ~~catálogo~~ | ~~Parámetros de trending sin validar (rutas hacia otros endpoints de TMDB)~~ | **Resuelto** (24/10/2026) | ~~Baja~~ | ~~3~~ |
| ~~F7~~ | ~~catálogo~~ | ~~Alta de reseñas con ids inexistentes o enormes: filas vacías y 500 (Internal Server Error)~~ | **Resuelto** (24/10/2026) | ~~Baja~~ | ~~3~~ |
| ~~F8~~ | ~~usuarios~~ | ~~Clave de confirmación de correo escrita en el log~~ | **Resuelto** (20/10/2026) | ~~Baja~~ | ~~3~~ |
| ~~F9~~ | ~~frontend~~ | ~~Redirección abierta posterior al login (`next`)~~ | **Resuelto** (20/10/2026) | ~~Baja~~ | ~~3~~ |
| F10 | catálogo | Moderación de reseñas reversible por el autor | **Pendiente** (verificado en el código el 28/10/2026; falta la decisión de producto, a cargo de Gonza) | Baja | 4 (decisión de producto) |
| ~~F11~~ | ~~usuarios~~ | ~~Login y reset de contraseña sin barra final esquivan los límites de F2~~ | **Resuelto** (26/10/2026) | ~~Media~~ | ~~1~~ |
| — | frontend | Sin cabeceras anti-framing | Rechazado | — | Endurecimiento opcional |

## Orden sugerido

1. F1 (configuración de Redis).
2. F3 y F2: identidad del cliente y límites de tasa.
3. F9 y F8, que son cambios chicos.
4. F6 y F7 (catálogo).
5. F5 (admin).
6. F4 (resuelto) y F10, después de decidir el comportamiento con el equipo.

Cada fix va como tarea aparte, con su test de regresión y su entrada en `docs/decisiones.md`.

## Registro de correcciones

Rama `security/fixes`, un PR por grupo hacia `security/audit`. Solo resume qué se hizo; el detalle técnico vive en `docs/decisiones.md` y no incluye credenciales.

- **20/10/2026, F1 (Redis):** Redis exige contraseña y su puerto solo se publica en la propia máquina. En producción la aplicación se niega a arrancar si alguna de las tres URLs de Redis no trae contraseña, y la caché de Django dejó de usar un formato que puede ejecutar código al leerse. Se agregaron tests de configuración y de serializador; la suite completa pasa. Quien tenga un `.env` local debe definir `REDIS_PASSWORD` (ver `.env.example`).
- **20/10/2026, F2 y F3 (límites de tasa):** el login, el registro y el reenvío de la confirmación tienen límites por cuenta o correo y por IP, y el reenvío suma un enfriamiento entre envíos al mismo correo. Los límites por IP ya no se pueden eludir falseando un encabezado: la cantidad de proxies de confianza es configurable (por defecto 0, a confirmar al desplegar). El catálogo rechaza páginas fuera del rango de TMDB, y Redis tiene un tope de memoria que no desaloja la cola de tareas. Quedan fuera de este grupo, y siguen abiertos, el tope de llamadas a TMDB por pedido y el control de los demás parámetros del catálogo (F6 y F7). Tests nuevos para cada límite; la suite completa pasa.
- **20/10/2026, F8 y F9 (log y redirección):** el log de la confirmación de correo ya no incluye la clave del enlace, ni entera ni en partes; conserva el largo para diagnosticar. La redirección posterior al login solo acepta destinos del mismo sitio, comprobado con el mismo análisis de URL que hace el navegador. Tests nuevos de backend y de frontend (incluida la página de login); las suites completas pasan.
- **20/10/2026, F5 (administración):** un usuario de staff con permiso solo para editar usuarios ya no puede concederse privilegios, ver ni modificar superusuarios, ni cambiar la contraseña ni borrar a otro staff. Sigue pudiendo editar a los usuarios comunes, y el superusuario conserva el control total. Tests nuevos para ambos lados; la suite completa pasa.
- **20/10/2026, F4 (cuentas pendientes):** una cuenta sin confirmar el correo deja de reservar el correo y el nombre de usuario pasado el plazo del enlace, y una tarea diaria las elimina. El correo de confirmación del registro ahora avisa que no hay que abrir el enlace si no se pidió la cuenta. Queda como mejora recomendada antes del despliegue que la contraseña se elija al confirmar el correo; está descrita en `docs/decisiones.md`.
- **24/10/2026, F7 (ids de producciones):** calificar o agregar a una lista una producción que TMDB no conoce ya no deja una fila vacía en la base, y un id más grande de lo que admite la columna responde un error de validación en lugar de un error interno. Las lecturas y las vistas del catálogo validan el mismo rango. Tests nuevos en reseñas, listas y materialización; la suite completa pasa.
- **24/10/2026, F6 (tendencias y llamadas a TMDB):** las tendencias solo aceptan los tipos y períodos que muestra la aplicación, así que ya no se puede llevar el pedido a otros endpoints de TMDB. Además, cada pedido tiene un tope de llamadas a TMDB (reintentos incluidos) y cada IP un límite por minuto que cuenta llamadas reales, no pedidos: lo que sale de la caché no cuenta. Tests nuevos de validación, de los dos topes y de los hilos de Buscar; la suite completa pasa.
- **26/10/2026, F11 (rutas sin barra final):** el inicio de sesión y la recuperación de contraseña también limitaban los intentos solo si se llamaban con la barra final; sin ella se llegaba a la vista original, sin límite. Ahora las dos variantes llevan los mismos límites. Test nuevo; la suite completa pasa.

## Abiertos de la revisión del 24/10/2026 (verificados el 28/10/2026)

La revisión con subagentes del 24/10/2026 dejó hallazgos sin aplicar además de F11 (resuelto). Siguen abiertos en el código:

- **Media:** el reset de contraseña no tiene límite por IP y un cuerpo inválido responde 500 (Internal Server Error).
- **Baja:** la clave de TMDB queda registrada en el log; Postgres se publica en todas las interfaces; `entrypoint.sh` maneja la contraseña del superusuario en el comando.
- **Al desplegar:** cookies seguras, HSTS y cabecera de proxy de Django; `NUM_PROXIES`; restringir `/admin/`; CSP (que además cubre el rechazo de las cabeceras anti-framing); cifrado en reposo de la base; Sentry.
- **Decisiones abiertas:** techo de ítems en Favoritos y Pendientes, duración del access token (8 h), tope por IP detrás de NAT y enumeración por tiempo en el reset.

Todavía no hay un despliegue público; los puntos «al desplegar» se cierran antes de publicar la instancia. El detalle técnico y la reproducción están en los informes locales (`security-audit/`, ignorado por git) y en `docs/decisiones.md`; acá queda solo el estado, como en el resto del archivo.

Resueltos desde esa revisión: `/admin/login/` con límite, topes de escritura, reseñas de cuentas dadas de baja anónimas, escalada por el admin y Google con correo verificado. El detalle está en `docs/decisiones.md`.
