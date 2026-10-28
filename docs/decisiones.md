# Decisiones y Cambios — FilmAI

Registro de decisiones de diseño y cambios relevantes del proyecto.
Formato: fecha (DD/MM/AAAA), título y descripción (qué, por qué, archivos afectados).

---

## 28/10/2026 — Nombres de usuario reservados (issue #137)

- **Fecha**: 28/10/2026
- **Descripción**: el registro, el alta con Google y el cambio de nombre en el perfil rechazan nombres que se confunden con una cuenta del equipo. Los permisos siguen dependiendo de `is_staff`/`is_superuser`, nunca del nombre: esto solo evita la suplantación.
  - **Regla** (`usuarios/validators.py`, `es_nombre_usuario_reservado`): se compara en minúsculas, sin los dígitos del final («admin2026»), sin ningún dígito («1admin», sugerencia de PR-Agent) y leyendo los números como letras («Adm1n», «r00t»), y también sin un prefijo o sufijo decorativo («theadmin», «soporteoficial», «adminteam»). Una lista se compara entera (`admin`, `root`, `staff`, `soporte`, `support`, `sistema`, `noreply`…) y otra se busca dentro del nombre (`filmai`, `administr`, `superadmin`, `moderador`…). «admin» no se busca adentro porque dejaría afuera a «badminton».
  - **Error**: `username_not_allowed` (400), que ya estaba en el catálogo y traducido («No podés usar ese nombre de usuario. Elegí otro.»). No dice que el nombre está reservado ni muestra la lista; el contrato no cambia.
  - **Chequeo en vivo**: `GET /api/auth/username-available/` responde `{"disponible": false, "motivo": "reservado"}` y el formulario muestra el mismo error que al enviarlo, en vez de «ya está en uso».
  - **Cuentas existentes**: quien ya tenía un nombre así lo conserva; guardar el perfil sin cambiarlo no falla. El superusuario que crea `entrypoint.sh` no pasa por esta validación (se crea directo en la base).
  - Límite aceptado: una lista no cubre toda variante posible; se suman nombres a medida que aparezcan.
- **Archivos afectados**: `backend/usuarios/validators.py`, `backend/usuarios/serializers.py`, `backend/usuarios/views.py`, `backend/usuarios/test_nombres_reservados.py` (nuevo), `frontend/lib/use-username-availability.ts`, `frontend/app/(public)/register/page.tsx`, `frontend/app/complete-signup/page.tsx`, `frontend/e2e/acceso.spec.ts`, doc 02, `openspec/specs/error-contract/spec.md`.

---

## 28/10/2026 — XSS: revisión, enlace de TMDB validado y dos pendientes (CSP y chatbot)

- **Fecha**: 28/10/2026
- **Descripción**: revisión de las vías de XSS a pedido de Gonza.
  - **Lo que ya protege**: React escapa todo lo que muestra y no hay `dangerouslySetInnerHTML` ni librerías de Markdown/HTML; las plantillas de Django (correos, documentación) escapan y ninguna usa `|safe` ni `autoescape off`; `?next=` del login pasa por `destinoSeguro` (`lib/safe-next.ts`), que solo acepta el mismo origen; las cookies del JWT son `HttpOnly` (un XSS no podría robar el token, aunque sí actuar como el usuario).
  - **Arreglado**: el `link` de `watch/providers` de TMDB iba tal cual al `href` de «See all options on TMDB». Un `javascript:` se habría ejecutado al hacer clic. Ahora `catalogo/services/plataformas.py` lo acepta solo si empieza con `https://`; si no, `enlace` va en `null` y las plataformas se siguen mostrando.
  - **Pendiente: CSP (Content-Security-Policy)**, para antes del despliegue. Hoy no hay una segunda barrera si algo se cuela. Para decidir entonces (con la skill `comparar-opciones`): CSP con *nonce* desde el middleware de Next (fuerza el render dinámico) frente a una política estática con `'unsafe-inline'` para estilos; incluir `frame-ancestors 'none'`. Probar antes en modo `Content-Security-Policy-Report-Only`.
  - **Pendiente: el chatbot**, cuando se implemente. Lo que responde el modelo es texto que un tercero puede manipular (inyección de prompt a través de sinopsis, reseñas o el propio mensaje). Reglas: mostrarlo como texto o, si lleva Markdown, con un renderizador que no acepte HTML crudo y con sanitizado (`rehype-sanitize` o DOMPurify); los enlaces solo `https://` y, si son internos, armados por el frontend a partir de ids (las tarjetas), nunca URLs que escriba el modelo; nada de `dangerouslySetInnerHTML`. Agregar tests con respuestas maliciosas (`<script>`, `<img onerror>`, `javascript:`).
- **Archivos afectados**: `backend/catalogo/services/plataformas.py`, `backend/catalogo/tests_plataformas.py`, `openspec/specs/tmdb-endpoints/spec.md`.

---

## 27/10/2026 — «Dónde verla» solo con sesión (issue #124)

- **Fecha**: 27/10/2026
- **Descripción**: sin sesión, el país de las plataformas salía de la región del navegador y en la práctica caía en EE. UU. Decisión de Gonza: en vez de adivinarlo, la sección pide iniciar sesión.
  - **Backend**: `ProvidersView` deja de ser pública (como `RecommendedView`: autenticación y permiso por defecto, 401 sin sesión, sin caché pública del navegador) y toma el país de `request.user.pais`; un `?pais=` en la URL se ignora. Un perfil con país inválido sigue dando 400 `country_invalid`.
  - **Frontend**: sin sesión, la ficha no pide plataformas y muestra «Iniciá sesión para ver dónde verla en tu país» con el enlace al ingreso (`title.providers.signedOut`). Con sesión no usa la caché de la visita: el país cambia si se edita el perfil o entra otra cuenta (el backend igual cachea TMDB 12 h).
  - Opciones descartadas: ocultar la sección sin decir nada (el visitante no sabe que existe) y cerrar solo el frontend (la API seguiría respondiendo con cualquier país).
  - `regionDelNavegador` (`lib/format.ts`) queda sin uso en la app; se conserva con su test por si el registro lo usa para preseleccionar el país.
  - Queda abierto del mismo issue lo que agregó Marcos: alternativas de diseño para la caja de plataformas.
- **Archivos afectados**: `backend/catalogo/views.py`, `backend/catalogo/tests_plataformas.py`, `backend/catalogo/test_seguridad_id_tmdb.py`, `contracts/openapi.yaml`, `frontend/components/features/title/TitleView.tsx`, `frontend/tests/title-view.test.tsx`, `frontend/e2e/ficha.spec.ts`, `traducciones/claves-extra.csv`, `frontend/messages/`, docs 02, 03 y 05, `openspec/specs/{tmdb-endpoints,title-page-ui,error-contract}/spec.md`.

---

## 26/10/2026 — Skills `cerrar-tramo` y `comparar-opciones`

- **Fecha**: 26/10/2026
- **Descripción**: dos skills nuevas en `.agents/skills/` para lo que se venía haciendo a mano:
  - **`cerrar-tramo`** (adaptada de la de otro proyecto de Gonza): los chequeos de `ci.yml` en local, agentes de revisión en paralelo con cada hallazgo verificado antes de tocarlo, `decisiones.md` y graphify al día, commit, y cómo mergear una pila de PRs (cambiar la base antes de borrar la rama y empujar para que corra el CI). Se invoca solo a mano (`/cerrar-tramo`).
  - **`comparar-opciones`**: las decisiones del equipo como cuadro comparativo (qué hace, a favor, en contra, costo), la recomendada primera, y la pregunta con opciones interactivas.
- **Archivos afectados**: `.agents/skills/cerrar-tramo/SKILL.md`, `.agents/skills/comparar-opciones/SKILL.md` (nuevos).

---

## 26/10/2026 — Dependencias al día: Next 15.5.28 y Django 5.2 LTS

- **Fecha**: 26/10/2026
- **Descripción**: subida de versiones por seguridad, sin cambios de código de la app:
  - **Next.js 15.5.28** (y `eslint-config-next` igual): corrige GHSA-2464-fhr4-w9xw, una ejecución remota de código en el optimizador de imágenes con SVG (crítica). Se quedó en la serie 15 para no mezclar el salto a Next 16 con un parche de seguridad. Pasaron `tsc`, lint, los 436 tests de Vitest y `next build`.
  - **Django 5.2 LTS** (5.2.18): la 5.1 no recibe parches de seguridad desde 12/2025. Con ella suben **DRF 3.16** (la primera con soporte oficial de 5.2), **django-cors-headers 4.9** y **django-allauth 65.19.7** (parches de la serie 65.19, pin exacto porque `ConfirmarCorreoView` usa una API interna). La suite completa del backend (1038 tests) pasa sin cambios.
  - De los avisos que citó la revisión, dos identificadores GHSA no existen; se verificó cada uno antes de actuar.
- **Archivos afectados**: `backend/requirements.txt`, `frontend/package.json`, `frontend/package-lock.json`.

---

## 26/10/2026 — Comentarios de PR-Agent sobre #133 a #136

- **Fecha**: 26/10/2026
- **Descripción**: cada comentario se verificó contra el código antes de tocar nada. En #133 (bloqueo del admin), uno de tres era válido y menor:
  - **IP falsificable con `X-Forwarded-For`**: falso positivo. `NUM_PROXIES` es 0 en desarrollo (DRF usa `REMOTE_ADDR`) y obligatorio en producción.
  - **POST de otro sitio que agota el contador**: falso positivo. El middleware de CSRF corta con 403 antes de la vista; queda un test que lo prueba.
  - **`Retry-After: 3600`**: es una cota superior, porque la ventana corre desde el primer fallo. Se documenta en el código.
  - **#134, clave `title.reviews.deletedAuthor` faltante**: falso positivo; los catálogos y el CSV están en el PR (el diff que recibió venía recortado por graphify).
  - **#134, clave de React por posición**: riesgo bajo y aceptado; la API no manda el id de reseñas ajenas a propósito.
  - **#135, duplicado con la lista llena y carrera en el techo de ítems**: válidos; arreglados en #135 (ver «Topes de escritura»).
  - **#135, el techo de listas cuenta las inactivas**: falso positivo; borrar una lista la elimina (`lista.delete()`) y la app nunca marca una lista como inactiva.
  - **#136, `EmailConfirmation` en el admin**: falso positivo; ese modelo no está registrado en el admin (allauth registra solo `EmailAddress`).
- **Archivos afectados**: `backend/filmai/documentation.py`, `backend/filmai/test_seguridad_admin_login.py`.

---

## 26/10/2026 — Acceso endurecido tras la segunda revisión de seguridad

- **Fecha**: 26/10/2026
- **Descripción**: hallazgos sin decisión de la segunda pasada de seguridad, cada uno verificado antes de tocarlo:
  - **Escalada por el admin (media)**: F5 limitaba solo a `Usuario`. `SocialAccount` (allauth) dejaba editar `user` y `uid`, así que un staff podía vincular su Google a un superusuario y entrar como él. `OutstandingToken` (simplejwt) mostraba el refresh JWT entero. `Group` permitía armarse un grupo con todos los permisos. Esos 7 modelos (los cuatro de allauth, los dos de simplejwt y `Group`) quedan solo para superusuarios (`usuarios/admin.py`, con la misma clase de admin original).
  - **`SESSION_LOGIN: False`**: el login de la app abría además una sesión de Django, válida en `/admin/`. La API usa solo JWT.
  - **Google exige el correo verificado** en una cuenta nueva, mirando el claim firmado del token (`extra_data["email_verified"]`). `login.email_addresses` no sirve: con `VERIFIED_EMAIL: True`, allauth marca todo correo de Google como verificado. Las cuentas existentes no cambian.
  - **Solo JSON** en login, registro, Google, reset, confirmación del reset y reenvío: con formularios, otro sitio podía dejar al navegador logueado en la cuenta del atacante (*login CSRF*). Un formulario responde 415 (Unsupported Media Type). El contrato OpenAPI deja de ofrecer `x-www-form-urlencoded` y `multipart` en esas rutas.
  - **Un contador por cuenta en el login**: si el correo o el usuario corresponden a una cuenta, la clave es su `pk`. Antes, la misma cuenta se probaba 10 veces por correo y 10 por usuario.
  - **Google con límite por IP** (`GoogleIPThrottle`, scope `google_ip`, 30 por minuto como el login, pero con contador propio): cada pedido verifica una firma y puede crear una cuenta. Compartir el contador con el login hacía que una ráfaga de logins con contraseña bloqueara Google en esa IP (lo señaló PR-Agent en #136).
  - **Logout sin barra** con su código `logged_out`, como con barra.
  - **Correos fuera de los logs** (se registra el `pk` o la cantidad) y el logger `usuarios` en DEBUG solo con `DEBUG=True`.
  - **Cabeceras básicas** en el frontend (`next.config.ts`): `X-Content-Type-Options: nosniff` y `Referrer-Policy: strict-origin-when-cross-origin`, y `no-referrer` en `/reset-password` y `/confirm-email`, que llevan un token en la ruta. La CSP queda para decidir.
- **Tests existentes ajustados**: los dobles de login de Google (`usuarios/tests.py`, `filmai/tests_contrato.py`, `usuarios/test_seguridad_pendientes.py`) no traían `email_verified`, que Google siempre manda; se les agregó.
- **Archivos afectados**: `backend/usuarios/admin.py`, `backend/usuarios/views.py`, `backend/usuarios/serializers.py`, `backend/usuarios/throttles.py`, `backend/filmai/urls.py`, `backend/filmai/settings.py`, `backend/filmai/email_backends.py`, `backend/usuarios/test_seguridad_acceso.py` (nuevo), los tres tests de Google, `contracts/openapi.yaml`, `frontend/next.config.ts`.

---

## 26/10/2026 — Ajustes tras la segunda revisión con subagentes (#133 a #135)

- **Fecha**: 26/10/2026
- **Descripción**: una segunda ronda de tres revisores de solo lectura revisó los PRs abiertos, lo mergeado entre el 24 y el 26/10 y la seguridad que la primera no cubrió. Ajustes sin decisión, verificados antes de aplicarlos:
  - **Carrera en los bloqueos del admin y de la documentación** (#133): se consultaba el contador, se autenticaba y recién después se sumaba, así que una ráfaga en paralelo probaba más de 10 contraseñas. Ahora `_contar_intento` suma primero (`incr`, atómico) y un ingreso borra la clave. El 429 del admin lleva `Retry-After` y `no-store`. El test de reinicio no probaba el reinicio (pasaba sin `cache.delete`); se corrigió y hay uno que comprueba que el intento ya está contado mientras la vista autentica.
  - **Clave de React de las reseñas anónimas** (#134): usaba el nombre, y dos reseñas anónimas del mismo día chocaban. Ahora usa la posición y la fecha (la API no manda el id de reseñas ajenas a propósito).
  - **Calificar y agregar a una lista dentro de los topes de TMDB** (#135): materializan una producción nueva en el mismo pedido (~4 llamadas) y quedaban fuera del tope por pedido y del de la IP. `TopesTMDBMixin` pasó a `catalogo/presupuesto.py` y lo usan también `CalificacionesView` y `ListaItemsView`.
  - **`PUT /api/preferences/`** suma `EscrituraThrottle`. Un test recorre todas las vistas de escritura y exige el límite en cada una.
- **Verificado y documentado sin cambio**: con watchdog 6.0, `watchmedo auto-restart` relanza Celery cuando termina, así que un worker matado por memoria vuelve a arrancar dentro del contenedor (no es un ciclo de reinicios del contenedor; el techo igual protege a WSL). Queda como decisión pendiente, igual que el resto de lo que pide decisión (duración del access token, tope por IP frente al NAT, enumeración por tiempo en el reset, CSP y costo de Buscar).
- **Archivos afectados**: `backend/filmai/documentation.py`, `backend/filmai/test_seguridad_admin_login.py`, `frontend/components/features/title/ReviewsSection.tsx`, `backend/catalogo/presupuesto.py`, `backend/catalogo/views.py`, `backend/catalogo/reviews.py`, `backend/listas/views.py`, `backend/usuarios/cuenta.py`, `backend/catalogo/test_seguridad_topes_tmdb.py`, `backend/listas/test_topes.py`.

---

## 26/10/2026 — Topes de escritura: tasa común por usuario y techos de cantidad

- **Fecha**: 26/10/2026
- **Descripción**: hallazgo de la revisión de seguridad del 24/10/2026: las escrituras autenticadas no tenían límite. El usuario eligió, entre cuatro opciones (tasa común, tasa más techos, tasa por acción, nada), **tasa común más techos**:
  - `EscrituraThrottle` (`filmai/throttles.py`, scope `escritura`, 60 por minuto por usuario) en reseñas (alta, edición, borrados), listas (alta, renombre, borrado, ítems, reordenar) y perfil. Las lecturas no cuentan y el contador lo comparten todos esos endpoints. Pasado el límite: 429 (Too Many Requests) con `throttled`.
  - Techo de **100 listas personalizadas** por usuario (`list_limit_reached`, con `maxLists`) y de **1000 ítems por lista personalizada** (`list_items_limit_reached`, con `maxItems`), los dos 409 (Conflict) y en `listas/models.py`. El de ítems corta antes de materializar: no gasta llamadas a TMDB.
  - `PUT /api/lists/order/` rechaza más de 100 ids (`max_length`) y arma el conjunto de ids una sola vez (antes era cuadrático).
- **Decisiones**:
  - El techo de ítems **no** rige en las predeterminadas (Favoritos, Pendientes, Vistas): calificar agrega a «Vistas» (regla del 30/09/2026), y con un techo calificar dejaría de funcionar a los 1000 títulos. La tasa común igual frena el abuso.
  - **Ajustes tras PR-Agent (#135)**: con la lista llena, un título que ya está responde `list_item_duplicated` y no «lista llena» (un doble clic no es un intento de pasar el techo). Y el techo se vuelve a contar dentro de la transacción con la lista bloqueada (`select_for_update`): dos altas en paralelo con un lugar libre pasaban las dos.
  - **Pendiente de decidir**: PR-Agent señaló que la razón de la excepción vale solo para «Vistas»; Favoritos y Pendientes se pueden llenar sin techo (la tasa de 60/min es el único freno). Recomendación: techo también en esas dos.
  - El conteo de listas se hace antes de crear y no con un bloqueo: dos altas simultáneas pueden pasar el techo por una. Se aceptó.
  - Los dos códigos son nuevos: `contracts/error-codes.json`, `contracts/openapi.yaml` (enumeración de códigos), `traducciones/claves-extra.csv` y `messages/` (con sus `.d.json.ts`) se regeneraron.
- **Archivos afectados**: `backend/filmai/throttles.py` (nuevo), `backend/filmai/settings.py`, `backend/filmai/errores/catalogo.py`, `backend/listas/models.py`, `backend/listas/views.py`, `backend/listas/serializers.py`, `backend/catalogo/reviews.py`, `backend/usuarios/perfil.py`, `backend/listas/test_topes.py` (nuevo), `contracts/`, `traducciones/claves-extra.csv`, `frontend/messages/`, `openspec/specs/list-endpoints/spec.md`.

---

## 26/10/2026 — Las reseñas de cuentas dadas de baja se muestran anónimas

- **Fecha**: 26/10/2026
- **Descripción**: hallazgo de la revisión de seguridad del 24/10/2026. Las reseñas de una cuenta dada de baja seguían públicas con su nombre de usuario y su avatar. El usuario eligió **anonimizarlas** entre tres opciones (dejarlas, anonimizarlas, ocultarlas): el contenido queda y la identidad no. `ResenaComunidadSerializer` devuelve `nombre_usuario` y `avatar_id` en `null` y `autor_dado_de_baja: true` cuando `estado = baja`. La ficha muestra «Usuario dado de baja» (clave `title.reviews.deletedAuthor`) con el avatar genérico.
- **Decisiones**:
  - La identidad no sale de la API: no depende de que el frontend la oculte.
  - Se descartó ocultarlas porque se pierde contenido y cambian los conteos de golpe, y dejarlas porque choca con el derecho a la supresión de la Ley 25.326. CU-007 dice que los datos se conservan: se siguen conservando, solo cambia lo que se muestra.
  - El estado viaja en la fila del usuario, que ya se trae con `select_related`: no suma consultas (`filmai/test_consultas.py`).
  - `messages/*/common.d.json.ts` (los tipos que genera el plugin de next-intl) se regeneró con el mismo formato: sin correr `next dev` o `next build` quedaba sin la clave nueva y `tsc` fallaba.
- **Archivos afectados**: `backend/catalogo/serializers_reviews.py`, `backend/catalogo/tests_reviews.py`, `backend/filmai/tests_estado_cuenta.py` (el test de caracterización pasa a exigir el anonimato), `frontend/components/features/title/ReviewsSection.tsx`, `frontend/tests/reviews-section.test.tsx`, `traducciones/claves-extra.csv`, `frontend/messages/`, `openspec/specs/reviews-api/spec.md`.

---

## 26/10/2026 — Límite de intentos en `/admin/login/` y cómo se cumple el cifrado del correo

- **Fecha**: 26/10/2026
- **Descripción**: dos hallazgos de la revisión de seguridad del 24/10/2026, decididos por el usuario.
  - **`/admin/login/` sin límite**: Django no limita ese formulario. `con_limite_de_intentos` (`filmai/documentation.py`) envuelve `admin.site.login` con el mismo bloqueo que el login de la documentación: 10 fallos por IP bloquean 60 minutos con 429 (Too Many Requests). Un POST que vuelve a mostrar el formulario (200) cuenta como fallo; uno que redirige (302), como ingreso, y reinicia el contador. Se monta en `admin/login/` antes de `admin.site.urls`.
  - **IP de los dos bloqueos**: pasan a usar `BaseThrottle().get_ident()`, que respeta `NUM_PROXIES`, en lugar de `REMOTE_ADDR`. Detrás de un proxy, 10 fallos de cualquiera bloqueaban a todo el staff.
  - **Correo «cifrado»**: el CU-001 decía «El correo se almacena cifrado» y el código lo guarda en texto plano. Se decidió **no** cifrarlo como columna: el login, la unicidad y los límites de intentos lo buscan por valor, y cifrarlo exige una columna de hash aparte y manejo de claves. RNF #2 pide cifrado en reposo «a nivel de base de datos» y RNF #12 incluye los correos: los dos se cumplen con el cifrado en reposo de la base entera, que es una tarea del **despliegue** (en desarrollo no lo hay). Se corrigió el texto del CU-001.
- **Decisión del usuario**: el admin además no debería quedar expuesto en internet; restringirlo (proxy o lista de IPs) queda para el despliegue, y el límite es la defensa mientras tanto.
- **Archivos afectados**: `backend/filmai/documentation.py`, `backend/filmai/urls.py`, `backend/filmai/test_seguridad_admin_login.py` (nuevo), `docs/02_Especificación de Requerimientos.md`.

---

## 26/10/2026 — Rutas de acceso sin barra final esquivaban los límites de F2 (F11)

- **Fecha**: 26/10/2026
- **Descripción**: la revisión de seguridad con subagentes (24/10/2026) encontró que `POST /api/auth/login` y `POST /api/auth/password/reset`, **sin barra final**, caían en las vistas originales de dj-rest-auth (`login/?$` y `password/reset/?$`): sin `LoginCuentaThrottle` ni `LoginIPThrottle`, y el reset sin el límite de 5 por día ni la respuesta genérica. Se confirmó con `resolve()`: `/api/auth/login` → `dj_rest_auth.views.LoginView`, sin throttles. Era una regresión de F2: cualquiera podía probar contraseñas sin tope saltándose la barra. Se agregan las variantes sin barra de `login`, `password/reset` y `password/reset/confirm` hacia las vistas propias, igual que ya se había hecho con `password/change` y `token/refresh`.
- **Decisiones**: se registran las rutas a mano y no se deja de incluir `dj_rest_auth.urls`, para no tocar el resto de sus rutas (logout, user). Las tres rutas nuevas aparecen en `contracts/openapi.yaml` como las dos que ya existían sin barra. El test (`usuarios/test_seguridad_rutas_sin_barra.py`) resuelve cada ruta con y sin barra a la misma vista propia y comprueba el 429 (Too Many Requests) del login sin barra.
- **Archivos afectados**: `backend/filmai/urls.py`, `backend/usuarios/test_seguridad_rutas_sin_barra.py` (nuevo), `contracts/openapi.yaml`, `docs/auditoria-seguridad-resumen.md`.

---

## 26/10/2026 — Revisión con tres subagentes (seguridad, accesibilidad, calidad): pendientes

- **Fecha**: 26/10/2026
- **Descripción**: el 24/10/2026 se lanzaron tres revisiones de solo lectura sobre `main` con los PRs #129 a #131 integrados. Lo único que se arregló solo fue F11 (entrada de arriba). El resto queda **sin aplicar**, con evidencia de archivo y línea en los informes; esta lista es el índice.
- **Seguridad** (sin IDOR ni fugas de datos personales):
  - `/admin/login/` sin límite de intentos. **Decidir** si `/admin/` se expone públicamente; si sí, contador como el de la documentación (`filmai/documentation.py`).
  - La API key de TMDB va en la query string y `httpx` la escribe en el log INFO del worker (`catalogo/client.py:60`): subir `httpx` a WARNING en `LOGGING` o usar el token v4 en el encabezado.
  - Reset de contraseña sin límite por IP, y `{"email": 5}` da 500 (`usuarios/throttles.py:32`).
  - El bloqueo de login de la documentación usa `REMOTE_ADDR` e ignora `NUM_PROXIES` (`filmai/documentation.py:114`).
  - Al desplegar: `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, HSTS y `SECURE_PROXY_SSL_HEADER`.
  - Postgres publicado en todas las interfaces (`docker-compose.yml`, `"5432:5432"`): pasar a `127.0.0.1`, como Redis.
  - Escrituras autenticadas (reseñas, listas, perfil) sin límite de tasa; `ids` de reordenar listas sin `max_length` y con costo cuadrático. **Decidir** los topes.
  - **Decidir**: las reseñas de cuentas dadas de baja siguen públicas con su nombre de usuario; y el doc 02 dice que el correo «se almacena cifrado» y se guarda en texto plano.
  - `entrypoint.sh` arma código Python con `DJANGO_SUPERUSER_PASSWORD` dentro: una comilla simple lo rompe (lo controla quien opera el servidor).
- **Accesibilidad** (alta): la barra inferior y el botón flotante del celular tapan el foco (WCAG 2.4.11, falta `scroll-padding`); Escape en Buscar navega fuera de la página al cerrar el menú de cuenta (`SearchView.tsx:119`). **Media**: regiones `role="status"` que se montan con el texto ya puesto (no se anuncian), foco que se pierde al desaparecer el control, dos diálogos que no son `<dialog>` (hoja «Agregar a lista», confirmación de cerrar sesión), borde de campos con contraste 1,2:1, registro con botón deshabilitado y sin `required`, nombre accesible que no contiene el texto visible, notas sin «de 10», Inicio sin h1 si el hero no tiene imagen.
- **Calidad**: **alta**, la sync diaria se cae entera si falla un listado de descubrimiento (`catalogo/tasks.py:254`); **media**, campos de TMDB sin recortar a los `max_length` del modelo (500 posible), backfill de embeddings que no avanza porque `.update()` no toca `auto_now`, relleno de traducciones que se traba con las mismas filas, y reseñas por fecha que pueden repetir un ítem entre páginas. Siete divergencias entre docs 02/03 y el código (por ejemplo el correo «cifrado»).
- **Decisión de proceso**: no se arregla nada de esto sin acordarlo; los de severidad alta y los de bajo riesgo (sync, recorte de campos, `auto_now`, h1, `scroll-padding`) son buenos candidatos para el próximo tramo.
- **Archivos afectados**: `docs/decisiones.md`.

---

## 24/10/2026 — Limpieza de `frontend/public/`

- **Fecha**: 24/10/2026
- **Descripción**: se borraron seis archivos que nadie referencia, uno de los pendientes de rendimiento del 22/10/2026: `avatars/Gemini_Generated_Image_p6bcr2p6bcr2p6bc.png` (6,9 MB, la imagen de la que se recortaron los avatares), `collage-posters/Opcion 2.jpg` y `Opcion 3.jpg` (alternativas del collage que no se eligieron) y `file.svg`, `globe.svg` y `window.svg` (de la plantilla de `create-next-app`). Son unos 7,3 MB menos en el repositorio y en la imagen del frontend.
- **Cómo se verificó que no se usan**: `git grep` de cada nombre en todo el repositorio, también con los espacios codificados como `%20`; solo aparecen en esta entrada y en la del 22/10. Los avatares del selector salen de `backend/usuarios/avatares.py`, que arma las rutas solo con `avatars/recortados/`. La pantalla de acceso (`AccessShell.tsx`) y los tests de Playwright usan solo `Opcion 1.jpg`.
- **Archivos afectados**: los seis de `frontend/public/`, `docs/decisiones.md` y `graphify-out/`.

---

## 24/10/2026 — El Hero del Inicio llega en el HTML del servidor

- **Fecha**: 24/10/2026
- **Descripción**: uno de los pendientes de rendimiento del 22/10/2026. Antes, el HTML del Inicio no traía el Hero: el navegador bajaba el JavaScript, recién ahí pedía tendencias y recién ahí pedía la imagen de fondo, que es el LCP. Ahora `app/home/page.tsx` (Server Component) pide al backend lo que el Hero necesita (tendencias de «Todo» y, con Películas o Series, las de ese tipo, más las dos listas de géneros), en el idioma de la página, y se lo pasa a `HomeView` como `inicial`. `useCatalog` acepta esa respuesta inicial: con ella no repite el pedido y el dato está desde el primer render.
- **Cómo llega el servidor al backend**: dentro de Docker, `localhost` es el propio contenedor del frontend, así que el servidor usa `API_URL_INTERNA` (`http://backend:8000`, en `docker-compose.yml`). Sin esa variable no se pide nada en el servidor y todo sigue como antes. Así corren el CI y los tests de Playwright, que simulan la API en el navegador.
- **Decisiones**:
  - Nunca rompe la página: un error o una espera de más de 500 ms devuelve `null` y el navegador pide el dato por su cuenta (`lib/catalogo-servidor.ts`). La espera es corta porque el HTML entero espera ese pedido (lo señaló PR-Agent en #130). Pasa solo cuando Next no tiene ninguna copia, por ejemplo al arrancar el servidor: con una copia vencida, la caché de datos de Next sirve la vieja y la renueva por detrás. Mejora posible: hacer *streaming* del Hero (pasarle a `HomeView` la promesa dentro del `Suspense`), así el resto de la página no espera nunca.
  - Las respuestas quedan 5 minutos en la caché de datos de Next (`revalidate`), igual que en el navegador: el Inicio no espera al backend en cada visita.
  - Los datos del servidor se usan solo si son del idioma que se está mirando: el idioma puede cambiar sin recargar.
  - Servidor y navegador piden las mismas rutas (`rutasDelHero` en `lib/home.ts`), que además son la clave de la caché de `useCatalog`.
- **Verificación**: con Docker, el HTML de `/home` trae el `<h1>` con el título de tendencias, el `<link rel="preload" as="image">` del backdrop y el título en español si la página está en español. Una segunda visita respondió en 0,38 s en modo desarrollo. No se midió el LCP con un build de producción.
- **Archivos afectados**: `frontend/app/home/page.tsx`, `frontend/components/features/HomeView.tsx`, `frontend/lib/use-catalog.ts`, `frontend/lib/home.ts`, `frontend/lib/catalogo-servidor.ts` (nuevo), `frontend/tests/catalogo-servidor.test.ts` (nuevo), `frontend/tests/home-page.test.tsx`, `docker-compose.yml`, `openspec/specs/home-ui/spec.md`.

---

## 24/10/2026 — Auditoría F6: `trending` validado y topes de llamadas a TMDB

- **Fecha**: 24/10/2026
- **Descripción**: se corrigió el hallazgo F6 (severidad baja) y el pendiente de F2/F3 sobre el tope de llamadas a TMDB por pedido. Tres cambios:
  - **`trending` con listas cerradas**: `media_type` (`all`, `movie`, `tv`) y `time_window` (`day`, `week`) iban sin validar al path de TMDB (`/trending/{media_type}/{time_window}`), así que `media_type=../movie/550` llevaba el pedido a otro endpoint. Ahora un valor fuera de la lista responde 400 (Bad Request) con `invalid_choice` sin llamar a TMDB. `person` existe en TMDB, pero FilmAI no muestra personas. `_opcion` pasó a nivel de módulo para que la usen Buscar y tendencias.
  - **Tope por pedido** (`catalogo/presupuesto.py`): cada vista abre un contador (`contar_llamadas`, en una `ContextVar`) y el cliente llama a `registrar_llamada()` antes de cada pedido HTTP, reintentos incluidos. Pasadas 30 (`MAX_LLAMADAS_POR_PEDIDO`) lanza `TMDBPresupuestoAgotado`, que responde 503 (Service Unavailable) con el código existente `upstream_unavailable`. Antes, Buscar con texto en «Todo» podía encadenar 20 llamadas con 3 reintentos cada una: hasta 80.
  - **Límite por IP que cuenta llamadas** (`TMDB_LLAMADAS_POR_IP_POR_MINUTO`, 300): cada llamada suma, en el momento, en un contador atómico por IP y por minuto de reloj (`cache.incr`, que en Redis es `INCR`; si la clave no existe o Redis la desalojó, se siembra con `cache.add`). La llamada que pasa el límite corta con 429 (Too Many Requests), `throttled` y `Retry-After` (los segundos que faltan para que termine el minuto). Lo que sale de la caché de Redis no llama al cliente y no cuesta nada. El límite de 60 pedidos por minuto (`catalogo`) sigue igual.
- **Decisiones** (elegido por el usuario el 24/10/2026: los dos topes, no uno solo):
  - El tope por pedido sale del máximo legítimo: Buscar con texto en «Todo» y en español son 20 llamadas (10 páginas y su respaldo en inglés). 30 deja lugar a algún reintento.
  - `TMDBPresupuestoAgotado` hereda de `TMDBError`: la caché lo trata como «TMDB no disponible» y sirve la copia de respaldo si la tiene, sin otra llamada.
  - Los hilos de `ThreadPoolExecutor` no heredan las `ContextVar`. Buscar envuelve sus funciones con `con_contexto`, que corre cada una en una copia del contexto del pedido (todas comparten el mismo contador). Sin eso, las llamadas de Buscar no se contaban.
  - La primera versión cobraba el pedido al terminar, con un throttle de DRF. PR-Agent señaló en #129 que así pedidos en paralelo pasaban todos la revisión de entrada con el contador en cero: 60 pedidos simultáneos con textos nuevos sumaban unas 1200 llamadas. Contar cada llamada en el momento, de forma atómica, lo cierra; hay un test con 10 pedidos en paralelo. La ventana es fija (por minuto de reloj): en el borde entre dos minutos pueden juntarse hasta 600, el compromiso de un contador simple.
  - Fuera de un pedido HTTP no hay tope: Celery, la sync diaria y el seed hacen miles de llamadas y no deben cortarse.
  - No cambian `contracts/` ni `traducciones/`: los dos códigos ya existían y el frontend los traduce.
- **Archivos afectados**: `backend/catalogo/presupuesto.py` (nuevo), `backend/catalogo/client.py`, `backend/catalogo/services/browse.py`, `backend/catalogo/views.py`, `backend/catalogo/exceptions.py`, `backend/filmai/exceptions.py`, `backend/filmai/settings.py`, `backend/catalogo/test_seguridad_topes_tmdb.py` (nuevo), `openspec/specs/tmdb-endpoints/spec.md`, `docs/auditoria-seguridad-resumen.md`.

---

## 24/10/2026 — Auditoría F7: `id_tmdb` inexistente o fuera de rango

- **Fecha**: 24/10/2026
- **Descripción**: se corrigió el hallazgo F7 (severidad baja). El alta de reseñas tenía dos fallas, y el alta de ítems de listas las mismas, porque las dos pasan por `materializar()` con el mismo payload:
  - **Id que TMDB no conoce**: la respuesta ya era 404 (Not Found) con `upstream_not_found`, pero `materializar()` crea la fila vacía antes de pedirle el detalle a TMDB, así que cada id probado dejaba una `ProduccionAudiovisual` sin título. Ahora `_obtener_o_crear` devuelve `(fila, creada)` y, si TMDB responde 404, `_descartar_cascaron` borra la fila que creó esa misma llamada, o el cascarón sin título que haya dejado un fallo transitorio anterior (sugerencia de PR-Agent en #128).
  - **Id fuera de rango**: `id_tmdb` es un `integer` de Postgres (máximo 2147483647). Un id mayor pasaba la validación y el INSERT respondía 500 (Internal Server Error). La constante `ID_TMDB_MAXIMO` (`catalogo/models.py`) pone `max_value` en los serializers de reseñas y listas (alta y lecturas) y en las vistas del catálogo que reciben `id_tmdb`; ahora responde 400 (Bad Request) con `max_value` y `maxValue`, sin llamar a TMDB.
- **Decisiones**:
  - Nunca se borra una fila con datos: puede tener calificaciones y listas colgando (CASCADE), por ejemplo si TMDB da de baja un título que la sync refresca. Un cascarón sin título y sin enriquecer no puede tenerlas, porque calificaciones e ítems se crean solo después de enriquecer. El borrado filtra además por `fecha_enriquecimiento IS NULL`, por si otro pedido la enriqueció en paralelo, y por `titulo = ''` como defensa explícita (sugerencia de PR-Agent en #128).
  - Ante un fallo transitorio (TMDB caído) la fila nueva se conserva, como hasta ahora: el id puede existir y la próxima visita a la ficha la vuelve a encolar.
  - El borrado abre una carrera: el pedido que perdió el INSERT busca la fila ganadora y, si el otro ya la descartó, no la encuentra. Antes eso era siempre un error ajeno a la carrera y se propagaba como 500 (Internal Server Error); ahora hay **un solo** reintento del alta. Dos choques seguidos sin fila se siguen propagando: un reintento sin límite escondería un error real (sugerencia de PR-Agent en #128, acotada a un reintento).
  - El 404 se mantiene en lugar de un 400 sobre el campo: el código `upstream_not_found` ya existe y el frontend lo traduce, así que no cambian `contracts/` ni `traducciones/`.
  - Las vistas del catálogo también validan el máximo aunque no escriben: un id más grande da 404 seguro en TMDB y así no se gasta la llamada. `_page` pasó a usar el mismo parámetro `maximo` de `_int_param`, con la misma respuesta de antes.
- **Archivos afectados**: `backend/catalogo/models.py`, `backend/catalogo/services/materialization.py`, `backend/catalogo/serializers_reviews.py`, `backend/catalogo/views.py`, `backend/listas/serializers.py`, `backend/catalogo/test_seguridad_id_tmdb.py` (nuevo), `backend/listas/test_seguridad_id_tmdb.py` (nuevo), `openspec/specs/reviews-api/spec.md`, `openspec/specs/catalog-materialization/spec.md`, `docs/auditoria-seguridad-resumen.md`.

---

## 24/10/2026 — Docker de desarrollo: techo de memoria por servicio y sin reinicio automático

- **Fecha**: 24/10/2026
- **Descripción**: WSL se colgó tres veces seguidas en la máquina de Gonza (7,7 GB de RAM para WSL y 2 GB de swap). El registro del kernel del último cuelgue muestra unos 7,2 GB de memoria de procesos y el swap lleno, sin que el kernel matara ningún proceso: el sistema se queda trabado moviendo páginas entre la RAM y el swap. Pasó con los seis contenedores arriba, VS Code y corridas de tests. Tres cambios en `docker-compose.yml`:
  - **Celery con `--concurrency=2` y `--max-memory-per-child=300000`**. Sin la primera opción, Celery arranca un proceso hijo por núcleo, y en una máquina de 12 hilos eran 13 procesos con Django entero cargado. Desde el 16/10/2026 (#109) esos procesos trabajan de verdad (cada listado encola lo que muestra), así que además crecen. La segunda (en KB) recicla un hijo que termina una tarea por encima de 300 MB antes de que se acerque al techo del contenedor (sugerencia de PR-Agent en #127).
  - **`mem_limit` y `memswap_limit` por servicio** (backend 1536m, frontend 2g, celery-worker 1g, celery-beat 256m, db 512m, redis 512m). `mem_limit` es el techo de la cgroup del contenedor: si lo supera, el kernel mata el proceso más grande de ese contenedor y no se traba todo WSL. Si era el principal, el contenedor queda `Exited (137)`; si era un hijo (Celery, Postgres), el padre lo reemplaza y el fallo solo se ve en los logs. `memswap_limit` igual al techo impide que el contenedor use swap; sin él, Docker le permite usar tanto swap como RAM, y llenar el swap es justo lo que cuelga WSL.
  - **Sin `restart: unless-stopped`**. Con esa política, iniciar Docker levantaba los seis servicios a la vez, y un contenedor que terminara por memoria se reiniciaría en ciclo. Ahora nada arranca solo, y uno caído queda detenido en `docker compose ps` hasta levantarlo a mano.
- **Decisiones**:
  - Redis lleva 512m y no 256m: ya tiene `--maxmemory 256mb` (F3) y ocupa algo más que sus datos; además, al guardar el snapshot en disco hace un fork. Con el techo igual a `maxmemory`, el contenedor moriría antes de que Redis desaloje claves.
  - El frontend también lleva techo: `next dev --turbopack` es el servicio que más crece.
  - Los valores son un punto de partida para desarrollo; se ajustan midiendo con `docker stats`.
  - Para los tests no hacen falta el frontend ni Celery (las tareas están reemplazadas por mocks y los tests solo usan Postgres y Redis): `docker compose run --rm backend python manage.py test` levanta solo `db` y `redis`, corre en un contenedor de un solo uso y lo borra al terminar.
- **Para quien ya tenga los contenedores creados**: la política `restart` queda guardada en cada contenedor, así que hay que recrearlos una vez (`docker compose down` y después `docker compose up -d`). Los datos viven en los volúmenes y no se pierden.
- **Archivos afectados**: `docker-compose.yml`, `docs/decisiones.md`.

---

## 22/10/2026 — Pendientes de seguridad y rendimiento: quién los toma

- **Fecha**: 22/10/2026
- **Descripción**: al integrar en `main` y `develop` la auditoría de seguridad (`security/audit`) y las mejoras de rendimiento (`polish-performance`), quedaron abiertos estos puntos. Ninguno se aplicó en esa integración.
- **Para Gonza**:
  - **F6** (seguridad, catálogo): validar los parámetros de `trending`, que hoy pueden llevar el pedido a otros endpoints de TMDB, y poner un tope a las llamadas a TMDB por pedido (quedó fuera de F2/F3).
  - **F7** (seguridad, catálogo): el alta de reseñas acepta `id_tmdb` inexistentes o enormes y deja filas vacías o responde 500 (Internal Server Error).
  - **F10** (seguridad, catálogo): el autor puede revertir la moderación de su reseña. Antes del código, decidir en equipo cómo tiene que funcionar.
  - **Hero del Inicio desde el servidor** (rendimiento): hoy el LCP del Inicio espera a que el navegador pida `trending`; renderizar el hero en el servidor lo adelantaría.
  - **Borrar lo que no se usa en `frontend/public/`** (rendimiento): `avatars/Gemini_Generated_Image_p6bcr2p6bcr2p6bc.png` (6,9 MB, la imagen de la que se recortaron los avatares), `collage-posters/Opcion 2.jpg` y `Opcion 3.jpg` (el acceso usa `Opcion 1.jpg`), y `file.svg`, `globe.svg` y `window.svg` de la plantilla de Next. Confirmar con una búsqueda que nadie los referencia antes de borrarlos.
- **Al desplegar**: volver a evaluar la mejora de **F4** (elegir la contraseña al confirmar el correo, descrita en la entrada de F4 del 20/10/2026), Sentry y `NUM_PROXIES` según el proxy real.

## 22/10/2026 — Fluidez: medición en celular con CPU 4x y tres arreglos

- **Fecha**: 22/10/2026
- **Cómo se midió**: las mediciones de la entrada siguiente (renders, bytes, LCP) no dicen si la app se siente fluida. Se repitió la comparación entre dos builds de producción (antes de la entrada siguiente y después, puertos 3100 y 3101) con un script de Playwright: celular emulado (390×844, densidad 3, táctil), CPU 4x más lenta por CDP y toques reales (eventos confiables, que son los que cuenta la Event Timing API). El recorrido es carga del Inicio, scroll de punta a punta, chip «Películas», Listas, Buscar, escribir «dune», Inicio, una ficha (con scroll) y el menú de cuenta. Mide CLS, tareas largas (más de 50 ms), la interacción más lenta (aproxima el INP), cuadros de más de 50 ms durante el scroll y cuánto tarda en aparecer cada pantalla. Cinco rondas por build, alternando el orden; abajo, medianas.
- **Resultados finales** (antes → después): CLS del Inicio 0,07–0,14 → 0–0,01; CLS de la ficha 0,13 en dos de cinco rondas → 0,005 o menos; primera entrada a Listas 626 → 550 ms; scroll sin cuadros de más de 50 ms en las dos versiones (17 ms por cuadro); interacción más lenta 144 → 152–160 ms (por debajo de los 200 ms que la Web Vitals llama «bueno»); el resto de las pantallas, igual (±20 ms).
- **Arreglos que salieron de la medición**:
  1. **Listas tardaba el doble** (597 → 1124 ms) con el lazy loading de la entrada siguiente. Dos causas: el chunk de dnd-kit se pedía recién después del JS de la ruta, y `next/dynamic` suspende aunque el chunk ya esté, y React 19 retiene hasta ~300 ms el reemplazo del esqueleto. Ahora `ListsGridPreload` (montado en el layout, solo con sesión) baja el chunk con `requestIdleCallback` y lo deja en memoria; `ListsView` ya no usa `next/dynamic`: si la grilla está la dibuja directo, y si no la pide al montarse y muestra el esqueleto (si falla, el mismo «Reintentar» de las listas). `/lists` queda en 10,3 kB propios y 200 kB de First Load JS.
  2. **Salto de layout en el Inicio**: con sesión, la fila «Recomendado para vos» aparecía recién cuando llegaba la cuenta y empujaba hacia abajo las filas ya dibujadas. `AccountProvider` expone `sesionPosible` (si llegaron cookies de sesión, lo decide el servidor) y el Inicio reserva la fila en esqueleto mientras la cuenta carga. `MediaRow` reserva además el renglón de la descripción mientras carga, porque la de Recomendado depende de la respuesta.
  3. **El avatar del usuario no se veía en el build de producción** (también antes de estos cambios): el backend escapaba los paréntesis del archivo (`avatar%20%2826%29.png`), `next start` no encuentra el archivo público con ese nombre y el optimizador de imágenes respondía 400 (Bad Request). `usuarios/avatares.py` deja los paréntesis sin escapar (`avatar%20(26).png`, la forma que ya usaban los fixtures del e2e).
- **Costo aceptado**: los `srcset` de `tmdbLoader` suman trabajo en el hilo principal cada vez que cambian las filas. Con tamaños en px, Next arma 16 candidatos por imagen, y el perfil de CPU del chip «Películas» muestra `setAttribute` 91 → 179 ms en tres rondas. Es la diferencia de 144 → 152–160 ms en la interacción más lenta. Se acepta a cambio de bajar 2 a 3 veces menos bytes de imágenes; recortar `images.imageSizes` en `next.config.ts` la achicaría, pero cambia los anchos de todas las imágenes de la app.
- **Pendiente detectado (también antes)**: ir a Buscar a veces tarda ~250 ms y a veces ~900 ms. En el caso lento, el buscador espera a que lleguen `browse` y los pósters antes de verse. No depende de estos cambios y queda para revisar aparte.
- **Archivos**: `frontend/components/features/lists/{ListsGridPreload,ListsView}.tsx`, `frontend/app/layout.tsx`, `frontend/components/AccountProvider.tsx`, `frontend/components/features/{HomeView,MediaRow}.tsx`, `backend/usuarios/avatares.py`; tests: `frontend/tests/lists-grid-preload.test.tsx` (nuevo), `frontend/tests/home-page.test.tsx` (fila reservada con y sin cookies; falla con el código anterior) y `backend/usuarios/test_perfil.py` (ruta del avatar).

## 22/10/2026 — Rendimiento: renders, lazy loading, caché HTTP, queries e imágenes

- **Fecha**: 22/10/2026
- **Cómo se midió**: build de producción (`next build` + `next start`) servido en el puerto 3100 contra el backend del `docker compose` y la base de desarrollo, con el MCP de Chrome DevTools (trace de carga, requests, un contador de commits de React inyectado en la página) y un script de Django que cuenta queries y tiempos por endpoint con `CaptureQueriesContext`. Cada número de abajo es antes → después, en las mismas condiciones.
- **1. Renders innecesarios** (`AccountProvider`): el efecto que carga la cuenta dependía de `pathname`, así que **cada navegación** volvía a pedir perfil, avatares y preferencias, pasaba `cargando` a `true` y de nuevo a `false`, y el valor del contexto era un objeto nuevo en cada render: todo lo que usa `useAccount()` se volvía a renderizar al cambiar de ruta. Ahora el perfil se pide una vez por sesión (`perfilCargado`; se vuelve a pedir después de `limpiar()`, de un error o desde el login), `recargar` no cambia con la ruta (la lee de un ref) y el valor del contexto va en `useMemo`. Carga de `/home`: 12 → 9 commits de React y 1566 → 825 renders de componentes. Tres navegaciones (`/lists`, `/search`, `/home`): 25 → 19 commits y 4310 → 3470 renders.
- **2. Bundle y lazy loading**: dnd-kit (el arrastre de «Lists») se cargaba con la página. La grilla ordenable pasó a `SortableListsGrid.tsx`, en un chunk aparte; `ListsView` lo pide al montarse, en paralelo con `/api/lists/`, y mientras tanto muestra el mismo esqueleto (`ListsGridSkeleton.tsx`). (Primero se cargó con `next/dynamic`; la medición de fluidez de la entrada anterior lo cambió por una precarga sin Suspense.) `/lists`: 28,1 → 11,4 kB propios y 216 → 201 kB de First Load JS. El JS compartido por todas las rutas subió 1,3 kB comprimido (por cómo Turbopack reparte los chunks; se acepta). Se evaluó cargar en diferido los diálogos (calificar, confirmar, nombre de lista, avatar), pero pesan pocos kB y la carga diferida sumaría espera al primer clic; quedaron como estaban.
- **3. Requests y caché**:
  - Navegar ya no repite los pedidos de la cuenta: en las tres navegaciones de arriba, 14 → 4 requests a la API.
  - El catálogo público (`CatalogoBaseView`: sin autenticación, solo varía con `Accept-Language`) responde los 200 (OK) con `Cache-Control: public, max-age=300` y `Vary: Accept-Language`; los errores no se cachean. Además se comprime con `gzip_page` solo en esas vistas, no con `GZipMiddleware` global, para no exponer a BREACH respuestas con cookies o CSRF. `trending`: 13 007 → 5 378 bytes.
  - Los enlaces a `/chat` (el chatbot todavía no existe) van con `prefetch={false}`: cada página pedía de fondo ese 404 (Not Found).
- **4. Queries lentas y N+1**: no se encontraron. Con 17 ítems en una lista y las reseñas de la comunidad, cada endpoint hace de 0 a 4 queries de 1 a 3 ms; lo lento son los pedidos a TMDB en frío (200 a 1100 ms), que ya cachea Redis (4 ms en caliente). Hay dos repeticiones constantes, que no son N+1: el `COUNT` de «Mis reseñas» (total sin filtros y total filtrado) y la consulta de géneros de «Recomendado», una por tipo. Ahorrarían 1 ms cada una y se dejaron así. Para que no aparezca un N+1 más adelante, `filmai/test_consultas.py` exige la misma cantidad de queries con 1 y con 8 filas en listas, ítems de una lista, mis reseñas y reseñas de la comunidad.
- **5. Imágenes, fuentes y scripts**:
  - `tmdbLoader` (`lib/catalog.ts`): las imágenes de TMDB pasan de `unoptimized` a un `loader` que arma el `srcset` con los anchos que sirve TMDB. El ancho de la URL es el tope, así que nunca baja más que antes, y acepta un 10 % menos para no saltar de 780 a 1280. En la ficha, en un celular con densidad 2: backdrop 185 → 64 kB y póster 58 → 25 kB. En las tarjetas de 132 a 176 px el ancho no cambia (w342).
  - Los avatares de las reseñas de la comunidad dejaron de ser `unoptimized`: cada uno bajaba el PNG de 286 px (106 kB) para mostrarlo a 40 px; ahora pasa por el optimizador de Next (2,6 kB en WebP).
  - Las imágenes LCP (hero del Inicio, backdrop de la ficha, collage de acceso) llevan `fetchPriority="high"`: en Next 15.5 `priority` solo precarga y quita el lazy, y el navegador pedía el hero con prioridad baja. LCP del Inicio en el trace: 599 → 483 ms.
  - Fuentes: ya van con `next/font` (autoalojadas y precargadas, Big Shoulders con un solo peso). Scripts de terceros: solo el SDK de Google, que ya se carga recién en las pantallas con el botón. No se cambió nada.
- **Fuera de alcance**: Sentry (no hay producción todavía; queda para el despliegue). Pendientes posibles: renderizar el hero del Inicio en el servidor (el LCP espera a que el cliente pida `trending`) y borrar de `public/` los archivos que no usa nadie (un PNG de 6,9 MB, dos collages y tres SVG de la plantilla de Next).
- **Archivos**: `frontend/components/AccountProvider.tsx`, `frontend/components/features/lists/{ListsView,SortableListsGrid,ListsGridSkeleton}.tsx`, `frontend/lib/catalog.ts`, `frontend/lib/routes.ts`, `frontend/components/{Footer,features/HomeView,features/HomeHero,features/MediaCard,access/AccessShell}.tsx`, `frontend/components/features/{lists/ListCard,reviews/MyReviewItem,title/TitleView,title/ReviewsSection}.tsx`, `backend/catalogo/views.py`; tests: `backend/filmai/test_consultas.py` y `backend/catalogo/test_cache_navegador.py` (nuevos), `frontend/tests/{session-account,catalog,lists-view}.test.*`, `frontend/e2e/listas.spec.ts` (espera a la grilla, que ahora llega aparte).

## 20/10/2026 — JWT con 10 segundos de tolerancia de reloj (test intermitente)

- **Fecha**: 20/10/2026
- **Descripción**: la suite completa fallaba al azar (3 de 6 corridas) en `usuarios.test_perfil` y `usuarios.test_cuenta` con 401 (Unauthorized) `invalid_token`. Se reprodujo con carga de CPU y la causa real fue `ImmatureSignatureError ("The token is not yet valid (iat)")`: el reloj del sistema (WSL2) retrocedió unos 2 segundos, así que un token recién emitido quedaba "en el futuro" y PyJWT lo rechazaba, porque simplejwt no tenía tolerancia (`LEEWAY` 0). Pasa lo mismo en producción si el reloj del servidor se corrige hacia atrás o si varias instancias no están sincronizadas.
- **Cambio**: `SIMPLE_JWT["LEEWAY"] = timedelta(seconds=10)`. Diez segundos sobre un access de 8 horas no debilitan el vencimiento; la revocación (claim de hash de contraseña y blacklist) no depende del reloj. Con el cambio, 12 corridas bajo carga sin fallos (antes 3 de 10).
- **Archivos**: `backend/filmai/settings.py`, `backend/usuarios/test_reloj_jwt.py` (nuevo: token emitido 3 s adelantado se acepta; 60 s adelantado se rechaza con `invalid_token`).

## 20/10/2026 — Auditoría F4: las cuentas pendientes vencen y dejan de reservar el correo

- **Fecha**: 20/10/2026
- **Corrección tras la revisión de PR-Agent**: el primer commit cambió solo `claves.csv` y los correos reales no se enteraron (las plantillas son la fuente); se corrigió. También se alineó el corte con el reloj que usa `fecha_registro` (`date.today()`) y se agregaron los tests del alta con Google y del reenvío. En una segunda pasada PR-Agent planteó que liberar la pendiente podía borrar la cuenta que allauth ya había resuelto para el login con Google (500 (Internal Server Error) al guardar); se comprobó con un test que recorre el alta completa con allauth real: el login de Google trae un usuario nuevo sin guardar (la vinculación por correo de allauth está desactivada), así que no hay referencia a la fila borrada y la cuenta se crea con normalidad. No hace falta código adicional; el test queda como regresión.
- **Descripción**: `POST /api/auth/registration/` crea la cuenta `PENDIENTE` sin probar que quien registra sea el titular del correo, y la pendiente no vencía nunca. Quien registraba el correo de otra persona lo bloqueaba para siempre (el registro respondía `email_already_used` y la recuperación de contraseña no enviaba nada, porque solo atiende cuentas activas). Si la víctima abría el enlace de confirmación que no pidió, la cuenta pasaba a `ACTIVA` con la contraseña del atacante. Cambios:
  - **Vencimiento (1c)**: una pendiente deja de reservar su correo y su nombre de usuario pasado el plazo del enlace (`ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS`). Dos mecanismos que comparten `usuarios/pendientes.py`: (1) al registrar (y al dar de alta con Google) se borra la pendiente vencida que ocupa ese correo o nombre, así el plazo es exacto; (2) la tarea diaria `usuarios.limpiar_pendientes_vencidas` (Celery Beat, 5 AM) borra todas las vencidas, para no conservar datos personales de quien nunca confirmó. El chequeo `username-available` ignora las vencidas sin borrar nada (es un GET).
  - **Registro sobre una pendiente vigente (2a)**: se sigue rechazando con `email_already_used`. Reemplazarla permitiría a un atacante quitarle a la víctima su registro legítimo y dejar su propia contraseña en la cuenta que ella terminaría confirmando.
  - **Aviso en el correo de registro (3d)**: el correo `confirmacion_registro` (texto y HTML, español e inglés) ahora pide no abrir el enlace ni hacer clic en el botón si no se creó la cuenta, y avisa que la cuenta sin confirmar se elimina sola. Se aplicó solo a ese correo, que es el que recibe quien no se registró; el de `confirmacion_correo` (cambio de correo de una cuenta existente) no cambia. La fuente de los textos son las plantillas de `backend/templates/correos/`; `traducciones/claves.csv` las documenta y se mantiene alineado.
- **Decisiones**:
  - `Usuario` solo guarda el día de registro (`fecha_registro`, sin hora). Para no agregar una migración, el corte es por días enteros: se libera la cuenta registrada antes de `hoy - plazo`. Nunca vence antes que el primer enlace; en el peor caso reserva casi 48 horas. El plazo cuenta desde el registro y **no se renueva al reenviar el enlace**: si se renovara, quien registra un correo ajeno podría reservarlo para siempre pidiendo reenvíos.
  - Un atacante puede volver a registrar el correo cada vez que vence. Lo frenan los límites de F2 (5 registros por hora por correo, 10 por hora por IP), que lo encarecen sin eliminarlo.
  - Consecuencia de lo anterior: un enlace reenviado cerca del corte puede vencer antes que su plazo propio, y uno reenviado cuando la cuenta ya se borró deja de ser válido (`link_invalid`); la persona debe registrarse de nuevo. El texto "Reenviar enlace" de la pantalla de enlace vencido solo sirve mientras la cuenta existe. Hay tests de que reenviar no cambia la fecha y de que, pasado el corte, no se envía nada.
  - **Riesgo residual aceptado**: durante esa ventana de hasta 48 horas, si la víctima confirma un correo que no pidió, la cuenta queda con la contraseña del atacante. La mitigación es el aviso del correo (3d).
- **Recomendación para el despliegue (3c)**: el cierre completo de ese riesgo es que la contraseña se elija al confirmar el correo y no en el formulario de registro. Así, toda contraseña de una cuenta nueva la define alguien con acceso al buzón, sin excepciones por navegador. Implicaría: quitar `password1` y `password2` de `RegisterSerializer` y del formulario; que `ConfirmarCorreoView` reciba la clave y la contraseña nueva, y las fije y active la cuenta en una sola transacción; una pantalla "Elige tu contraseña" en `confirm-email/[key]` (reutilizando la de `reset-password`); y actualizar `contracts/`, los golden files `registro_password1_*`, los tests y e2e de registro, las traducciones y CU-001, CU-002 y el documento 04. No se hizo ahora por el alcance del TP y porque cambia el contrato del registro (toca el trabajo de Gonza); conviene hacerlo antes de desplegar. Se descartó vincular la confirmación al navegador del registro: obliga a elegir contraseña de nuevo a quien registra en un navegador y confirma en otro (PC y celular, o el visor de la app de Gmail), un caso frecuente.
- **Archivos afectados**: `backend/usuarios/pendientes.py` (nuevo), `backend/usuarios/tasks.py` (nuevo), `backend/usuarios/serializers.py`, `backend/usuarios/views.py`, `backend/filmai/settings.py` (tarea en Celery Beat), `backend/usuarios/test_seguridad_pendientes.py` (nuevo), `backend/templates/correos/confirmacion_registro/` (4 plantillas), sus referencias en `backend/filmai/tests_golden/correos/`, `traducciones/claves.csv` y los correos de ejemplo de `traducciones/revision-correos/`, `docs/auditoria-seguridad-resumen.md`.

---

## 20/10/2026 — Auditoría F5: límites del admin para staff con permisos parciales

- **Fecha**: 20/10/2026
- **Descripción**: `UsuarioAdmin` heredaba de `UserAdmin` de Django, que trata el permiso `change_usuario` como administración total: un staff que solo tuviera ese permiso podía marcarse `is_superuser`, darse permisos o grupos, editar a un superusuario y fijar su contraseña. Ahora, para quien no es superusuario: (1) `get_queryset` oculta a los superusuarios; (2) `get_readonly_fields` deja `is_superuser`, `is_staff`, `groups` y `user_permissions` en solo lectura; (3) `has_change_permission` y `has_delete_permission` aplican la misma regla por objeto: niegan editar o borrar a un superusuario o a otro staff (la vista de contraseña de Django usa el permiso de cambio). Puede editar y borrar a usuarios comunes, y editarse a sí mismo. El superusuario no cambia. **Códigos exactos**: para un superusuario el objeto ni aparece en el queryset, así que la ficha redirige al índice del admin (302 (Found)) y la vista de contraseña responde 404 (Not Found); para otro staff sí aparece, la ficha se abre en modo lectura (200 (OK), gracias a `view_usuario`) y guardar, cambiar la contraseña o borrar responde 403 (Forbidden).
- **Decisiones**: se bloquea también la edición de otro staff, no solo de superusuarios, porque fijar su contraseña daría los permisos de esa cuenta (escalada lateral). Los usuarios de staff siguen viéndose entre sí en el listado, en solo lectura. Hoy no hay grupos ni staff con ese permiso en el repo, por eso la probabilidad real es baja; el arreglo evita que el día que se conceda sea una escalada. Quien necesite que un staff administre a otro staff debe ser superusuario.
- **Correcciones tras la revisión de PR-Agent**: faltaba `has_delete_permission` (un staff con `delete_usuario` podía borrar a otro staff, también por acción masiva); se implementó con la regla por objeto y sin devolver `False` para `obj is None`, porque eso desactivaría el borrado en el listado para todos (la acción masiva vuelve a preguntar por cada fila). La documentación decía 403 (Forbidden) para superusuarios y era incorrecto (ver códigos exactos arriba). Se cubrieron con tests la edición de sí mismo, el POST sobre otro staff y el borrado individual y masivo.
- **Archivos afectados**: `backend/usuarios/admin.py`, `backend/usuarios/test_seguridad_admin.py` (nuevo), `docs/auditoria-seguridad-resumen.md`.

---

## 20/10/2026 — Auditoría F8 y F9: clave de confirmación fuera del log y destino seguro tras el login

- **Fecha**: 20/10/2026
- **Descripción**: se corrigieron dos hallazgos de severidad baja.
  - **F8**: `ConfirmarCorreoView` escribía la clave del enlace de confirmación en el log (nivel INFO) y, para claves inválidas, el mensaje de `BadSignature`, que repite la firma recibida. Ahora registra solo el largo y el tipo de error. La clave ya filtrada a logs viejos vence a las 24 horas (`ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1`), así que no hace falta rotar nada.
  - **F9**: `/login?next=…` aceptaba cualquier valor que empezara con `/`, incluidos `//host` y `/\host`, que el navegador trata como otro sitio. La nueva función `destinoSeguro` (`frontend/lib/safe-next.ts`) resuelve `next` con `new URL()` contra un origen ficticio, igual que el navegador (descarta tabulaciones y saltos de línea, convierte `\` en `/`), y solo acepta el resultado si el origen no cambia; devuelve `pathname + search + hash`. También rechaza resultados que empiezan con `//` (caso `/..//host`).
- **Decisiones**: se usa el parser de URL en vez de una lista de patrones prohibidos, porque la lista siempre deja pasar alguna variante. El origen ficticio evita depender de `window` (la página también se renderiza en el servidor). Queda sin probar en un navegador real el salto de redirección (los tests cubren la función y la página de login con `next` hostil).
- **Revisión de alcance tras PR-Agent**: se recorrieron todos los `router.push/replace`, `redirect` y `window.location` del frontend. El login es el único punto que navega a un valor tomado de la URL; los demás usan rutas fijas (`routes.*`) o el `pathname` propio codificado. El parámetro `?from=` de la ficha (miga de pan) no es un destino: `origenDesde` solo acepta `search`, `reviews` o `list-<dígitos>` y el enlace se construye con `routes.list(id)`, así que un valor hostil cae en Home. Se ampliaron los tests: más variantes hostiles de `next`, una prueba exhaustiva de combinaciones de caracteres delicados (más de 20 000) que exige que el resultado nunca salga del origen, y valores hostiles de `from`.
- **Archivos afectados**: `backend/usuarios/views.py`, `backend/usuarios/test_seguridad_logs.py` (nuevo), `frontend/lib/safe-next.ts` (nuevo), `frontend/app/(public)/login/page.tsx`, `frontend/tests/safe-next.test.ts` (nuevo), `frontend/tests/access-screens.test.tsx`, `docs/auditoria-seguridad-resumen.md`.

---

## 20/10/2026 — Auditoría F2 y F3: límites de tasa por cuenta e IP, `NUM_PROXIES` y tope de página

- **Fecha**: 20/10/2026
- **Descripción**: se corrigieron los hallazgos F2 (login, registro y reenvío de confirmación sin límite) y F3 (límite del catálogo eludible con `X-Forwarded-For`).
  - **F3**: `REST_FRAMEWORK["NUM_PROXIES"]` se lee de la variable `NUM_PROXIES`: en desarrollo vale 0 si falta, pero **con `DEBUG=False` es obligatoria y el arranque falla si no está** (un 0 olvidado detrás de un proxy haría que todos los usuarios compartan un contador por IP; el comentario en `settings.py` explica qué hacer al desplegar). Con 0 DRF usa la IP de la conexión e ignora `X-Forwarded-For`; con N toma la N-ésima IP desde la derecha, la que añade el proxy propio. El catálogo rechaza `page` mayor que 500 (el máximo que sirve TMDB) con 400 (Bad Request) y `max_value`, ahora en `CatalogoBaseView._page` para todas las vistas. Redis arranca con `maxmemory 256mb` y `volatile-lru`: solo desaloja claves con vencimiento (caché de TMDB y contadores), nunca la cola de Celery.
  - **F2**: nuevas clases en `usuarios/throttles.py`. Login: 10 por minuto por cuenta (correo o nombre de usuario, normalizado y guardado como hash) y 30 por minuto por IP. Registro: 5 por hora por correo y 10 por hora por IP. Reenvío: 1 por minuto por correo (enfriamiento), 3 por hora por correo y 10 por hora por IP. Superado el límite responde 429 (Too Many Requests) con el código existente `throttled` y `Retry-After`; no se creó un código nuevo, así que no cambian `contracts/` ni `traducciones/`.
- **Decisiones**: el límite por cuenta cuenta todos los intentos, no solo los fallidos (más simple y no revela si la contraseña era correcta); con la cuenta bloqueada tampoco pasa la contraseña correcta, a cambio de que alguien pueda bloquear 1 minuto a otra persona (el costo es menor que permitir adivinar contraseñas). Sin identidad en el cuerpo del pedido solo aplica el límite por IP. El reenvío aplica sus límites con `as_view(throttle_classes=...)` y no con una subclase, porque una subclase cambiaba `contracts/openapi.yaml`. Los tests comparten IP y los contadores se arrastraban entre ellos: el ejecutor de pruebas (`filmai/pruebas.py`) vacía la caché antes de cada test.
- **Correcciones tras la revisión de PR-Agent**: el límite por cuenta acepta cualquier escalar (un `username` numérico en JSON lo esquivaba); `NUM_PROXIES` es obligatorio en producción; y el 429 (Too Many Requests) muestra la espera en segundos, minutos u horas según su duración (`esperaLegible` en `frontend/lib/errors.ts`, claves `throttledWithWaitMinutes` y `throttledWithWaitHours` en `traducciones/claves-extra.csv`), en lugar de «3600 segundos». Un efecto aceptado del límite por cuenta: quien conozca un correo puede bloquear el login de esa cuenta durante un minuto, y el reenvío durante una hora; el alcance del proyecto no justifica más.
- **Pendiente**: confirmar la topología al desplegar (cuántos proxies hay delante y que sobrescriban `X-Forwarded-For`); el tope de llamadas a TMDB por pedido (browse hace hasta 10) y la validación de los demás parámetros del catálogo quedan para F6 y F7; los límites de Resend y del proxy no están en el repo.
- **Archivos afectados**: `backend/filmai/settings.py`, `backend/filmai/urls.py`, `backend/filmai/pruebas.py`, `backend/usuarios/throttles.py`, `backend/usuarios/views.py`, `backend/catalogo/views.py`, `docker-compose.yml`, `backend/usuarios/test_seguridad_throttles.py`, `backend/catalogo/test_seguridad_throttle.py`, `backend/filmai/test_seguridad_redis.py`, `docs/auditoria-seguridad-resumen.md`.

---

## 20/10/2026 — Auditoría F1: Redis con contraseña, solo loopback y caché sin pickle

- **Fecha**: 20/10/2026
- **Descripción**: se corrigió el hallazgo F1 de la auditoría (Redis sin contraseña, publicado en todas las interfaces, con una caché de Django que deserializaba pickle). Tres capas: (A) el puerto 6379 se publica solo en `127.0.0.1`; (B) Redis arranca con `requirepass` y el compose aborta si falta `REDIS_PASSWORD`; (C) la caché de Django usa `filmai.cache.JSONRedisSerializer` en lugar del pickle por defecto. `settings.py` arma las tres URLs (caché, broker y resultados de Celery) con la contraseña a partir de `REDIS_PASSWORD` y, con `DEBUG=False`, lanza `ImproperlyConfigured` si alguna llega sin contraseña, igual que ya hace con `EMAIL_BACKEND`.
- **Decisiones**: la contraseña va por variable de entorno del contenedor y no en la línea de comandos, para que no se vea en `docker ps`. Los enteros se guardan crudos porque `cache.incr` (contadores de throttle) usa `INCR` de Redis. Un valor de caché que no es JSON válido se descarta y se registra un aviso, nunca se interpreta; una clave vieja en formato pickle devuelve `None` hasta que vence su TTL (minutos o un día). El caché de TMDB (`catalogo/cache.py`) ya usaba JSON y toma la URL con contraseña de `settings.REDIS_URL`, sin cambios.
- **Pendiente a nivel despliegue**: política `maxmemory` de Redis (se hace con F3, usando `volatile-lru` porque la cola de Celery comparte instancia y no debe ser desalojada).
- **Archivos afectados**: `docker-compose.yml`, `.env.example`, `backend/filmai/settings.py`, `backend/filmai/cache.py` (nuevo), `backend/filmai/test_seguridad_redis.py` (nuevo), `docs/auditoria-seguridad-resumen.md`. **Quien tenga un `.env` anterior (por ejemplo Gonza) debe: agregar `REDIS_PASSWORD`, borrar `REDIS_URL`, `CELERY_BROKER_URL` y `CELERY_RESULT_BACKEND` si no llevan contraseña (con `DEBUG=True` no hay aviso al arrancar y Celery falla con `NOAUTH` al ejecutar una tarea) y recrear los contenedores con `docker compose up -d --force-recreate`.** El detalle está también en `.env.example`.
- **Correcciones tras la revisión de PR-Agent**: `redis-server` se invoca vía `docker-entrypoint.sh` para conservar la baja de root al usuario `redis` (con `sh -c` a secas corría como root); `REDIS_PASSWORD` va vacía en `.env.example` porque un valor de ejemplo no vacío anula el `:?` del compose; el mensaje de `ImproperlyConfigured` explica los dos remedios; y hay un test de ida y vuelta por `RedisCache` con un cliente en memoria.

---

## 18/10/2026 — Auditoría de seguridad (run-2): validación en sandbox y lista de fixes

- **Fecha**: 18/10/2026
- **Descripción**: se validó por ejecución, en un sandbox Docker aislado (red interna sin internet, repo en solo lectura, TMDB simulado, datos ficticios), las 11 pistas `needs_validation` de run-1. Cada una la reprodujo un validador y la repitió un verificador independiente: las 11 quedaron **confirmadas** (6 de severidad media y 5 baja; ninguna alta ni crítica). Las cabeceras anti-framing siguen rechazadas. La probabilidad real depende de factores de despliegue que el repo no muestra (proxy, límites de Resend y TMDB, acceso a logs, exposición de Redis).
- **Decisión**: no se corrige nada en esta tarea. Cada fix va como tarea aparte con test de regresión y su entrada aquí. Orden sugerido: Redis, identidad del cliente y límites de tasa, cambios chicos (`next`, log), catálogo, admin, y al final lo que requiere decidir con el equipo (pre-secuestro y moderación de reseñas). Hay una discrepancia de severidad en el admin y en Redis (el verificador opinó alta); se mantiene media por la baja probabilidad.
- **Qué se sube y qué no**: se sube solo `docs/auditoria-seguridad-resumen.md` (títulos, módulos, estado y prioridad, sin pasos de explotación) a la rama `security/audit`, sin PR, para que no corran PR-Agent ni DeepSeek sobre el contenido. Los informes completos (`security-audit/run-1/` y `run-2/`, incluida `FIX-LIST.md`) siguen locales e ignorados por git.
- **Archivos afectados**: `docs/auditoria-seguridad-resumen.md` (nuevo), `docs/decisiones.md`.

---

## 18/10/2026 — Primera auditoría de seguridad (run-1): estado y pendientes

- **Fecha**: 18/10/2026
- **Descripción**: se corrió la primera auditoría `standard` de `security-audit` sobre el commit `f7bbb6b`. Fue una pasada parcial de solo lectura de código: no hubo sandbox, así que no se ejecutó nada del proyecto y por regla de la skill no hay hallazgos `confirmed` ni severidades. Resultado: 35 unidades cubiertas, 12 candidatos, 11 pistas en `needs_validation` y 1 descartada. Los validadores de la skill pasan y la corrida quedó `complete` en procedimiento, no en evidencia de ejecución. No se cambió código del proyecto.
- **Informes**: están en `security-audit/run-1/` (`REPORT.md`, `NEEDS-VALIDATION.md`, `findings.json`, `coverage-ledger.json`). Siguen ignorados por git a propósito, porque describen problemas sin arreglar; viven solo en la máquina de Marcos y no se pueden recuperar desde el repositorio. Si se pierde esa carpeta, hay que repetir la auditoría.
- **Pendiente**: armar un sandbox Docker (red aislada, código montado de solo lectura, entorno vacío, límites de memoria, CPU y tiempo, sin `.env` real ni servicios externos) y validar cada pista con un test local sobre datos ficticios, para confirmarla o descartarla. Con eso se arma la lista final de arreglos priorizada.
- **Después**: cada arreglo sale como tarea aparte, con su test y su entrada en este archivo. El resumen para el equipo se comparte por el chat o por el PR del arreglo, no con detalles en docs versionados.
- **Archivos afectados**: `docs/decisiones.md`.

---

## 18/10/2026 — Skill security-audit de Cloudflare

- **Fecha**: 18/10/2026
- **Descripción**: se instaló `security-audit` (https://github.com/cloudflare/security-audit-skill, licencia MIT, commit `c1c8a8c`) con `npx skills add cloudflare/security-audit-skill --skill security-audit --agent codex --copy`, que deja una copia en `.agents/skills/security-audit/` y la registra en `skills-lock.json`. Antes de instalarla se leyeron sus archivos completos: son guías en markdown, un JSON Schema y dos validadores en Node sin dependencias ni acceso a red. La copia instalada es idéntica a la revisada y no se edita; las adaptaciones al proyecto viven en `AGENTS.md`. Tiene dos modos: guía (preguntas de seguridad puntuales) y auditoría completa de 6 fases con perfiles `quick`, `standard` y `deep`; esta última solo corre a pedido explícito. La skill no modifica el código auditado: los arreglos se deciden y se hacen aparte, con su test y su entrada acá.
- **Informes**: se escriben en `security-audit/run-<N>/`, ignorado por git. Describen vulnerabilidades todavía sin arreglar, así que no se commitean; el resumen que se comparte con el equipo sale por el chat o por el PR del fix.
- **Archivos afectados**: `.agents/skills/security-audit/`, `skills-lock.json`, `.gitignore`, `AGENTS.md` y `docs/decisiones.md`.

---

## 03/10/2026 — Nota identificable y lectura condicional de reseñas

- **Fecha**: 03/10/2026
- **Descripción**: Mis reseñas acompaña la nota `X/10` con una estrella amarilla (`#f5c518`) de Lucide y una etiqueta accesible para distinguirla de la fecha, que pasa a la esquina superior derecha. La disposición final aprobada es estrella y nota juntas, en ese orden. «Leer más/Leer menos» aparece solo si el contenido excede las tres líneas visibles: `ResizeObserver` mide nuevamente cuando cambia el tamaño del párrafo; también se mide al editar el texto. Se conserva el control al expandir un texto largo.
- **Sin texto**: «Todavía no escribiste una reseña.» usa semántica de nota informativa, icono, fondo tenue, borde discontinuo y cursiva para evitar que parezca texto escrito por el usuario.
- **Foco al editar**: el modal se titula «Editar calificación y reseña de "{título}"», enfoca el campo de reseña al abrir y mantiene la nota guardada. Se evita el outline inicial en la primera estrella sin quitar la navegación ni los indicadores de foco para teclado.
- **Archivos afectados**: `ReviewCard`, `ReviewModal`, `Modal`, tests unitarios y Playwright, docs 02/04/05, wireframe y spec `reviews-api`.
- **Tests**: estrella junto a nota y etiqueta accesible; fecha arriba a la derecha; texto corto y exactamente tres líneas sin control; expansión/contracción; ajuste del control entre escritorio y móvil y después de editar; título con producción y foco inicial en texto con calificación conservada. Verificación: 41 tests unitarios, 24 Playwright y 410 Django, además de Ruff, ESLint, TypeScript y Prettier.

## 03/10/2026 — Confirmación del avatar y consistencia visual de botones

- **Fecha**: 03/10/2026
- **Descripción**: el selector mantiene una selección temporal independiente del borrador. Solo «Guardar» del modal aplica el avatar al formulario; «Cancelar» o Escape descartan la selección. El guardado del perfil conserva la persistencia por API. Se elimina el título duplicado y se indica click con cursor pointer.
- **Disposición**: se reserva el espacio de la barra de desplazamiento mediante `scrollbar-gutter: stable`; al devolver el foco se evita desplazar la página. Así bloquear el fondo del modal no altera la posición del contenido.
- **Colores**: las variantes de `Button` comparten tokens; el primario usa texto oscuro sobre naranja y el destructivo un rojo legible para cada tema. Se eliminan ajustes locales para que las mismas acciones conserven colores y contraste.
- **Archivos afectados**: `AvatarSelector`, perfil, `Modal`, CSS global, `Button` y botones de reseñas/navegación; tests unitarios y Playwright; docs 02/04, wireframe HTML y spec `profile-ui`.
- **Tests**: selección temporal y confirmación; cancelación/reapertura y Escape; título único; cursor; posición y scroll en móvil/escritorio; igualdad de colores y contraste de texto en ambos temas. Suite completa: 38 tests unitarios, 23 recorridos Playwright y 410 tests Django. Ruff, TypeScript, ESLint y Prettier sin errores.

## 03/10/2026 — Perfil con modales y Mis reseñas con pósters

- **Fecha**: 03/10/2026
- **Descripción**: se aprobó mostrar pósters en Mis reseñas, aunque el wireframe anterior no los incluía. Las tarjetas reservan 80 × 120 px en escritorio y 56 × 84 px en móvil y reemplazan imágenes ausentes/fallidas. Se implementa la gestión con la API existente: editar; borrar solo texto conservando nota y Vistas; quitar nota borrando texto y Vistas. Se mantienen las decisiones del 26 y 30/09. Las calificaciones sin texto y reseñas moderadas propias siguen presentes. Buscar y ficha quedan fuera del alcance; no se ofrecen enlaces a esas rutas pendientes.
- **Perfil**: capa visible para cambiar avatar durante edición, catálogo en modal, confirmación personalizada al cancelar/navegar con borrador modificado, y disponibilidad en verde/rojo. El historial conserva índices propios sin reemplazar el estado de Next.js para revertir y repetir el recorrido solicitado. Recarga/cierre mantiene aviso nativo.
- **Baja**: texto aprobado «Esta acción es irreversible. Se cerrarán todas tus sesiones y no podrás volver a iniciar sesión ni reactivar tu cuenta. Asegurate de querer dar de baja la cuenta antes de continuar.». Describe la pérdida irreversible del acceso; no cambia la conservación interna definida por CU-007.
- **Corrección necesaria de API**: `MisCalificacionesView` interpretaba el parámetro `cursor` como filtro de ficha y respondía 400 en la segunda página. Un test de regresión con 22 calificaciones reprodujo el fallo; solo `id_tmdb`/`tipo` seleccionan ahora el modo ficha. Afecta `backend/catalogo/reviews.py` y `tests_reviews.py`, sin cambiar el contrato público.
- **Archivos afectados**: páginas de perfil, preferencias y Mis reseñas; componentes compartidos de modal, navegación y reseñas; utilidades; configuración y suites de Vitest/Playwright; docs 02/04/05, wireframe HTML y specs de reseñas/perfil. Se incorpora Vitest 4 con Testing Library y jsdom para probar componentes y lógica; Playwright recorre los flujos en navegador.
- **Verificación**: suite Django completa, 410 tests; Vitest, 35 tests unitarios; Playwright, 19 recorridos con API controlada en Chromium. TypeScript, ESLint y Prettier se verifican en frontend; Ruff en backend. Las capturas y recorridos cubren 390, 1440 y 1920 px, foco y teclado, cursor/reintento, edición y ambos borrados. El CI incorpora `npm run test:unit` además de Playwright.

## 30/09/2026 — Corrección del aviso de acceso a la documentación

- **Descripción**: se corrige la variable `recurso` en la plantilla de acceso
  restringido para que el mensaje de una sesión sin permisos nombre Swagger UI
  o el esquema OpenAPI. Se reduce un 95 % el margen superior del contenido
  principal de esa página y se agrega una prueba para ambas rutas.
- **Motivo**: el salto de línea dentro de `{{ recurso }}` impedía que Django
  interpolara el nombre y el espacio entre la marca y el aviso era excesivo.
- **Archivos afectados**: `backend/templates/filmai/documentacion_restringida.html`
  y `backend/filmai/tests.py`.

---

## 30/09/2026 — Acceso denegado a Swagger y OpenAPI con instrucciones para el Admin

- **Descripción**: cuando alguien abre `/api/docs/` o `/api/schema/` en un
  navegador sin sesión staff, recibe una página HTML con estado 403 que explica
  el permiso necesario y enlaza al login del Django Admin. El enlace conserva
  la ruta solicitada para volver tras ingresar. Una sesión común recibe un
  mensaje específico; los clientes que piden JSON reciben un 403 JSON claro.
  La verificación de `is_staff` y los permisos de DRF siguen protegiendo ambas
  vistas. El control externo evita que la negociación YAML/JSON del esquema
  devuelva otro error antes de mostrar el aviso.
- **Motivo**: hacer entendible el rechazo y ofrecer un paso de recuperación
  sin exponer el esquema a visitantes.
- **Archivos afectados**: `backend/filmai/documentation.py`,
  `backend/filmai/urls.py`, `backend/filmai/tests.py`,
  `backend/templates/filmai/documentacion_restringida.html` y
  `openspec/specs/admin-api-docs/spec.md`.

---

## 30/09/2026 — Documentación API restringida a staff y semilla de reseñas repetible

- **Descripción**: `/api/docs/` y `/api/schema/` requieren ahora una sesión de
  Django Admin y el permiso `is_staff` mediante `SessionAuthentication` e
  `IsAdminUser`. La sesión del Admin permite consultarlas incluso si el
  navegador conserva una cookie JWT inválida. Esta decisión reemplaza la
  publicación abierta registrada más abajo el mismo día.
- **Semilla de desarrollo**: `seed --solo-resenas` completa hasta 15
  calificaciones por usuario de prueba (o todas las producciones disponibles).
  Cuenta las calificaciones existentes antes de crear otras y garantiza al
  menos nueve reseñas con texto cuando hay 15 notas, incluso si ya existían.
  Conserva las reseñas previas y deja de agregar filas al repetir el comando sobre los
  mismos usuarios y catálogo. El seed completo mantiene su muestra aleatoria.
- **Motivo**: limitar la exposición de la descripción de la API y permitir
  poblar datos relacionados para desarrollo sin actividad real de producción
  ni crecimiento accidental en cada ejecución.
- **Archivos afectados**: `backend/filmai/urls.py`, `backend/filmai/tests.py`,
  `backend/usuarios/management/commands/seed.py`, `backend/usuarios/tests.py`,
  `README.md`, `docs/05_Plan_de_Desarrollo.md`,
  `openspec/specs/admin-api-docs/spec.md` y
  `openspec/specs/development-seed/spec.md`.

---

## 30/09/2026 — Swagger y esquema OpenAPI públicos, sin autenticación

- **Descripción**: `/api/docs/` y `/api/schema/` se declaran ahora con
  `authentication_classes=[]`, el mismo criterio de `CatalogoBaseView`. Antes
  una cookie `access` vieja o corrupta en el navegador los convertía en 401:
  `JWTCookieAuthentication` rechaza el token antes de evaluar permisos, aunque
  la vista no exija sesión.
- **Motivo**: la documentación es pública por diseño; un recurso abierto no
  debe fallar por credenciales vencidas que el navegador conserva. Se agrega
  un test de regresión en `filmai/tests.py`.
- **Archivos afectados**: `backend/filmai/urls.py`, `backend/filmai/tests.py`,
  `README.md` (URLs).

---

## 30/09/2026 — Módulo 6: reseñas de desarrollo con `seed --solo-resenas`; el seed conserva al superusuario

- **Descripción**: el Admin de reseñas (AD-01') estaba implementado y con
  tests, pero la base de desarrollo no tenía reseñas: el guard de C-04c impide
  que `seed` resetee un catálogo poblado y forzarlo tira horas de llamadas a
  TMDB. Se agrega el modo no destructivo `python manage.py seed
--solo-resenas`: siembra calificaciones (1–10) y reseñas (texto ≤1000,
  ~60% de las notas) sobre el catálogo y las cuentas de desarrollo existentes
  (`@filmai.com`, activas, sin staff). Es idempotente —saltea pares
  usuario–producción ya calificados, respetando
  `uq_calificacion_usuario_produccion`— y 1 de cada 7 reseñas nace
  `activa=False` para que el Admin tenga ejemplos reales de filtro,
  desactivación y reactivación (CU-017).
- **Superusuario preservado**: `seed._limpiar()` ya no borra cuentas
  `is_staff` ni sus `EmailAddress`, cumpliendo lo que el README prometía; un
  reset de desarrollo ya no deja al equipo sin acceso a `/admin/`.
- **Chequeo end-to-end** (BD de desarrollo, 30/09): las 34 calificaciones y
  20 reseñas sembradas cumplen rango de nota, unicidad de pares, largo de
  texto y composición 1:1 reseña–calificación. Contra la API de C-08, la
  moderada no aparece en la comunidad y sí en «mías» de su autor; el
  changelist del Admin lista las 20 y el filtro `activa=No` responde.
- **Motivo**: cerrar operativamente el Módulo 6; decisión del usuario de que
  el mecanismo viva dentro del propio `seed` para que el otro integrante lo
  replique con el mismo comando.
- **Archivos afectados**: `backend/usuarios/management/commands/seed.py`,
  `backend/usuarios/tests.py`, `README.md`, `docs/05_Plan_de_Desarrollo.md`,
  `docs/reportes_dev/explicacion-modulo-6-admin.md`.

---

## 26/09/2026 — Selector de avatar: foco y selección circulares

- **Descripción**: en el selector de avatar del perfil, cada opción es un
  `label` en una grilla (`grid-cols-4 sm:grid-cols-6`) que se estira al ancho
  de la celda, quedando más ancho que alto. El contorno de foco
  (`focus-within:outline-2 focus-within:outline-ring`, color `--ring` #f5c518)
  y el resaltado de la opción marcada (`has-[:checked]:bg-primary/20`) seguían
  esa silueta no circular, por lo que se veía un rectángulo (o píldora con
  `rounded-full` en un elemento no cuadrado) alrededor del avatar. Se hace el
  label cuadrado con `aspect-square` y la imagen pasa de tamaño fijo 72×72 a
  `fill` dentro de un contenedor circular, así ambos efectos siguen la
  silueta circular del avatar y el tinte de selección queda visible en el
  anillo de padding.
- **Archivos afectados**: `frontend/app/perfil/page.tsx`.

---

## 26/09/2026 — Perfil, avatares ampliables y preferencias visibles

- **Descripción**: el perfil muestra nombre y apellido en la cabecera y en
  campos separados, además de los datos de cuenta de CU-005. La edición inline
  explica las reglas antes de guardar. Nombre y apellido permiten espacios
  entre palabras y normalizan espacios sobrantes antes de persistir; una
  migración corrige los registros existentes. El cambio de contraseña conserva
  un formulario y una confirmación independientes de la edición del perfil.
- **Avatares**: se publican las 26 imágenes individuales de
  `frontend/public/avatars/recortados/`. Un script genera el catálogo con IDs
  estables para que nuevos archivos no cambien elecciones previas; los IDs de
  archivos retirados permanecen inactivos y no se reutilizan. La API
  valida el mismo catálogo que consulta el selector; la navbar muestra la
  selección y usa iniciales como respaldo. No hay subida de fotos.
- **Preferencias y reseñas**: el tema guardado en la cuenta se aplica a la
  interfaz. Los controles de privacidad y correo persisten, con un aviso de
  que aún no tienen efecto sobre publicaciones o envíos. El enlace «Mis reseñas»
  abre una pantalla informativa vacía hasta que C-08 permita implementar P-06.
  Se añaden pruebas de Django y recorridos Playwright para estos flujos.
- **Verificación sin interrumpir desarrollo**: Playwright escribe sus archivos
  de Next en `.next-e2e`; un build de comprobación usa
  `NEXT_DIST_DIR=.next-build`. Se evita compartir `.next` con el servidor
  de desarrollo después de comprobar que ejecutar un build en paralelo lo
  dejaba sin sus manifests. `next.config.ts` permite elegir el directorio por
  variable de entorno y ambos directorios se excluyen de Git.
- **Archivos afectados**: `backend/usuarios/`, `backend/filmai/urls.py`,
  `frontend/app/`, `frontend/components/`, `frontend/lib/`, `frontend/e2e/`,
  `frontend/playwright.config.ts`, `scripts/sync_avatars.py`, `.github/workflows/ci.yml`,
  docs 02, 03, 04, 05 y `docs/decisiones.md`.

---

## 24/09/2026 — P-03/P-05: preferencias y baja lógica sin pérdida de datos

- **Descripción**: `GET/PUT /api/preferences/` consulta y actualiza parcialmente
  `tema`, `perfil_publico`, `notif_recomendaciones`, `notif_resenas` y
  `notif_novedades`. Solo se modifica al usuario autenticado; campos ajenos a las
  preferencias se ignoran. `POST /api/account/deactivate/` cambia `estado` a
  `baja`, bloquea access JWT por estado y agrega los refresh del usuario a la
  blacklist. El cambio de estado, blacklist y cierre de sesión son atómicos.
- **Conservación**: no se elimina ni modifica contenido de listas, ítems,
  calificaciones, reseñas, chats, mensajes, perfil ni vínculo Google. Se corrigen
  las descripciones de eliminación permanente en CU-007 y su modal de UI.
- **Autenticación**: pendiente y baja se rechazan en login local, Google, access
  y refresh. Google resuelve el `sub` contra la cuenta social persistida antes
  de iniciar sesión; no se decide por el correo ni por el usuario provisional de
  allauth. Confirmar un correo antiguo no reactiva una cuenta en baja.
  La documentación OAuth aclara contraseña inutilizable, no `NULL`, y alta de
  contraseña local por recuperación sobre el mismo usuario.
- **Reportes**: se trasladan `explicacion-modulo-6-admin.md` y
  `explicacion-prs-27-28-29.md` desde la raíz a `docs/reportes_dev/`, conservando
  su contenido. El contrato del módulo 4 se documenta allí también.
- **Archivos afectados**: `backend/usuarios/{cuenta,adapter,serializers,
test_cuenta,tests}.py`, `backend/filmai/urls.py`, docs 02, 03, 04, 05,
  `docs/decisiones.md` y `docs/reportes_dev/`.

---

## 24/09/2026 — P-01: perfil propio y contraseñas con revocación de sesiones

- **Descripción**: se agregan `GET/PUT /api/profile/` y
  `POST /api/profile/change-password/`. El perfil permite actualizar parcialmente
  nombre, apellido, nombre de usuario y avatar; el resto es de solo lectura.
  Nombre y apellido siguen CU-001 (solo letras, hasta 50 caracteres). Los nombres
  de usuario son únicos sin distinguir mayúsculas también en PostgreSQL, mediante
  la migración `usuarios.0005`; los conflictos devuelven 409.
- **Contraseñas**: el cambio requiere `old_password`, `password1` y `password2`;
  reutiliza `validate_password`. Una cuenta sin contraseña local debe usar la
  recuperación por correo. Se conserva su usuario y su vínculo Google.
  `CHECK_REVOKE_TOKEN` vincula los JWT al hash de contraseña vigente. Se agrega
  la misma comprobación al refresh, porque el serializer instalado solo comprueba
  el estado activo. Los JWT anteriores sin ese claim requieren un nuevo login.
- **Recuperación**: conserva token temporal de una hora, confirmación y límites
  de intentos. El estado y token se revalidan bajo bloqueo de fila al guardar:
  dos solicitudes no pueden consumir el mismo enlace. Cambiar o restablecer la
  contraseña limpia cookies y sesión Django, invalida JWT de todos los dispositivos
  y exige un nuevo login. La notificación se envía después del commit; un fallo de
  correo se registra y no revierte una contraseña ya guardada.
- **Compatibilidad**: `/api/auth/password/change/` pasa por el mismo contrato;
  no queda un camino alternativo sin contraseña actual. Refresh por cookie exige
  CSRF. Los endpoints públicos de login, Google, recuperación y obtención de CSRF
  toleran cookies JWT antiguas, sin omitir la validación CSRF en mutaciones.
- **UI**: debe avisar antes de confirmar que se cerrarán las sesiones en todos
  los dispositivos y redirigir al login después del cambio. No se implementa UI
  nueva en esta entrega.
- **Archivos afectados**: `backend/usuarios/{perfil,authentication,passwords,
exceptions,serializers,views,models,test_perfil}.py`, migración `0005`,
  `backend/filmai/{settings,urls}.py`, docs 02 y 04 y
  `docs/reportes_dev/modulo-4-api.md`.

---

## 21/09/2026 — AD-01': moderación de reseñas con borrado lógico en Django Admin

- **Descripción**: se conserva `UsuarioAdmin` y se registra `ResenaAdmin` con
  usuario, producción, tipo y valor visibles; búsqueda por texto, usuario y
  producción; filtros por estado y tipo. El formulario permite cambiar `texto`
  y `activa`, pero deja fija la calificación. La acción «Desactivar reseñas»
  establece `activa=False` y no elimina la fila; las reseñas desactivadas
  siguen visibles y pueden reactivarse. El alta y el borrado físico individual
  o masivo desde el Admin quedan deshabilitados. Los permisos nativos de Django
  controlan acceso y cambios. Las pruebas HTTP crean sus datos en la base
  temporal de Django y comprueban también las operaciones de `UsuarioAdmin`.
- **Motivo**: moderar contenido sin perder la relación 1:1 con la calificación
  ni afectar el historial de valoraciones del usuario. El Admin resuelve
  CU-016 y CU-017 sin API ni interfaz de moderación adicional.
- **Archivos afectados**: `backend/catalogo/admin.py`,
  `backend/catalogo/test_admin.py`, `docs/02_Especificación de Requerimientos.md`,
  `docs/05_Plan_de_Desarrollo.md`, `docs/decisiones.md` y
  `docs/reportes_dev/explicacion-modulo-6-admin.md`.

---

## 12/09/2026 — C-03: endpoints de catálogo públicos con AllowAny explícito

- **Descripción**: los 7 endpoints de catálogo (`/api/catalogo/trending/`,
  `now-playing/`, `discover/`, `search/`, `movie/<id>/`, `tv/<id>/`,
  `keywords/`) se sirven con `authentication_classes = []` y
  `permission_classes = [AllowAny]` en `CatalogoBaseView`, sobrescribiendo
  explícitamente el `DEFAULT_PERMISSION_CLASSES = IsAuthenticated` introducido
  en PR #9. El catálogo (trending, búsqueda, detalle) es accesible sin login,
  consistente con docs 04 y 05 (Home y Buscador muestran contenido a usuarios
  no autenticados). El throttle `catalogo: 60/min` aplica a todos igualmente.
- **Motivo**: arquitectura del Módulo 2 (docs/05) describe discovery público;
  el usuario confirmó explícitamente que el catálogo es público.
- **Archivos**: `backend/catalogo/views.py`, `backend/catalogo/urls.py`,
  `backend/filmai/urls.py`, `backend/catalogo/tests.py`,
  `openspec/changes/catalog-tmdb-endpoints/`.

---

## 12/09/2026 — Skills centralizadas para todos los harnesses

- **Descripción**: `.agents/skills/` es la única fuente versionada de skills
  para Codex, OpenCode y Antigravity CLI. Se migró `conventional-commits` desde
  `.opencode/skills/` y se eliminaron de allí las copias de `humanizer` y
  `vercel-quality`. `AGENTS.md` instruye a los tres harnesses a consultar la
  fuente central antes de implementar.
- **Motivo**: evitar definiciones divergentes de una misma skill y conservar
  una revisión única y auditable de las instrucciones del proyecto.
- **Archivos afectados**: `AGENTS.md`, `.agents/skills/`,
  `.opencode/skills/` y `docs/decisiones.md`.

---

## 12/09/2026 — Contrato API centralizado y perfiles sociales inmutables al login

- **Descripción**: se incorpora OpenAPI con Swagger UI en `/api/docs/` y su
  esquema en `/api/schema/`; la documentación de parámetros deja de vivir en
  docstrings extensos de rutas. Las URLs de API usan slash final de forma
  explícita (`APPEND_SLASH=True`) y el helper del frontend lo normaliza antes
  de cada request. El handler global conserva los mapeos de TMDB y agrega
  respuestas consistentes para 404, 405 y 429. En Google OAuth, una cuenta ya
  vinculada devuelve el perfil FilmAI existente sin modificar estado ni datos
  personales; Google solo precarga una cuenta nueva.
- **Motivo**: consolidar el contrato público de la API, evitar discrepancias de
  rutas entre frontend y backend y proteger las modificaciones de perfil hechas
  dentro de FilmAI.
- **Archivos afectados**: `backend/requirements.txt`, `backend/filmai/settings.py`,
  `backend/filmai/urls.py`, `backend/filmai/exceptions.py`,
  `backend/filmai/views.py`, `backend/usuarios/adapter.py`,
  `backend/usuarios/avatares.py`, `backend/usuarios/factories.py`,
  `frontend/lib/api.ts` y sus pruebas asociadas.

---

## 11/09/2026 — El perfil de FilmAI prevalece sobre el perfil de Google

- **Descripción**: Google provee nombre y apellido solo para precargar el alta
  de una cuenta nueva. Una vez creada, el perfil de FilmAI es la fuente de
  verdad: un inicio de sesión posterior con una cuenta Google ya vinculada no
  actualiza `nombre` ni `apellido`. Se agregó una prueba de regresión que crea
  una cuenta social vinculada y verifica que conserva ambos valores locales.
- **Motivo**: permitir que la persona edite su identidad visible en FilmAI sin
  que cambios posteriores en su perfil de Google reviertan esa elección.
- **Archivos afectados**:
  - `backend/usuarios/adapter.py` — el mapeo de nombre y apellido permanece
    limitado a `populate_user`, usada para altas sociales nuevas.
  - `backend/usuarios/tests.py` — prueba de preservación del perfil local.

---

## 10/09/2026 — Tests en CI, AGENTS.md con reglas de testing y skills, limpieza de archivos raíz

- **Descripción**: se integraron los tests de Django al pipeline de CI (`ci.yml`) con un servicio PostgreSQL 16 en GitHub Actions. Se hizo configurable el host de base de datos en `settings.py` (`DATABASE_HOST`, default `"db"`) para permitir que CI use `localhost`. Se actualizó `AGENTS.md` agregando reglas de tests unitarios (§5) y consulta de skills (§6). Se limpió `.env.example` eliminando boilerplate. Se actualizó `.gitignore` agregando `.codegraph/` y `.ruff_cache/`. Se reescribió la Problemática del `README.md` y se agregó un diagrama ER Mermaid del modelo de datos. Testing del frontend queda pendiente para implementar cuando se analice el stack del frontend (Next.js no tiene framework de tests configurado aún).
- **Motivo**: análisis de Etapa 1 del proyecto detectó que el CI solo verificaba lint/formato pero no ejecutaba los tests existentes. Las NOTAs del usuario solicitaron los cambios en los demás archivos.
- **Archivos afectados**:
  - `.github/workflows/ci.yml` — agregado job de tests con PostgreSQL service.
  - `backend/filmai/settings.py` — `DATABASE_HOST` configurable.
  - `AGENTS.md` — nuevas reglas §5 y §6, renumeración.
  - `.gitignore` — agregadas entradas para `.codegraph/` y `.ruff_cache/`.
  - `.env.example` — eliminado boilerplate de títulos con `===`.
  - `README.md` — reescrita Problemática, agregado diagrama ER, ñ en todo el documento.

---

## 10/09/2026 — Grafo de conocimiento con graphify y directiva de actualización periódica

- **Descripción**: se incorporó un grafo de conocimiento del repositorio generado
  con **graphify** (`/graphify`, outputs en `graphify-out/`: `graph.html`,
  `graph.json`, `GRAPH_REPORT.md`). Se agregó la directiva en `AGENTS.md` (§5)
  de ejecutar `graphify update .` periódicamente para mantener el grafo al día.
  Momento conveniente elegido: al finalizar una tarea que haya creado o modificado
  archivos relevantes, ANTES de dar el OK al usuario o de crear el commit, para que
  el grafo actualizado quede versionado en el mismo commit. `graphify-out/` se
  versiona en git excepto `cache/`, `.graphify_python`, `.graphify_root`, la firma
  de labels y los backups automáticos (en `.gitignore`).
- **Motivo**: el usuario pidió mantener actualizado el grafo tras cada commit,
  y que la actualización ocurra ANTES del commit para que el grafo actualizado se
  suba con el cambio.
- **Archivos**: `AGENTS.md`, `.gitignore`, `graphify-out/` (nuevo).

---

## 08/09/2026 — Auditoría de consistencia y normalización documental end-to-end

- **Descripción**: se auditó el estado real del repositorio contra los docs 01–06,
  `README.md`, el diagrama de datos y OpenSpec. Resultado: en `main` están
  implementados autenticación (A-01..A-09), modelos base, seed, CI, C-01
  (cliente TMDB) y C-02 (caché Redis); siguen pendientes C-03 (endpoints de
  catálogo), C-04a (materialización), infraestructura pgvector/Ollama,
  `ProduccionEmbedding`, C-04b (sync Celery), APIs/UI de listas, reseñas,
  perfil y chatbot. Se corrigieron las contradicciones detectadas:
  1. README describía la jerarquía Persona/Usuario/Administrador ya eliminada.
  2. Docs 02/03 hablaban de "cron job" mientras el plan y la infraestructura
     prevista usan Celery Beat + workers.
  3. Docs 05 mencionaba `embedding IS NULL` en `ProduccionAudiovisual` mientras
     docs 03 definía la tabla `ProduccionEmbedding`: gana la tabla separada.
  4. El diagrama de tablas no incluía `keywords` ni `ProduccionEmbedding`.
  5. Docs 03 describía el chat persistido "al primer mensaje", pero la
     implementación (B-01) crea el chat por defecto al registrar el usuario.
  6. Docs 04 marcaba Sprint 1 (Home, Buscar) como completado sin código.
  7. Docs/decisiones documentaba CI como pendiente pese a que
     `.github/workflows/ci.yml` ya existe.
     Se actualizó el plan de desarrollo con el estado real por tarea, los
     próximos trabajos (catálogo, materialización, embeddings, sync, listas,
     chatbot/RAG) y el reparto vigente. No se crearon archivos nuevos: todo el
     trabajo futuro queda especificado dentro de la documentación existente.
- **Motivo**: el usuario aprobó ejecutar solo la normalización documental (pasos
  1 y 2 del plan); la implementación de código queda para fases posteriores.
- **Archivos**: `README.md`, `docs/02_Especificación de Requerimientos.md`,
  `docs/03_Modelos de Datos y de Diseño.md`,
  `docs/03_DiagramaClases_DiagramaTablas.json`, `docs/03_DiagramaCU.md`,
  `docs/04_Lineamientos_UI.md`, `docs/05_Plan_de_Desarrollo.md`,
  `docs/06_TMDB_API_Referencia.md`, `docs/decisiones.md`.

## 08/09/2026 — Embeddings asíncronos con Celery e idempotencia (reemplaza embeddings síncronos)

- **Descripción**: la generación de embeddings será asíncrona mediante Celery.
  La materialización persiste la producción y crea/encola un trabajo de
  embedding con estado `pending`, sin esperar al proveedor (Ollama BGE-M3).
  Estados: `pending`, `processing`, `ready`, `failed`. La búsqueda semántica
  solo considera embeddings `ready`; las producciones pendientes o fallidas
  siguen visibles en catálogo y son recuperables vía TMDB en vivo.
  **Reemplaza** la decisión del 25/08/2026 ("Embeddings síncronos en la
  materialización"), que quedaba sin efecto.
- **Motivo**: no bloquear catálogo ni detalle por una operación externa lenta;
  permitir reintentos con backoff, backfill y crecimiento progresivo del corpus
  sin degradar la experiencia (RNF #6/#7).
- **Idempotencia**: `ProduccionEmbedding` es 1:1 con `ProduccionAudiovisual`
  (`produccion_id` UNIQUE, no una FK común); no se aplica unicidad al vector
  (producciones distintas pueden tener vectores iguales). Antes de invocar al
  proveedor se compara el hash del texto canónico (`source_hash`) y la
  `model_version`: si no cambiaron y el estado es `ready`, no se recomputa.
  Celery puede duplicar tareas: la tarea usa claim/lease con actualización
  condicional y no mantiene transacciones abiertas durante la llamada externa.
  Garantía fuerte: nunca habrá dos embeddings persistidos por producción ni
  recomputación innecesaria; garantía imposible: un worker caído después de
  generar y antes de persistir puede haber invocado a Ollama dos veces.
- **Texto canónico a embeber**: `Title + Genres + Directors + Cast + Keywords
  - Synopsis` normalizado (espacios, vacíos y orden de arrays).
- **Archivos** (futuros): `backend/catalogo/models.py` (`ProduccionEmbedding`),
  `backend/catalogo/tasks.py`, `backend/catalogo/services/`,
  `docker-compose.yml` (worker + beat), `backend/requirements.txt`
  (`pgvector`, `django-pgvector`), `docs/05_Plan_de_Desarrollo.md`.

## 08/09/2026 — Corpus semántico global y progresivo + contrato TMDB → dominio

- **Descripción**: `ProduccionAudiovisual` se define como un catálogo global
  materializado progresivamente: la materialización no depende de que una
  producción pertenezca a una lista o tenga calificación. El corpus de
  búsqueda semántica es compartido por todos los usuarios; los datos personales
  (calificaciones, listas, historial) se usan vía SQL para personalizar y
  reordenar, nunca para acotar qué es buscable. Poblamiento:
  1. **Seed inicial global**: populares, tendencias, novedades y muestra
     diversa por género/año/tipo, para evitar cold start.
  2. **Materialización de lo expuesto**: cada producción servida por el
     catálogo/detalle se materializa y se enriquece (detalle + keywords)
     antes de encolar su embedding.
  3. **Cola larga**: producciones no materializadas se resuelven on-demand vía
     TMDB y se incorporan progresivamente al corpus.
     No se sincroniza todo TMDB de entrada. Además se fija el contrato canónico
     de tipos: TMDB usa `movie`/`tv` y el dominio local `pelicula`/`serie`; la
     conversión se hace en un único adaptador, nunca guardando valores TMDB
     crudos en `TipoProduccion`. La sincronización periódica (Celery Beat 3 AM)
     pasa a ser mantenimiento/seed, no prerrequisito del catálogo en vivo.
- **Motivo**: un corpus limitado a interacciones personales haría inútil la
  búsqueda semántica para descubrimiento; sincronizar todo TMDB no escala
  (decisión 25/08/2026 de arquitectura híbrida).
- **Archivos**: `docs/02_Especificación de Requerimientos.md` (CU-008, CU-013,
  CU-021), `docs/03_Modelos de Datos y de Diseño.md`,
  `docs/05_Plan_de_Desarrollo.md`, `docs/06_TMDB_API_Referencia.md`,
  `docs/decisiones.md`.

## 04/09/2026 — Corrección de arranque DRF y chequeo end-to-end

- **Descripción**: durante el chequeo end-to-end se corrigió la ruta de importación
  de `DEFAULT_PERMISSION_CLASSES` en `backend/filmai/settings.py`: DRF requiere
  `rest_framework.permissions.IsAuthenticated`, no `rest_framework.IsAuthenticated`.
  La imagen del backend también se reconstruyó para instalar las dependencias ya
  declaradas, incluida `fakeredis`. Se documentaron las cuentas y comandos de
  desarrollo en `README.md`.
- **Motivo**: el backend estaba en `Restarting (1)` y no podía ejecutar migraciones
  ni atender requests por el `ImportError` de DRF. El chequeo confirmó luego los
  servicios, la BD, el login, el envío de email y los 56 tests backend.
- **Archivos**: `backend/filmai/settings.py`, `README.md`, `docs/decisiones.md`.

## 26/08/2026 — Fix decodificación de parámetros en rutas dinámicas (useParams en Next.js)

- **Descripción**: se solucionó el fallo en la verificación de correo (`/confirmar-correo/[key]`) y restablecimiento de contraseña (`/restablecer-contrasena/[uid]/[token]`):
  1. `useParams()` de Next.js (App Router) retorna los segmentos de ruta URL-encoded.
  2. Las keys generadas por allauth (`signing.dumps`) contienen dos puntos (`:`) para separar payload, timestamp y firma HMAC (ej. `MjU:1wzFi6:sZEa...`).
  3. Al llegar a la página vía URL, `useParams()` devolvía la clave con `%3A` en vez de `:` (ej. `MjU%3A1wzFi6%3A...`). Al enviarla en el payload JSON a `/api/auth/registration/verify-email/`, `django.core.signing.loads` fallaba con `BadSignature: No ":" found in value`, respondiendo `400 {"codigo": "invalido"}`.
  4. Se aplicó `decodeURIComponent()` sobre los parámetros extraídos de `useParams` en `confirmar-correo/[key]/page.tsx` y `restablecer-contrasena/[uid]/[token]/page.tsx`.
- **Motivo**: corregir el error donde los enlaces de correo informaban "No se pudo confirmar" / "El enlace es inválido".
- **Archivos**: `frontend/app/confirmar-correo/[key]/page.tsx`, `frontend/app/restablecer-contrasena/[uid]/[token]/page.tsx`, `docs/decisiones.md`.

## 26/08/2026 — Cierre de gaps Fundación/Auth: keywords, navbar, A-09, bcrypt, Shadcn

- **Descripción**: se cerraron gaps detectados al comparar el código con docs 01–05:
  1. **`keywords` en `ProduccionAudiovisual`**: se agrega `ArrayField` (VARCHAR[])
     para keywords temáticos de TMDB (`/movie/{id}/keywords`, `/tv/{id}/keywords`).
     Queda vacío hasta C-04; se adelanta para no migrar después. Alimenta el texto
     a embeber de B-06 (`Title + Genres + Directors + Cast + Keywords + Synopsis`).
  2. **A-09 (middleware JWT) — opción B**: el middleware de Next.js solo comprueba
     presencia de la cookie `access` para redirigir a `/login`. La verificación
     real (firma, expiración, blacklist) queda en el backend
     (`JWTCookieAuthentication` + `IsAuthenticated`). Evita compartir
     `SECRET_KEY` con el frontend y duplicar lógica de auth.
  3. **bcrypt confirmado**: `PASSWORD_HASHERS` ya usa
     `BCryptSHA256PasswordHasher` y `bcrypt>=4.0` está en `requirements.txt`
     (RNF #2 cumplido). Sin cambio de código.
  4. **Shadcn sobre `@base-ui/react`**: desviación de F-03 (el plan decía
     shadcn/ui sobre Radix). El `components.json` usa `style: "base-nova"` y
     `@base-ui/react`. Se documenta para no romper expectativas en PRs futuros.
     Hoy solo está construido `components/ui/button.tsx`.
  5. **Navbar completa (doc 04 §4)**: links Inicio / Buscar / Listas + dropdown
     Mi perfil / Mis reseñas / Preferencias / Cerrar sesión. Las opciones aún
     no implementadas muestran toast `"Todavía no está implementado"`. Logo
     apunta a `/inicio`. Landing: CTA "Explorar catálogo" navega a `/inicio`
     (ya no `/catalogo`).
  6. **AGENTS.md §4**: los agentes deben correr `ruff format/check` y
     `prettier --check` antes de dar el OK.
- **Motivo**: auditoría end-to-end vs docs 01–05; el usuario confirmó opción B
  para A-09 y pidió adelantar `keywords`, completar la navbar visualmente y
  dejar el formateo como gate de entrega.
- **Archivos**: `backend/catalogo/models.py`,
  `backend/catalogo/migrations/0003_produccionaudiovisual_keywords.py`,
  `frontend/components/Navbar.tsx`, `frontend/app/(public)/page.tsx`,
  `docs/05_Plan_de_Desarrollo.md` (A-09), `AGENTS.md`.

## 26/08/2026 — Fix login Google vs registro + access token solo en cookie httpOnly

- **Descripción**: tres correcciones al flujo de autenticación:
  1. **Login con cuenta de Google existente (bug raíz)**: en
     `GoogleSocialLoginSerializer.validate`, el chequeo `if not
login.is_existing:` corría ANTES de `complete_social_login()`, que es donde
     allauth ejecuta el `lookup()`. Como `is_existing` es una property que
     devuelve `False` hasta ese lookup, SIEMPRE entraba a la rama de "cuenta
     nueva" y, al no recibir `nombre_usuario`/`fecha_nacimiento`/`genero` en el
     login, respondía 400 → el frontend mandaba a `/completar-google` incluso a
     cuentas ya vinculadas. Ahora se consulta `SocialAccount.objects.filter(
provider, uid).exists()` (mismo criterio que el `_lookup_by_socialaccount`
     interno de allauth) ANTES del chequeo: si existe, es login y no se exigen
     los campos extra.
  2. **Check de email duplicado muerto**: en el segundo `if not
login.is_existing`, `getattr(login.user, "email", None)` usaba `email`,
     pero el modelo expone `correo`; el chequeo nunca aplicaba. Corregido a
     `correo`.
  3. **Access token fuera de localStorage**: el frontend ya no persiste el
     access token en `localStorage` (superficie XSS). El backend autentica vía
     cookie httpOnly (`JWTCookieAuthentication` ya era el auth class por
     defecto) y el `Authorization: Bearer` desde localStorage era redundante. Se
     eliminaron `getAccessToken`/`storeTokens`/`clearTokens` y la opción `auth`
     de `apiFetch`; las cookies viajan con `credentials: "include"`.
- **Motivo**: corregir el bug reportado (iniciar sesión con Google mandaba a la
  pantalla de registro) y endurecer el manejo de tokens (el refresh ya estaba
  fuera de localStorage; ahora el access también).
- **Archivos**: `backend/usuarios/serializers.py`, `backend/usuarios/tests.py`
  (regresión: login de cuenta existente sin campos + cuenta nueva exige campos),
  `frontend/lib/api.ts`, `frontend/lib/google-auth.ts`,
  `frontend/app/(public)/login/page.tsx`,
  `frontend/app/(public)/register/page.tsx`,
  `frontend/app/confirmar-correo/[key]/page.tsx`,
  `frontend/app/restablecer-contrasena/[uid]/[token]/page.tsx`,
  `frontend/components/Navbar.tsx`.

## 26/08/2026 — CSRF para el access token en cookie httpOnly (JWT_AUTH_COOKIE_USE_CSRF)

- **Descripción**: al quedar el access token solo en cookie httpOnly (sin header
  Bearer), se habilitó protección CSRF explícita en lugar de descansar solo en
  `SameSite=Lax`:
  1. `JWT_AUTH_COOKIE_USE_CSRF=True`: `JWTCookieAuthentication` exige el header
     `X-CSRFToken` en las mutaciones autenticadas por la cookie `access` (los
     métodos seguros GET/HEAD/OPTIONS quedan exentos).
  2. `CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS`: el frontend es otro origen
     (localhost:3000), así que Django valida el `Origin` cross-origin contra
     estos orígenes; sin esto, cualquier mutación legítima se rechazaba con
     "Referer checking failed".
  3. Endpoint `GET /api/auth/csrf/` (`CSRFTokenView` + `ensure_csrf_cookie`):
     setea la cookie `csrftoken` (legible por JS) para que el frontend la
     reenvíe como header.
  4. Frontend: `apiFetch` lee la cookie `csrftoken` (o la pide al endpoint si
     aún no existe) y manda `X-CSRFToken` en toda mutación. Relee la cookie en
     cada request, por lo que la rotación del token tras el login (dj-rest-auth
     hace `django_login` con `SESSION_LOGIN=True`, que llama `rotate_token`) es
     transparente.
- **Motivo**: resolver el pendiente del tradeoff XSS/CSRF: con cookie httpOnly la
  protección CSRF ahora valida el token en cada mutación y no solo confía en el
  `SameSite` de la cookie.
- **Archivos**: `backend/filmai/settings.py`, `backend/usuarios/views.py`
  (`CSRFTokenView`), `backend/filmai/urls.py`, `backend/usuarios/tests.py`
  (`CsrfCookieTests`, 2 casos), `frontend/lib/api.ts`.

## 26/08/2026 — Google OAuth: login abre el selector y registro completa datos (flujos distintos)

- **Descripción**: se separan los dos flujos de Google. El botón de LOGIN
  ("Iniciar sesión con Google", `GoogleButton text="signin_with"`) abre el
  selector de cuentas de Google directamente; si la cuenta ya existe entra
  directo, y si es nueva se deriva a `/completar-google`. El botón de REGISTRO
  ("Crear cuenta con Google", `GoogleLinkButton`) no abre Google: marca el
  flujo pendiente (`google_signup_pending`) y navega a `/completar-google`,
  donde se completan los datos faltantes y se toca el botón de Google
  (`signup_with`) — un único popup en todo el flujo de registro. Se elimina el
  texto que explicaba el motivo de los tokens (no aporta al usuario final).
- **Motivo**: UX — dos situaciones distintas: iniciar sesión (abrir el
  selector) vs crear cuenta (completar datos + elegir cuenta una sola vez).
- **Archivos**: `frontend/components/GoogleLinkButton.tsx` (nuevo),
  `frontend/app/(public)/login/page.tsx`,
  `frontend/app/(public)/register/page.tsx`,
  `frontend/app/completar-google/page.tsx`, `frontend/lib/google-auth.ts`.

## 26/08/2026 — Fix del id_token de un solo uso en el flujo Google de 2 pasos

- **Descripción**: tras corregir el 500 (RawPostDataException), el flujo de
  completado de cuenta Google fallaba con `400 "No se pudo autenticar con
Google."` en el segundo POST. Causa: el `id_token` de Google es de UN SOLO
  USO — allauth implementa anti-replay (`verify_jti` en
  `allauth.socialaccount.internal.jwtkit`): la primera verificación marca el
  `jti` del token en caché y cualquier reenvío del mismo token lanza
  `OAuth2Error("token already used")`. El frontend reutilizaba el mismo
  id_token (guardado en `sessionStorage`) para el paso de completado.
- **Decisión (Opción 1)**: obtener un id_token FRESCO en la pantalla de
  completado mediante re-autenticación con Google. El frontend ya no guarda ni
  reutiliza el token: guarda solo un marcador (`google_signup_pending`) para
  proteger la ruta, y `/completar-google` pide un token nuevo (botón Google con
  `text="signup_with"` para distinguirlo del de login). Se mantiene intacta la
  garantía anti-replay de allauth.
- **Archivos**: `frontend/lib/google-auth.ts`,
  `frontend/app/completar-google/page.tsx`, `frontend/components/GoogleButton.tsx`.

## 26/08/2026 — Fix del 500 en Google OAuth: no releer `request.body` en `populate_user`

- **Descripción**: el login con Google (`POST /api/auth/google/`) respondía 500
  con `django.http.request.RawPostDataException: You cannot access body after
reading from request's data stream`. En un view de DRF, `self.request.data`
  consume el stream del body al parsear el JSON; luego
  `UsuarioSocialAccountAdapter.populate_user` releía `request.body` para obtener
  los campos que Google no provee (`nombre_usuario`, `fecha_nacimiento`,
  `genero`), lo que lanzaba la excepción y derivaba en 500.
- **Solución**: esos campos ahora viajan pegados al request
  (`request.google_extra`), seteado por `GoogleSocialLoginSerializer.validate`
  desde los `attrs` ya validados antes de llamar a `complete_login`. El adapter
  los lee con `getattr(request, "google_extra", {})` y ya no toca el body.
  Se eliminó el helper `_extra_from_body`.
- **Archivos**: `backend/usuarios/serializers.py`,
  `backend/usuarios/adapter.py`, `backend/usuarios/tests.py` (regresión:
  `GoogleOAuthTests`).

## 25/08/2026 — Pendientes de revisión del PR #3 de autenticación

- **Descripción**: durante la revisión del PR #3 se identificaron los siguientes
  pendientes para notificar a su autor:
  - El frontend almacena el access token, pero no implementa la renovación
    automática mediante el refresh token cuando aquel expira.
  - El parseo inicial del `id_token` de Google queda fuera del manejo de
    excepciones y podría responder con un error 500 ante un token malformado.
  - La validación de nombres de usuario usa comparación insensible a mayúsculas,
    pero la restricción `unique=True` de la base de datos no garantiza esa misma
    unicidad en condiciones de carrera.
  - Las rutas de confirmación de correo, completado de Google y restablecimiento
    de contraseña no están incluidas entre las pantallas sin Navbar.
  - `.env.example` deja Resend como backend activo con valores incompletos; al
    copiarlo sin configurar la API key, el registro puede informar que envió el
    correo aunque el backend no lo entregue.
- **Motivo**: dejar documentados los riesgos y las diferencias detectadas entre
  el comportamiento implementado y los criterios de autenticación, seguridad y
  UI antes de continuar con el desarrollo. Estos puntos quedan como pendientes,
  no como decisiones cerradas.
- **Archivos**: `frontend/lib/api.ts`, `backend/usuarios/serializers.py`,
  `backend/usuarios/models.py`, `frontend/components/Navbar.tsx`, `.env.example`,
  `docs/05_Plan_de_Desarrollo.md`, `docs/04_Lineamientos_UI.md`.

## 25/08/2026 — Limpieza de `storeTokens` (quitar parámetro `refresh`)

- **Descripción**: se eliminó el parámetro `refresh` de `storeTokens` en el
  frontend (`storeTokens(access)`), y se actualizaron sus tres llamadores (login
  por email/contraseña, login con Google y completado de cuenta Google). También
  se reformateó `Navbar.tsx` con Prettier (una línea JSX demasiado larga).
- **Motivo**: el refresh token ya viaja como cookie httpOnly y no se persiste en
  el cliente (ver decisión del 22/08/2026); el parámetro `_refresh` era un
  remanente sin uso que generaba un warning de ESLint (`--max-warnings=0`) y
  bloqueaba el hook de pre-commit de husky para cualquier commit.
- **Archivos**: `frontend/lib/api.ts`, `frontend/lib/google-auth.ts`,
  `frontend/app/(public)/login/page.tsx`,
  `frontend/app/completar-google/page.tsx`, `frontend/components/Navbar.tsx`.

## 25/08/2026 — El lint solo corre en local; pendiente agregar CI

- **Descripción**: un warning de ESLint (`_refresh` sin uso en `storeTokens`)
  entró a `main` porque el commit que lo introdujo (`2cc3ffe`) se integró vía
  "Merge pull request" desde GitHub, que no ejecuta el hook local de husky, y el
  repo no tiene CI (no hay `.github/workflows/`). El hook de pre-commit corre en
  toda rama pero solo en la máquina de cada dev (depende de husky instalado y
  `node_modules` sincronizado), y además saltea `ruff` si Docker no está
  levantado.
- **Motivo**: documentar la causa y dejar registrada la tarea pendiente de
  agregar CI para enforzar lint/format independientemente de la máquina de cada
  integrante.
- **Tarea pendiente (asignada a Gonza)**: crear un workflow de GitHub Actions
  que corra `eslint` + `prettier` (frontend) y `ruff` (backend) en cada PR a
  `main`.
- **Archivos**: `.husky/pre-commit`, `frontend/eslint.config.mjs`,
  `frontend/.prettierrc`. Pendiente: `.github/workflows/`.

## 25/08/2026 — Arquitectura híbrida del catálogo (TMDB + PostgreSQL)

- **Descripción**: el Módulo 2 (Catálogo) adopta un modelo híbrido. El
  descubrimiento (trending, discover, search) se sirve en vivo desde la API de
  TMDB con caché Redis; PostgreSQL es la fuente de verdad para los datos del
  usuario (calificaciones, reseñas, listas) y para la búsqueda semántica
  (pgvector). No se adopta una variante "BD como única fuente" porque
  sincronizar todo TMDB no escala y rompería la búsqueda en vivo de títulos no
  sincronizados.
- **Motivo**: el plan ya describe ambos mecanismos (C-03 en vivo + C-04 sync);
  se explicita para evitar interpretar que la BD reemplaza a TMDB en discovery.
- **Archivos**: `docs/05_Plan_de_Desarrollo.md`, `backend/catalogo/`.

## 25/08/2026 — Materialización on-demand con unicidad compuesta

- **Descripción**: cuando el usuario abre el detalle o interactúa con una
  producción, ésta se materializa en `ProduccionAudiovisual` mediante un helper
  centralizado (`catalogo/services/materialization.py`). La búsqueda se hace por
  `id_tmdb` + `tipo`; la creación es atómica y, ante `IntegrityError` por
  concurrencia, se resuelve con un `get()` posterior. No se ejecutan llamadas
  externas (TMDB/embeddings) dentro de una transacción abierta.
- **Motivo**: `id_tmdb` no es único entre películas y series; la unicidad real
  es compuesta `(id_tmdb, tipo)` (ya definida como `uq_produccion_tmdb_tipo`).
  Esto permite calificar o listar una producción encontrada por búsqueda aunque
  la sync diaria nunca la haya traído.
- **Archivos**: `backend/catalogo/models.py`, `backend/catalogo/services/`.

## 25/08/2026 — Embeddings síncronos en la materialización (adelanto parcial de B-06)

- **Descripción**: el embedding se genera de forma síncrona dentro del helper
  de materialización, después de persistir la producción. Si el proveedor de
  embeddings falla, la producción queda creada con `embedding IS NULL` y el
  backfill (C-04b) la completa después. Se registran `content_hash` y la versión
  del modelo para no recomputar embeddings innecesarios.
- **Motivo**: una producción materializada on-demand en Fase 1 quedaría sin
  embedding hasta el cron si no se genera acá, y entonces no aparecería en
  búsquedas semánticas. El costo es una llamada adicional similar a la de TMDB.
- **Implicación**: adelanta infraestructura de B-06 (pgvector,
  `ProduccionEmbedding`, servicio de embeddings y proveedor BGE-M3/Ollama).
- **Archivos**: `backend/catalogo/`, `docker-compose.yml`,
  `docs/05_Plan_de_Desarrollo.md`.

## 25/08/2026 — División de C-04 y caché Redis en todos los entornos

- **Descripción**: C-04 se divide en C-04a (Fase 1: materialización +
  embeddings) y C-04b (Fase 3: Celery para backfill, mantenimiento del catálogo
  popular, regeneración ante cambio de modelo y red de seguridad
  `embedding IS NULL`). La caché de TMDB usará Redis también en desarrollo (no
  LocMem) para probar el mismo comportamiento que en producción. El sync
  actualizará únicamente campos provenientes de TMDB, sin pisar metadatos
  locales.
- **Motivo**: desacoplar el funcionamiento del catálogo de la dependencia del
  cron; que la sync pase a ser mantenimiento y no un prerrequisito.
- **Archivos**: `docs/05_Plan_de_Desarrollo.md`, `backend/filmai/settings.py`,
  `backend/catalogo/`.

## 22/08/2026 — Datepicker de fecha de nacimiento: máximo hoy −13 años

- **Descripción**: los inputs `type="date"` de fecha de nacimiento (registro
  tradicional y completado de Google) definen `max` como la fecha de hoy menos
  13 años. Esto brinda feedback visual inmediato al usuario, impidiendo
  seleccionar fechas que el backend rechazaría. La validación backend
  (`validate_fecha_nacimiento` en `serializers.py`) sigue siendo la enforcement
  definitiva.
- **Motivo**: mejorar la UX del datepicker sin duplicar lógica de negocio;
  el navegador grisará las fechas no elegibles.
- **Archivos**: `frontend/app/(public)/register/page.tsx`,
  `frontend/app/completar-google/page.tsx`.

## 22/08/2026 — JWT_AUTH_SECURE derivado del entorno; JWTCookieAuthentication

- **Descripción**: `JWT_AUTH_SECURE` ahora se lee de la variable de entorno
  (default `True`); en desarrollo local se puede setear `False` en `.env`.
  Además, se reemplazó `JWTAuthentication` de simplejwt por
  `JWTCookieAuthentication` de dj-rest-auth para soportar autenticación tanto
  por header Bearer como por la cookie httpOnly `access`.
- **Motivo**: seguridad en producción (cookies Secure) y compatibilidad con
  el flujo de cookies httpOnly que ya usa dj-rest-auth.
- **Archivos**: `backend/filmai/settings.py`.

## 22/08/2026 — Registro de Usuario en Django Admin

- **Descripción**: se registró `usuarios.Usuario` en `admin.py` con un
  `UsuarioAdmin` personalizado que adapta los fieldsets de `UserAdmin` a los
  campos del modelo (`correo`, `nombre_usuario`, `nombre`, `apellido`, etc.).
- **Motivo**: permitir la gestión de usuarios desde el panel de administración
  de Django (Módulo 6); el archivo estaba vacío y el modelo no aparecía.
- **Archivos**: `backend/usuarios/admin.py`.

## 22/08/2026 — transaction.atomic en señal de aprovisionamiento

- **Descripción**: el handler `crear_recursos_por_defecto` (señal `post_save`
  de `Usuario`) ahora envuelve la creación de listas y chat en
  `transaction.atomic()`, de modo que un fallo en cualquier escritura revierte
  todas las creaciones parciales.
- **Motivo**: garantizar consistencia: si la creación del Chat falla, las
  listas tampoco se persisten.
- **Archivos**: `backend/usuarios/signals.py`.

## 22/08/2026 — Validación de campos Google antes de complete_social_login

- **Descripción**: en `GoogleSocialLoginSerializer.validate`, la validación de
  `CAMPOS_FALTANTES_GOOGLE` ahora se ejecuta antes de `complete_social_login`
  para evitar que allauth persista un usuario incompleto cuando faltan
  `nombre_usuario`, `fecha_nacimiento` o `genero`.
- **Motivo**: prevenir usuarios huérfanos en la BD cuando la pantalla de
  completación aún no envió los campos faltantes.
- **Archivos**: `backend/usuarios/serializers.py`.

## 22/08/2026 — Refresh token fuera de localStorage

- **Descripción**: `storeTokens` del frontend ya no persiste el refresh token
  en localStorage; el refresh token viaja exclusivamente como cookie httpOnly
  seteada por el backend (`JWT_AUTH_HTTPONLY: True`). Se eliminó
  `getRefreshToken` y `REFRESH_KEY`.
- **Motivo**: reducir la superficie de ataque XSS; el refresh token solo debe
  ser accesible por el navegador (cookie httpOnly), no por JavaScript.
- **Archivos**: `frontend/lib/api.ts`.

## 22/08/2026 — Fecha de nacimiento con datepicker nativo

- **Descripción**: el campo "Fecha de nacimiento" (registro tradicional y
  completado de Google) usa el input HTML nativo `type="date"`, que valida
  automáticamente y envía el valor en ISO `YYYY-MM-DD` (el backend ya acepta
  `%Y-%m-%d` y `%d/%m/%Y`). El orden de visualización lo decide el locale del
  navegador (mm/dd/aaaa en en-US, dd/mm/aaaa en es-ES).
- **Motivo**: evitar la validación manual de texto libre y sus dolores de
  cabeza; el datepicker nativo ya la hace. Se acepta la variación visual por
  locale a cambio de validación automática.
- **Archivos**: `frontend/app/(public)/register/page.tsx`,
  `frontend/app/completar-google/page.tsx`,
  `docs/02_Especificación de Requerimientos.md`, `docs/04_Lineamientos_UI.md`.

## 22/08/2026 — Adopción de dj-rest-auth + django-allauth para autenticación

- **Descripción**: Se adoptó `dj-rest-auth` + `django-allauth` como stack de
  autenticación, cubriendo tanto el registro tradicional (email + contraseña)
  como el inicio de sesión con Google OAuth (proveedor `socialaccount` de
  allauth, expuesto vía `dj-rest-auth`). La confirmación de cuenta utiliza el
  token de confirmación de email propio de allauth (no un JWT de un solo uso).
- **Referencia**: [django-allauth](https://docs.allauth.org/en/dev/index.html).
- **Motivo**: No reinventar el intercambio de tokens OAuth ni la verificación
  de email; aprovechar librerías mantenidas y estándar para SPA + JWT.
- **Decisiones asociadas**:
  - **bcrypt** como hasher (`PASSWORD_HASHERS` con `BCryptSHA256PasswordHasher`
    - dependencia `bcrypt`); cumple RNF #2 / RNF #12.
  - **`is_active` (Opción A1)**: propiedad derivada de `estado` (getter
    `estado == ACTIVA`) con _setter_ (`True → estado = ACTIVA`, `False` =
    no-op). Se elimina la columna huérfana `is_active` de la BD. `estado`
    (PENDIENTE/ACTIVA/BAJA) es la única fuente de verdad.
  - **Usuario Google nuevo**: `estado = ACTIVA` directo (Google ya verifica el
    email, sin confirmación por correo) + pantalla intermedia de UI para
    completar `nombre_usuario`, `fecha_nacimiento` y `genero` (campos que
    Google no provee). `google_id` se mantiene y se sincroniza desde
    `SocialAccount.uid`.
- **Archivos afectados**: `docs/05_Plan_de_Desarrollo.md` (A-01..A-08),
  `docs/04_Lineamientos_UI.md`, `docs/03_Modelos de Datos y de Diseño.md`,
  `docs/02_Especificación de Requerimientos.md` (CU-002); pendientes de
  implementación: `backend/usuarios/models.py`, `backend/filmai/settings.py`,
  `backend/requirements.txt`.

## 22/08/2026 — Carácter `!` permitido en la contraseña

- **Descripción**: Se amplió el conjunto de caracteres especiales válidos de la
  contraseña (CU-001) para incluir `!`: ahora es `@#$%&*!`. Se actualizó el
  validador (`usuarios/validators.py`) y la documentación (docs/02, docs/04 y
  el wireframe).
- **Motivo**: `!` es un carácter especial de uso común y el password de seed
  (`Password123!`) ya lo usaba; se unifica para coherencia entre validación,
  documentación y datos de desarrollo.
- **Archivos**: `backend/usuarios/validators.py`,
  `docs/02_Especificación de Requerimientos.md`,
  `docs/04_Lineamientos_UI.md`, `docs/wireframes/Opcion 1/app.html`.

## 18/08/2026 — Renombrado completo de la aplicación: FilmIA → FilmAI

- **Descripción**: Se realizó un análisis end-to-end del repositorio para
  reemplazar todas las ocurrencias del nombre incorrecto "FilmIA" por el
  nombre oficial "FilmAI". El cambio afectó tanto el nombre visible de la
  marca como los identificadores técnicos internos (`filmia` → `filmai`).
- **Motivo**: El nombre correcto y definitivo de la aplicación es "FilmAI"
  (con la sigla AI en mayúsculas, haciendo referencia a Artificial Intelligence).
  "FilmIA" era un error de escritura que se había propagado en todo el proyecto.
- **Archivos afectados**:
  - `README.md`, `AGENTS.md`, `.gitignore`, `.env.example`
  - `.husky/pre-commit`
  - `docker-compose.yml` (header, container names: `filmai_db`, `filmai_redis`,
    `filmai_backend`, `filmai_frontend`; red: `filmai_network`)
  - `backend/filmia/` → renombrado a `backend/filmai/` (módulo Django)
  - `backend/filmai/settings.py`, `asgi.py`, `wsgi.py`, `urls.py`
  - `backend/manage.py`, `backend/Dockerfile`, `backend/entrypoint.sh`
  - `backend/pyproject.toml`, `backend/requirements.txt`
  - `backend/usuarios/models.py`, `factories.py`,
    `management/commands/seed.py`
  - `frontend/Dockerfile`, `frontend/app/layout.tsx`,
    `frontend/app/globals.css`, `frontend/app/(public)/page.tsx`
  - `docs/decisiones.md`, `docs/01_Presentación...`, `docs/03_Modelos...`,
    `docs/04_Lineamientos_UI.md`, `docs/05_Plan_de_Desarrollo.md`,
    `docs/06_TMDB_API_Referencia.md`
  - `docs/wireframes/Opcion 1/app.html`
- **Nota**: Las variables de entorno de PostgreSQL (`POSTGRES_DB=filmai_dev`,
  `POSTGRES_USER=filmai_user`) y los emails ficticios de prueba
  (`@filmai.com`) también fueron actualizados para mantener coherencia.
  Si ya existe un volumen Docker con datos de desarrollo bajo el nombre
  anterior, es necesario recrearlo (`docker compose down -v`).

## 13/08/2026 — Unificación de Persona/Usuario/Administrador en un único `Usuario`

- **Descripción**: Se eliminaron las entidades `Persona` y `Administrador`.
  El modelo quedó con una única entidad `Usuario` que es el `AUTH_USER_MODEL`
  de Django, heredando de `AbstractBaseUser` + `PermissionsMixin`. Sus campos
  de identidad (`nombreUsuario`, `correo`, `contraseña`, `googleId`) se absorben
  en `Usuario`.
- **Motivo**: La gestión de administradores se realiza a través del Django Admin
  nativo (Módulo 6), que usa flags `is_staff`/`is_superuser` y no una entidad
  separada. La herencia multi-tabla era especulativa (una sola subclase) y
  chocaba con el `AUTH_USER_MODEL`.
- **Archivos**: `backend/usuarios/models.py`, `backend/filmai/settings.py`,
  `backend/entrypoint.sh`.

## 13/08/2026 — `estado` como fuente única de verdad del ciclo de vida

- **Descripción**: `is_active` dejó de ser un campo de BD; ahora es una propiedad
  derivada de `estado` (`is_active` es `True` solo si `estado == Activa`).
- **Motivo**: evitar una doble fuente de verdad; `estado` representa el ciclo
  completo pendiente → activa → baja (CU-001, CU-002, CU-007).
- **Archivos**: `backend/usuarios/models.py`.

## 13/08/2026 — `contraseña` VARCHAR(50) → VARCHAR(128)

- **Descripción**: el hash de bcrypt mide 60+ caracteres; el campo se amplió a
  128 caracteres (coherente con RNF #2).
- **Archivos**: `backend/usuarios/models.py` (campo `password` heredado de
  `AbstractBaseUser`), `docs/03_DiagramaClases_DiagramaTablas.json`,
  `docs/03_Modelos de Datos y de Diseño.md`.

## 13/08/2026 — `Mensaje.texto` VARCHAR(250) → TextField

- **Descripción**: una respuesta del LLM puede superar 250 caracteres; se usa
  `TextField` para no truncar el contenido.
- **Motivo**: el límite VARCHAR(250) del diagrama de tablas no era adecuado
  para respuestas conversacionales del chatbot.
- **Archivos**: `backend/chatbot/models.py`.

## 13/08/2026 — Unicidades añadidas (integridad a nivel BD)

- **Descripción**: se añadieron restricciones de unicidad compuestas exigidas
  por los casos de uso, aunque no estuvieran explícitas en el diagrama:
  - `(idTMDB, tipo)` en `ProduccionAudiovisual` — los IDs de TMDB no son únicos
    entre películas y series.
  - `(usuario, produccion)` en `Calificacion` — una calificación por usuario y producción.
  - `(usuario, nombre)` en `Lista` — nombre de lista único por usuario.
  - `(lista, produccion)` en `Tiene` — PK compuesta del diagrama (no duplicar ítem).
- **Motivo**: integridad referencial a nivel de base de datos (última línea de defensa).
- **Archivos**: `backend/catalogo/models.py`, `backend/listas/models.py`.

## 13/08/2026 — Nombres camelCase → snake_case

- **Descripción**: los nombres de atributos del diagrama (camelCase, ej.
  `nombreUsuario`, `fechaNacimiento`) se normalizaron a snake_case en el código
  (`nombre_usuario`, `fecha_nacimiento`) por convención de Django/Python.
- **Archivos**: todos los `models.py`.

## 13/08/2026 — `Reseña` → `Calificacion` modelada como OneToOne

- **Descripción**: la composición "una calificación tiene 0..1 reseña" se modeló
  con `OneToOneField` (no FK simple), según el diagrama de clases.
- **Archivos**: `backend/catalogo/models.py`.

## 18/08/2026 — Seeds de desarrollo con factory_boy (F-05)

- **Descripción**: se implementó el comando `python manage.py seed` que puebla
  la BD con datos consistentes para desarrollar la UI: 3 usuarios de prueba
  (contraseña común `Password123!`), 50 producciones (25 películas + 25 series),
  calificaciones y reseñas asociadas, listas predeterminadas (Favoritos,
  Pendientes, Vistas) + personalizadas, y un chat con mensajes por usuario.
  El comando es **destructivo e idempotente**: borra los datos de las apps de
  negocio y los recrea en cada ejecución.
- **Motivo**: facilitar el desarrollo de la UI (Módulos 2-5) sin depender de la
  API de TMDB ni de datos reales.
- **Archivos**: `backend/usuarios/factories.py`, `backend/catalogo/factories.py`,
  `backend/listas/factories.py`, `backend/chatbot/factories.py`,
  `backend/usuarios/management/commands/seed.py` (+ `management/__init__.py`).
- **Convención**: los factories viven en `factories.py` dentro de cada app; el
  comando `seed` vive en `usuarios/management/commands/` (no hay app `core`).
  El password se aplica vía `create_user` (override de `_create` en el factory)
  para que quede hasheado.

## 18/08/2026 — Reset de BD por InconsistentMigrationHistory

- **Descripción**: al intentar `migrate` con el `AUTH_USER_MODEL` custom ya
  declarado, Django lanzó `InconsistentMigrationHistory` porque `auth`/`admin`
  estaban aplicadas sobre el `User` por defecto (migradas antes del F-04) pero
  sus dependencias swappable (`usuarios.0001_initial`) no. Se resolvió con un
  reset del schema (`DROP SCHEMA public CASCADE; CREATE SCHEMA public;`) y
  re-migración limpia. La BD no tenía datos de negocio (solo el superuser
  auto-generado por `entrypoint.sh`, que se recrea al reiniciar el contenedor).
- **Motivo**: documentar el gotcha para futuros resets/migraciones del entorno
  de desarrollo.
- **Archivos**: ninguno (operación de base de datos).

## 18/08/2026 — Ruff como linter + formatter único (F-06)

- **Descripción**: se configuró Ruff como linter **y** formatter (`ruff check` +
  `ruff format`) en `backend/pyproject.toml`. `ruff format` reemplaza a `black`
  (compatible: line-length 88, doble comilla). Config: `target-version = py312`,
  `exclude = ["*/migrations/*"]`, `per-file-ignores` de `RUF012` en `models.py`
  (falso positivo de Django: `ordering`, `constraints` y `REQUIRED_FIELDS` son
  metadatos, no defaults mutables). Se omitió `E501`: la longitud la controla
  el formatter, no el linter.
- **Motivo**: el plan F-06 pedía "ruff o flake8 + black". Se usó el formatter de
  Ruff en lugar de instalar `black` por separado (ya venía con ruff, es drop-in
  compatible y evita una dependencia redundante).
- **Archivos**: `backend/pyproject.toml` + reformateo de los `models.py`,
  `settings.py`, `manage.py`, `admin.py`/`apps.py`/`tests.py`/`views.py`
  (quita imports sin usar) y los `factories.py`.

## 18/08/2026 — Arquitectura de retrieval del chatbot: tool calling + pgvector + BGE-M3

- **Descripción**: se definió la arquitectura de retrieval del chatbot (Módulo 5)
  para desarrollo posterior. Consta de tres decisiones:
  1. **Tool calling obligatorio** (no se embebe el contexto del usuario): el LLM
     recibe herramientas `buscar_por_titulo`, `top_por_genero`, `similares_a`
     (TMDB) y `buscar_semantico` (pgvector). El historial de gustos del usuario
     (calificaciones, reseñas, vistas) se obtiene por SQL y se inyecta
     anonimizado al prompt (B-05), sin pasar por ningún vector store.
  2. **Embeddings locales con BGE-M3 vía Ollama** (gratis, cross-lingual): el
     corpus (sinopsis de TMDB) está en inglés pero el usuario consulta en
     español, por lo que se necesita un modelo multilingüe. Se descarta
     `nomic-embed-text` por ser monolingüe (inglés).
  3. **pgvector sobre el PostgreSQL 16 existente**: imagen
     `pgvector/pgvector:pg16-alpine`, `CREATE EXTENSION vector`, vector(1024),
     índice HNSW.
- **Texto a embebear** (plantilla en inglés con labels):
  `Title + Genres + Directors + Cast + Keywords + Synopsis`. Los campos
  cuantitativos (`calificacion_promedio`, `fecha_lanzamiento`, `duracion`,
  `tipo`, `estatus`) **no** van al vector: se aplican como filtros SQL
  post-recuperación.
- **Cambios de modelo asociados**: nuevo campo `keywords` (ArrayField) en
  `ProduccionAudiovisual` sincronizado desde TMDB en C-04
  (`/movie/{id}/keywords`, `/tv/{id}/keywords`); nuevo modelo
  `ProduccionEmbedding` (FK + `VectorField(1024)` + índice HNSW).
- **Motivo**: personalización basada en historial sin pagar por embeddings ni
  exponer datos del usuario; consultas conceptuales sobre el catálogo que TMDB
  `discover` no expresa; grounding contra datos reales para evitar
  alucinaciones del LLM.
- **Archivos**: `docs/05_Plan_de_Desarrollo.md` (Módulo 5, C-01, C-04),
  `docs/06_TMDB_API_Referencia.md` (nuevo), futuros: `docker-compose.yml`
  (servicio `ollama`), `backend/requirements.txt` (`httpx`, `pgvector`,
  `django-pgvector`), `backend/catalogo/models.py`.

## 18/08/2026 — Documento de referencia de la API de TMDB

- **Descripción**: se creó `docs/06_TMDB_API_Referencia.md` con el listado
  completo de endpoints de TMDB API v3 (base URL, autenticación, secciones y
  notas de uso para el tool calling del chatbot). Sirve como referencia rápida
  para implementar `TMDBClient` (C-01) y las herramientas del LLM.
- **Motivo**: tener a mano y de forma consultable qué expone la API externa
  integrada (RNF #14) al momento de implementar catálogo y chatbot.
- **Archivos**: `docs/06_TMDB_API_Referencia.md`.

## 18/08/2026 — Prettier + ESLint + Husky en frontend (F-06)

- **Descripción**: Prettier (`.prettierrc` + `.prettierignore`) + integración de
  `eslint-config-prettier` en `eslint.config.mjs` (flat config). Scripts `format`
  y `format:check` en `package.json`. Husky con hook `pre-commit` que corre
  backend (ruff vía `docker compose exec`) y frontend (eslint + prettier con las
  dependencias del host).
- **Motivo**: por el layout monorepo (`package.json` en `frontend/`, `.git` en la
  raíz), husky 9 exige ejecutarse desde el directorio que contiene `.git`; por
  eso `prepare = "cd .. && husky"` y el hook vive en `.husky/` (raíz).
- **Archivos**: `frontend/.prettierrc`, `frontend/.prettierignore`,
  `frontend/eslint.config.mjs`, `frontend/package.json`,
  `frontend/package-lock.json`, `.husky/pre-commit`.

## 24/08/2026 — A-04/A-05: link de recuperación solo visual, error genérico de login y endpoint de disponibilidad de username

- **Descripción**: se cerraron los criterios pendientes de A-04 y A-05 (docs/05).
  1. **"¿Olvidaste tu contraseña?" solo visual (A-04)**: el link aparece en la
     pantalla de login alineado a la derecha, sin acción asociada. El mecanismo
     completo (modal con email + "Enviar enlace", CU-020) se implementa en
     A-07, tal como lo separa el plan. El wireframe ya lo dejaba como
     placeholder (`alert('Modal: recuperar contraseña')`).
  2. **Error genérico de login**: ante cualquier fallo de login por credenciales,
     el frontend muestra el mensaje genérico "Email, usuario o contraseña
     incorrectos." en lugar del mensaje crudo del backend (docs/04:634). No
     revela si el email o el username existen.
  3. **Endpoint custom de disponibilidad de username (A-05)**:
     `GET /api/auth/username-available/?username=X` → `{"disponible": bool}`.
     dj-rest-auth no provee este chequeo; se agregó `UsernameDisponibleView`
     que valida formato (CU-001: alfanumérico 5–25, misma regex de
     `validators.py`) y unicidad insensible a mayúsculas (`iexact`, igual que
     `validate_nombre_usuario`). Formato inválido también responde
     `{"disponible": false}` para simplificar el cliente.
  4. **Validaciones inline onBlur + disponibilidad debounced (A-05)**:
     nuevo `frontend/lib/validation.ts` con las reglas de CU-001; cada campo
     valida al perder foco con mensaje inline bajo el input; el username hace
     el chequeo de disponibilidad contra el endpoint con debounce de 400 ms
     ("Verificando…" / "Disponible" / "No disponible"). Los errores de campo
     del backend (DRF `{campo: [msgs]}`) se mapean a errores inline vía
     `extraerErroresPorCampo` en `lib/api.ts`.
  - **Nota sobre nombres/apellidos**: la restricción "solo letras" se interpreta
    permitiendo espacios internos simples (nombres compuestos); sin números ni
    símbolos.
- **Motivo**: cumplir los criterios de aceptación de A-04/A-05 sin adelantar
  A-07; unificar las reglas de validación del lado cliente con las del backend.
- **Archivos**: `frontend/app/(public)/login/page.tsx`,
  `frontend/app/(public)/register/page.tsx`, `frontend/lib/api.ts`,
  `frontend/lib/validation.ts` (nuevo), `backend/usuarios/views.py`,
  `backend/usuarios/tests.py`, `backend/filmai/urls.py`.

## 24/08/2026 — Menú de avatar con solo "Cerrar sesión", navbar oculto en auth y toasts con sonner

- **Descripción**:
  1. **Menú del avatar (alcance reducido de P-07/A-08)**: el navbar
     autenticado muestra un avatar circular con las iniciales del usuario
     (nombre + apellido) que despliega un menú con el único ítem "Cerrar
     sesión" (divider + color danger). El dropdown se cierra al clickear fuera
     o presionar Escape (criterio de aceptación de P-07). Antes de cerrar la
     sesión aparece el modal de confirmación "¿Está seguro que desea cerrar
     sesión?" (CU-004 / A-08); al confirmar se llama a `dj-rest-auth`
     (`POST /api/auth/logout/`), se limpian los tokens y se redirige a Home.
     _Desviación consciente del plan_: P-07 define 4 ítems (Mi perfil, Mis
     reseñas, Preferencias, Cerrar sesión), pero esas pantallas dependen de
     P-02+ que aún no existen. Los ítems restantes se agregan cuando se
     implementen.
  2. **Navbar oculto en /login y /register**: según los wireframes de auth
     (docs/04 §5f), login y registro son pantalla completa con la caja
     centrada y el wordmark "FilmAI" DENTRO de la caja — no llevan navbar.
     Se agregó el check junto al existente para la landing ("/") y se agregó
     el wordmark a ambas cajas. Esto elimina la duplicación de opciones
     (Iniciar sesión/Registrarse) entre navbar y formulario.
  3. **Toast de bienvenida post-login (CU-003)**: se adoptó `sonner` como
     librería de toasts (estándar de shadcn; los docs ya prevén toasts en
     flujos futuros: cuenta confirmada, recuperar contraseña, guardar perfil).
     `<Toaster position="top-center">` montado en el layout raíz. Login por
     formulario y Google muestran "¡Hola de nuevo, @{usuario}!" antes de
     redirigir al Home. Destino actual: "/" (landing); cuando exista el
     catálogo (A-06) se apunta allí — docs/04:635 dice "Redirect al Home".
- **Motivo**: pedido del usuario; cumplir CU-003/CU-004 sin adelantar pantallas
  inexistentes y resolver la duplicación visual en las rutas de autenticación.
- **Archivos**: `frontend/components/Navbar.tsx`, `frontend/app/layout.tsx`,
  `frontend/app/(public)/login/page.tsx`,
  `frontend/app/(public)/register/page.tsx`, `frontend/lib/google-auth.ts`,
  `frontend/package.json`.

## 24/08/2026 — Envío de emails transaccionales vía Resend (backend de email custom)

- **Descripción**: se reemplaza el console backend por un `EMAIL_BACKEND`
  custom sobre la API HTTP de Resend para los emails de allauth/dj-rest-auth
  (confirmación de cuenta CU-002; a futuro A-07 password reset).
  1. **`filmai.email_backends.ResendBackend`**: traduce `EmailMessage` a
     `resend.Emails.send` (SDK oficial, `resend>=2.0`). Soporta texto y
     alternativa HTML (`EmailMultiAlternatives`). Los destinatarios `to`,
     `cc` y `bcc` van como campos separados (sin fusionar en `to` para no
     exponer los BCC ni cambiar la semántica de los CC). En producción, la
     ausencia de `RESEND_API_KEY` rompe el arranque (`ImproperlyConfigured`
     vía `filmai.email_validation`) en lugar de degradar el envío a un
     "éxito" silencioso.
  2. **Redirección de destinatario para testing sin dominio propio**: Resend
     solo permite enviar desde `onboarding@resend.dev` y únicamente al email
     dueño de la cuenta (403 con cualquier otro destinatario). Si
     `RESEND_TEST_RECIPIENT` está definido, TODO email saliente se redirige a
     esa dirección (solo en entornos no productivos): la confirmación de
     cualquier registro llega a esa bandeja y el link sigue siendo válido para
     la cuenta registrada. En producción (`DEBUG=False`) la variable se
     rechaza al arranque. Con dominio propio verificado: borrar la variable y
     cambiar `DEFAULT_FROM_EMAIL`.
  3. **Variables** (`.env` + `.env.example`): `EMAIL_BACKEND`,
     `RESEND_API_KEY`, `RESEND_TEST_RECIPIENT`, `DEFAULT_FROM_EMAIL`. El
     fallback a console backend solo aplica en desarrollo (sin `EMAIL_BACKEND`
     configurado); en producción el backend debe elegirse explícitamente.
  4. **Comando de prueba**: `python manage.py send_test_email [destino]`.
  5. **Logging**: `LOGGING` mínimo en settings para ver cada envío
     (id de Resend) en `docker compose logs -f backend`.
  6. Tests unitarios con mock del SDK en `filmai/tests.py` (envío básico,
     redirección de destinatarios, HTML alternativo, falta de API key,
     propagación de errores).
- **Motivo**: poder probar CU-002 end-to-end con emails reales sin dominio
  propio ni SMTP local; dejar lista la infraestructura para A-07.
- **Limitación conocida**: mientras no haya dominio verificado, solo recibe
  emails reales el dueño de la API key.
- **Archivos**: `backend/filmai/email_backends.py` (nuevo),
  `backend/filmai/tests.py` (nuevo), `backend/filmai/settings.py`,
  `backend/requirements.txt`, `backend/usuarios/management/commands/send_test_email.py`
  (nuevo), `.env.example`, `.env` (local, no versionado), `Dockerfile`
  (rebuild para incluir el SDK).

## 24/08/2026 — Confirmación de correo: validez 24h, templates propios en español y errores diferenciados (CU-002)

- **Descripción**:
  1. **Validez del enlace**: `ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1`
     (24 horas). Se descartó un token custom por horas: allauth solo soporta
     expiración en días enteros y 1 día resultó suficiente; se mantiene el
     mecanismo nativo de keys firmadas (HMAC + timestamp, sin tabla en DB).
  2. **Templates propios del email** (antes usaba los built-in de allauth, en
     inglés): `backend/templates/account/email/` con
     `email_confirmation_{signup_,}{subject,message.txt,message.html}`.
     Asunto "[FilmAI] Confirmación de cuenta" (se escribió completo en el
     template porque `ACCOUNT_EMAIL_SUBJECT_PREFIX` pasó a vacío para no
     duplicar la marca). Cuerpo en registro formal ("su cuenta", "ignore").
     El HTML es una card oscura con la paleta de la app (#161625 sobre
     #0d0d14, botón #e67e22), tablas y estilos inline para clientes de correo,
     botón + link plano de fallback. Ambas variantes (signup y genérica)
     quedan cubiertas para que los reenvíos también lleguen en español.
     La validez de 24 horas se informa en el propio email, en la pantalla
     "Revisá tu bandeja de entrada" del registro y en el mensaje de enlace
     expirado del frontend.
  3. **Errores diferenciados**: `ConfirmarCorreoView` reemplaza a
     `VerifyEmailView` de dj-rest-auth en la ruta existente
     `/api/auth/registration/verify-email/`. Decodifica la key firmada y
     responde `200 {"detail":"ok"}` o
     `400 {"codigo": "expirado"|"invalido"|"ya_confirmada"}`. El éxito delega
     en `mark_email_address_as_verified()` de allauth (mantiene la lógica del
     adapter). El frontend mapea cada código a su pantalla: ya_confirmada se
     muestra como estado positivo, expirado explica las 24h y cómo reenviar.
  4. **Bug corregido de paso**: `UsuarioAccountAdapter.confirm_email()`
     llamaba a `super()` sin hacer `return`, devolviendo siempre `None`.
     allauth usa ese retorno para considerar confirmada la dirección, así que
     cualquier flujo que dependiera del resultado fallaba silenciosamente.
  5. **Tests**: `ConfirmarCorreoTests` cubre flujo completo
     (registro → email → confirmar → ACTIVA → login), reuso de key,
     key corrupta y expiración (+25h mockeando `django.core.signing.time`).
- **Motivo**: pedido del usuario tras encontrar el mensaje genérico "No se pudo
  confirmar" (la cuenta ya estaba confirmada por una prueba previa) y necesidad
  de branding/copy propios.
- **Archivos**: `backend/filmai/settings.py`, `backend/templates/account/email/*`
  (nuevos), `backend/usuarios/views.py`, `backend/usuarios/adapter.py`,
  `backend/usuarios/tests.py`, `backend/filmai/urls.py`,
  `frontend/app/confirmar-correo/[key]/page.tsx`,
  `frontend/app/(public)/register/page.tsx`, `.env.example` (sin cambios).

## 24/08/2026 — A-07: Recuperación de contraseña (CU-020) conectada de punta a punta

- **Descripción**:
  1. **Solicitud**: `RecuperarContrasenaView` reemplaza a la de dj-rest-auth
     en `/api/auth/password/reset/` (rutas propias ANTES del `include()`).
     Envía el email solo si existe cuenta ACTIVA con ese correo; la respuesta
     HTTP es idéntica siempre (no revela si el correo está registrado,
     docs/02 CU-020 obs.). Cuentas pendientes o de baja no reciben email.
     Si el render o el envío del email falla, se loguea y se responde el
     mismo mensaje genérico (no se rompe el request ni se revela la cuenta).
  2. **Email**: templates propios en
     `backend/templates/registration/recuperar_contrasena_{subject,message.txt,message.html}`
     — asunto "[FilmAI] Restablecimiento de contraseña", registro formal, card
     oscura con la paleta de la app, botón + link fallback. El enlace apunta a
     `{FRONTEND_URL}/restablecer-contrasena/{uid}/{token}/`.
  3. **Validez**: `PASSWORD_RESET_TIMEOUT = 3600` (1 hora, CU-020). Tokens del
     generador nativo (`allauth` `default_token_generator`, HMAC con timestamp;
     sin estado en DB). Un token usado queda invalidado porque `_make_hash_value`
     incluye el hash de la contraseña.
  4. **Confirmación**: `RestablecerContrasenaView` en
     `/api/auth/password/reset/confirm/`. Campos `password1`/`password2`
     (consistente con registro). Enlace inválido/vencido/usado →
     `400 {"codigo": "invalido"}` (mismo contrato que ConfirmarCorreoView);
     contraseña que no cumple CU-001 → errores de campo DRF (la política se
     aplica vía `validate_password` + `ComplejidadContrasenaValidator` que ya
     estaba en AUTH_PASSWORD_VALIDATORS).
  5. **Rate limit**: DRF `ScopedRateThrottle` con dos scopes:
     solicitud de email "recuperar_contrasena" 1/min (estricto, CU-020) y
     confirmación "restablecer_contrasena" 5/min (tolera reintentos por
     validación inline). `CACHES` usa Redis en producción (apunta al servicio
     `redis` de Docker Compose) y LocMem en desarrollo; así los límites
     aplican globalmente entre workers.
  6. **Frontend**: modal en login (campo email + validar formato + botones
     Enviar enlace/Cancelar, cierre por backdrop). Toast de éxito SIEMPRE
     ("Te enviamos un email..."); 429 → error inline pidiendo esperar un
     minuto. Página nueva `app/restablecer-contrasena/[uid]/[token]/` con dos
     campos + toggle visibilidad, validaciones inline onBlur reutilizando
     `validarPassword`/`validarConfirmacion`, pantallas de éxito y de enlace
     inválido (informa validez de 1 hora).
  7. **Tests**: `RecuperarContrasenaTests` (8 casos): envío con enlace válido,
     no-revelación, exclusión de no activas, cambio efectivo + login, enlace
     inválido, expiración (+2h mockeando `_now` del generador), contraseña débil
     y rate limit 429.
- **Motivo**: completar la última actividad del Módulo 1 Autenticación (A-07),
  conectando el link visual que quedó en A-04.
- **Archivos**: `backend/filmai/settings.py`, `backend/filmai/urls.py`,
  `backend/usuarios/serializers.py`, `backend/usuarios/views.py`,
  `backend/templates/registration/*` (nuevos), `backend/usuarios/tests.py`,
  `frontend/app/(public)/login/page.tsx`,
  `frontend/app/restablecer-contrasena/[uid]/[token]/page.tsx` (nueva).

## 24/08/2026 — Saludo de los emails: nombre + apellido con fallback "Hola usuario"

- **Descripción**: nuevo filtro de template `nombre_completo`
  (`usuarios/templatetags/nombres.py`) usado por TODOS los emails
  transaccionales (confirmación, reenvío y restablecimiento): el saludo muestra
  "Nombre Apellido"; si ambos están vacíos (seed, Google sin perfil) cae a
  "Hola usuario". Además se corrigió un bug real: el contexto del email de
  restablecimiento pasaba la clave `usuario` pero el template leía `{{ user }}`,
  por lo que el nombre salía SIEMPRE vacío ("Hola ,"). Ahora el serializer pasa
  `"user"` (misma convención que allauth).
- **Motivo**: reporte del usuario — el email decía "Hola ," al probar con una
  cuenta cuyo campo nombre estaba vacío.
- **Archivos**: `backend/usuarios/templatetags/{__init__,nombres}.py` (nuevos),
  los 6 templates de `backend/templates/{account/email,registration}/`,
  `backend/usuarios/serializers.py`, `backend/usuarios/tests.py`
  (asserts de saludo + test de fallback).

## 24/08/2026 — Revisión de calidad: rate limit de disponibilidad, contraste de emails y pin de allauth

- **Descripción**: se aplicaron correcciones surgidas de la revisión de
  calidad:
  1. **Rate limit de disponibilidad de username (A-05)**:
     `UsernameDisponibleView` agrega `ScopedRateThrottle` con el scope
     `username_disponible` (`30/min` por IP) registrado en
     `DEFAULT_THROTTLE_RATES`, para acotar la enumeración de usernames en un
     endpoint anónimo sin entorpecer el tipeo normal.
  2. **Contraste del email de restablecimiento**: el texto secundario (13px)
     del template `recuperar_contrasena_message.html` pasa de `#777777` a
     `#a0a0a8` para cumplir el contraste 4.5:1 contra `#161625`.
  3. **Pin de django-allauth**: se fija `django-allauth[socialaccount]==65.19.1`
     en `requirements.txt` (antes `>=64.0.0,<66.0`) porque
     `allauth.account.internal.flows.email_verification` (usado por
     `ConfirmarCorreoView`) no es API pública y puede cambiar entre releases
     menores; 65.19.1 es la versión instalada y probada en el contenedor.
- **Motivo**: hallazgos de la revisión de calidad (seguridad anti-enumeración,
  accesibilidad del correo y reproducibilidad de dependencias).
- **Archivos**: `backend/usuarios/views.py`, `backend/filmai/settings.py`,
  `backend/templates/registration/recuperar_contrasena_message.html`,
  `backend/requirements.txt`.

## 26/08/2026 — Revisión de PR: email duplicado en Google OAuth, CSRF del login, decodes de URL y sincronización de documentación

- **Descripción**: correcciones surgidas de la revisión del PR (feat/Autenticación):
  1. **Check de email duplicado movido ANTES de `complete_social_login`**:
     en `GoogleSocialLoginSerializer.validate`, el chequeo
     `Usuario.objects.filter(correo__iexact=...)` ahora corre dentro de la
     rama `not es_existente` (junto a la validación de campos faltantes),
     antes de llamar a allauth. Con `SOCIALACCOUNT_AUTO_SIGNUP=True`, allauth
     puede crear el usuario dentro de `complete_social_login`
     (`flows.signup.process_signup`) cuando el usuario existente no tiene
     `EmailAddress` (p.ej. los del seed): un chequeo a posteriori llegaba
     tarde y dejaba una segunda fila `Usuario` pese a responderse 400 (la
     unique de PostgreSQL solo cubre el caso exacto). Se agrega test de
     regresión que verifica el error 400, que la fila existente queda como
     única (`Usuario.objects.count() == 1`) y que
     `complete_social_login` no se invoca.
  2. **`LenientJWTCookieAuthentication` propaga `PermissionDenied`**: el
     `except Exception` genérico tragaba el `PermissionDenied` que
     `JWTCookieAuthentication.enforce_csrf` lanza al fallar CSRF
     (`JWT_AUTH_COOKIE_USE_CSRF=True`) cuando el browser trae una cookie
     `access` previa; el login quedaba sin protección CSRF (pasaba por
     anónimo). Ahora esa excepción se re-lanza (403) y solo las cookies
     inválidas/vencidas se tratan como anónimas.
  3. **URIError al decodificar parámetros URL**: `decodeURIComponent` lanza
     URIError ante secuencias inválidas (p.ej. "%" suelto). En
     `app/confirmar-correo/[key]/page.tsx` el throw dejaba la página trabada
     en "cargando": ahora el decode está protegido y deriva al estado de
     enlace inválido ("error"). En
     `app/restablecer-contrasena/[uid]/[token]/page.tsx` un URIError caía en
     el mensaje de fallo de contraseña: se clasifica como `enlace_invalido`.
  4. **Sincronización con la implementación real**:
     - A-08 (docs/05) ya no describe tokens en storage: logout basado en
       cookies (`POST /api/auth/logout/` invalida refresh y limpia las
       cookies httpOnly).
     - Filas C-08 y P-03 (docs/05): los pipes internos (`POST | PUT |
DELETE`, `GET | PUT`) van escapados para que cada fila tenga las 6
       columnas del encabezado; Q-05/Q-06 pierden la celda extra de
       responsable (lo cubren el título del módulo y el resumen final).
     - docs/03 JSON: arista e-usuario-calificacion pasa de `1..* ─ 0..*` a
       `1..1 ─ 0..*` (FK obligatoria: cada calificación pertenece a
       exactamente un usuario; un usuario puede tener cero o más).
     - Skill conventional-commits: "12 tipos" → "11 tipos" (la tabla tiene
       11 y coincide con references/examples.md).
     - Skill humanizer: el ejemplo de Lisboa elimina detalles inventados
       (fotos, popularidad del tranvía, filas, planes futuros); conserva
       solo hechos presentes en la entrada.
  5. **No aplicado (verificado contra settings.py)**: propuesta de
     `SameSite=None; Secure` para JWT/CSRF cookies. El despliegue actual es
     mismo sitio (localhost:3000 → localhost:8000 comparten host registrable)
     y la decisión del 26/08/2026 (`JWT_AUTH_COOKIE_USE_CSRF` +
     `CSRF_TRUSTED_ORIGINS`) hace que la protección CSRF no dependa del
     SameSite; forzar `SameSite=None` + `Secure=True` rompería las cookies en
     desarrollo http. Se reconsidera si el frontend y la API terminan en
     sitios distintos.
- **Motivo**: hallazgos verificados de la revisión del PR; el check duplicado
  y el manejo del CSRF eran huecos reales de seguridad/atrición de datos.
- **Archivos**: `backend/usuarios/serializers.py`, `backend/usuarios/views.py`,
  `backend/usuarios/tests.py`,
  `frontend/app/confirmar-correo/[key]/page.tsx`,
  `frontend/app/restablecer-contrasena/[uid]/[token]/page.tsx`,
  `docs/05_Plan_de_Desarrollo.md`,
  `docs/03_DiagramaClases_DiagramaTablas.json`,
  `.opencode/skills/conventional-commits/SKILL.md`,
  `.opencode/skills/humanizer/SKILL.md`.

## 26/08/2026 — Errores globales DRF excluidos del mapa de campos en el frontend (400 de /completar-google sin campos marcados)

- **Fecha**: 26/08/2026
- **Descripción**: al completar el registro con Google en `/completar-google`
  se mostraba "Corregí los campos marcados y tocá de nuevo el botón de
  Google." sin ningún campo resaltado, y el backend registraba
  `POST /api/auth/google/ 400` con body de 55 bytes. Verificación: renderizado
  con `JSONRenderer` (dentro del contenedor, settings reales) de todos los
  bodies posibles del endpoint; solo
  `{"non_field_errors":["El correo ya está registrado."]}` mide exactamente
  55 bytes. La causa era doble:
  1. **Backend (correcto, no modificado)**: la cuenta de Google usada tiene un
     correo que ya existe como `Usuario` local sin `SocialAccount` vinculado;
     el serializer toma la rama de registro nuevo y rechaza por email
     duplicado (`GoogleSocialLoginSerializer.validate`, chequeo UNIQUE_EMAIL).
     Es un error global (no de campo), y es el comportamiento previsto hasta
     decidir si se hace auto-vinculación.
  2. **Frontend (bug)**: `extraerErroresPorCampo` trataba TODAS las claves del
     body como si fueran campos, incluida `non_field_errors`. Con
     `{non_field_errors: ["El correo ya está registrado."]}` el objeto tenía
     claves > 0, así que `/completar-google` entraba en la rama de errores de
     campo, mostraba el mensaje genérico de "corregí los campos" e intentaba
     marcar el inexistente campo `non_field_errors`, que nunca se renderiza.
     Fix: `extraerErroresPorCampo` ahora omite `non_field_errors` y `detail`;
     esos mensajes llegan a las pantallas por la vía ya existente
     (`extractError` → `ApiError.message`). En `/completar-google` el usuario ve
     ahora "El correo ya está registrado."; los errores reales de campo (p.ej.
     nombre de usuario ocupado) siguen marcándose inline, y el banner genérico
     solo aparece cuando hay errores de campo genuinos. Los otros dos llamadores
     (`register`, restablecer contraseña) quedan verificados: no dependían de
     recibir claves globales en el mapa.
- **Motivo**: error reportado por el usuario; el mensaje genérico indicaba una
  acción imposible ("campos marcados") porque la clasificación backend/global
  vs campo se hacía mal en el frontend.
- **Archivos**: `frontend/lib/api.ts`.

## 26/08/2026 — Mensaje personalizado para correo ya registrado en Google OAuth (se mantiene el rechazo)

- **Fecha**: 26/08/2026
- **Descripción**: ante un registro con Google cuyo correo ya existe como
  cuenta tradicional (sin `SocialAccount` vinculado), se decide MANTENER el
  rechazo actual (no auto-vincular cuentas) pero reemplazar el mensaje
  genérico "El correo ya está registrado." por uno que explique la situación:
  "Ya existe una cuenta registrada con este correo. Iniciá sesión con tu
  contraseña." El mensaje viaja como error global (`non_field_errors`) y el
  frontend lo muestra en la parte superior del formulario de
  `/completar-google` gracias a la corrección previa de
  `extraerErroresPorCampo` (ver decisión anterior del mismo día). La prueba
  unitaria de email duplicado (`usuarios/tests.py`) se actualiza al nuevo
  texto.
- **Motivo**: pedido explícito del usuario; el mensaje anterior no explicaba
  por qué Google "no funciona" cuando el problema es una cuenta preexistente
  con contraseña.
- **Archivos**: `backend/usuarios/serializers.py`, `backend/usuarios/tests.py`.

## 11/09/2026 — Provisión atómica de recursos iniciales de usuario

- **Fecha**: 11/09/2026
- **Descripción**: se mantiene la señal `post_save` como disparador único de
  las listas y el chat inicial, pero cada flujo de alta se envuelve en una
  transacción para que un fallo revierta también el `Usuario`. El MVP requiere
  exactamente un chat por usuario; se agrega una restricción de unicidad sobre
  `Chat.usuario`. La futura funcionalidad de chats múltiples reemplazará esa
  restricción mediante una migración. Se incorpora el comando idempotente
  `reparar_recursos_usuarios` para auditar y reparar datos históricos o
  importados; no se ejecuta en el login ni en cada request.
- **Motivo**: antes, la transacción de la señal sólo protegía listas y chat,
  por lo que una falla podía dejar una cuenta persistida e incompleta.
- **Archivos**: `backend/usuarios/models.py`, `backend/usuarios/adapter.py`,
  `backend/usuarios/serializers.py`, `backend/usuarios/signals.py`,
  `backend/usuarios/provisioning.py`,
  `backend/usuarios/management/commands/reparar_recursos_usuarios.py`,
  `backend/chatbot/models.py`, su migración y pruebas.

## 13/09/2026 — Corrección de sintaxis en las rutas del catálogo

- **Fecha**: 13/09/2026
- **Descripción**: se restauraron las comas separadoras en las rutas de detalle
  de película y serie. Su ausencia impedía importar `catalogo.urls`, por lo que
  Django no podía ejecutar las migraciones ni sus system checks. Se ajustó además
  el formato de la ruta de Swagger para que Ruff valide el backend sin cambios
  pendientes.
- **Motivo**: el backend quedaba en bucle de reinicio y CI reportaba un error de
  sintaxis antes de evaluar los endpoints, incluido `KeywordsView`, que existe y
  está correctamente importado.
- **Archivos**: `backend/catalogo/urls.py`, `backend/filmai/urls.py`,
  `docs/decisiones.md`.

## 14/09/2026 — Créditos de TMDB, tarea `generar_embedding` idempotente y auto-reload del worker

- **Fecha**: 14/09/2026
- **Descripción**: fase 4 de C-04a.
  1. **`get_credits(id_tmdb, tipo)`, un método y no dos.** Los endpoints de
     detalle de TMDB no incluyen `cast` ni `crew`: sin pedirlos aparte, los
     campos `reparto` y `directores` quedarían vacíos y la búsqueda semántica
     no encontraría nada por actor ni director. Se implementa con la firma de
     `get_keywords(id_tmdb, tipo)` —misma forma de URL, `/{tipo}/{id}/credits`
     vs `/{tipo}/{id}/keywords`— en lugar de los dos métodos por tipo que
     preveía el diseño. TTL de 24 h en `ENDPOINT_TTLS["credits"]`, igual que
     el detalle: el reparto de una producción estrenada casi no cambia.
  2. **`generar_embedding` con tres defensas contra el trabajo duplicado.**
     Celery entrega "al menos una vez": la misma tarea puede llegar dos veces
     o a dos workers en paralelo.
     - Corte por huella: si el embedding ya está `ready` con el mismo
       `source_hash` y `model_version`, se sale sin llamar al proveedor.
     - Claim atómico: `UPDATE ... SET estado='processing' WHERE estado IN
('pending','failed')` devuelve la cantidad de filas afectadas; de dos
       ejecuciones simultáneas exactamente una recibe 1 y la otra 0, sin locks
       explícitos. Los `ready` quedan fuera de los estados reclamables a
       propósito: un vector utilizable no se degrada a `failed` por un
       proveedor caído. Refrescar los `ready` cuyo texto cambió es trabajo del
       backfill de C-04b, que los devuelve a `pending`.
     - La llamada al proveedor ocurre fuera de toda transacción (puede tardar
       segundos) y cualquier excepción se captura: la fila termina en `failed`
       y la tarea reporta éxito, porque propagar haría que Celery reintentara
       en loop sin aportar nada — la producción sigue visible igual.
       Verificado de punta a punta contra el worker real: la tarea se recibe, el
       stub falla con `NotImplementedError`, la fila queda en `failed` y la
       producción permanece visible.
  3. **Auto-reload del worker en desarrollo (`watchmedo`).** Celery NO recarga
     código como el `runserver` de Django, y eso tiene dos síntomas de muy
     distinta gravedad: agregar o renombrar una tarea produce un error
     explícito (`KeyError: 'catalogo.generar_embedding'`, el worker rechaza el
     mensaje), pero **editar el cuerpo de una tarea existente no produce
     ningún error: el worker sigue ejecutando en memoria la versión vieja**,
     en silencio, mientras en el editor se ve el código nuevo. Ese segundo
     caso es el que hace perder horas. Se agrega `watchdog[watchmedo]` a
     `requirements.txt` y el `command` del servicio `celery-worker` se envuelve
     en `watchmedo auto-restart --directory=/app --pattern=*.py --recursive`.
     Se evaluó `docker compose watch` (disponible, Compose 2.40): se descartó
     porque el proyecto ya usa bind mounts (la mitad `sync` sería redundante),
     obliga a correr `docker compose watch` en primer plano en lugar del
     `docker compose up -d` que documenta el README —y si alguien se olvida,
     vuelve el bug silencioso— y reinicia el contenedor entero en vez del
     proceso. La envoltura es solo de desarrollo: en producción se despliega
     una imagen nueva y se corre `celery` directo.
- **Archivos**: `backend/catalogo/client.py`, `backend/catalogo/cache.py`,
  `backend/catalogo/tasks.py`, `backend/catalogo/tests.py`,
  `backend/requirements.txt`, `docker-compose.yml`.

## 14/09/2026 — Capa `catalogo/services/`, adaptador de tipos y texto canónico

- **Fecha**: 14/09/2026
- **Descripción**: fase 3 de C-04a, tres decisiones:
  1. **Se unifica la capa de servicios en `catalogo/services/`.** Iba a quedar
     `catalogo/service.py` (C-03, singleton de TMDB) conviviendo con
     `catalogo/services/` (C-04a), dos nombres casi idénticos en la misma app.
     `service.py` pasa a ser `catalogo/services/tmdb.py`; se actualizan sus
     dos importadores (`views.py`, `tests.py`, incluidos los destinos de
     `patch()`). Cambio mecánico, verificado con la suite de C-03 en verde.
  2. **`services/adapter.py` es la única traducción `movie`/`tv` ↔
     `pelicula`/`serie`.** Lanza `ValueError` ante cualquier otro valor,
     incluido `"all"`: es un filtro válido de discovery (C-03) pero no un tipo
     de producción. Las vistas siguen hablando `movie`/`tv` de cara al
     exterior; la traducción ocurre al cruzar hacia el modelo.
  3. **`services/embeddings.py` normaliza el texto antes de hashearlo.** Los
     arrays (`generos`, `directores`, `reparto`, `keywords`) se ordenan
     alfabéticamente y se descartan los vacíos. TMDB no garantiza un orden
     estable entre respuestas: sin normalizar, dos respuestas con el mismo
     contenido darían hashes distintos y el sistema regeneraría embeddings
     indefinidamente. El proveedor real queda aislado en `generar_vector()`,
     que hoy lanza `NotImplementedError` a propósito — es el único punto que
     B-06 debe reemplazar, y su falla deja el embedding en `failed` sin
     afectar la visibilidad de la producción.
- **Motivo**: aislar en un solo lugar cada traducción y cada decisión de
  formato, que son las que generan bugs silenciosos si se repiten dispersas.
- **Archivos**: `backend/catalogo/services/{__init__,adapter,embeddings,tmdb}.py`,
  `backend/catalogo/views.py`, `backend/catalogo/tests.py`.

## 14/09/2026 — Modelo `ProduccionEmbedding`: invariantes en la base, no en Python

- **Fecha**: 14/09/2026
- **Descripción**: se implementa `ProduccionEmbedding` (C-04a, fase 2) con dos
  garantías delegadas al motor de base de datos en lugar de a validaciones de
  aplicación, para que ningún camino de escritura (ORM, admin, SQL manual,
  scripts de backfill) pueda saltearlas:
  - `OneToOneField` con `on_delete=CASCADE` → columna `produccion_id UNIQUE`:
    imposible tener dos embeddings de la misma producción, y borrar la
    producción se lleva su embedding.
  - `CheckConstraint` `ck_embedding_ready_requiere_vector`: un embedding en
    estado `ready` no puede tener `vector` nulo. Un `ready` sin vector sería
    invisible para la búsqueda pero contaría como procesado, dejando la
    producción fuera del corpus en silencio.
    Índices: `idx_embedding_estado` (btree, para que el backfill busque
    `pending`/`failed`) e `idx_embedding_vector_hnsw` (HNSW con
    `vector_cosine_ops`, `m=16`, `ef_construction=64`) para la búsqueda por
    similitud que usará `buscar_semantico` (B-06).
    La migración `0004_produccionembedding` lleva `VectorExtension()` agregado a
    mano como primera operación: `makemigrations` no infiere que el tipo
    `vector` proviene de una extensión, y sin eso la migración falla con `type
"vector" does not exist`.
    Se registra `ProduccionEmbedding` en el admin (excluyendo el vector, que son
    1024 números ilegibles en un formulario) para poder auditar estados en
    desarrollo; el registro de `Usuario` y `Reseña` sigue siendo AD-01'.
- **Motivo**: los embeddings los escribe un worker asincrónico que puede
  fallar a mitad de camino; las invariantes tienen que sobrevivir a eso.
- **Archivos**: `backend/catalogo/models.py`,
  `backend/catalogo/migrations/0004_produccionembedding.py`,
  `backend/catalogo/admin.py`, `backend/catalogo/tests.py`.

## 14/09/2026 — Entrypoint parametrizable y imagen pgvector Debian (wiring de Celery)

- **Fecha**: 14/09/2026
- **Descripción**: al conectar Celery (C-04a, Fase 1) surgieron dos cambios de
  infraestructura:
  1. **Entrypoint al patrón estándar de Docker.** `backend/entrypoint.sh`
     terminaba con `exec python manage.py runserver 0.0.0.0:8000` hardcodeado,
     por lo que ignoraba el `command:` del servicio: el `celery-worker`
     habría levantado un segundo servidor Django y corrido `migrate` + creación
     de superuser en paralelo con `backend`. Ahora el script termina con
     `exec "$@"` y el `Dockerfile` define
     `CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]`, de modo que el
     backend arranca igual que antes y cada servicio elige su comando. Las
     migraciones y el superuser quedan detrás de `RUN_MIGRATIONS` (default
     `true`); el `celery-worker` la define en `false` para que migre un solo
     contenedor.
  2. **Imagen de la base: `pgvector/pgvector:pg16` (Debian), no
     `pg16-alpine`.** El tag Alpine que figuraba en la documentación no
     existe: pgvector solo publica imágenes Debian. Como el cambio implica
     pasar de musl a glibc —y las reglas de ordenamiento (collation) de los
     índices de texto difieren entre ambas—, se decide **recrear el volumen
     `pgdata`** en lugar de reutilizarlo. En desarrollo el costo es nulo (el
     entrypoint recrea migraciones y superuser, y las listas predeterminadas
     las repone la señal). **Acción requerida para el equipo**: al traer estos
     cambios hay que correr `docker volume rm filmai_pgdata` (con los
     contenedores frenados) y `docker compose up --build -d`.
     Se verificó en la imagen nueva que la extensión `vector` 0.8.6 está
     disponible y que el rol de Postgres del `.env` tiene `rolsuper = true`, es
     decir que podrá ejecutar `CREATE EXTENSION` en la migración de la Fase 2.
- **Configuración de Celery**: broker en la DB 1 de Redis y backend de
  resultados en la DB 2, separadas de la DB 0 que usa el caché de TMDB, para
  que las claves de la cola no se mezclen con las `tmdb:*` ni las borre un
  flush del otro rol. Serialización JSON únicamente y
  `CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True` (explícito porque el
  default cambia en Celery 6).
- **Motivo**: sin el arreglo del entrypoint el servicio `celery-worker` no
  podía funcionar; sin el cambio de imagen no hay extensión `vector` para
  `ProduccionEmbedding`.
- **Archivos**: `backend/entrypoint.sh`, `backend/Dockerfile`,
  `docker-compose.yml`, `backend/filmai/celery.py`, `backend/filmai/__init__.py`,
  `backend/filmai/settings.py`, `backend/filmai/tests.py`,
  `backend/requirements.txt`, `.env.example`, `README.md`.

## 14/09/2026 — Rutas de detalle sin conversor `int:`: 400 en vez de 404 ante `id_tmdb` no entero

- **Fecha**: 14/09/2026
- **Descripción**: `catalogo/urls.py` declaraba la ruta de detalle de película
  con `<int:id_tmdb>` y la de serie con `<id_tmdb>`. Con el conversor `int:`,
  un `id_tmdb` no entero no matchea la URL y Django responde 404 antes de
  llegar a la vista, mientras que la ruta de serie sí llegaba a `_int_param` y
  devolvía 400: dos endpoints hermanos con comportamientos distintos ante la
  misma entrada inválida. La spec de C-03
  (`openspec/specs/tmdb-endpoints/spec.md`, "Invalid params rejected") exige
  400 sin llamar a TMDB. Se quita el conversor `int:` de la ruta de película
  para que ambas deleguen la validación en `_int_param`.
  El bug no fue detectado por `ParamValidationTest` porque ese test invoca
  `MovieDetailView.as_view()(request, id_tmdb="not-an-id")` directamente,
  salteando el ruteo de Django. Se agrega
  `EndpointIntegrationTest.test_non_integer_detail_id_returns_400_through_url_routing`,
  que recorre la URL real con `APIClient` sobre ambas rutas.
- **Motivo**: hallazgo durante la auditoría de `docs/05_Plan_de_Desarrollo.md`
  contra el código (14/09/2026); incumplía la spec ya archivada de C-03.
- **Archivos**: `backend/catalogo/urls.py`, `backend/catalogo/tests.py`.

## 14/09/2026 — C-04a adelanta la infraestructura mínima de embeddings; corrección de paquete pgvector

- **Fecha**: 14/09/2026
- **Descripción**: la especificación de C-04a (08/09/2026) requiere crear un
  `ProduccionEmbedding` en estado `pending` y encolar `generar_embedding.delay(...)`,
  pero esa infraestructura (modelo, pgvector, wiring de Celery) estaba asignada
  a B-06 (Marcos, Fase 3), que en el plan corre en paralelo/después de C-04a.
  Se decide **adelantar dentro de C-04a** lo mínimo necesario para no dejar el
  helper de materialización sin poder encolar nada: modelo `ProduccionEmbedding`
  - migración con la extensión `vector`, wiring de Celery (`filmai/celery.py`,
    settings, servicio `celery-worker`), y la tarea `generar_embedding` con toda
    la lógica real de idempotencia (claim `pending`/`failed`→`processing`, corte
    por `source_hash`+`model_version`). La llamada al proveedor de embeddings en
    sí (Ollama/bge-m3) queda como stub documentado (`generar_vector()`, lanza
    `NotImplementedError`) — punto de extensión para que B-06 lo reemplace sin
    tocar el resto. No se agrega el servicio `ollama` ni se hace pull de
    `bge-m3`: eso sigue siendo 100% de B-06.
    Decisiones asociadas:
  * El paquete Django correcto para `VectorField`/`HnswIndex`/`VectorExtension`
    es `pgvector` (paquete `pgvector-python`, submódulo `pgvector.django`); se
    corrige la mención previa a `django-pgvector` en
    `docs/05_Plan_de_Desarrollo.md`, que no es el paquete mantenido para esto.
  * `materializar()` se invoca como side-effect desde `MovieDetailView`/
    `TVDetailView` (C-03) dentro de la misma tarea C-04a, sin cambiar su
    contrato de respuesta — de lo contrario el helper quedaría sin ningún
    llamador real hasta la UI de ficha de detalle (C-07).
  * El test de concurrencia obligatorio para mergear es determinístico (mockea
    `IntegrityError` en `.create()` y verifica el fallback a `.get()`); un
    test adicional con `TransactionTestCase` + `threading.Barrier` (dos
    threads reales contra Postgres) se agrega como prueba de confianza extra,
    pero no bloquea el merge si es inestable por timing.
- **Motivo**: evitar que C-04a quede bloqueada esperando una fase posterior
  del plan, sin adelantar trabajo que no le corresponde (el proveedor real de
  embeddings sigue siendo responsabilidad de B-06).
- **Archivos**: `docker-compose.yml`;
  `openspec/changes/catalog-materialization/{proposal,design,tasks}.md`;
  `docs/05_Plan_de_Desarrollo.md`. (Modelo, wiring de Celery, tarea y vistas
  se agregan en commits siguientes de la misma rama
  `feat/c-04a-materializacion`.)

## 15/09/2026 — C-04a completa: `materializar()` y su política de fallo en las vistas

- **Fecha**: 15/09/2026
- **Descripción**: se cierra C-04a con la fase 5, que junta las piezas de las
  fases 1-4 en `catalogo/services/materialization.py::materializar(id_tmdb,
tipo_tmdb)` y la enchufa a `MovieDetailView`/`TVDetailView`. Decisiones
  asociadas:
  - **`materializar()` propaga sus errores; quien la llama fija la política.**
    Las vistas de detalle la envuelven en `_materializar_sin_interrumpir()`,
    que registra y sigue: el contrato de C-03 es passthrough puro de TMDB y un
    problema nuestro (base, red, broker) nunca debe impedir que el usuario vea
    la ficha. Tragarse el error dentro de `materializar()` la haría mentirosa
    para el backfill de C-04b, que sí necesita enterarse.
  - **El INSERT de la producción va dentro de `transaction.atomic()`.** En
    PostgreSQL un error aborta la transacción completa; sin ese savepoint, la
    consulta de rescate posterior al `IntegrityError` de la carrera también
    fallaría. Un `IntegrityError` que no venga de la carrera (la fila sigue
    sin aparecer) se propaga en vez de disfrazarse de "ya existía".
  - **El embedding se crea con `get_or_create`**, que ya resuelve internamente
    la misma carrera para el `OneToOneField`. **Solo se encola cuando la fila
    se acaba de crear**: reencolar en cada visita llenaría la cola de trabajo
    repetido. Refrescar los `failed` o desactualizados es del backfill C-04b.
  - **`_extraer_keywords()`** aísla una rareza de la API: TMDB devuelve la
    misma lista bajo `keywords` en películas y bajo `results` en series.
  - **Limitación conocida y aceptada** en `_necesita_enriquecimiento()`: el
    criterio de "fila incompleta" solo mira el título, así que una fila con
    título pero sin géneros no se repararía. Hoy no puede ocurrir porque
    `materializar()` es el único camino de escritura de la tabla y completa
    todos los campos juntos; queda documentado en el docstring como el único
    lugar a endurecer cuando C-04b agregue el sync masivo.
- **Criterios de aceptación verificados**: unicidad por `(id_tmdb, tipo)`;
  concurrencia resuelta (test determinista con `IntegrityError` mockeado, más
  uno best-effort con dos hilos reales contra Postgres, cinco corridas en
  verde); idempotencia (dos visitas → una fila, un embedding, un encolado);
  fallo del proveedor → `failed` sin afectar la visibilidad de la producción.
  Smoke de punta a punta con el worker real: la tarea se consume una sola vez
  y el stub de B-06 deja el embedding en `failed`.
- **Motivo**: cerrar CU-021 (toda producción abierta en detalle se
  materializa) y desbloquear el Módulo 3 (Listas, Marcos), que necesita filas
  reales de `ProduccionAudiovisual` para referenciar.
- **Archivos**: `backend/catalogo/services/materialization.py`,
  `backend/catalogo/views.py`, `backend/catalogo/tests.py`,
  `openspec/changes/catalog-materialization/tasks.md`,
  `docs/05_Plan_de_Desarrollo.md`.

## 15/09/2026 — Las series se acreditan por `created_by`, no por el crew

- **Fecha**: 15/09/2026
- **Descripción**: al verificar C-04a contra la API real de TMDB (una vez
  cargada la `TMDB_API_KEY`) se detectó que **toda serie quedaba sin
  directores**. La causa no es un bug del mapeo sino una asimetría de la API:
  en TV los directores son por episodio, así que `/tv/{id}/credits` no expone
  ningún `job == "Director"` a nivel serie. Se comprobó sobre Breaking Bad
  (1396): el crew devuelve Executive Producer, Casting, Costume Design,
  Original Music Composer y demás, ninguno Director. En su lugar, el detalle
  de la serie trae `created_by` (para Breaking Bad, `Vince Gilligan`).
  Se decide que `_directores()` use `created_by` en series y el crew en
  películas, con fallback al crew cuando una serie no declara creadores
  (miniseries y documentales a veces sí traen un Director).
- **Motivo**: `Directors` es una de las seis secciones del texto canónico que
  se embebe. Con el campo vacío, ninguna serie podría encontrarse por su autor
  —que es justamente el dato que un usuario recuerda de una serie—. Además, el
  `source_hash` se calcula sobre ese texto: corregirlo **después** de que B-06
  conecte Ollama obligaría a regenerar el embedding de todas las series. Hoy
  no cuesta nada, porque todos terminan en `failed` por el stub.
- **Limitación aceptada (no se corrige)**: TMDB devuelve `episode_run_time`
  vacío en muchas series, así que `duracion` queda en NULL para ellas. No
  forma parte del texto embebido y `last_episode_to_air.runtime` no es un
  sustituto representativo.
- **Lección sobre los tests**: el fixture `_CREDITS_TV` incluía un
  `{"job": "Director"}` inventado, que la API real nunca devuelve. Por eso los
  tests pasaban mientras la realidad fallaba. Se corrigió el fixture para que
  refleje la forma real de la respuesta.
- **Archivos**: `backend/catalogo/services/materialization.py`,
  `backend/catalogo/tests.py`,
  `openspec/specs/catalog-materialization/spec.md`.

## 15/09/2026 — El CI corre también en PRs apilados sobre ramas `feat/**`

- **Fecha**: 15/09/2026
- **Descripción**: `.github/workflows/ci.yml` solo se disparaba en PRs cuya
  rama destino era `main`, así que un **PR apilado** (uno cuya base es otra
  rama de feature, para que la revisión muestre solo el tramo nuevo) quedaba
  sin tests: únicamente corría "AI Review". Pasó con el PR #13 de C-04a. Se
  agrega `feat/**` al filtro `branches` del disparador `pull_request`.
- **Motivo**: el presupuesto de revisión del proyecto (400 líneas,
  `openspec/config.yaml`) empuja a partir el trabajo en PRs encadenados, y esa
  práctica no puede salir a costa de perder el gate de tests.
- **Detalle no obvio**: `branches` filtra por la rama **destino** del PR, no
  por la de origen. Y **reapuntar la base de un PR ya abierto no dispara el
  workflow**, porque GitHub emite el evento `edited`, que no está entre los
  tipos por defecto (`opened`, `synchronize`, `reopened`); para forzarlo hay
  que cerrar y reabrir el PR, o pushear un commit.
- **Alcance**: solo `feat/**`. Un PR apilado sobre una rama `fix/**` o
  `chore/**` seguiría sin CI; si eso llegara a pasar, la alternativa es quitar
  el filtro `branches` por completo para que corra en todo PR.
- **Archivos**: `.github/workflows/ci.yml`.

## 15/09/2026 — C-04b: la sync escribe por `materializar()`, y la frescura se vuelve explícita

- **Fecha**: 15/09/2026
- **Descripción**: al planificar C-04b (sync diaria) se detectó que el plan
  original del 08/09/2026 —"sincroniza con `update_or_create`"— ya no encaja
  con lo que C-04a dejó construido. Se toman cuatro decisiones:
  1. **La sync no escribe: llama a `materializar()` por ítem.** El spec
     canónico de `catalog-materialization` exige un único camino de escritura,
     y un ítem de listado de TMDB no alcanza para llenar una fila. Verificado
     contra la API en vivo: un ítem de `trending` trae `genre_ids` (IDs
     numéricos, no nombres) y **no trae** `genres`, `status`, `runtime`,
     reparto, crew ni keywords — es decir, **cuatro de las seis secciones** del
     texto que se embebe. Una fila creada así quedaría embebida sobre un texto
     mutilado y, con el criterio viejo, contaría como completa para siempre.
     Pasar por `materializar()` cuesta 3 llamadas por ítem, todas cacheadas 24 h.
  2. **Nuevo campo `ProduccionAudiovisual.fecha_enriquecimiento`**
     (`DateTimeField`, nulo) que registra cuándo se trajo por última vez el
     detalle completo. Reemplaza el criterio `not titulo` de C-04a, que no
     distinguía una fila completa de una creada desde un listado y que además
     no permitía refrescar nada. Se evaluó usar `estatus` vacío como centinela
     —es confiable, porque solo lo devuelve el detalle— pero no lleva edad, así
     que la sync nunca podría actualizar una fila existente.
  3. **El seed inicial (~10k producciones) sale de C-04b** y pasa a ser una
     tarea aparte (C-04c). Necesita paginado, control de ritmo y reanudación, y
     conviene correrlo recién cuando el mapeo esté probado: hacerlo antes
     significa escribir diez mil filas mal. El plan ya lo contemplaba ("con
     C-04b **o** comando de management").
  4. **Se adopta `transaction.on_commit()` para el `.delay()`** del embedding,
     sugerencia del review del PR #12 que había quedado pendiente. Hoy es
     idéntico (sin transacción abierta se ejecuta al instante) y protege el día
     que algo envuelva la materialización en un `atomic()` —la sync por lotes
     es candidata—, para que el worker nunca reciba el id de una fila que
     todavía no se commiteó. Cuesta mover dos tests a
     `captureOnCommitCallbacks(execute=True)`.
- **Motivo**: cerrar CU-021 por el lado proactivo sin romper las garantías que
  C-04a acababa de establecer, y sin dejar filas a medio llenar que después
  nadie repararía.
- **Consecuencia sobre C-04a**: `materializar()` suma un parámetro `forzar` —
  la única forma de re-enriquecer sin abrir un segundo camino de escritura— y
  la limitación conocida de `_necesita_enriquecimiento()` deja de existir.
- **Pendiente de calibrar**: la ventana de frescura (`_DIAS_FRESCURA = 30`) es
  una primera estimación; conviene revisarla cuando haya corpus real (C-04c) y
  datos de cuánto cambia TMDB una producción ya estrenada.
- **Archivos**: `openspec/changes/catalog-daily-sync/{proposal,design,tasks}.md`.

## 15/09/2026 — La frescura la responde TMDB, no una ventana de tiempo

- **Fecha**: 15/09/2026
- **Descripción**: refina la decisión 2 tomada horas antes en esta misma
  jornada. El diseño inicial de C-04b resolvía "¿esta fila está vieja?" con una
  ventana fija de 30 días sobre `fecha_enriquecimiento`. Al revisarlo se
  verificó que **TMDB publica la respuesta exacta**: `GET /movie/changes` y
  `GET /tv/changes` devuelven los IDs modificados en las últimas 24 h
  (comprobado en vivo: 7.351 películas, 74 páginas). La sync cruza esa lista
  con los IDs que tenemos guardados y refresca solo la intersección.
  El criterio queda partido en **tres capas**, cada una respondiendo una
  pregunta distinta:
  1. **Completitud** — `fecha_enriquecimiento is None`: la fila nunca se
     enriqueció.
  2. **Cambio real** — el ID aparece en la lista de cambios del día.
  3. **Red de seguridad** — `_DIAS_RED_DE_SEGURIDAD = 90`, por si la lista de
     cambios se perdió (la sync no corrió una noche, la API falló).
- **Motivo**: una ventana de tiempo refresca filas **hayan cambiado o no**.
  Sobre un corpus de 10.000, una ventana de 30 días re-pide ~333 filas por
  noche, la mayoría idénticas a lo que ya tenemos. La intersección refresca
  exactamente lo que se movió, y además resulta más barata que el barrido que
  reemplaza. La diferencia de fondo es que la ventana **adivina** y la lista de
  cambios **pregunta a la fuente**.
- **Consecuencia**: se agrega `get_changes(tipo, page)` a `TMDBClient` y
  `TMDBClientCache` (aditivo, con la forma de los métodos existentes) y un TTL
  `"changes"` de 6 h. La intersección se hace **en Python**, no con un
  `id_tmdb__in` de miles de elementos. La fase 2 pasa a entregarse en dos PR,
  cortando en la costura natural entre "hacer crecer el corpus" y "mantenerlo
  fresco".
- **Queda por medir**: cuán grande es la intersección diaria con un corpus
  real. Si resultara que una porción significativa de 10.000 filas cambia cada
  noche, el costo por corrida crece y puede necesitar su propio tope.
- **Origen**: pregunta del usuario — "¿no se podría usar algo más robusto?,
  ¿buscar otra estrategia más de raíz?". La tenía.
- **Archivos**: `openspec/changes/catalog-daily-sync/{proposal,design,tasks}.md`.

## 17/09/2026 — La sync refresca antes de descubrir

- **Contexto**: la sync nocturna (C-04b, fase 2) tiene dos pasadas: el
  **refresco** (cruzar nuestros IDs con `/changes` y re-enriquecer con
  `forzar=True`) y el **descubrimiento** (recorrer trending, cartelera y
  discover, materializando lo que no tenemos). El `design.md` las describía
  en el orden descubrimiento → refresco.
- **Decisión**: se ejecutan **refresco → descubrimiento**. El refresco solo
  toca filas que existían antes de esa noche; el descubrimiento después ve
  `fecha_enriquecimiento` fresca en las que acaba de refrescar y las saltea.
- **Motivo**: una película en cartelera se está editando activamente en TMDB,
  así que casi seguro está también en la lista de cambios del día. Con
  descubrimiento primero, la sync la enriquecía como nueva y segundos después
  el refresco la volvía a enriquecer. Al revés no hay trabajo doble.
- **Medido en vivo**: sobre 60 filas (todas de trending/cartelera), 39
  estaban en la lista de cambios — un corpus popular se mueve mucho. La
  primera corrida tardó 26 s; la segunda 0,47 s, entera desde Redis.
- **Ajustes al diseño anotados en la aplicación**: `_MAX_PAGINAS_CAMBIOS`
  pasa de 100 a **200** (`/movie/changes` tuvo 98 páginas el 17/09 contra 74
  el 15/09; 100 quedaba a un día ocupado de truncar); las estadísticas suman
  `refrescadas`; si `/changes` falla se saltea el refresco de ese tipo, se
  cuenta un error y el descubrimiento corre igual.
- **Consecuencia**: `sync_catalogo_diaria()` en `backend/catalogo/tasks.py`;
  `design.md` y `tasks.md` de `openspec/changes/catalog-daily-sync/`
  actualizados para reflejar lo construido.

## 18/09/2026 — Zona horaria de Celery declarada, y el backfill cierra C-04b

- **Contexto**: `celery-beat` dispara la sync del catálogo y, desde esta fase,
  también el backfill de embeddings. Celery interpreta los horarios de
  `CELERY_BEAT_SCHEDULE` en **UTC** salvo que se le diga otra cosa.
- **Decisión**: `CELERY_TIMEZONE = TIME_ZONE` en `settings.py`, reutilizando la
  zona que ya declara Django (`America/Argentina/Buenos_Aires`). El
  `crontab(hour=3)` significa entonces las 3 AM argentinas.
- **Motivo**: sin la línea, la sync correría a medianoche local. Es la clase de
  error que no rompe nada, no aparece en ningún test y se descubre meses
  después mirando por qué los datos se actualizan a una hora rara. Reutilizar
  `TIME_ZONE` en vez de repetir la cadena evita que las dos queden
  desincronizadas.
- **Backfill a las 4 AM, una hora después de la sync**: así recoge los
  embeddings que la sync acaba de encolar y fallaron esa misma noche. Toca
  como máximo 100 filas por corrida; sin tope, sobre un corpus de 10.000 una
  corrida encolaría 10.000 tareas de golpe.
- **Ambas poblaciones se recorren por `fecha_actualizacion` ascendente**. El
  campo es `auto_now`, así que procesar una fila la manda al final: ninguna
  queda indefinidamente detrás del tope.
- **Hallazgo durante la implementación**: reencolar un `ready` desactualizado
  no alcanzaba. `generar_embedding` reclama con `estado__in=(pending, failed)`,
  así que la tarea llegaba al worker, no reclamaba nada y volvía sin hacer
  nada — el vector viejo se habría quedado para siempre. El backfill ahora
  devuelve la fila a `pending` **antes** de encolar. Los siete tests unitarios
  no lo detectaron porque parchean `generar_embedding` entera; lo encontró un
  test de integración con la tarea real. Queda como recordatorio de que un
  test con todo mockeado prueba el llamado, no el efecto.
- **Consecuencia**: `backend/filmai/settings.py`, `backend/catalogo/tasks.py`,
  spec canónica `openspec/specs/catalog-daily-sync/spec.md`. C-04b queda
  completa salvo el archivado del SDD.

## 18/09/2026 — Herramientas de review automáticas desactivadas y simplificación de openspec

- **Contexto**: El workflow de AI Review (`.github/workflows/ai-review.yml`) se
  ejecutaba automáticamente en cada pull request. En el PR #23 generó 15
  comentarios, de los cuales 14 eran falsos positivo (93%) que no detectaban
  bugs reales ni sugerían mejoras válidas. Los comentarios no tenían contexto
  del proyecto (convenciones de idioma, valores de configuración, arquitectura).
  CodeRabbit también estaba instalado como app de GitHub, pero la prueba
  gratuita expiró.
- **Decisión**: Desactivar completamente AI Review (eliminar el workflow) y
  desinstalar CodeRabbit (app de GitHub). La revisión de código se hace
  manualmente por los maintainers, con apoyo de los skills disponibles y la
  documentación de dominio en `docs/`.
- **Motivo**: El costo de revisar los comentarios de AI Review (tiempo perdido
  analizando falsos positivos, fatiga de review, falso sentido de seguridad)
  supera el beneficio. Los bots de review genéricos no entienden el dominio del
  proyecto ni las decisiones de diseño específicas. CodeRabbit se desinstaló
  porque la prueba gratuita expiró y no se renovó.
- **Simplificación de openspec**: Se eliminaron los cambios archivados en
  `openspec/changes/archive/` (4 cambios completados: tmdb-client, tmdb-cache,
  tmdb-endpoints, materialization). La información de decisiones ya está
  registrada en `docs/decisiones.md`. Se mantiene `openspec/specs/` como
  referencia canónica de cada módulo, y `openspec/changes/` solo para cambios
  activos en progreso.
- **Consecuencia**: `.github/workflows/ai-review.yml` eliminado.
  `openspec/changes/archive/` eliminado. CodeRabbit desinstalado de GitHub.
  `AGENTS.md` actualizado con sección 8 (herramientas de review desactivadas)
  y sección 9 (estructura de documentación).

## 18/09/2026 — `actualizadas` pasa a `ya_existentes`; C-04b cerrada

- **Contexto**: la sync devuelve cinco contadores. Al explicar la diferencia
  entre `actualizadas` y `refrescadas` quedó claro que el primero describe mal
  lo que mide.
- **Decisión**: `actualizadas` → **`ya_existentes`**. `refrescadas` se queda
  con ese nombre.
- **Motivo**: el contador no cuenta producciones actualizadas; cuenta las que
  la pasada de descubrimiento encontró y ya estaban guardadas. Si la fila
  estaba fresca, `materializar()` ni le pidió el detalle a TMDB y el contador
  sube igual.
- **Por qué `refrescadas` NO pasó a llamarse `actualizadas`**, que era la
  alternativa más intuitiva y la que alinea literal con el CU: `refrescadas`
  nombra una **acción** que siempre ocurre cuando el contador sube (se volvió a
  pedir la ficha y se reescribieron los campos). `actualizadas` afirmaría un
  **resultado** que no verificamos: si TMDB reporta un cambio en un campo que
  no guardamos (un backdrop, un video, una traducción), reescribimos los mismos
  valores. Habría sido cambiar un nombre preciso por otro impreciso, y encima
  reciclando la misma palabra que se acababa de retirar del otro contador.
- **Trazabilidad con CU-021**: el paso 5 pide «cantidad de producciones nuevas,
  actualizadas y errores». Ese requisito lo cumple **`refrescadas`**. El texto
  del caso de uso **no se tocó** (es un entregable académico); la aclaración
  está en su campo _Observaciones_.
- **Cierre de C-04b**: con todo mergeado a `main` (PRs #19 a #23), se elimina
  `openspec/changes/catalog-daily-sync/` siguiendo la política de la sección 9
  de `AGENTS.md` (los cambios completados se eliminan, no se archivan). La spec
  canónica `openspec/specs/catalog-daily-sync/spec.md` queda como referencia.
- **Skill `explicar-al-implementar`**: se concilió la regla 4. El cuerpo pedía
  brevedad y el `description` pedía lo contrario; ahora ambos dicen lo mismo —
  apuntar a la versión corta y expandir donde el concepto lo pida.
- **Origen**: pregunta del usuario — «¿diferencia entre actualizadas y
  refrescadas?». El nombre no resistía la explicación.

## 19/09/2026 — L-01: contrato enriquecido de resúmenes de listas

- **Decisión**: `GET /api/lists/` devuelve, por cada lista propia, los tres
  contadores `cantidad_items`, `cantidad_peliculas` y `cantidad_series`, más
  hasta tres rutas de póster recientes para la preview. La ListCard muestra el
  total como dato principal y el desglose debajo. Los nombres personalizados
  mantienen el límite de 80 caracteres y admiten letras Unicode, números,
  espacios y guiones; la unicidad por usuario no distingue mayúsculas.
- **Motivo**: el total permite comprender el tamaño de la lista sin cargar sus
  ítems; el desglose hace visible su composición (películas y series) y evita
  que la UI tenga que inferirla desde una preview incompleta. Permitir nombres
  como `Sci-Fi` coincide con el wireframe y conserva una experiencia de
  escritura natural.
- **Archivos**: `backend/listas/`, `backend/filmai/urls.py`,
  `docs/02_Especificación de Requerimientos.md`,
  `docs/04_Lineamientos_UI.md`,
  `docs/05_Plan_de_Desarrollo.md`,
  `docs/wireframes/Opcion 1/app.html`.

## 19/09/2026 — Preview de ListCard centralizada en cinco pósters

- **Decisión**: la API devuelve hasta cinco pósters recientes no vacíos en
  `preview_posters`. El límite vive en la constante privada
  `_MAX_PREVIEW_POSTERS` de `listas.views`, inicialmente con valor `5`; no se
  expone como parámetro HTTP. El wireframe ajusta las miniaturas a 32×48 px y
  3 px de separación para mostrar cinco sin desbordar la card.
- **Motivo**: centralizar la política evita valores mágicos dispersos y permite
  cambiarla posteriormente en un único punto. Cinco previews hacen más
  reconocible una lista con contenido variado sin cargar sus ítems completos.
- **Archivos**: `backend/listas/views.py`, `backend/listas/tests.py`,
  `docs/04_Lineamientos_UI.md`, `docs/05_Plan_de_Desarrollo.md`,
  `docs/wireframes/Opcion 1/app.html`,
  `openspec/specs/list-endpoints/spec.md`.

## 19/09/2026 — Nombres de listas sin guiones ni símbolos

- **Decisión**: los nombres de listas personalizadas admiten exclusivamente
  letras Unicode, números y espacios, con un máximo de 80 caracteres. Se
  conserva la normalización de espacios y la unicidad insensible a
  mayúsculas. Esta decisión reemplaza la parte de la entrada L-01 del mismo
  día que admitía guiones.
- **Motivo**: una regla de texto plano reduce casos de validación y ofrece una
  convención uniforme para el MVP. Un nombre como `Sci-Fi` debe escribirse
  como `Sci Fi`.
- **Archivos**: `backend/listas/serializers.py`, `backend/listas/tests.py`,
  `docs/02_Especificación de Requerimientos.md`,
  `docs/05_Plan_de_Desarrollo.md`,
  `openspec/specs/list-endpoints/spec.md`, `docs/decisiones.md`.

## 19/09/2026 — C-04c: el seed del catálogo muestrea por género × década × tipo, en round-robin barajado

- **Fecha**: 19/09/2026
- **Contexto**: la sync (C-04b) mantiene el catálogo fresco pero no lo hace
  crecer: lee la página 1 de cuatro listados, ~60 producciones por noche, casi
  todas repetidas. El corpus es el espacio de búsqueda semántica (B-06), y un
  corpus de éxitos del mes solo puede recomendar éxitos del mes.
- **Decisión**: `python manage.py seed_catalogo`
  (`backend/catalogo/management/commands/seed_catalogo.py`), un comando de
  management —no una tarea Celery— que recorre `/discover` por **género ×
  década × tipo** y materializa por `materializar()`, sin abrir un segundo
  camino de escritura. Spec canónica en `openspec/specs/catalog-seed/spec.md`.
  - **Muestreo, no popularidad**: 19 géneros de película × 6 décadas + 16 de
    serie × 6 = **210 combinaciones**, desde 1970 hasta la década en curso.
    Los géneros se piden a `/genre/{tipo}/list` (difieren por tipo; ids de
    TMDB, no nuestros). Dentro de cada combinación, `sort_by=vote_count.desc`:
    verificado en vivo, trae _The Shining_, _Blade Runner_ y _Die Hard_, no lo
    que trendea esta semana.
  - **Round-robin sobre un orden barajado con semilla fija**: página 1 de
    todas las combinaciones antes que la 2 de ninguna. La corrida se corta
    (por `--limite`, Ctrl-C o una notebook cerrada) y en profundidad dejaría
    todo Action y nada de Drama; en orden de declaración sesgaría al primer
    género de la lista. La semilla fija hace que dos corridas recorran el mismo
    camino, así retomar cubre el mismo terreno y un test puede afirmar el orden.
  - **Pared de 500 páginas**: `min(total_pages, 500)`. `/discover` reporta
    1001 y la página 501 devuelve HTTP 400 (verificado 18/09). Misma lección
    que los 98 páginas de `/changes` en C-04b: los números de la API son
    entrada, no verdad.
  - **`--limite` cuenta lo materializado en ESA corrida** (default 2.000). Lo
    fresco no descuenta cupo. Se eligió la lectura literal del SDD por ser la
    más simple de explicar: «hacé N más».
  - **Resumible sin estado propio**: al arrancar carga `claves_frescas()`
    —nuevo helper de solo lectura en `materialization.py`, con el **mismo
    umbral** de 90 días que `_necesita_enriquecimiento` (se extrajo
    `_umbral_de_frescura()` para que no puedan divergir)— y saltea esas
    claves sin llamar a `materializar()`. Las filas que existen pero nunca se
    enriquecieron sí se mandan. Sin archivo de progreso ni tabla de estado.
  - **Fallos por ítem y por página**: se loguean, se cuentan en `errores` y
    se sigue; una página que falla saca su combinación de la ronda. Ctrl-C
    imprime el resumen y sale sin traceback: cada `materializar()` es su
    propia transacción.
  - **`--dry-run` recorre `discover` de verdad** (cacheado 6 h) sin escribir:
    muestra el muestreo real en pantalla y una corrida real después no paga
    dos veces las llamadas.
  - **Guard en `manage.py seed`** (`usuarios/management/commands/seed.py`):
    por encima de `UMBRAL_CATALOGO_PROTEGIDO` (100, el doble de lo que crea el
    propio comando) aborta con `CommandError` y nombra `--borrar-catalogo`.
    Documentarlo en el README dependía de que alguien lo hubiera leído justo
    cuando intenta resetear su base.
- **Verificado en vivo (19/09/2026)**: `--limite 50` materializó 50 en 34 s
  (~0,7 s por producción, más rápido que la estimación de 1,5 s), todas con
  reparto, directores, keywords y `fecha_enriquecimiento`. Con 50 solo se
  alcanzan 3 combinaciones, así que la dispersión se verificó con un
  `--dry-run --limite 600`: 37 combinaciones, 26 película / 11 serie, las 6
  décadas. Con 0,7 s medidos: 2.000 ≈ 25 min, 10.000 ≈ 2 h.
- **Pendiente, a resolver con B-06 andando**: si 2.000 alcanza o vale dejar la
  máquina para 10.000; y si los géneros de TV _Talk_, _Soap_, _News_ y
  _Reality_ (que TMDB lista y el seed incluye) merecen un `--excluir-generos`.
- **Archivos**: `backend/catalogo/management/commands/seed_catalogo.py`
  (nuevo), `backend/catalogo/services/materialization.py`
  (`claves_frescas`, `_umbral_de_frescura`), `backend/catalogo/tests.py`
  (22 tests), `backend/usuarios/management/commands/seed.py` y `tests.py`
  (3 tests), `openspec/specs/catalog-seed/spec.md` (nueva), `README.md`,
  `docs/05_Plan_de_Desarrollo.md`. Se elimina `openspec/changes/catalog-seed/`
  (sección 9 de `AGENTS.md`).

## 21/09/2026 — Integración de L-01 con el seed de catálogo C-04c

- **Fecha**: 21/09/2026
- **Descripción**: al integrar la API de listas del PR #27 sobre `main`, se
  conservaron tanto el cierre de L-01 como el cierre de C-04c de los PR #28 y
  #29. El plan marca L-01 como completado y mantiene C-04c implementada. Los
  artefactos de graphify se regeneran desde el árbol combinado en lugar de
  fusionar manualmente sus archivos derivados.
- **Motivo**: las ramas modificaban las mismas secciones de seguimiento y el
  mismo grafo, aunque sus cambios funcionales no se solapan. La resolución
  preserva la intención de ambos módulos y evita reemplazar documentación o
  metadatos vigentes de catálogo con versiones anteriores de la rama de listas.
- **Archivos afectados**: `docs/05_Plan_de_Desarrollo.md`,
  `docs/decisiones.md` y `graphify-out/`.

## 26/09/2026 — Estado del plan verificado por tarea

- **Fecha**: 26/09/2026
- **Título**: Seguimiento por tarea en el plan de desarrollo.
- **Descripción**: se quitó de `docs/05_Plan_de_Desarrollo.md` el historial de PRs,
  especificaciones técnicas duplicadas, estimaciones de horas desactualizadas
  y fases con estados viejos. Cada tarea conserva su ID y tiene un estado
  respaldado por el código actual: ✅ implementada, 🟡 parcial o ⬜ pendiente.
  F-05 queda parcial porque el registro de avatares habilita 10 IDs frente a
  los 20 previstos; P-07 y B-06 también son parciales. Q-06 queda implementada
  porque el workflow de CI ya existe. Este cambio registra el estado observado;
  no modifica los contratos de dominio ni la implementación.
- **Archivos afectados**: `docs/05_Plan_de_Desarrollo.md` y
  `docs/decisiones.md`.

## 26/09/2026 — Cuadros del plan restaurados y contratos de cuenta aclarados

- **Fecha**: 26/09/2026
- **Título**: Detalle y criterios por módulo en el plan.
- **Descripción**: se restauran en `docs/05_Plan_de_Desarrollo.md` las
  dependencias, descripciones y condiciones de aceptación de las 49 tareas.
  Fuera de los cuadros queda solo una leyenda. Los módulos 2, 4 y 5 figuran
  con Gonza y Marcos como actores. El estado se contrasta con los documentos
  01–04, el código y la suite Django. C-03 documenta el passthrough real de
  TMDB; C-04a queda parcial porque los listados aún no materializan cada
  resultado expuesto, y C-04b porque falta la notificación de fallo total
  prevista en CU-021.
- **Avatar, aclarado por el usuario**: solo se eligen avatares predefinidos;
  no se suben fotos propias ni se fija un máximo de 20 opciones. El registro
  actual contiene 10 IDs y puede ampliarse. Esto reemplaza la referencia a
  20 avatares y el selector de archivos en los docs 03, 04 y README, y
  corrige la clasificación de F-05 de la entrada anterior.
- **Sesión, aclarada por el usuario**: el contrato definitivo es el del
  código: access JWT de ocho horas desde emisión y refresh JWT de siete días,
  sin cierre por inactividad. Se corrigen RNF 3.5 y CU-003 en el doc 02,
  además del README y A-03 en el plan.
- **Recuperación de contraseña, aclarada por el usuario**: se adopta el límite
  implementado por `EmailRateThrottle`: cinco solicitudes diarias por correo
  electrónico, con IP como alternativa si no se recibe un correo. Se
  corrigen CU-020 en el doc 02 y A-07 en el plan. La referencia previa a una
  solicitud por minuto por IP queda reemplazada.
- **Archivos afectados**: `README.md`, docs 02, 03, 04 y 05, y
  `docs/decisiones.md`.

---

## 26/09/2026 — C-08: eliminar la reseña conserva la calificación; moderación visible solo para el autor

- **Fecha**: 26/09/2026
- **Contexto**: `Calificacion` y `Resena` existen desde F-04 y **nada podía
  escribirlas**. Dos entregas ya mergeadas dependen de que existan: L-01
  bloquea con 409 el quitar de `Vistas` una producción calificada —y su
  mensaje pide «eliminá la calificación», que no se podía hacer—, y el
  `ResenaAdmin` de AD-01' modera reseñas que nadie podía publicar. C-08 es
  además el último backend pendiente del Módulo 2.
- **Decisión 1 — eliminar la reseña borra SOLO el texto**: la calificación
  1-10 sobrevive. Respeta que el texto es opcional (se puede calificar sin
  escribir), así que borrarlo no debería arrastrar un dato que el usuario no
  pidió borrar.
  - **Consecuencia en la UI, a corregir en `docs/04_Lineamientos_UI.md`**: el
    documento dice que tras eliminar «el botón Calificar vuelve a mostrarse».
    No puede: la calificación sigue ahí. La card «Tu reseña» desaparece (§5c
    ya dice que solo se listan reseñas _con texto_), pero el botón muestra la
    calificación vigente y abre el modal en modo editar.
  - **Por eso hay DOS endpoints de borrado**: `DELETE /api/reviews/{id}/texto/`
    (solo el texto, es el 🗑️ del modal) y `DELETE /api/reviews/{id}/` (la
    calificación y su texto por CASCADE, que es lo que el error de L-01 le
    pide al usuario). Dos rutas que hacen lo que dice su URL, en vez de una
    con un flag.
- **Decisión 2 — una reseña moderada (`Resena.activa=False`) no la ve nadie
  salvo su autor**: desaparece de «Reseñas de la comunidad», pero el autor
  sigue viéndola en su ficha y en «Mis reseñas». No se le avisa que fue
  moderada: CU-017 no lo pide y anunciarlo es una decisión de producto. Lo que
  se evita es que su texto desaparezca de sus propias pantallas sin que exista
  ninguna explicación posible.
- **Decisión 3 — el borrado del usuario es FÍSICO**; `activa` significa una
  sola cosa: moderado por un administrador (AD-01'). CU-015 pide «eliminar
  esta reseña permanentemente», y darle dos sentidos a la misma columna
  volvería imposible responder «¿por qué no se ve esta reseña?».
  `Calificacion.activa` lo escribe siempre en `True` esta API, pero todas las
  lecturas lo filtran, para que el día que AD-01 modere calificaciones no haya
  que tocar nada acá.
- **Decisión 4 — los tres `GET` entran en el alcance**, aunque el plan solo
  listaba `POST | PUT | DELETE`: la ficha (§5c) necesita «Reseñas de la
  comunidad (N)» con «Cargar más» y «Mis reseñas» (§5i) un scroll infinito.
  Sin lectura esas pantallas no tienen de dónde sacar datos. La fila del plan
  se corrige en vez de seguirse literal.
- **Decisión 5 — escribe por `materializar()`**, igual que L-01: es el quinto
  llamador del único camino de escritura del catálogo (tras C-04a, C-04b,
  C-04c y L-01). Se puede calificar desde un resultado de búsqueda que ninguna
  ficha abrió, y la FK tiene que apuntar a una fila completa.
- **Lo que C-08 NO toca**: `calificacion_promedio` (es el `vote_average` de
  TMDB, no el promedio de nuestros usuarios — mezclarlos cambiaría el
  significado de un campo que tres pantallas muestran); el embedding (el texto
  canónico no incluye calificaciones, así que no hay nada que regenerar); y la
  pertenencia a listas (calificar no agrega a `Vistas`: sería escribir en las
  tablas de otro módulo en silencio).
  - **Reemplazada el 30/09/2026** por la regla «calificada ⇒ en Vistas» (ver la
    entrada del 30/09/2026 al final de este archivo): calificar agrega la
    producción a `Vistas` y borrar la calificación la saca, con la escritura en
    `Tiene` expuesta por `listas/services.py` en vez de armada desde `catalogo`.
- **SDD**: `openspec/changes/reviews-api/{proposal,design,tasks}.md`.
- **Origen**: preguntas del usuario al retomar el backend del Módulo 2, y el
  hallazgo de que el mensaje de error de L-01 pedía una acción que la API no
  ofrecía.

---

## 21/09/2026 — Se elimina la revisión de pull requests

- **Fecha**: 21/09/2026 (registrado el 26/09/2026)
- **Decisión**: no se revisan más los pull requests. Cada uno mergea su propio
  trabajo a `main` en cuanto el CI está verde, y le deja al otro un resumen en
  markdown de lo que entró.
- **Motivo**: con los bots ya desactivados el 18/09 (93% de falsos positivos en
  AI Review, prueba de CodeRabbit expirada), la revisión manual entre dos
  personas que trabajan en módulos separados agregaba espera sin agregar
  hallazgos: en la práctica ninguno de los dos leía el módulo del otro con
  suficiente contexto para encontrar algo que el CI no viera.
- **Qué queda como control**: el CI (`ruff check`, `ruff format --check` y
  `python manage.py test`) sobre PRs contra `main` y contra `feat/**`. Al no
  haber un segundo lector, el peso recae en los tests y en el registro de
  decisiones: una entrega sin tests del comportamiento nuevo ya no la frena
  nadie.
- **Merge commit, no squash**: se deja de squashear. El squash rompía los PRs
  apilados (los commits de la rama base quedan con otro identificador y el
  apilado necesita rebase) y hacía perder commits pusheados mientras el merge
  estaba en curso — pasó con el rename del PR #23.
- **Archivos afectados**: `AGENTS.md` (sección 8), `docs/decisiones.md`.

---

## 26/09/2026 — C-08 implementado: la API de reseñas, el flag de `Vistas` y un bug de C-04a

- **Fecha**: 26/09/2026
- **Contexto**: continuación de la entrada anterior, ya con código. Ver
  `openspec/specs/reviews-api/spec.md` para el contrato completo.
- **Qué quedó**: `POST /api/reviews/`, `PUT /api/reviews/{id}/`,
  `DELETE /api/reviews/{id}/texto/` (solo el texto),
  `DELETE /api/reviews/{id}/` (ambas) y los tres `GET`
  (`?id_tmdb=&tipo=` para la comunidad, `mias/` para P-06 y
  `mias/?id_tmdb=&tipo=` para la ficha). 65 pruebas nuevas.
- **`?borrar_calificacion=true` en el endpoint de listas** (aprobado por Marcos
  el 26/09): quitar de «Vistas» una producción calificada seguía respondiendo
  409 —lo pide CU-011—, pero ahora la UI puede advertir qué se pierde y
  confirmarlo en un paso. Las dos escrituras van en **una transacción**: dos
  llamadas desde el frontend no serían atómicas y un fallo entre ellas dejaría
  al usuario sin la calificación y con la producción todavía en «Vistas». El
  flag es permiso y no orden: sin calificación es un borrado normal, y en otra
  lista no borra nada. Un valor que no sea `true` ni `false` da 400 en vez de
  adivinarse, porque un typo leído como `false` respondería 409 a alguien que
  ya confirmó.
- **Bug encontrado y corregido en C-04a**: `materializar()` devolvía la fila con
  `fecha_lanzamiento` como el **string** de TMDB (`"1999-10-15"`), porque
  `_enriquecer()` asignaba el valor del JSON a un `DateField` y no volvía a
  leerla. Quien serializara ese retorno se llevaba el string: el
  `POST /api/lists/{id}/items/` de L-01 moría con
  `AttributeError: 'str' object has no attribute 'year'`, o sea **un 500 al
  agregar a cualquier lista una producción que no estuviera ya en la base**.
  Se arregla en la raíz con `refresh_from_db()` al final de `_enriquecer()`, con
  tres pruebas propias. Lo destapó la prueba de integración de C-08; no se veía
  antes porque las pruebas de listas usan la factory (que escribe un `date`
  real) o mockean `materializar()` entera. **Es otra vez la lección de C-04b: un
  test con todo mockeado prueba el llamado, no el efecto.**
- **Doc 04 corregido**: decía que al eliminar «el botón Calificar vuelve a
  mostrarse», imposible ahora que la calificación sobrevive. La card «Tu
  reseña» desaparece, el botón muestra la nota vigente y abre el modal en modo
  editar, y se documenta la acción aparte «Quitar calificación» y la
  confirmación al quitar de «Vistas».
- **Archivos afectados**: `backend/catalogo/{reviews,serializers_reviews,
pagination_reviews,exceptions,tests_reviews}.py`,
  `backend/catalogo/services/materialization.py`, `backend/catalogo/tests.py`,
  `backend/listas/{views,serializers,tests}.py`, `backend/filmai/urls.py`,
  `openspec/specs/reviews-api/spec.md`, docs 04 y 05.

---

## 30/09/2026 — Calificada implica vista: calificar agrega a «Vistas» y borrar la calificación la saca

- **Fecha**: 30/09/2026
- **Contexto**: CU-011 ya pedía una mitad de la regla: no se puede sacar de
  «Vistas» una producción calificada sin eliminar antes la calificación (el
  409 de L-01, con la confirmación en un paso de C-08). La otra mitad no
  existía: se podía calificar algo que no estaba en «Vistas», y la ficha
  mostraría `⭐ 9/10` con el ojo 👁 apagado, justo el estado que CU-011 intenta
  evitar. El doc 04 (§5c) y el código de L-01 ya lo decían con esas palabras:
  «si la calificaste, la viste».
- **Decisión** (del usuario, acordada con Marcos): toda producción calificada
  está en «Vistas». Los cuatro casos:
  - **Entra 1**: calificar la agrega a «Vistas». El modal de calificación lo
    avisa antes de publicar, si todavía no estaba.
  - **Entra 2**: se puede marcar como vista sin calificar, en cualquier
    momento. La inversa de la regla no rige.
  - **Sale 1**: eliminar la calificación la saca de «Vistas». El modal de
    confirmación lo avisa, y el usuario puede volver a marcarla.
  - **Sale 2**: sacarla de «Vistas» elimina la calificación, con la
    confirmación previa que ya existía (`?borrar_calificacion=true`).
  - Editar la calificación o eliminar solo el texto de la reseña no cambian
    «Vistas». La reseña cae con la calificación por CASCADE, como antes.
- **Reemplaza** a la decisión de C-08 del 26/09/2026 «calificar no agrega a
  `Vistas`: sería escribir en las tablas de otro módulo en silencio». La
  escritura deja de ser silenciosa (la regla está en los docs 02 y 04 y en las
  specs) y pasa por el módulo dueño: `listas/services.py` expone
  `agregar_a_vistas()` y `quitar_de_vistas()`, que C-08 llama dentro de su
  propia transacción. Sin la lista «Vistas», calificar falla entero (500) en
  vez de dejar una nota que viole la regla; ese estado lo repara
  `reparar_recursos_usuarios`.
- **Caso aceptado**: si alguien marca una producción como vista, después la
  califica y después borra la calificación, sale de «Vistas» aunque la había
  marcado antes. `Tiene` no guarda el motivo de la pertenencia y agregarlo
  sumaba una migración de esquema en el módulo de listas. Se prefirió la regla
  simple con el aviso en el modal.
- **Datos existentes**: la migración de datos `listas.0004_calificadas_en_vistas`
  agrega a «Vistas» las calificaciones previas (las 34 de
  `seed --solo-resenas` en la base de Marcos). Su reverse no hace nada: no se
  puede distinguir lo que agregó de lo que el usuario marcó a mano. El `seed`
  crea las notas con la factory, sin pasar por la API, así que aplica la regla
  él mismo.
- **UI** (se implementa en C-07 y P-06): los textos del aviso de calificar,
  del modal «Quitar calificación» con y sin reseña, y los toasts según haya o
  no texto («Calificación publicada.» / «Calificación y reseña publicadas.»)
  quedan en el doc 04 §5c y §5d.
- **Archivos afectados**: `backend/listas/services.py` (nuevo),
  `backend/listas/migrations/0004_calificadas_en_vistas.py` (nueva),
  `backend/catalogo/reviews.py`, `backend/usuarios/management/commands/seed.py`,
  `backend/catalogo/tests_reviews.py`, `backend/listas/tests.py`,
  `backend/usuarios/tests.py`, docs 02, 04 y 05, y las specs `reviews-api`,
  `list-endpoints` y `development-seed`.

---

## 30/09/2026 — El contenido de TMDB sigue en inglés, por ahora

> Decisión de alcance reemplazada el 08/10/2026 por el plan de multiidioma y
> la elección de `es-MX` registrada abajo. El comportamiento actual se conserva
> hasta implementar F6; esta entrada permanece como antecedente histórico.

- **Fecha**: 30/09/2026
- **Hallazgo**: el cliente de TMDB (`catalogo/client.py`) nunca manda el
  parámetro `language`, así que TMDB responde en su idioma por defecto
  (en-US): títulos, sinopsis y géneros llegan en inglés, y así quedaron también
  las producciones materializadas (`generos` guarda nombres como `Action`). No
  era una decisión registrada; no se notaba porque ninguna pantalla lo mostraba
  hasta el Home (C-05).
- **Verificado en vivo**: con `es-MX` los títulos y géneros llegan traducidos
  («Resident Evil: Noche cero», «Acción») y 7 de 80 sinopsis de tendencias y
  cartelera llegan vacías; con `es-ES`, 5 de 80.
- **Decisión** (del usuario): seguir en inglés por ahora, para no frenar C-05.
- **Costo de cambiarlo después**: agregar `language` en el cliente, vaciar la
  caché de Redis (si no, sirve respuestas viejas hasta que venzan), volver a
  enriquecer el catálogo materializado y decidir qué mostrar cuando la sinopsis
  llega vacía. Todo lo que compare géneros por nombre depende del idioma de lo
  guardado.
- **Archivos afectados**: ninguno; solo `docs/decisiones.md`.

---

## 30/09/2026 — El Home separa películas y series con un selector global (C-05)

- **Fecha**: 30/09/2026
- **Decisión** (del usuario): el Home tiene un selector `Todo · Películas ·
Series` arriba de las filas. «Todo» es el valor por defecto y mezcla los dos
  tipos, como pide hoy el doc 04 §5; las otras dos opciones cambian la fuente
  de cada fila.
- **Alternativas descartadas**: filas mezcladas sin selector (no deja mirar
  solo series), filas separadas por tipo (seis filas más el Hero, muy largo en
  mobile y siete pedidos al cargar) y un selector por fila (tres controles que
  hacen lo mismo).
- **Motivo**: Buscar (C-06) ya pide el mismo selector, así que se construye una
  vez y la app queda consistente. En «Recomendado para ti» cada tipo usa los
  géneros de lo que el usuario calificó de ese tipo, y «Todo» es la unión: no
  hace falta traducir géneros entre películas y series (TMDB los nombra
  distinto; `Action` en películas es `Action & Adventure` en series). La fila
  excluye solo lo que está en «Vistas», que con la regla anterior incluye todo
  lo calificado.
- **Pendiente**: el doc 04 §5 y el diseño completo se actualizan en el SDD de
  C-05.
- **Archivos afectados**: ninguno todavía; solo `docs/decisiones.md`.

---

## 03/10/2026 — P-06: el toast de quitar calificación nombra la reseña, y su UI pasa a `profile-ui`

- **Fecha**: 03/10/2026
- **Descripción**: al quitar una calificación desde «Mis reseñas», el toast decía
  siempre «Calificación eliminada.», aunque la reseña se borrara con ella. Ahora
  dice «Calificación y reseña eliminadas.» cuando había texto, como pide el doc
  04 §5d desde el 30/09. El requisito de UI de «Mis reseñas», que había quedado
  en la spec `reviews-api` después de «Known limitations», pasa a
  `profile-ui`; en `reviews-api` queda solo lo que es de la API, como requisito
  propio: el `cursor` no selecciona la respuesta de una sola ficha.
- **Archivos afectados**: `frontend/components/MisResenas.tsx`,
  `frontend/tests/mis-resenas.test.tsx`, `openspec/specs/reviews-api/spec.md`,
  `openspec/specs/profile-ui/spec.md`.

---

## 07/10/2026 — OT-03: build de producción en CI y locale de Playwright

- **Fecha**: 07/10/2026
- **Descripción**: el job de frontend ejecuta `npm run build`, que usa
  `next build --turbopack`, para detectar errores de compilación y renderizado
  de producción antes de integrar cambios. Playwright fija `locale: "es-AR"`
  para que los formatos y el idioma del navegador sean reproducibles, como
  exige F0 del plan de multiidioma. No se modifica ningún test existente.
- **Archivos afectados**: `.github/workflows/ci.yml`,
  `frontend/playwright.config.ts` y `docs/plan-multiidioma.md`.

---

## 07/10/2026 — OT-02: referencias de correos y del esquema antes del multiidioma

- **Fecha**: 07/10/2026
- **Descripción**: se caracteriza la salida real de los cuatro flujos de correo
  (asunto, texto y HTML), normalizando únicamente las claves y tokens de los
  enlaces. La notificación de contraseña actualizada conserva su ausencia
  actual de HTML. Las referencias solo se regeneran con
  `FILMAI_ACTUALIZAR_REFERENCIAS=1`; la ejecución normal falla ante divergencias.
  El contrato OpenAPI se captura con el comando `spectacular` y se compara
  semánticamente para que el formato del YAML no genere diferencias falsas.
  Se conserva la salida actual del generador, que informa 14 advertencias
  (11 únicas) y 100 errores de introspección (21 únicos), principalmente por
  vistas sin serializer declarado: este archivo no garantiza una descripción
  completa de todos los endpoints.
- **Comprobación de comportamiento**: los mensajes específicos de cuenta
  inactiva se lanzan antes de validar la contraseña, por correo o nombre de
  usuario, y HTTP los reemplaza por el 403 genérico de permisos. La baja real
  conserva la reseña, la nota y el nombre del autor en la comunidad. Esta orden
  no cambia ninguno de esos comportamientos; la validación previa de credenciales
  corresponde a F3.
- **Archivos afectados**: `backend/filmai/tests_correos_contrato.py`,
  `backend/filmai/tests_esquema.py`, `backend/filmai/tests_estado_cuenta.py`,
  `backend/filmai/tests_golden/correos/`, `contracts/openapi.yaml`,
  `openspec/specs/admin-api-docs/spec.md`, `openspec/specs/reviews-api/spec.md`
  y `docs/plan-multiidioma.md`.

## 07/10/2026 — Caracterización del contrato de respuestas previo a multiidioma

- **Fecha**: 07/10/2026
- **Descripción**: se agregaron pruebas de caracterización en `backend/filmai/tests_contrato.py` y
  referencias JSON en `backend/filmai/tests_golden/api/`. Comparan el estado HTTP y
  el cuerpo completo que produce el código actual, con `DEBUG=False` y `es-ar`.
  La regeneración solo se permite con `REGENERAR_REFERENCIAS_API=1`; una ejecución
  normal nunca reescribe referencias. Esto permite detectar cambios involuntarios
  al introducir el contrato de códigos en las siguientes órdenes.

Se ejercitan endpoints y serializers reales. Google se aísla en la frontera
OAuth y TMDB en el transporte HTTP; los mensajes siguen siendo los que genera
el código de producción. Las ramas defensivas se distinguen de los flujos HTTP
en `backend/filmai/tests_golden/README.md`. La spec
`openspec/specs/api-characterization/spec.md` describe esta red de seguridad.
No se modificaron comportamiento ni tests existentes.

La verificación combinada de F0 detectó que algunos escenarios de catálogo
inicializaban el servicio singleton antes de rechazar parámetros inválidos.
Las nuevas pruebas limpian esa caché en `setUp` y mediante `addCleanup`, que
Django ejecuta también ante un fallo. Así no alteran el estado que reciben
otros tests; los cuerpos de referencia y los tests existentes se conservan.

---

## 08/10/2026 — Multiidioma: decisiones del plan y alcance de implementación

- **Fecha**: 08/10/2026
- **Descripción**: se registra el diseño aprobado de `docs/plan-multiidioma.md`,
  secciones 1 a 4 y respuestas de la sección 9. Este registro define el trabajo
  pendiente; no afirma que F2 a F9 estén implementadas.

| Decisión                        | Regla acordada                                                                                                                                                                                                                                                                                                                                 |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1: idiomas e infraestructura   | Inglés y español; inglés nativo de los diseños y por defecto. Frontend con next-intl 4.x, mensajes ICU y sin prefijos de idioma en las rutas.                                                                                                                                                                                                  |
| D2: resolución y persistencia   | La cuenta es la fuente de verdad con sesión; la cookie `filmai_locale` es su espejo para renderizar. Selector autenticado guarda preferencias y cookie; sin sesión solo cookie. Login sincroniza el idioma guardado. Backend resuelve cuenta, `Accept-Language`, `en`, en ese orden. Registro local y Google guardan el idioma del encabezado. |
| D3: responsabilidad del backend | El backend emite códigos, no traducciones de respuestas. `LANGUAGE_CODE` sigue en `es-ar`, sin LocaleMiddleware. Solo correos y TMDB consumen el idioma efectivo. El chatbot queda fuera de la implementación.                                                                                                                                 |
| D4 y D5: contrato de errores    | Sobre `code`, `params`, `errors`; cada error tiene `field` o nulo, `code` y `params`. Códigos ingleses snake_case; campos y enumeraciones actuales siguen en español. `debug` solo con DEBUG=True y nunca se muestra en frontend. Catálogo único y exportación versionada.                                                                     |
| D6: enumeraciones               | `Lista.clave` identifica `favoritos`, `pendientes`, `vistas`; nulo para personalizadas. Nombres almacenados en español; etiquetas traducidas en frontend. Se reservan nombres predeterminados en ambos idiomas y se unifica género por valor estable.                                                                                          |
| D7: texto de interfaz y baja    | Se preservan los textos y comportamiento de baja de cuenta. La migración actual es intermedia: capas compartidas y tres pilotos; las pantallas restantes conservan español fijo hasta su rediseño.                                                                                                                                             |
| D8: contenido de TMDB           | Idioma por request, caché por idioma y fallback campo por campo a inglés. Persistencia canónica y embeddings en inglés; traducciones en `ProduccionTraduccion`, géneros identificados por ID. Pósters por idioma, con respaldo al original.                                                                                                    |
| D9: formatos                    | Intl con `en-US` y `es-AR`; fecha medium/long en ambos idiomas. Se acepta «28 sept 2026» y se corrigen los diseños. Duración con NumberFormat: narrow en inglés y short en español («2 h 49 min»). Toda lógica de formato se centraliza.                                                                                                       |
| D10: rutas                      | Rutas visibles en inglés, incluida `/complete-signup`; constantes compartidas. Backend, frontend y tests cambian juntos. No se necesitan redirecciones: no hay producción ni enlaces permanentes emitidos.                                                                                                                                     |
| D11: vocabulario y alcance      | Glosario en `docs/i18n/glosario.md`; copia española con voseo. No se incorporan instrucciones del sistema de diseño, nombres de mesas de trabajo ni datos de muestra como textos de interfaz.                                                                                                                                                  |
| D12: correos                    | Cuatro casos en texto y HTML, plantillas por idioma con base y servicio compartidos. Idioma del destinatario; vigencias por contexto (24 horas de confirmación, 1 hora de restablecimiento).                                                                                                                                                   |
| D13: catálogos                  | `equivalencias.json` queda inmutable (634 entradas, 41 pantallas). CSV por fila con clave, namespace y estado. Fragmentos se recomponen con ICU; se excluyen muestras/diseño/chatbot. Errores y selector nuevos requieren aprobación de copia antes de sembrar.                                                                                |

La ventana de compatibilidad F3–F7 conserva las claves anteriores junto al sobre
nuevo. F8 primero migra las aserciones y después elimina las claves anteriores.
Los estados `account_deactivated` y `account_pending_confirmation` se revelan
únicamente después de validar contraseña o token de Google; credenciales
incorrectas siempre producen `invalid_credentials`.

Se migran Preferencias y las pantallas de confirmación y restablecimiento como
pilotos. Login, registro, completar Google, perfil, reseñas, navbar y modales
conservan textos heredados y una lista de excepciones de lint que solo disminuye.
Las capas compartidas, errores, validación, etiquetas, formatos, metadatos y rutas
sí se adaptan. La interfaz mixta es una consecuencia aceptada, sin usuarios reales.

Las cuentas existentes no reciben relleno de idioma: la semilla crea cuentas
conocidas en `es` y `en`. Idioma nulo queda para altas externas al registro
(superusuario y Admin); se usa el encabezado hasta que el usuario elija.
Las correcciones menores de la tabla se aplican a la curaduría; el original no
se reescribe. La duración y los formatos de miles se obtienen de Intl, no de
literales de los diseños. Estas reglas incorporan las 14 respuestas de la sección 9.

- **Archivos afectados**: `docs/decisiones.md`, `docs/i18n/glosario.md` y
  `docs/plan-multiidioma.md`. Los archivos de producción se modifican en sus OT.

---

## 08/10/2026 — TMDB en español mexicano con respaldo a inglés

- **Fecha**: 08/10/2026
- **Descripción**: por decisión del usuario, español usa `es-MX` e inglés
  `en-US` al consultar TMDB. Una variante fija evita selección regional por
  usuario o país y prioriza títulos de distribución latinoamericana. La medición
  histórica tuvo 7 sinopsis vacías de 80 con es-MX frente a 5 con es-ES; F6 cubre
  los campos vacíos con la versión inglesa e identifica el respaldo en la API.
  Los pósters cambian por idioma con respaldo al original. Esto reemplaza la
  decisión de alcance de mantener TMDB únicamente en inglés del 30/09/2026;
  el corpus de embeddings y la producción canónica continúan en inglés.
- **Archivos afectados**: `docs/decisiones.md`; implementación posterior en
  `backend/filmai/idioma.py`, cliente, servicios y modelos de catálogo.

---

## 08/10/2026 — Baja de cuenta: cuestión de copia conservada para revisión futura

- **Fecha**: 08/10/2026
- **Descripción**: el usuario decidió no cambiar copia ni comportamiento de baja
  en este trabajo. La baja es lógica y conserva todos los datos. Un administrador
  puede reactivar desde Django Admin, pero el usuario no puede hacerlo solo.
  Reseñas y calificaciones continúan públicas con nombre de usuario; correo y
  username siguen ocupados. La copia dice «irreversible» y no permite reactivar:
  describe la capacidad del usuario, no la del administrador. Los términos hablan
  de baja definitiva y supresión de datos a pedido, cuyo circuito no existe hoy;
  la interfaz no avisa que las reseñas permanecen públicas. Queda como cuestión
  pendiente para otro alcance, sin cambiar estos textos al sembrar catálogos.
- **Archivos afectados**: `docs/decisiones.md`; no se modifica la lógica de baja.

---

## 08/10/2026 — Ejecución de multiidioma fuera de main y excepciones de pruebas

- **Fecha**: 08/10/2026
- **Descripción**: el usuario amplió la sesión al resto del plan, autorizó agentes
  paralelos y eligió una rama de integración con PRs por orden. Los cambios se
  mantienen en `feat/i18n-multiidioma`; el PR de seguimiento #43 permanece en draft.
  No se permite merge a main, incluso con CI verde. Las entregas se integran
  únicamente en esa rama después de verificar sus checks.
  Se autorizó `size:exception` solo para OT-01. Se autoriza adaptar exclusivamente
  las nuevas pruebas y referencias de F0 cuando las fases cambien deliberadamente
  el comportamiento: en OT-30 se afirma la proyección heredada durante emisión
  doble y se prueba el sobre nuevo por separado. Los tests anteriores al plan
  mantienen las restricciones y excepciones originales.
  Ante la contradicción del doc 02 sobre enlaces permanentes, el usuario confirmó
  conservar la vigencia actual de 24 horas y corregir ese documento al alinearlo.
- **Archivos afectados**: `docs/decisiones.md`, `docs/plan-multiidioma.md`;
  pruebas nuevas de F0 al implementar cambios deliberados y doc 02 al cerrar.

---

## 08/10/2026 — Curaduría trazable por grupos de pantallas

- **Fecha**: 08/10/2026
- **Descripción**: OT-12 conserva la tabla original y registra en CSV cada ID,
  texto y pantalla de origen junto a la clave semántica, estado y texto curado.
  Los fragmentos se proponen como mensajes completos ICU; las claves de pantallas
  futuras quedan provisionales hasta implementar sus diseños. Se entrega en tres
  bloques por grupos para facilitar revisión, sin sembrar catálogos todavía.
  El primer bloque cubre las entradas 1–270; los dos siguientes completan 634.
  La aprobación editorial pertenece a OT-13.
- **Archivos afectados**: `docs/i18n/claves.csv`, `docs/i18n/README.md`,
  `docs/plan-multiidioma.md`.

---

## 08/10/2026 — Catálogo y correspondencia del contrato de errores

- **Fecha**: 08/10/2026
- **Descripción**: OT-11 especifica el sobre, códigos, parámetros, normalización
  de terceros y respuestas exitosas. El CSV documenta las 91 referencias de F0
  y todas sus cadenas distintas, fuentes defensivas y exclusiones fuera de API.
  El catálogo ejecutable y la exportación quedan para F3; la copia para OT-13.
  No cambian producción ni tests. Se conserva la emisión doble y se validan
  credenciales antes de revelar estados de cuenta. El usuario aprobó códigos
  por significado con estados HTTP por contexto, conservando el estado actual
  (credenciales: 400 en login, 401 en autenticación; username: 400 en validación,
  409 en perfil). También aprobó propagar Retry-After real de TMDB y omitir
  parámetro/encabezado si se desconoce la espera, sin inventar segundos.
- **Archivos afectados**: `openspec/specs/error-contract/spec.md`,
  `docs/i18n/errores.csv`, `docs/decisiones.md` y `docs/plan-multiidioma.md`.

---

## 08/10/2026 — Aprobación editorial y resolución de la curaduría multiidioma

- **Fecha**: 08/10/2026
- **Descripción**: el usuario aprobó las 91 filas bilingües de OT-13 y resolvió
  las seis dudas. Las confirmaciones 214/215 reutilizan frases completas de
  eliminación; 355 es la etiqueta de contraseña; 448 es metadato de locale
  excluido; 535 es un encabezado autónomo y 320 filtra una nota exacta X/10.
  Los mensajes de credenciales cubren Google y contraseña, el límite compartido
  con TMDB no culpa al usuario y el reenvío evita prometer un envío que no ocurre
  para destinatarios desconocidos o ya confirmados. Se preservan los originales
  y los textos de baja. El CSV tiene 451 filas utilizables y 425 claves distintas,
  sin incoherentes. Las specs aprobadas definen requisitos aún por implementar;
  la aprobación no afirma cambios de producción ni cierre de CI.
- **Archivos afectados**: `docs/i18n/copia-propuesta.csv`, `claves.csv`,
  `revision-ot13.md`, `README.md`, `docs/plan-multiidioma.md`,
  `openspec/specs/i18n-core/spec.md` y `openspec/specs/emails/spec.md`.

---

## 08/10/2026 — Núcleo de idioma por operación (OT-20, primera entrega)

- **Fecha**: 08/10/2026
- **Descripción**: se agrega `Usuario.idioma` nullable con opciones `en`/`es`,
  sin relleno de cuentas anteriores. `idioma_efectivo` prioriza la cuenta,
  luego el encabezado HTTP analizado por Django y por último inglés. Descarta
  preferencias con peso cero y resuelve regiones al idioma base. Mantiene
  `LANGUAGE_CODE=es-ar` y no activa traducción global. Preferencias, altas y
  semilla se completan en las siguientes entregas de OT-20.
- **Verificación**: cuatro tests nuevos cubren negociación, prioridad de cuenta
  explícita, aislamiento del locale global y migración real ida/vuelta de una
  cuenta previa. Pasan en 1,013 s; Ruff sin errores. No se aplicó la migración
  ni se ejecutó la semilla contra la base de desarrollo.
- **Archivos afectados**: configuración, modelo y migración de usuarios,
  `filmai/idioma.py`, sus tests, doc 03 y spec `i18n-core`.

## 08/10/2026 — Excepciones acotadas de verificación del plan

- **Fecha**: 08/10/2026
- **Descripción**: el usuario autorizó ajustar las igualdades exactas anteriores
  al plan para errores de confirmación, restablecimiento, documentación y TMDB
  en OT-31/32. Se conserva el HTTP y la expectativa de cada campo heredado;
  el sobre nuevo se prueba por separado. No habilita cambios a otros tests.
  También autorizó reparar recursos faltantes del superusuario únicamente en
  la copia temporal del volcado de OT-42, antes de establecer su referencia;
  la base de desarrollo original permanece intacta. Para OT-70 aprobó el
  título transitorio «Mis reseñas» / “My reviews”.
- **Archivos afectados al implementar**: tests de usuarios y filmai de OT-31/32,
  registro de verificación de OT-42 y catálogo transitorio de OT-70. Las
  autorizaciones se conservan en las notas del plan; esta entrada no afirma
  que dichas órdenes estén implementadas.

---

## 08/10/2026 — Idioma en preferencias y altas (OT-20, segunda entrega)

- **Fecha**: 08/10/2026
- **Descripción**: preferencias acepta `en`/`es`; rechaza nulo o valores
  no soportados. Nulo se conserva para lectura de cuentas anteriores y altas
  fuera del registro. Detalles y perfil exponen el campo solo en lectura.
  Ambos adaptadores guardan el idioma de la cuenta nueva; el retorno temprano
  de Google mantiene el idioma de cuentas existentes. `Accept-Language` no
  necesita configuración CORS adicional porque es un encabezado permitido
  directamente por el navegador. El esquema distingue lectura nullable y
  escritura restringida mediante un serializer de respuesta.
- **Verificación**: once tests de idioma/preferencias aprobados (4,071 s),
  incluido guardado social real con la frontera OAuth aislada; esquema F0
  regenerado por la autorización vigente, conservando su prueba de paridad.
  Solo se amplía la igualdad exacta de preferencias autorizada por F2.
- **Archivos afectados**: adaptadores, serializers, preferencias, tests de
  usuarios, `contracts/openapi.yaml`, doc 03, plan y spec `i18n-core`.

---

## 08/10/2026 — Cuentas ES/EN conocidas en la semilla (OT-20, tercera entrega)

- **Fecha**: 08/10/2026
- **Descripción**: el seed completo asigna español a usuario001/usuario003 e
  inglés a usuario002, manteniendo sus credenciales. El modo de reseñas no
  asigna ni reemplaza idiomas. El README documenta esas cuentas y el contrato
  de preferencias. No se resetea la base automáticamente ni se rellena el
  idioma de usuarios previos; el integrante decide cuándo usar el seed.
- **Verificación**: dos tests pasan en 3,663 s sobre la base de pruebas:
  recreación repetida con idiomas deterministas y conservación del admin;
  modo de reseñas conservando un idioma guardado y uno nulo. Suite completa
  backend: 520 tests en 184,491 s, con cinco fallos de autenticación 401 en
  subcasos de una prueba anterior de preferencias. La entrega API previa pasó
  su CI completo y los tests enfocados; se investiga la causa antes del cierre.
  La repetición normal completa pasó: 520 tests en 190,527 s. El rechazo
  intermitente anterior quedó registrado, sin causa determinada ni cambios
  a sus oráculos. Frontend conserva el árbol validado en OT-13.
- **Archivos afectados**: `seed.py`, test de semilla, README, plan y specs
  `development-seed` e `i18n-core`.

---

## 08/10/2026 — Catálogo general y excepción tipada de OT-30

- **Fecha**: 08/10/2026
- **Descripción**: se inicia OT-30 con un registro de códigos generales, de
  dominio y de éxito, sus mensajes internos y estados por contexto. Login y
  autenticación conservan 400/401 para `invalid_credentials`; validación y perfil
  conservan 400/409 para `username_already_used`. La excepción base exige un
  contexto cuando hay más de uno, rechaza códigos desconocidos y valida tipos
  y rangos de parámetros. Cero segundos es una espera conocida válida. Los
  códigos de éxito se registran sin alterar respuestas existentes. Esta unidad
  todavía no integra el manejador ni el catálogo de hojas de validación.
- **Archivos afectados**: `backend/filmai/errores/{__init__,catalogo,base}.py`,
  `backend/filmai/test_catalogo_errores.py` y `openspec/specs/error-contract/spec.md`.

---

## 08/10/2026 — Hojas y metadatos de validación de OT-30

- **Fecha**: 08/10/2026
- **Descripción**: se completa el catálogo de hojas de validación y se introduce
  una excepción que conserva parámetros por ruta después de la conversión de
  DRF. Los errores Django agregados se convierten antes de perder sus códigos;
  solo se copian parámetros declarados o límites provistos explícitamente por
  el validador, excluyendo valores sensibles. Se rechazan límites no finitos,
  booleanos como números y metadatos sin una hoja correspondiente. Esta unidad
  todavía no modifica validadores de dominio ni el manejador de producción.
- **Archivos afectados**: `backend/filmai/errores/{catalogo,validacion}.py`,
  `backend/filmai/test_metadatos_errores.py` y `openspec/specs/error-contract/spec.md`.

---

## 08/10/2026 — Composición y compatibilidad del sobre de OT-30

- **Fecha**: 08/10/2026
- **Descripción**: una función independiente del transporte construye el sobre
  registrado y otra lo agrega sin reemplazar campos heredados. Cada hoja de
  validación conserva su orden, campo y parámetros; los índices de mensajes
  no forman parte del campo, mientras los elementos de serializers anidados
  usan rutas como `items.0.nombre`. Las listas generales conservan su contenido
  bajo `non_field_errors`. Se validan estados, formas y colisiones reservadas;
  `debug` solo se agrega al habilitarlo explícitamente. El portador de metadatos
  debe construirse después de la última conversión de DRF: no se promete que
  sobreviva a `validate` o `validate_<field>`. La adopción de esa frontera en
  módulos reales corresponde a OT-31 y OT-32.
- **Archivos afectados**: `backend/filmai/errores/sobre.py`,
  `backend/filmai/test_sobre_errores.py` y `openspec/specs/error-contract/spec.md`.

---

## 08/10/2026 — Emisión doble del manejador y oráculos F0 de OT-30

- **Fecha**: 08/10/2026
- **Descripción**: el manejador agrega códigos, parámetros y hojas al cuerpo
  heredado de las excepciones DRF reconocidas, conservando HTTP y encabezados.
  Los métodos y formatos de contenido provienen del request; no se interpretan
  mensajes. El retorno TMDB y los endpoints con respuestas directas permanecen
  para OT-31/OT-32; la cobertura obligatoria de códigos se cierra en OT-34.
  Se aplicó la autorización vigente del usuario para adaptar los tests nuevos
  de F0: OT-01 compara campos heredados y contenido de listas raíz, mientras
  OT-02 conserva completa su matriz de estados/credenciales y compara el detalle
  anterior. Los tests nuevos prueban el sobre por separado, incluido HTTP real.
  También se conserva el 403 y detalle de `PermissionDenied` de Django, que
  DRF reconoce aunque carezca de `default_code`; se prueba en ambos modos DEBUG.
  No se modifican tests anteriores al plan ni archivos de referencia originales.
- **Archivos afectados**: `backend/filmai/exceptions.py`,
  `backend/filmai/{tests_contrato,tests_estado_cuenta,test_manejador_sobre}.py` y
  `openspec/specs/error-contract/spec.md`.

---

## 08/10/2026 — Clave estable para las listas existentes (OT-40)

- **Fecha**: 08/10/2026
- **Descripción**: se agrega `Lista.clave` nullable con los valores
  `favoritos`, `pendientes` y `vistas`. La migración `0005_lista_clave` asigna
  las claves a las predeterminadas existentes por `Lower(nombre)` y rechaza
  explícitamente los nombres desconocidos antes de escribir. Las
  personalizadas permanecen sin clave, incluso si comparten una etiqueta del
  sistema. La reversión vacía las claves y quita la columna sin perder filas.
- **Motivo**: separar la identidad del texto mostrado permite localizar las
  etiquetas sin cambiar nombres ni relaciones. Se conserva la nulabilidad
  hasta que OT-41 adapte la provisión y los consumidores; OT-42 agregará las
  restricciones. Se prueba el viaje real del esquema y los datos con
  `MigrationExecutor`, en una base de tests aislada de desarrollo. Las otras
  apps permanecen en sus hojas actuales; se conserva el idioma de las cuentas.
- **Archivos**: `backend/listas/models.py`,
  `backend/listas/migrations/0005_lista_clave.py`,
  `backend/listas/test_migracion_clave.py`,
  `docs/03_Modelos de Datos y de Diseño.md`, `openspec/specs/list-endpoints/spec.md`.
- **Validación final sobre OT-30**: tres pruebas de migración aprobadas en
  3,769 s y suite normal completa de 546 aprobada en 196,439 s. Ruff, Prettier
  y consistencia de migraciones aprobados; no cambia el árbol frontend.
- **Historial de verificación**: tres pruebas aprobaron en 3,507 s sobre OT-20A.
  Suite de 515 aprobada en 212,284 s con diagnóstico temporal que registra
  excepciones JWT sin tokens ni hashes. La corrida normal previa tuvo un 401
  inesperado en un test anterior de baja; el diagnóstico no lo reprodujo ni
  estableció su causa. Sobre la base anterior, su clase pasó aislada y la
  repetición completa de 511 pasó en 168,260 s sin modificar tests existentes.
  Ruff, Prettier y consistencia de migraciones aprobados. El frontend conserva
  el árbol validado en OT-13; se requiere CI sobre la cabeza final.

## 08/10/2026 — Núcleo de idioma del frontend sin prefijos (OT-70 A)

El frontend usa next-intl 4.14.9 con un proveedor en el layout raíz. La cookie
`filmai_locale` soportada gana al encabezado `Accept-Language`, que se interpreta
por pesos y regiones; el respaldo es inglés. Leer cookies y encabezados en el
servidor vuelve dinámico el render, como prevé el plan. El middleware conserva
su responsabilidad de autenticación y las rutas mantienen sus nombres actuales.
La declaración de mensajes generada se versiona para que TypeScript funcione
antes del build en CI. Se modifican `frontend/i18n/`, `messages/`, el layout,
`next.config.ts`, las dependencias y `tsconfig.json`; se agregan pruebas de
resolución y del idioma del documento. Las pantallas conservan su copia actual.

Verificación del núcleo: 65 tests unitarios, TypeScript, ESLint y Prettier
aprobados; cuatro recorridos de idioma pasan en el servidor propio del puerto 3117. El puerto habitual 3100 respondía desde otro servidor; la configuración
de verificación fue temporal y no se versiona. Reversión: retirar el plugin,
`i18n/`, los catálogos iniciales y el proveedor para volver al layout anterior.
El build de producción y Ruff también pasan; backend sin cambios funcionales.

## 08/10/2026 — Catálogo transitorio aprobado para las piezas actuales (OT-70 B)

El usuario aprobó 53 traducciones inglesas faltantes y el título temporal
«Mis reseñas» / «My reviews». Las 77 claves de `legacy` conservan la copia
española actual de preferencias, confirmación, restablecimiento, validaciones
y metadatos; las restantes traducciones inglesas reutilizan copia aprobada
de OT-13. `docs/i18n/ot70-catalogo-transitorio.csv` registra textos, archivos
de origen y aprobación, sin alterar el CSV de 91 mensajes de OT-13.
Los mensajes viven en `frontend/messages/{en,es}/common.json` y no traducen
todavía las páginas. OT-76 aplicará el voseo; OT-77 sembrará los catálogos
completos de los diseños. Los tests comprueban claves, aprobación, sintaxis
ICU y conservación de los textos actuales sensibles. Revertir esta unidad
retira solo el catálogo transitorio y su registro, preservando el núcleo.
Verificación: 69 tests unitarios, TypeScript, ESLint y Prettier pasan;
los cuatro recorridos de idioma pasan con el catálogo completo transitorio.

## 08/10/2026 — Metadatos localizados y proveedor de pruebas (OT-70 C)

`generateMetadata` localiza los cuatro puntos existentes: layout raíz,
perfil, preferencias y mis reseñas. Los títulos conservan el sufijo FilmAI;
«Mis reseñas» / «My reviews» usa la aprobación temporal del usuario.
`frontend/tests/render.tsx` envuelve el render con next-intl en español y
conserva cualquier proveedor particular; permite inglés mediante una opción.
Los cuatro archivos de tests existentes solo cambian ese import, sin tocar
selectores ni aserciones. Se agregan pruebas de los cuatro metadatos en ambos
idiomas, del envoltorio y del resultado en navegador. Esta unidad se revierte
independientemente de los catálogos y del núcleo de resolución de idioma.
El tipado experimental genera declaraciones para ambos idiomas; `AppConfig`
acepta la unión de sus catálogos literales para pasar español o inglés al
proveedor sin forzar tipos. Verificación final: 73 unitarios, TypeScript,
ESLint, Prettier, build y Ruff aprobados. Los 30 e2e (24 heredados y 6 nuevos)
pasan en 41,0 segundos con la configuración habitual y servidor propio 3100.
La primera ejecución dejó un servidor propio huérfano: se identificó por su
PID y directorio, se detuvo junto al servidor temporal 3117 y se repitió la
suite íntegra en 3100. Los intentos temporales fallaron por comparar URLs
absolutas del puerto habitual y por un reinicio de desarrollo durante la
corrección de tipos. No se modificaron esas aserciones ni la configuración.

Validación tras el único rebase sobre OT-40: backend 546 tests en 199,264 s
con base aislada `test_filmai_ot70`; 73 unitarios en 10,93 s, build,
TypeScript, ESLint, Prettier y Ruff (105 archivos) aprobados. El frontend
conserva el árbol `267f94944eecbb1347b5ff60bce1b2da3241073b`, validado con
30 e2e antes del rebase; esa evidencia se reutiliza y el CI la repetirá.
El puerto 3100 pertenece ahora a otra aplicación. No se detuvo ni se
cambiaron las URLs o los oráculos de pruebas para adaptar el entorno.

---

## 08/10/2026 — Cliente TMDB y caché por idioma (OT-60, primera entrega)

- **Fecha**: 08/10/2026
- **Descripción**: el mapa EN/ES se expresa como `en-US`/`es-MX`. Cada cliente
  tiene un idioma fijo; la fábrica comparte una instancia por idioma y
  normaliza la llamada sin argumentos al inglés canónico. Los siete métodos
  localizables envían `language`; Redis incluye el mismo valor en su hash de
  parámetros, conservando formato y TTL. Los métodos globales no lo envían.
- **Tests**: cinco pruebas nuevas cubren parámetros HTTP EN/ES, endpoints
  globales, dos entradas Redis con aciertos separados, independencia de
  clientes y rechazo de idioma no soportado antes del HTTP. Los 29 tests
  enfocados pasan en 7,159 s. El usuario autorizó ampliar únicamente los cuatro
  fixtures anteriores de caché con `language: en-US`, conservando sus
  comprobaciones de acierto, almacenamiento y vencimiento.
- **Archivos afectados**: settings, cliente, caché, fábrica de servicios,
  tests de catálogo, doc 06, specs `tmdb-client`/`tmdb-cache` y plan. Las vistas
  y la verificación real se registrarán en la segunda entrega de OT-60.

---

## 08/10/2026 — Idioma de vistas públicas y evidencia TMDB (OT-60)

- **Fecha**: 08/10/2026
- **Descripción**: las seis vistas localizables seleccionan el servicio a
  partir del idioma efectivo del request. Su autenticación continúa vacía: el
  encabezado con pesos/regiones o EN decide. Keywords permanece global y la
  materialización conserva su llamada canónica. La evidencia real confirma
  ambas variantes, igualdad de la muestra inglesa, géneros de series e
  imágenes. Una traducción ausente puede devolver un título original no
  vacío; OT-61 conservará campos presentes y completará solo vacíos.
- **Tests**: tres pruebas nuevas cubren las seis rutas y encabezados/default,
  aciertos Redis separados desde HTTP, llamada de materialización y keywords
  globales. Los 29 tests enfocados pasan en 21,276 s; no se cambiaron tests
  anteriores en esta segunda unidad. La suite completa de ambas unidades
  pasó 528 tests en 189,141 s. Ruff/Prettier limpios; el árbol frontend
  `88f94c0` coincide con el validado en OT-13 (43 unitarios/24 e2e/build).
  La publicación y el cierre esperan CI de las cabezas sobre integración.
- **Archivos afectados**: vistas, `services/idioma_tmdb.py`, tests nuevos,
  evidencia `docs/i18n/tmdb-verificacion-ot60.md`, spec de endpoints y plan.

Validación final tras rebase sobre OT-70: 554 tests backend en 269,277 s,
Ruff (108 archivos) y Prettier limpios. El árbol frontend coincide con
`267f94944eecbb1347b5ff60bce1b2da3241073b`; el CI nuevo de OT-70 comprobó
73 unitarios, 30 e2e y build. La evidencia anterior 528/43/24 corresponde
a la base previa y queda conservada como historial. OT-60 requiere CI de
sus dos cabezas publicadas antes de integrarse.

---

## 08/10/2026 — Frontera compartida de errores de serializers

- **Fecha**: 08/10/2026
- **Descripción**: OT-31 construye `ErrorValidacion` al terminar `is_valid`,
  después de las reconstrucciones de DRF. Los parámetros provienen de los
  campos y validadores configurados; las rutas distinguen listas de elementos
  y listas de mensajes. Una identidad de campo explícita conserva el cuerpo
  heredado cuando su forma no identifica el campo; los errores generales
  usan contextos declarados. Siete tests nuevos ejercitan serializers reales,
  validación anidada y configuración distinta, además de doce regresiones.
  La adopción productiva queda pendiente. OT-32 reutilizará esta utilidad,
  por lo que se registra su dependencia técnica del primer bloque de OT-31
  y se ordenan ambas entregas sin cambiar el contrato funcional aprobado.
- **Archivos afectados**: `backend/filmai/errores/{serializadores,validacion,sobre}.py`,
  `backend/filmai/test_frontera_serializadores.py`,
  `openspec/specs/error-contract/spec.md` y `docs/plan-multiidioma.md`.

---

## 08/10/2026 — Códigos de perfil y preferencias

- **Fecha**: 08/10/2026
- **Descripción**: el perfil y las preferencias adoptan la frontera final
  compartida. Nombre de persona, formato del username y avatar asignan el
  código en su validador original, preservando mensajes y HTTP anteriores.
  Límites, choices e IDs se obtienen de constantes de reglas, campos reales
  y registro activo. El conflicto de username mantiene 409 sin hojas.
  Cinco tests HTTP nuevos comprueban el sobre por separado; usan un access
  token vinculado al usuario para respetar la revalidación bajo bloqueo.
  Los tests previos continúan cubriendo autenticación JWT sin cambios.
- **Archivos afectados**: `backend/usuarios/{errores,validators,serializers,cuenta}.py`,
  `backend/usuarios/test_errores_perfil.py` y `openspec/specs/error-contract/spec.md`.

---

## 08/10/2026 — Códigos de solicitudes y cambios de contraseña

- **Fecha**: 08/10/2026
- **Descripción**: recuperación, restablecimiento y cambio autenticado adoptan
  la frontera final. Los errores propios asignan códigos explícitos; las listas
  de Django conservan sus códigos antes de la conversión DRF. Complejidad
  publica los mismos límites y caracteres que aplica, sin adjuntar parámetros
  a mensajes con `%` ni interpretar textos. Se conservan mensajes, campos y
  HTTP anteriores; enlaces inválidos y respuestas exitosas quedan para sus
  unidades respectivas. No se modifica persistencia ni envío de correos.
  Seis pruebas nuevas verifican el sobre mediante endpoints reales, incluida
  una configuración Django de mínimo 11; **53 tests** enfocados pasan.
  Se conserva el primer resultado con fallos 401 en subcasos pre-plan, cuya
  repetición pasó sin modificar esos tests ni atribuir una causa.
- **Archivos afectados**: `backend/usuarios/{perfil,serializers,validators}.py`,
  `backend/usuarios/test_errores_contrasena.py` y `openspec/specs/error-contract/spec.md`.

---

## 08/10/2026 — Códigos del registro y frontera posterior en save

- **Fecha**: 08/10/2026
- **Descripción**: registro tradicional asigna códigos en sus condiciones de
  duplicado, formato, nombre, edad y mismatch, preservando listas y traducción
  heredada de dj-rest-auth. La edad mínima es la misma constante que aplica la
  validación. La frontera compartida también devuelve una excepción normalizada
  para `save`: BaseRegister vuelve a validar contraseña cuando construye el
  usuario, después de `is_valid`. Un test provoca un fallo tipado en esa etapa
  real y verifica metadata, non_field_errors y ausencia de usuario persistido.
  No se interpreta texto ni se reemplaza el algoritmo de persistencia heredado.
  Cinco pruebas nuevas y **15 tests** enfocados pasan; normalización de
  proveedores y estados de cuenta se mantiene en OT-32/OT-33 respectivamente.
- **Archivos afectados**: `backend/filmai/errores/serializadores.py`,
  `backend/usuarios/{errores,serializers,validators}.py`,
  `backend/usuarios/test_errores_registro.py` y `openspec/specs/error-contract/spec.md`.

---

## 08/10/2026 — Códigos propios de Google y validadores restantes

- **Fecha**: 08/10/2026
- **Descripción**: Google adopta la frontera compartida y asigna códigos a
  campos requeridos, reglas de perfil, duplicados y fallos operativos. El
  token faltante conserva non_field_errors, pero el sobre identifica id_token.
  Se preservan mensajes, HTTP y estados de cuenta anteriores; la clasificación
  específica de credenciales de proveedor queda para OT-32 y los estados para
  OT-33. El avatar de modelo/Admin y el conflicto de username también asignan
  sus códigos registrados en el origen. Los nuevos tests comparten preparación
  F0, sin heredar tests ni modificar referencias; cada caso de Google revierte
  su preparación para no reutilizar el mismo correo dentro de un test.
  **108 tests** enfocados pasan, incluidos F0 completo y regresiones Google;
  la fecha del test de edad se deriva del día actual y se verificó aparte.
- **Archivos afectados**: `backend/usuarios/{serializers,avatares,exceptions}.py`,
  `backend/usuarios/test_errores_google.py` y `openspec/specs/error-contract/spec.md`.

## 08/10/2026 — Servicio único sin cambiar copia de correos (OT-50, unidad 1)

- **Fecha**: 08/10/2026
- **Descripción**: los cuatro flujos delegan el render y transporte en
  `filmai.correos.servicio.enviar_correo`. Las plantillas actuales se trasladan
  intactas a `correos/<caso>/es/`; la notificación de contraseña conserva su
  texto anterior como plantilla. El servicio mantiene los espacios extremos
  que cada flujo enviaba. Confirmación/recuperación conservan sus enlaces;
  cambio de contraseña conserva el envío posterior al commit y su política
  de fallo. Esta unidad no selecciona EN ni añade HTML a la notificación.
- **Tests**: las cuatro referencias F0 coinciden sin regeneración. Tres tests
  nuevos verifican formatos, rechazo de entradas internas y propagación del
  fallo al flujo responsable. Los 34 tests enfocados pasan en 25,339 s. El
  usuario autorizó cambiar únicamente el destino del mock de transporte del
  test de fallo de notificación, manteniendo HTTP y comprobación de contraseña.
  El layout compartido se entrega en las unidades siguientes de OT-50.
- **Archivos afectados**: servicio, plantillas trasladadas, adaptador, reset
  serializer, passwords, tests, `.env.example`, plan y spec `emails`.

---

## 08/10/2026 — Layout de registro compartible (OT-50, unidad 2)

- **Fecha**: 08/10/2026
- **Descripción**: registro hereda `correos/base.html` y conserva su introducción. La estructura, estilos, enlaces, texto y espacios
  renderizados coinciden con el HTML anterior. Reenvío y recuperación se incorporan en
  las unidades siguientes, preservando sus diferencias de contenido y color.
- **Verificación**: siete tests de correo pasan en 1,964 s; las cuatro
  referencias completas F0 permanecen iguales sin regenerarse. No se añade
  una prueba que replique la herencia: la comparación del envío real verifica
  el resultado del layout.
- **Archivos afectados**: base HTML, variante de registro, decisiones,
  plan y spec `emails`.

---

## 08/10/2026 — Reenvío sobre el layout común (OT-50, unidad 3)

- **Fecha**: 08/10/2026
- **Descripción**: reenvío hereda la base del registro y sustituye únicamente
  su introducción, conservando estilos, enlaces, vigencia y texto anterior.
- **Verificación**: la prueba completa de cuatro correos y los tres tests
  nuevos pasaron sobre ambas confirmaciones compartidas (1,964 s); la unidad
  intermedia de registro también pasó siete tests (1,972 s). Referencias F0
  intactas, sin modificar ni regenerar sus oráculos.
- **Archivos afectados**: variante HTML de reenvío, decisiones, plan y spec.

---

## 08/10/2026 — Recuperación sobre el layout común (OT-50, unidad 4)

- **Fecha**: 08/10/2026
- **Descripción**: recuperación hereda la misma base y conserva título,
  introducción, botón y advertencia propios. El servicio suministra enlace
  común y color secundario para preservar exactamente cada variante actual;
  el contexto del caller no se modifica. Los cuatro flujos pasan por el
  servicio, tres comparten HTML y contraseña actualizada conserva solo texto
  hasta OT-51. `FRONTEND_URL` queda documentada en `.env.example`.
- **Verificación**: 34 tests pasan en 25,469 s; las cuatro referencias F0
  completas siguen idénticas sin regeneración. Incluye el fallo de correo
  posterior al commit con su mock trasladado por autorización expresa.
  Suite completa de las cuatro unidades: 523 tests, OK en 189,454 s. Ruff y
  Prettier limpios. Frontend exacto `88f94c0` conserva la evidencia 43/24/build
  de OT-13. Publicación pendiente después de rebase hacia integración.
- **Archivos afectados**: base HTML, variante de recuperación, contexto del
  servicio, decisiones, plan y spec `emails`.

---

## 08/10/2026 — Consumidores y API de identidad de listas (OT-41A)

- **Fecha**: 08/10/2026
- **Descripción**: provisión, calificaciones, bloqueo de remoción, orden de
  resúmenes, semilla y auditoría usan `Lista.clave`. La API expone la clave y
  devuelve nulo para personalizadas. La provisión conserva listas renombradas
  y permite completar claves nulas por nombre heredado sin recrear sus filas;
  un tipo o identidad incompatibles detienen la operación. Se conserva la
  tupla pública de nombres para los tests anteriores. No cambia `nombre`.
- **Motivo**: separar la identidad de la etiqueta evita que un renombrado
  rompa la regla calificada implica vista. Las consultas por nombres quedan
  solo en el respaldo de provisión; textos, docstrings y migraciones históricas
  pueden conservar etiquetas. Nombres reservados y exportación quedan para
  OT-41B y las restricciones para OT-42.
- **Pruebas**: siete casos nuevos cubren altas/API, orden tras renombrar, el
  flujo HTTP calificar–bloquear remoción–borrar nota, provisión/auditoría,
  transición nula, semilla por clave y colisión del respaldo. Pasan junto a
  doce regresiones de contraseña: 19 tests en 16,229 s, en base aislada.
  Suite normal completa: 553 tests en 201,893 s; Ruff, Prettier y coherencia
  de migraciones aprobados. La corrida previa de 552 tuvo un 401 inesperado
  en una regresión anterior de rollback de contraseña; se conserva ese
  resultado y su repetición sin modificar tests anteriores ni atribuir causa.
- **Archivos**: listas (servicios, vistas, serializer y tests), provisión y
  comandos de usuarios, doc 03, spec `list-endpoints` y plan multiidioma.

---

## 08/10/2026 — Reserva bilingüe y contrato de enums (OT-41B)

- **Fecha**: 08/10/2026
- **Descripción**: crear o renombrar una personalizada rechaza las etiquetas
  ES/EN del sistema sin distinguir mayúsculas y tras normalizar espacios.
  Se registra `list_name_reserved`, HTTP 409 sin parámetros, con copia
  aprobada por el usuario: «Ese nombre está reservado para una lista
  predeterminada.» / “This name is reserved for a default list.” Es una fila
  nueva; las 91 originales de OT-13 permanecen intactas. No se renombran
  automáticamente listas personalizadas anteriores.
- **Contrato**: `contracts/enums.json` publica `defaultListKeys`,
  `genderValues` y `reservedListNames` por idioma. `exportar_enums` lo deriva
  de los valores de los modelos y la reserva del backend; una prueba coteja
  sus etiquetas con el CSV editorial aprobado. Género conserva su modelo.
- **Regresión**: el escenario nuevo de F0 `lista_nombre_duplicado` pasa a
  duplicar una personalizada real. Conserva su golden, HTTP y campos previos;
  la reserva se verifica por separado. Aplica la autorización vigente para
  tests nuevos de F0 cuando una fase cambia deliberadamente su comportamiento.
  No se modifican tests anteriores al plan ni goldens de referencia.
- **Pruebas**: seis casos nuevos y la regresión F0 pasan juntos: siete en
  2,019 s. Cubren POST/PUT en ambos idiomas, reserva tras renombrar una
  predeterminada, nombres anteriores sin traducir, exportación reproducible,
  paridad editorial y código/copia aprobada. La primera suite normal tuvo
  559 tests en 200,128 s, con un 401 inesperado en una regresión anterior de
  baja. Su clase pasó aislada (6 en 3,087 s); se repite la suite sin cambiar
  tests anteriores al plan ni atribuir causa. Ruff, Prettier y migraciones
  consistentes aprobados.
- **Archivos**: identidad/serializer de listas, exportador y tests, catálogo
  de errores, escenario F0, CSVs i18n, contrato generado, specs y este registro.

---

## 08/10/2026 — Cierre parcial: entorno real, rama única `develop` y limpieza

- **Fecha**: 08/10/2026
- **Descripción**: cierre parcial para dejar el proyecto en un punto de
  continuación claro. El entorno local se reparó y verificó: la imagen del
  frontend se reconstruyó para instalar `next-intl@4.14.9` y el contenedor se
  **recreó** (el volumen anónimo de `node_modules` se siembra desde la imagen
  solo al crearlo, por eso el contenedor viejo arrancaba sin la dependencia y
  entraba en bucle de reinicio), y en la base de desarrollo se aplicaron las
  migraciones `usuarios.0007_usuario_idioma` y `listas.0005_lista_clave`.
  Con eso se cerró la duda que quedaba abierta: **login real probado contra la
  BD de desarrollo** (POST `/api/auth/login/` → 200 con cookies `access`,
  `refresh` y `sessionid`; `GET /api/auth/user/` → 200; password inválida →
  400 con el contrato de errores vigente), además de `Usuario.idioma` y
  `Lista.clave` legibles en esa base.
- **Integración**: todo el trabajo pasa a una sola rama, **`develop`**. Se
  integraron las entregas que estaban fuera de la línea principal: OT-31
  (frontera de errores, `ec509d2`), OT-50 (servicio y layout de correos,
  `b14785c`) y OT-41A (identidad por clave, `ed85794`); y se rescató el
  trabajo de **OT-41B que estaba sin commitear** en el worktree
  `/tmp/filmai-i18n-ot41b-retoma` (`7eb7584`: `list_name_reserved`,
  `contracts/enums.json`, comando `exportar_enums`, tests y este tipo de
  registro). Los conflictos fueron solo de documentación y `graphify-out/`,
  más los imports de `backend/usuarios/serializers.py` (OT-31 vs OT-50,
  conservando ambos lados). `contracts/openapi.yaml` se regeneró con
  `FILMAI_ACTUALIZAR_REFERENCIAS=1` porque el docstring de
  `FronteraErroresMixin` llega como `description` a los esquemas
  `CambiarContrasena` y `Preferencias`.
- **Limpieza**: de 49 a 2 ramas locales y de 36 a 2 remotas (quedan `develop`
  y `main`); 16 worktrees de `/tmp` eliminados; stash de OT-13 descartado
  (verificado que todo su contenido está en `develop`); PRs #42, #43, #66 y
  #67 cerrados con explicación. Los SHAs de las 47 ramas borradas y el
  procedimiento de recuperación quedaron en `docs/cierre-parcial-2026-10-08.md`.
  Antes de borrar se comprobó, archivo por archivo, que el contenido de los
  worktrees estaba commiteado o supersuperado por versiones aprobadas.
- **Pruebas**: suite backend completa **598 OK** (con los mounts de
  `contracts/` y `docs/` que esos tests resuelven vía `BASE_DIR.parent`; la
  corrida previa tuvo un `401 != 200` intermitente ya documentado en
  OT-41A/OT-41B, y la repetición salió en verde sin tocar tests),
  Vitest **73/73**, `ruff format`/`ruff check` limpios, Prettier de frontend
  limpio y `makemigrations --check` sin migraciones pendientes.
- **Archivos afectados**: `contracts/openapi.yaml` (regenerado),
  `docs/plan-multiidioma.md` (estados y traspaso), `docs/decisiones.md`
  (este registro), `docs/cierre-parcial-2026-10-08.md` (nuevo) y
  `graphify-out/` (regenerado).

## 08/10/2026 — OT-32: códigos en `listas` y `catalogo`, TMDB normalizado

- **Descripción**: F3 paso 2 (resto) y paso 4 (TMDB). Sin cambiar textos, HTTP
  ni claves heredadas, cada error de `listas` y `catalogo` lleva un código del
  catálogo y sus parámetros:
  - `listas`: `NombreListaSerializer` usa `FronteraErroresMixin`; emite
    `blank`, `max_length` (`maxLength: 80`), `list_name_missing_alphanumeric`
    y `list_name_invalid_characters`. Los serializers de consulta adoptan la
    misma frontera (`min_value`, `invalid_choice`, `invalid`).
  - `catalogo`: los parámetros de las vistas (`_int_param`, `_float_param`,
    `_validate_tipo`, `query`) lanzan `ErrorValidacion` con el texto en inglés
    heredado (cuerpo irregular `{campo: "texto"}` intacto) y código
    `required`/`invalid`/`min_value`/`number_not_finite`/`invalid_choice`.
    La actualización de reseñas vacía emite `review_update_empty`
    (`fieldNames: ["valor", "texto"]`).
  - TMDB: el manejador **global** agrega el sobre (`upstream_bad_request`,
    `upstream_not_found`, `upstream_error`, `upstream_unavailable`); el
    manejador especializado `tmdb_exception_handler` y su test directo no se
    tocan. **Decisión**: `TMDBRateLimited` (429) usa `throttled` sin
    `retry_after_seconds`, porque TMDB no informa la espera; OT-33 agrega el
    parámetro y `Retry-After` al 429 propio.
  - Los conflictos de `listas` y `CalificacionDuplicada` ya se mapeaban por
    `_CODIGOS_HEREDADOS`; no requirieron cambio.
- **Tests existentes tocados** (autorizado por el plan: "normalizando solo el
  global"): `filmai/tests.py::test_handler_global_conserva_el_mapeo_de_tmdb` y
  `filmai/test_manejador_sobre.py::test_tmdb_agrega_sobre_...` verifican
  `detail`, HTTP y `code` en vez de igualdad exacta del cuerpo.
- **Pruebas**: nuevos `listas/test_codigos_errores.py` y
  `catalogo/test_codigos_errores.py`; suite backend completa **611 OK**,
  `ruff format`/`ruff check` limpios.
- **Archivos afectados**: `backend/listas/serializers.py`,
  `backend/catalogo/{views,serializers_reviews}.py`,
  `backend/filmai/exceptions.py`, los tests citados, `docs/plan-multiidioma.md`
  y `graphify-out/`.

## 08/10/2026 — OT-33: espera del 429, códigos de éxito y estados de cuenta

- **Descripción**: F3 pasos 5, 6 y 7, sin quitar claves heredadas.
  - **429**: `Throttled` con espera emite `params.retry_after_seconds`
    (`ceil(wait)`); el encabezado `Retry-After` ya lo fija DRF.
  - **Éxito**: las respuestas con texto suman `code` junto a `detail`
    (`password_reset_requested`, `password_reset_completed`, `password_updated`,
    `account_deactivated_successfully`, `email_confirmed`, `csrf_ready`).
    Para vistas de dj-rest-auth (registro `registration_pending_confirmation`,
    reenvío `confirmation_email_sent`, logout `logged_out`) se usa el decorador
    `con_codigo_exito`, que envuelve la vista con `functools.wraps`; **no** se
    subclasean porque drf-spectacular perdería sus extensiones y cambiaría
    `contracts/openapi.yaml` (se probó y se descartó).
  - **Login**: `CuentaInactiva` (subclase de `PermissionDenied`) emite
    `account_deactivated` / `account_pending_confirmation` con el mismo 403 y
    `detail` genérico, **solo si la contraseña (o el token de Google) es
    correcta**. Con contraseña incorrecta la cuenta inactiva responde como
    cualquier otra: `invalid_credentials` (HTTP 400, cuerpo `non_field_errors`
    heredado). Las credenciales inválidas de cualquier cuenta pasan de
    `validation_error` a `invalid_credentials`.
- **Cambio de comportamiento deliberado**: cuenta de baja/pendiente con
  contraseña incorrecta pasa de 403 a 400 (el plan 3.3 pide no revelar el
  estado a quien no controla la cuenta). Se ajustó el test OT-02
  `filmai/tests_estado_cuenta.py` (separa contraseña correcta/incorrecta), lo
  autorizado para tests de F0 cuando el plan cambia el comportamiento.
- **Pruebas**: `usuarios/test_codigos_exito_estado.py` (11 tests); suite
  backend completa **622 OK**, `ruff` limpio, `openapi.yaml` sin cambios.
- **Archivos afectados**: `backend/filmai/{exceptions,urls}.py`,
  `backend/filmai/errores/sobre.py`, `backend/usuarios/{exceptions,serializers,
views,perfil,cuenta}.py`, tests citados, `docs/plan-multiidioma.md`,
  `graphify-out/`.

## 08/10/2026 — OT-34: contrato exportado, sobre en OpenAPI y modo estricto (cierra F3)

- **Descripción**: F3 pasos 8 y 9 más el rechazo de códigos no registrados.
  - `exportar_contrato` (`filmai/management/commands/`) escribe
    `contracts/error-codes.json` desde el catálogo (categoría, contextos HTTP,
    esquema de parámetros; **sin** mensajes internos). Para que Django vea el
    comando, `filmai` se agrega a `INSTALLED_APPS` (sin modelos ni migraciones).
    Un test compara el archivo completo.
  - `validar_respuesta_error` + `EjecutorConSobre` (`TEST_RUNNER`): toda
    respuesta 4xx/5xx JSON bajo `/api/` de **toda la suite** se valida (sobre,
    código registrado, estado HTTP del contexto, parámetros, ausencia de
    `debug` con `DEBUG=False`). Esto destapó respuestas sin sobre, ya corregidas:
    errores directos de enlaces (`link_expired`, `link_invalid`,
    `already_confirmed`), 401 de simplejwt (`token_not_valid` →
    `invalid_token`; `user_inactive`/`password_changed` → `session_revoked`),
    403 de documentación y los handlers 404/500 de Django.
  - **Modo estricto** (`FILMAI_SOBRE_ESTRICTO`, solo en la suite): un código o
    una hoja sin registrar lanza `ValueError`. En producción degrada al código
    genérico del estado (401/403/404/500) y registra el error.
  - OpenAPI: componentes `ErrorEnvelope`/`ErrorEntry` y respuestas `4XX`/`5XX`
    en cada operación (hook `agregar_sobre_de_errores`); solo se añade.
  - `GoogleSocialLoginSerializer` descarta el campo heredado `code`: un valor
    no textual lo habría hecho chocar con el `code` del sobre (500). Solo se
    usa `id_token`. Un test verifica que ningún serializer declare
    `code`/`params`/`errors`/`debug`.
- **Tests existentes tocados** (igualdades pre-plan autorizadas para
  confirmación/restablecimiento/documentación): `usuarios/tests.py`,
  `usuarios/test_perfil.py` y `filmai/tests.py` comparan `codigo`/`detail` en vez
  del cuerpo completo.
- **Pruebas**: `test_contrato_codigos.py`, `test_cobertura_codigos.py` (un caso
  por código del catálogo); suite backend **634 OK**, `ruff` limpio,
  `makemigrations --check` sin cambios. **F3 queda cerrada.**
- **Archivos afectados**: `backend/filmai/{errores/{contrato,openapi,sobre}.py,
exceptions,pruebas,views,documentation,settings,urls}.py`,
  `backend/filmai/management/`, `backend/usuarios/{views,serializers}.py`,
  tests citados, `contracts/{error-codes.json,openapi.yaml}`,
  `openspec/specs/error-contract/spec.md`, `docs/plan-multiidioma.md`.

## 08/10/2026 — OT-42: restricciones de `clave` y prueba sobre un volcado (cierra F4)

- **Descripción**: F4 paso 5 (contraer). Migración `listas.0006` en dos partes:
  1. `RunPython` de verificación que se detiene con un mensaje explícito (ids de
     lista y usuario) si hay predeterminadas sin clave, personalizadas con
     clave o claves repetidas por usuario; es reversible (no-op).
  2. `uq_lista_usuario_clave` (único por `usuario`+`clave` cuando la clave no es
     nula) y `ck_lista_tipo_clave` (predeterminada ⇔ clave presente;
     personalizada ⇔ clave nula). `nombre` se conserva (D6).
- **Prueba sobre copia de datos reales**: volcado `pg_dump` de la base de
  desarrollo restaurado en una base temporal (`ot42_copia`, eliminada al
  terminar). Con `listas.0005` en la copia: 4 usuarios, 13 listas, 78 ítems,
  0 predeterminadas sin clave, 0 personalizadas con clave, 0 claves repetidas.
  El superusuario `admin` (creado sin la señal) no tenía listas
  predeterminadas: se reparó **solo en la copia** con
  `reparar_recursos_usuarios` (+3 listas, 16 en total, 4 usuarios con las tres
  claves). Avance a `0006`, retroceso a `0005` y nuevo avance: mismos conteos
  (16 listas, 78 ítems) en cada paso. Salvedad: el entrypoint del backend
  ejecuta `migrate` en cada arranque, por lo que la línea base posterior a la
  reparación ya se tomó con `0006` reaplicada; la de `0005` pura es la primera
  (4/13/78).
- **Aviso**: por ese mismo entrypoint, las corridas de tests con Docker de esta
  sesión aplicaron `0006` a la base de desarrollo (sus datos eran válidos, no
  hubo cambios de filas). `admin` sigue sin listas predeterminadas allí; no se
  tocó la base original.
- **Test existente tocado**: `listas/test_identidad.py::test_provision_completa_
nulas_heredadas_sin_recrear_filas` simulaba una predeterminada sin clave, que
  la restricción ahora prohíbe; quita `ck_lista_tipo_clave` solo dentro de ese
  test (DDL transaccional, se revierte) para conservar la cobertura de la ruta
  de compleción.
- **Pruebas nuevas**: `listas/test_restricciones_clave.py` (restricciones de
  base y migración en ambos sentidos, con datos inválidos). Suite backend
  **644 OK**, `ruff` limpio, `makemigrations --check` sin cambios. **F4 queda
  cerrada** (falta publicar/CI).
- **Archivos afectados**: `backend/listas/{models.py,migrations/0006_*.py,
test_restricciones_clave.py,test_identidad.py}`, `docs/plan-multiidioma.md`,
  `graphify-out/`.

## 08/10/2026 — OT-51/52/53: correos localizados (cierra F5)

- **OT-51**: la vigencia de los enlaces sale de la configuración
  (`ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS`, `PASSWORD_RESET_TIMEOUT`) vía
  `vigencia_en_horas`, con singular/plural en plantilla. "Contraseña
  actualizada" gana HTML; su acción enlaza a `FRONTEND_URL/login/` (el inicio
  de sesión real; no se inventa un token ni un endpoint de recuperación).
- **OT-52**: plantillas `en` para los cuatro casos y `base_<idioma>.html` con la
  copia compartida. Idioma del correo = `idioma_efectivo(request, usuario)`:
  idioma guardado del destinatario, luego el del request, luego inglés. Lo
  resuelve el llamador (adaptador de allauth, recuperación, cambio y
  restablecimiento de contraseña) y el servicio renderiza una variante explícita.
  **Decisión**: el saludo sin nombre es «Hola usuario,» / “Hi there,”. La
  tabla no traía copia para ese caso; el usuario la aprobó el 08/10/2026.
- **OT-53**: la copia en español pasa a la de `docs/i18n/claves.csv` (filas
  603–634, voseo) y ambos idiomas suman encabezado, motivo y pie con año. El
  layout `base.html` queda neutro (sin texto). La notificación de contraseña no
  muestra la fila "copiá y pegá este enlace" (la tabla no la incluye).
- **Tests existentes tocados** (cambio deliberado de F5): `usuarios/tests.py`
  (`ConfirmarCorreoTests`, `RecuperarContrasenaTests`) y las referencias de F0
  envían `Accept-Language: es`, porque sin preferencia el correo ahora sale en
  inglés. Las 4 referencias `es` se regeneraron en OT-53 (y la de contraseña
  en OT-51, por el HTML); se agregaron 4 referencias `.en`. El año del pie se
  normaliza en las referencias.
- **Pruebas**: `filmai/test_correos_idioma.py` (matriz 4 casos × 2 idiomas ×
  3 partes, idioma del destinatario, saludo de reserva, voseo) y
  `test_servicio_correos.py` (vigencias). **Pendiente manual**: revisar los
  correos en un cliente real con `RESEND_TEST_RECIPIENT` (plan 10.1).
- **Archivos afectados**: `backend/filmai/correos/servicio.py`,
  `backend/templates/correos/**`, `backend/usuarios/{adapter,passwords,
serializers,views,perfil}.py`, `backend/usuarios/templatetags/nombres.py`,
  tests y referencias citadas, `openspec/specs/emails/spec.md`.

## 08/10/2026 — OT-60 a OT-63: TMDB según idioma (cierra F6)

- **OT-60**: ya integrada (cliente con `language`, clave de caché por idioma,
  vistas públicas por `Accept-Language`); se da por cerrada con la suite
  completa de esta etapa.
- **OT-61**: `catalogo/services/fallback.py`. Fuera del inglés, detalles y
  listados se envuelven en `CatalogoConRespaldo`: si `title`/`name`/`overview`
  llegan vacíos se pide la versión inglesa (cacheada) y se completa campo por
  campo. **Decisión**: la marca se llama `campos_en_ingles` (lista por detalle
  y por ítem de listado) y solo se agrega fuera del inglés, para que el
  passthrough en inglés no cambie. En listados se combina la misma página por
  (`media_type`, `id`); un ítem sin par en la página inglesa queda como llegó.
- **OT-62**: `ProduccionTraduccion` (producción, idioma, título, sinopsis,
  póster; único por producción+idioma) y `ProduccionAudiovisual.generos_ids`,
  migración `catalogo.0006`. `materializar` guarda la traducción de cada idioma
  no canónico después del canónico; un `TMDBError` ahí se registra y no
  invalida el enriquecimiento. Comando idempotente `rellenar_traducciones`
  (`--limite`, `--lote`). El texto canónico de embeddings y su hash no cambian
  (test de invariancia).
- **OT-63**: `texto_localizado` elige título/póster por idioma con respaldo
  canónico; lo usan ítems de lista, previews de listas y «mis reseñas» con
  `prefetch_related("produccion__traducciones")`. Nuevo
  `GET /api/catalogo/genres/` por idioma. La sincronización nocturna suma una
  tercera pasada acotada (`CELERY_BACKFILL_LIMIT`) que rellena traducciones
  pendientes y la informa en `traducciones`.
- **Tests existentes tocados** (adiciones previstas por la fase): dos
  aserciones de "una sola llamada" al detalle pasan a dos (una por idioma);
  las estadísticas de la sync incluyen `traducciones`; la fila "intacta" del
  test de refresco se crea ya traducida. `contracts/openapi.yaml` suma la ruta
  de géneros.
- **Verificación con la API real** (08/10/2026): `movie/1559362` con
  `Accept-Language: es` devuelve la sinopsis inglesa y
  `campos_en_ingles: ["overview"]`; `genres?tipo=tv` devuelve «Animación»,
  «Comedia»; `rellenar_traducciones --limite 5` guardó 5 traducciones
  (p. ej. «Buscando a Nemo») y `generos_ids` en la base de desarrollo.
- **Limitación conocida**: el orden por título usa el título canónico; la
  sinopsis traducida se guarda pero ningún serializer la expone todavía.
- **Archivos afectados**: `backend/catalogo/{models,views,urls,tasks,reviews,
serializers_reviews}.py`, `backend/catalogo/services/{fallback,traducciones,
materialization}.py`, `backend/catalogo/management/commands/
rellenar_traducciones.py`, migración `0006`, `backend/listas/{views,
serializers}.py`, tests nuevos (`test_fallback_idioma`, `test_traducciones`,
  `test_idioma_serializadores`), specs `tmdb-endpoints` y
  `catalog-materialization`.

## 08/10/2026 — Limpieza de `docs/` y documento de siguientes pasos

- Nuevo `docs/siguientes-pasos-multiidioma.md`: estado por fase, pendientes y
  órdenes que faltan (F7 a F9), con los comandos del entorno.
- Eliminados `docs/cierre-parcial-2026-10-08.md` (reemplazado por el anterior;
  sus SHAs de recuperación quedan en el historial, commit `05a53a2`) y
  `docs/i18n/revision-ot13.md` (lista de verificación de una orden cerrada).
- Se conservan los demás archivos de `docs/i18n/` porque los leen tests o el
  plan (`claves.csv`, `copia-propuesta.csv`, `ot70-catalogo-transitorio.csv`,
  `equivalencias.json`, `errores.csv`, `glosario.md`,
  `tmdb-verificacion-ot60.md`). `docs/reportes_dev/` y `docs/wireframes/` no se
  tocaron: son material del equipo y de diseño, no del plan multiidioma.

## 08/10/2026 — Arquitectura del chatbot (Módulo 5): DeepSeek, SSE sobre ASGI y contexto por SQL

- **Descripción**: Gonza y Marcos acordaron la arquitectura general antes de
  implementar B-02 a B-06. Complementa la decisión del 18/08/2026 (tool
  calling + pgvector + BGE-M3), que sigue vigente.
  1. **Proveedor**: DeepSeek, por su API compatible con OpenAI (SDK `openai`
     con `base_url` propia). Un único adaptador "compatible con OpenAI"
     permite pasar a Groq, OpenAI o Gemini cambiando el `.env`. Todavía no
     hay API key: mientras tanto se trabaja con un proveedor falso. Como los
     datos se procesan en servidores de terceros fuera del país, la
     anonimización (RNF #3) es estricta: el LLM no recibe nombre, apellido,
     correo ni nombre de usuario.
  2. **Transporte**: streaming SSE sobre ASGI desde el inicio, sin pasar por
     una versión síncrona. El orquestador es un async generator que emite
     eventos (`estado`, `texto`, `tarjetas`, `fin`, `error`). Para probarlo
     sin HTTP ni front se usa el comando `manage.py chatear`. El código async
     queda acotado al loop del orquestador y a un único ejecutor de tools,
     que envuelve con `sync_to_async` el código sync existente (ORM, cliente
     TMDB, Ollama). `POST /api/chat/mensajes/` es una vista async de Django
     (DRF no es async); el `GET` del historial sigue en DRF.
  3. **Cancelación (CU-014)**: el front aborta el `fetch` y Django cancela la
     vista al detectar la desconexión. La pregunta y la respuesta se guardan
     juntas, recién al terminar: una solicitud cancelada o fallida no deja
     nada persistido. Se verifica con un test en la implementación.
  4. **Respuesta**: texto en markdown + tarjetas de títulos. La tool de
     presentación `mostrar_tarjetas` solo acepta ids devueltos por otra tool
     en el mismo turno y descarta los que están en «Vistas». Nuevo campo
     `Mensaje.tarjetas` (JSON).
  5. **Contexto personal (cambia B-05)**: se arma por SQL en cada mensaje, en
     lugar de precomputarse en `Chat.contexto`: lo que le gustó (nota 7 o
     más, con un extracto de su reseña), lo que no le gustó (4 o menos),
     últimas vistas y favoritos. `Chat.contexto` queda para el estado de la
     conversación (títulos ya recomendados).
  6. **Idioma y alcance**: responde en el idioma de `idioma_efectivo()` y las
     tools consultan TMDB con `TMDBClient(idioma=...)`. Solo habla de cine,
     series y del historial del usuario; en español, con voseo.
  7. **Límites**: mensaje de hasta 500 caracteres, unos 20 mensajes por hora
     por usuario, últimos 10 mensajes como historial, como máximo 4 vueltas
     de tools y una sola solicitud en curso por chat.
  8. **Tools**: `buscar_por_titulo`, `descubrir` (generaliza
     `top_por_genero`), `similares_a`, `buscar_por_persona`, `detalle`,
     `buscar_semantico`, `mis_listas` y `mostrar_tarjetas`. Al cliente TMDB
     le faltan `get_similar` y `search_person`.
- **Motivo**: SSE es la práctica habitual en chats con LLM y, bajo ASGI,
  esperar la respuesta del modelo no ocupa un worker. Pasar antes por una
  versión síncrona obligaba a reescribir el orquestador como async. Precomputar
  el contexto exigía señales en calificaciones, listas y reseñas que las
  operaciones masivas (seed, migraciones, acciones del Admin) no disparan, y no
  ahorra tiempo frente a la latencia del LLM. Lo que no le gustó al usuario
  informa tanto como lo que sí.
- **Pendiente**: actualizar los docs 03 (`Mensaje.tarjetas`), 05 (B-02 a B-05)
  y 06 (tools nuevas); abrir el SDD en `openspec/changes/chatbot/`; medir la
  latencia contra DeepSeek cuando haya key (RNF #6).
- **Archivos afectados**: `docs/decisiones.md` (este registro).

## 08/10/2026 — Selector de idioma: dónde vive en la interfaz

- **Descripción**: el canvas de Claude Design decía «no hay selector de
  idioma» y lo postergaba; el plan multiidioma ya lo pedía en Preferencias y en
  las páginas públicas. Marcos aprobó esta ubicación y se actualizó el canvas
  (versiones 288 y 289):
  1. **Con sesión**: el idioma se cambia solo en Preferencias, sección
     «Language» (segmentado `English | Español`, copia «Interface language» y
     «Applies instantly and is saved to your account. Also used for the emails
     we send you.»). No hay selector en el menú del avatar.
  2. **Footer con sesión**: muestra el idioma actual y enlaza a Preferencias
     (`#t-idioma`). Escritorio: ítem en la columna Information; móvil: fila
     «Language · English ›». No cambia el idioma por sí mismo. Con sesión se
     ocultan «Sign up» y «Log in» del footer de escritorio.
  3. **Sin sesión**: pastilla `EN | ES` arriba a la derecha en Landing, inicio
     de sesión y registro (escritorio y móvil). El footer de escritorio sin
     sesión incluye el selector con los nombres completos. Estos controles solo
     escriben la cookie (regla de `docs/plan-multiidioma.md` 3.2); el idioma
     del registro define el de los correos de la cuenta nueva.
  4. Cada idioma con su propio nombre, sin banderas.
  5. **Formatos**: se unifica con el plan (3.5). En inglés los miles llevan
     coma (`41,355`); en español, punto (`41.355`). El canvas deja de usar
     `41.355` en inglés (Ficha) y sus notas se alinean.
- **Archivos afectados**: `docs/04_Lineamientos_UI.md` (4, 4.1 y 5j),
  `docs/plan-multiidioma.md` (fase 7c, paso 12),
  `docs/siguientes-pasos-multiidioma.md` (OT-74). Sin cambios de código: el
  `LanguageSwitcher` se implementa en OT-74.

## 08/10/2026 — Documentos 01 a 04 alineados con el multiidioma

- **Descripción**: se actualizan los documentos de dominio para reflejar el
  multiidioma ya decidido e implementado en el backend. La documentación se
  mantiene en español (la leen docentes hispanohablantes) y los textos de
  interfaz citados en los casos de uso quedan como referencia en español; el
  texto vigente de cada idioma vive en `docs/i18n/` y en los diseños.
  1. **Doc 01**: objetivo específico y población incluyen inglés y español.
  2. **Doc 02**: alcance, seis requisitos funcionales y RNF #17
     (internacionalización); notas de idioma en CU-001, 003, 006, 008, 012,
     013, 019, 020 y 021; sección final «Multiidioma». **Corrección**: CU-002
     decía que el enlace de confirmación era permanente; vence a las 24 horas
     (`ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1`), como el usuario confirmó el
     08/10/2026.
  3. **Doc 03**: «Vistos» pasa a «Vistas» y se documentan `Usuario.idioma`,
     `Lista.clave` con sus dos restricciones (OT-42), `generos_ids` y la nueva
     entidad `ProduccionTraduccion`. El JSON de los diagramas (clases y
     tablas) suma esos campos y la entidad; los gráficos se regeneran desde él.
  4. **Doc 04**: sección 4.1, rutas visibles en inglés (aún no implementadas),
     formato de duración por idioma, etiquetas de listas por idioma y
     accesibilidad (`lang`, `radiogroup`).
  5. **Canvas de diseño**: se quitan de sus notas dos avisos desactualizados
     sobre TMDB («quedan en inglés» y «decisión del 30/09 definitiva»), que la
     decisión del 08/10/2026 (TMDB según idioma) reemplazó.
- **Archivos afectados**: `docs/01_*`, `docs/02_*`, `docs/03_Modelos*`,
  `docs/03_DiagramaClases_DiagramaTablas.json`, `docs/04_Lineamientos_UI.md`,
  `docs/decisiones.md`. Pendiente: `docs/06_TMDB_API_Referencia.md` y las
  specs de `openspec/` (fase 9 del plan).

## 08/10/2026 — OT-71: formatos por idioma

**Descripción:** Se centralizan fechas medias/largas en UTC, enteros, notas decimales y duración en `frontend/lib/format.ts`, con `en-US`/`es-AR`. Perfil y ReviewCard usan la utilidad; los tests comparan contra Intl para respetar CLDR sin composición manual.

## 08/10/2026 — OT-72: errores por código y encabezados

**Descripción:** `apiFetch` y el bootstrap CSRF mandan Accept-Language. `ApiError` expone código, parámetros y hojas; `lib/errors.ts` busca mensaje de campo, código y desconocido, y convierte la espera a ICU en un único lugar. Los consumidores y la API simulada no leen diagnósticos ni cuerpos anteriores.

## 08/10/2026 — OT-73: validaciones y enumeraciones

**Descripción:** Los validadores de `lib/validation.ts` y los errores de `lib/reviews.ts` devuelven identidades estables. La traducción se hace en el consumidor. Género y tema usan etiquetas del catálogo; el contrato de enums se copia por generación dentro del frontend porque Docker/Turbopack no acceden al directorio padre. Un test exige igualdad con `contracts/enums.json`.

## 08/10/2026 — OT-74: selector y sincronización

**Descripción:** Se implementan radios reutilizables en Preferencias, la pastilla EN/ES pública y el footer mínimo aprobado (`LanguageSwitcher.tsx`, `LocaleControls.tsx`). Con sesión, AccountProvider confirma el PUT antes de cambiar cuenta/cookie/render; el fallo conserva el idioma. Login y Google sincronizan la cuenta; idioma nulo conserva el dispositivo. El footer autenticado enlaza a `/settings#t-idioma`, sin login/registro ni selector propio. Google recibe el locale vigente.

## 08/10/2026 — OT-75: rutas inglesas coordinadas

**Descripción:** Se renombraron páginas y enlaces en `frontend/app`, centralizados en `lib/routes.ts`; también los enlaces de `usuarios/adapter.py` y `serializers.py`, los tests y referencias de correo. `/lists` solo cambia en protección. El usuario confirmó que abrir un correo respeta cookie/navegador del dispositivo, aunque el idioma difiera del mensaje; no se añade un parámetro de idioma.

## 08/10/2026 — OT-76: tres pilotos bilingües

**Descripción:** Preferencias, confirmación y restablecimiento consumen catálogos sin rediseñar los layouts heredados. Confirmación usa voseo y reset incluye `*` en la ayuda. Los errores de reset se guardan como códigos para traducirse al renderizar. Los controles tienen foco visible, área táctil completa y estados de carga. Las demás pantallas conservan las excepciones aprobadas.

## 08/10/2026 — OT-77: siembra reproducible

**Descripción:** `frontend/scripts/i18n/generate.py` genera desde los CSV aprobados, conserva la copia transitoria y excluye ejemplos, diseño, chatbot y correos. La copia legal se guarda separada de common para no enviarla a todas las páginas. `--check` detecta divergencias semánticas respecto de la fuente; las declaraciones de next-intl se regeneran con el build.

## 08/10/2026 — OT-80: controles de idioma

**Descripción:** Paridad de claves, argumentos, tags, plurales, códigos y enums en Vitest; reglas ESLint contra literales visibles, debug y formatos fuera de `lib/format.ts`; script de residuos. Las 13 excepciones heredadas tienen techo probado. CI incorpora `develop` y el control de residuos. Archivos: `frontend/scripts/i18n`, tests, ESLint y `.github/workflows/ci.yml`.

## 08/10/2026 — OT-81: recorridos bilingües

**Descripción:** Playwright recorre registro, confirmación, login, cambio de idioma persistente y reset en en/es. También prueba footer y selector a 390/1280 px, teclado y fallo de guardado. Los controles heredados de registro/login reciben asociaciones label/input para usar nombres y campos estables sin rediseñarlos. La navegación de tests de perfil se acota al banner porque ahora existe un footer.

## 08/10/2026 — OT-82: aserciones por código

**Descripción:** Se migran tests y las referencias de API a código, campo de hoja y parámetros, preservando matrices HTTP, credenciales, seguridad y regresión. Se verificó la migración con emisión doble antes de contraer el contrato; una aserción de éxito convertida por error se corrigió y pasó antes de retirar las claves anteriores.

## 08/10/2026 — OT-83: contrato definitivo

**Descripción:** Se retira el mezclador legacy y se construye el sobre directamente en el manejador y respuestas explícitas (`filmai/exceptions.py`, `errores/sobre.py`, vistas y documentación de API). Los éxitos conservan datos de máquina y code sin detail. El ejecutor rechaza claves extra en todos los errores de API. OpenAPI y golden references reflejan el formato definitivo.

## 08/10/2026 — OT-90: documentación y aceptación externa

**Descripción:** Se alinean documentos 02, 04 y 06, specs canónicas, guía de uso, README y AGENTS. Los modelos del doc 03 ya estaban actualizados y no se duplican. La base de desarrollo quedó con tres listas para admin y cero traducciones pendientes entre producciones enriquecidas; las 39 sin enriquecer se completarán al materializarse. Se preparan ocho EML y una vista HTML sin enviar correo externo. El CI remoto y la revisión en cliente real se registran como pendientes hasta contar con evidencia. Chatbot queda fuera de esta entrega; el pair programming del 09/10 debe revisar idioma en SSE, cambio durante una solicitud y localización de tarjetas/errores.

## 08/10/2026 — Marcas de respaldo en filas persistidas

**Descripción:** La revisión de OT-72/76 encontró que listas y mis reseñas localizaban título/póster sin exponer `campos_en_ingles`. Se agrega esa marca por campo fuera del inglés en `catalogo/services/traducciones.py`, `serializers_reviews.py` y `listas/serializers.py`, usando el prefetch existente. Los tests verifican traducción parcial, traducción ausente, inglés nativo y que no crezcan consultas por fila. ReviewCard marca el título de respaldo con `lang="en"`.

## 08/10/2026 — Etiqueta compartida del avatar

**Descripción:** El control reforzado de literales detectó etiquetas accesibles en español en `frontend/components/Avatar.tsx`. Se usa la clave aprobada `common.avatar.currentAlt` tanto para la imagen como para las iniciales. Dos casos unitarios verifican el nombre accesible en inglés y español después de un fallo de imagen; no se amplían las excepciones heredadas.

## 09/10/2026 — Cierre del plan multiidioma y montajes del backend

**Descripción:** Verificación de cierre sobre `develop` (`5ed0472`): CI remoto verde en sus tres jobs (ejecución 37861657623), suites locales repetidas (Django 686, Vitest 96, Playwright 37), contratos y catálogos regenerados sin diferencias, y recorridos contra la API y el frontend reales en inglés y español. Se encontró que `docker compose exec backend python manage.py test` fallaba en 5 tests porque el contenedor no veía `contracts/` ni `docs/i18n/` (los tests y los comandos `exportar_contrato`/`exportar_enums` los resuelven como `BASE_DIR.parent`); en CI pasaban por tener el repo completo. Se decide montar `./contracts` (escritura, para los comandos de exportación) y `./docs/i18n` (solo lectura) en el servicio `backend`, en lugar de cambiar cómo el código resuelve esas rutas, porque así el contenedor y CI comparten la misma disposición. Quien ya tenga el contenedor creado debe recrearlo con `docker compose up -d backend`. Solo resta la revisión manual de correos en un cliente real, que no bloquea las interfaces. Archivos: `docker-compose.yml`.

## 09/10/2026 — Se retiran los documentos de planificación del multiidioma

**Descripción:** Terminado el plan, se eliminan `docs/plan-multiidioma.md`, `docs/siguientes-pasos-multiidioma.md` y, de `docs/i18n/`, `README.md`, `glosario.md`, `errores.csv`, `equivalencias.json` y `tmdb-verificacion-ot60.md`, para no dejar documentos de trabajo dispersos. Siguen disponibles en el historial de git (último commit que los contiene: `5ed0472`). Lo que sigue vigente se conservó: las fuentes de la copia, el glosario, las notas para implementar pantallas y el pendiente de correos pasan a `docs/i18n/guia.md`; la evidencia del comportamiento de TMDB pasa al doc 06. Quedan en `docs/i18n/` solo la guía, los tres CSV que usan el generador y los tests, y `revision-correos/` hasta completar esa revisión. Las entradas anteriores de este archivo que citan el plan o sus órdenes de trabajo (OT-xx) se conservan como historia. La base de desarrollo se volvió a sembrar con `seed --borrar-catalogo`: las cuentas de prueba tienen ahora su idioma guardado. Archivos: los eliminados, `docs/i18n/guia.md`, docs 02, 04 y 06, `openspec/specs/error-contract/spec.md`, `backend/catalogo/services/fallback.py`.

## 09/10/2026 — Chatbot: temas de idioma abiertos para el pair programming

**Descripción:** No es una decisión: son los puntos que Gonza y Marcos deben resolver juntos antes de implementar B-02–B-06, y que el plan multiidioma dejó deliberadamente sin cerrar. Lo ya acordado el 08/10/2026 (ver «Arquitectura del chatbot (Módulo 5)») se mantiene: respuestas en `idioma_efectivo()`, español con voseo, tools de TMDB localizadas, BGE-M3 sobre el corpus canónico en inglés y sin duplicar embeddings. Quedan abiertos:

1. **Idioma de una respuesta SSE en curso.** Cómo se fija el idioma al abrir el stream para que no cambie a mitad de la respuesta.
2. **Cambio de idioma durante una solicitud.** Qué pasa si el usuario cambia el idioma en Preferencias mientras hay una respuesta en curso.
3. **Tarjetas y errores.** Cómo se localizan las tarjetas de producciones dentro del chat y los errores del stream.

Insumos: `filmai/idioma.py` (`idioma_efectivo`), `catalogo/services/idioma_tmdb.py`, la spec `i18n-core` y las 21 filas `chatbot` de `docs/i18n/claves.csv`, que tienen la copia del diseño todavía sin sembrar. Al resolverlos, registrar la decisión en una entrada nueva.

## 09/10/2026 — Chatbot: idioma, tarjetas, errores y límites (cierra los temas abiertos)

- **Descripción**: Gonza y Marcos resolvieron en pair programming los tres
  temas de idioma que quedaron abiertos y ajustaron varios puntos de la
  arquitectura del 08/10/2026, que sigue vigente en todo lo que acá no se
  menciona.
  1. **Idioma del turno**: la vista resuelve `idioma_efectivo(request, usuario)`
     una sola vez, antes de abrir el stream, y lo pasa como dato inmutable al
     prompt, a las tools y a `TMDBClient`. Nadie más lee `usuario.idioma`
     durante el turno. Las tools, las tarjetas y los estados usan siempre ese
     idioma (`en` o `es`).
  2. **Idioma de la prosa (reemplaza el punto 6 del 08/10)**: el modelo
     responde en el idioma en que el usuario escribió el mensaje, sea cual sea
     (un usuario con la interfaz en inglés que escribe en portugués recibe la
     respuesta en portugués, con títulos y tarjetas en inglés). Si el idioma
     del mensaje no se puede identificar (por ejemplo «?»), responde en el
     idioma del turno. La detección la hace el modelo por instrucción del
     prompt, que recibe el idioma del turno como respaldo; no hay detección en
     código. El voseo aplica solo cuando responde en español.
  3. **Cambio de idioma durante una solicitud**: la respuesta en curso termina
     con el idioma con que empezó; el cambio rige desde el mensaje siguiente.
     Los mensajes anteriores quedan como se escribieron. No se agrega
     `Mensaje.idioma`: el servidor no sabe en qué idioma respondió el modelo.
  4. **Tarjetas**: `Mensaje.tarjetas` guarda el texto tal como se mostró
     (`id_tmdb`, `tipo`, `titulo`, `poster`, `año`), en el idioma del turno, y
     el historial lo devuelve sin volver a traducir. Como máximo 3 tarjetas por
     respuesta: `mostrar_tarjetas` recorta en el servidor y el prompt se lo
     avisa al modelo. La forma del JSON se valida al escribir con una clase de
     Python; no hay modelo `Tarjeta` ni FK a `ProduccionAudiovisual`. Mostrar
     una tarjeta no materializa la producción: eso sigue ocurriendo al abrir la
     ficha, calificar o agregar a una lista. Para descartar lo que está en
     «Vistas» alcanza con comparar `id_tmdb` y `tipo`.
  5. **Errores y estados**: viajan por código, nunca como texto. Antes de abrir
     el stream se responde HTTP normal con el sobre `{code, params, errors}`:
     401 (Unauthorized) sin sesión, 403 (Forbidden) por CSRF o cuenta no
     activa, 400 (Bad Request) por mensaje vacío o de más de 500 caracteres,
     409 (Conflict) si ya hay una solicitud en curso y 429 (Too Many Requests)
     por el límite por hora, con `retry_after_seconds`.
     Con el stream abierto, el evento `error` lleva el mismo sobre: proveedor
     caído, timeout, cuota del proveedor, tope de vueltas de tools o falla al
     guardar. La falla de una tool (TMDB u Ollama) no corta el turno: se le
     devuelve al modelo. Las tarjetas con ids inválidos se descartan en
     silencio. La cancelación (CU-014), una pregunta fuera de alcance y una
     búsqueda sin resultados no son errores. Si el stream termina sin evento
     `fin`, el front lo trata como error de red. El evento `estado` también es
     un código que el front traduce.
  6. **Mensaje del usuario**: hasta 500 caracteres, con tres controles: el
     campo no deja escribir más (`maxLength`), el front valida antes de enviar
     y el servidor rechaza con 400 (Bad Request). El navegador cuenta en unidades UTF-16 y
     Python en puntos de código, así que el navegador es siempre el más
     estricto.
  7. **Sin cola de mensajes**: mientras el bot responde no se puede enviar
     otro mensaje. El usuario puede escribir el borrador, el botón de enviar
     pasa a ser «Cancelar» y el servidor lo refuerza con el 409 (Conflict).
  8. **Ruta**: `POST /api/chat/messages/` (corrige el `/api/chat/mensajes/` de
     la entrada del 08/10).
- **Motivo**: complicarse lo menos posible. Fijar el idioma al entrar evita
  estados intermedios. El texto guardado es coherente con que el mensaje queda
  en el idioma en que se escribió, y evita las cuatro llamadas a TMDB por
  título que cuesta `materializar()` dentro de un turno que debe cumplir el
  RNF #6. Dejar que la prosa siga el idioma del mensaje no cuesta nada, porque
  lo resuelve el modelo y BGE-M3 es multilingüe. Una cola de mensajes complica
  la cancelación, el guardado al final del turno y el límite por hora.
- **Abierto para la próxima sesión** (no son decisiones):
  1. Paso a ASGI: hoy `settings.py` solo define `WSGI_APPLICATION` y no hay
     servidor ASGI en `docker-compose.yml`.
  2. La vista async queda fuera de DRF: hay que resolver a mano la
     autenticación por cookie JWT, el CSRF y el sobre de errores.
  3. Dónde se versiona el contrato de los eventos SSE, que drf-spectacular no
     incluye en `contracts/openapi.yaml`.
  4. Cómo se garantiza una sola solicitud en curso por chat.
  5. Lista exacta de códigos de error y de estado, y cuántos mensajes visibles
     distintos tiene el usuario.
  6. Copia del chatbot: curar las 21 filas `chatbot` de
     `docs/i18n/claves.csv`, pasar la conversación de ejemplo a `muestra` y
     agregar las filas que faltan (cancelación y errores). La aprueban Gonza y
     Marcos antes de sembrar.
  7. Texto del prompt: un prompt base con un bloque de estilo por idioma.
  8. Verificar con la key real que el modelo respeta la regla de idioma con
     historial mezclado y medir la latencia (RNF #6).
  9. Abrir el SDD en `openspec/changes/chatbot/` si se decide usarlo.
- **Archivos afectados**: `docs/decisiones.md`, docs 02 (CU-013), 03
  (`Mensaje.tarjetas`), 04 (§3.1), 05 (B-02 a B-05) y 06 (tools),
  `docs/i18n/guia.md` y `PRODUCT.md`.

## 12/10/2026 — Interfaces de acceso y aceptación de los Términos y Condiciones

- **Fecha**: 12/10/2026
- **Descripción**: se implementan Landing, Login, Registro y Confirmación del canvas «FilmAI — Sistema y catálogo» (sección «Access»), en escritorio y celular, y se exige aceptar los Términos y Condiciones al crear una cuenta.
- **Decisiones**:
  1. **Aceptación en la cuenta**: `Usuario.fecha_aceptacion_terminos` (`DateTimeField`, nulo). El registro local recibe `acepta_terminos` (obligatorio: falta → `required`; falso → `terms_not_accepted`, 400 (Bad Request)). El alta con Google lo exige solo para cuentas nuevas y se rechaza con el mismo código en el campo `acepta_terminos`. El servidor fija la fecha con su hora; el cliente no la envía. Las cuentas anteriores quedan en nulo (no se inventa una aceptación); el seed y la factory crean las cuentas con la fecha.
  2. **Texto legal en Markdown**: `frontend/content/legal/terms.{en,es}.md`, copiado del artboard «Terms and Conditions» del canvas, para que un abogado lo revise sin tocar código. Se retiró `legal.json` del catálogo i18n y del generador: el texto legal ya no sale de los CSV. `/terms` es una versión mínima (se refina en el punto 9: con/sin sesión y escritorio/celular).
  3. **Reenvío del enlace vencido**: la pantalla solo conoce la clave, no el correo. El correo se guarda en `sessionStorage` al registrarse y se usa para reenviar; si no está, la pantalla lo pide. La espera entre reenvíos es de 60 s en el cliente.
  4. **Tema**: solo oscuro. Se actualizaron los tokens oscuros al sistema del canvas y se agregaron los propios (`--raised`, `--line`, `--fg-2`, `--fg-3`, `--ok`, `--on-accent`); el claro llega con Apariencia en Preferencias.
  5. **Tipografía**: Big Shoulders (títulos) y Hanken Grotesk (texto) reemplazan a Inter y Roboto.
  6. **Pantallas completas**: Landing, Login, Registro y Confirmación ocultan barra y pie (`isAccessPath` en `lib/routes.ts`); el selector de idioma sin sesión vive en el marco de esas pantallas y reemplaza a `PublicLanguageControl`.
  7. Se eliminan `GoogleLinkButton` y las excepciones legacy de Landing, Login y Registro; `complete-signup` queda como excepción hasta que tenga diseño.
- **Motivo**: cumplir con la exigencia de aceptación con evidencia en la cuenta y permitir la revisión jurídica del texto sin acoplarlo al catálogo.
- **Archivos afectados**: backend (`usuarios/models.py`, migración `0008_fecha_aceptacion_terminos`, `serializers.py`, `adapter.py`, `admin.py`, `factories.py`, seed, `filmai/errores/catalogo.py`, `contracts/error-codes.json` y `contracts/openapi.yaml`, golden de registro y tests); frontend (`app/(public)/page.tsx`, `login`, `register`, `confirm-email`, `terms`, `complete-signup`, `components/access/*`, `lib/legal.ts`, `lib/password-rules.ts`, `lib/pending-email.ts`, `lib/routes.ts`, `app/globals.css`, `app/layout.tsx`, `scripts/i18n/*`, catálogos y tests unitarios/Playwright); docs 02, 03 (y JSON del diagrama), 04, `docs/i18n/copia-propuesta.csv` y `guia.md`.
- **Tests**: Django (registro sin/falso/verdadero, Google sin aceptación, fecha guardada, seed con fecha, contratos y golden); Vitest (reglas de contraseña, cuenta regresiva, Markdown legal, registro, login, recuperación y confirmación); Playwright (landing, login, registro, términos y confirmación en escritorio y celular).

## 12/10/2026 — Validación inline del registro: sin errores por foco/blur y envío condicionado

- **Fecha**: 12/10/2026
- **Descripción**: El formulario de registro marcaba cada campo al perder el foco, lo que llenaba la pantalla de errores al recorrerlo con Tab, y dejaba pulsar «Sign up» con datos inválidos. Se cambió a:
  1. **Campo «sucio»**: un campo solo puede mostrar error después de que la persona escribe o elige algo en él; foco y blur no intervienen. El error se deriva del valor actual (sin estado duplicado), por lo que la confirmación de contraseña se revalida sola al editar la contraseña original.
  2. **Retardo en texto**: el error de un campo de texto aparece tras ~600 ms sin teclear; selección y fecha, al instante. Un campo escrito y vaciado muestra «obligatorio».
  3. **Botón con `disabled` nativo** hasta que todo es válido, el usuario está disponible y los Términos están aceptados, con un texto de ayuda (`auth.signUp.submitPending`). Los errores del servidor se muestran en su campo y se limpian al editarlo.
  4. **`/complete-signup`**: mismo comportamiento; el botón de Google queda inerte (`inert`) hasta que el formulario es válido.
- **Motivo**: evitar una UI invasiva y no permitir envíos que se sabe que fallan.
- **Archivos afectados**: `frontend/app/(public)/register/page.tsx`, `frontend/app/complete-signup/page.tsx`, `docs/i18n/copia-propuesta.csv` (`auth.signUp.submitPending`), catálogos generados, `docs/04_Lineamientos_UI.md` (11.3), tests `tests/access-screens.test.tsx`, `tests/complete-signup.test.tsx`, `e2e/acceso.spec.ts`.

## 12/10/2026 — Pantallas de error y menú de cuenta (sección 11 del canvas)

- **Fecha**: 12/10/2026
- **Descripción**: se implementan «404 and error» (escritorio y celular) y «Account menu» del canvas «FilmAI — Sistema y catálogo».
- **Decisiones**:
  1. **404 (Not Found)**: `app/not-found.tsx` con el código «Error 404», Back to Home y Search. **Error inesperado**: `app/error.tsx` con «Try again» (llama a `reset()` de Next) y Back to Home. Ambas comparten `components/errors/ErrorScreens.tsx` y conservan el encabezado y el pie del sitio. Clave nueva: `errors.pages.notFoundCode`.
  2. **Rutas**: `routes.explore` (`/home`) y `routes.search` (`/search`) se enlazan aunque esas pantallas aún no existan; mientras tanto muestran la pantalla 404. La landing apunta a `routes.explore` en lugar del literal `/inicio`.
  3. **Encabezado**: `Navbar` sigue el canvas (marca, Home/Search/Lists, avatar) y sale de las excepciones legacy. Sin sesión ofrece Log in y Sign up como enlaces. La página actual lleva `aria-current`.
  4. **Menú de cuenta** (`components/AccountMenu.tsx`): cabecera con nombre y `@usuario`, Mi perfil, Calificaciones y reseñas, Preferencias y Cerrar sesión; teclado completo (flechas, Home, End, Escape). Cerrar sesión pide confirmación con `alertdialog` (el foco inicial queda en Cancelar). Si el servidor falla se avisa con un toast traducido y la sesión se mantiene.
  5. **Celular**: barra inferior `MobileTabs` (Home, Search, Lists, Profile) solo con sesión. Hasta integrar Perfil móvil (sección 9, donde el canvas ubica «Log out»), el avatar del encabezado abre el mismo menú en celular para no perder el cierre de sesión.
  6. **Tema**: solo oscuro; todo usa tokens semánticos (`bg-raised`, `text-fg-2`, `border-line`…), de modo que el tema claro se activa sin tocar estos componentes.
- **Motivo**: cerrar la sección 11 del canvas y retirar `Navbar` de las excepciones del linter i18n.
- **Archivos afectados**: `frontend/components/{Navbar,AccountMenu,MobileTabs}.tsx`, `frontend/app/not-found.tsx`, `frontend/app/{not-found,error,layout}.tsx`, `frontend/app/(public)/page.tsx`, `frontend/lib/routes.ts`, `frontend/scripts/i18n/rules.mjs`, `docs/i18n/copia-propuesta.csv`, catálogos generados, tests `tests/errors-and-account-menu.test.tsx`, `e2e/errores-menu.spec.ts` y ajustes en `e2e/cuenta.spec.ts` y `e2e/perfil.spec.ts`.

---

## 12/10/2026 — Acceso a la documentación interna (sección 12 del canvas)

- **Fecha**: 12/10/2026
- **Descripción**: la página 403 de `/api/docs/` y `/api/schema/` pasa a seguir «Admin access» del canvas (escritorio y celular): estado «iniciar sesión» con formulario real, estado de error y estado «sin permisos».
- **Decisiones**:
  1. **Dónde vive**: es una página servida por Django (`templates/filmai/documentacion_restringida.html`), no una ruta de Next.js, porque protege recursos del backend y usa la sesión de Django. Un solo HTML responsive: en celular el formulario se muestra sin tarjeta, como en el canvas.
  2. **Formulario**: `POST /api/docs/login/` (`ingresar_a_documentacion`, `csrf_protect`) autentica por correo o nombre de usuario, exige `is_staff` y cuenta activa, abre la sesión de Django y vuelve a la ruta pedida. Una contraseña incorrecta, una cuenta inexistente y una cuenta común con clave válida reciben el mismo aviso («Incorrect admin credentials.»), con costo de hash igualado para no revelar qué cuentas existen. El destino `next` solo puede ser `/api/docs/` o `/api/schema/`; cualquier otro valor vuelve a Swagger.
  3. **Límite de intentos** (aprobado por el equipo): 10 fallos por IP cada 60 minutos (caché de Django); al superarlo responde 429 (Too Many Requests). El formulario muestra siempre la política y, tras cada fallo, los intentos restantes. Un ingreso correcto reinicia el contador. Es una defensa nueva respecto del Admin de Django, que no limita intentos.
  4. **Sin permisos**: una sesión sin `is_staff` ve «Your account has no access» con su `@usuario`. **Diferencia con el canvas**: «Switch account» no enlaza al login de la aplicación (que abre una sesión JWT distinta y no sirve para la documentación) sino al mismo formulario (`?cuenta=otra`); el ingreso staff reemplaza la sesión anterior. «Back to FilmAI» y «Back to Home» apuntan a `FRONTEND_URL`.
  5. **Idioma**: el canvas está en inglés, pero la página respeta la regla de idioma de la aplicación: cuenta → `Accept-Language` → inglés (`idioma_efectivo`), con textos en/es de paridad verificada por test. Antes estaba fija en español.
  6. **Tema**: solo oscuro; los tokens del tema claro quedan definidos en la plantilla (`.tema-claro`) para activarlo luego.
  7. **Omitido**: la lista vacía «Includes» del canvas no se renderiza (no tiene contenido).
- **Motivo**: cerrar la sección 12 del canvas y reemplazar el aviso con enlace al login del Admin por un acceso con el mismo diseño que el resto del producto.
- **Archivos afectados**: `backend/filmai/documentation.py`, `backend/filmai/urls.py`, `backend/templates/filmai/documentacion_restringida.html`, `backend/filmai/tests.py` (`DocumentacionApiTests` actualizada e `IngresoDocumentacionTests` nueva), `frontend/e2e/documentacion-admin.spec.ts`, `openspec/specs/admin-api-docs/spec.md`.

---

## 12/10/2026 — 404 con y sin sesión (sección 11 del canvas)

- **Fecha**: 12/10/2026
- **Descripción**: `NotFoundScreen` tiene dos variantes aprobadas en el canvas. **Con sesión**: «This page doesn’t exist», Back to Home y Search. **Sin sesión**: «We can’t find that page», Back to Home, Log in y «New to FilmAI? Create a free account». Mientras se resuelve la sesión se muestra la variante con sesión, que no pide cuenta.
- **Encabezado**: sin sesión desaparece el enlace a Lists, como en la propuesta; la barra inferior móvil ya solo existía con sesión.
- **Archivos afectados**: `frontend/app/not-found.tsx`, `frontend/components/Navbar.tsx`, `docs/i18n/copia-propuesta.csv` (4 claves `errors.pages.*`), catálogos generados, `tests/errors-and-account-menu.test.tsx` y `e2e/errores-menu.spec.ts`.

---

## 12/10/2026 — Correos de cuenta con el diseño del canvas

- **Fecha**: 12/10/2026
- **Descripción**: los cuatro correos (confirmación de cuenta, confirmación de correo, restablecer contraseña y contraseña actualizada) adoptan el diseño de las cuatro pantallas «Correo-*» del canvas, en español e inglés.
- **Decisiones**:
  1. **Una sola base**: se rediseña `correos/base.html`; las plantillas por caso y por idioma conservan sus bloques, asunto y texto plano. La copia ya coincidía con el canvas, solo se unió la advertencia en un único párrafo.
  2. **Estilo**: tarjeta oscura con barra de acento, marca, título grande, botón amarillo y fila de enlace copiable. «Contraseña actualizada» usa botón secundario con borde, como en el canvas, y no repite el enlace.
  3. **Cliente de correo**: tabla con estilos en línea. La tipografía de marca se declara con alternativas del sistema, porque Gmail y otros clientes ignoran las fuentes web. La marca usa una celda amarilla con estrella en lugar del SVG del canvas, que muchos clientes eliminan.
  4. **Tema**: solo oscuro. El canvas ofrece una variante clara, que no se implementa en correo porque el cliente decide el esquema.
  5. **Omitido**: las líneas «From» y «Subject» del canvas son anotaciones de la maqueta, no parte del mensaje.
  6. **Limpieza**: se elimina `color_secundario` del contexto del servicio y el naranja anterior.
- **Pruebas**: referencias doradas regeneradas (`tests_golden/correos/*.json`) y `test_html_sigue_el_diseno_del_canvas` en `filmai/test_servicio_correos.py`.
- **Archivos afectados**: `backend/templates/correos/base.html`, `backend/templates/correos/*/*/message.html`, `backend/filmai/correos/servicio.py`, `backend/filmai/test_servicio_correos.py`, `backend/filmai/tests_golden/correos/`, `openspec/specs/emails/spec.md`.

---

## 12/10/2026 — Footer del canvas en escritorio y celular

- **Fecha**: 12/10/2026
- **Descripción**: el pie de página se reconstruye según los tableros «Footer · desktop» y «Footer · mobile» del canvas, que son la referencia vigente. Reemplaza al pie anterior (`LocaleControls.tsx`), que mezclaba una versión mínima con el selector de idioma.
- **Decisiones**:
  1. **Escritorio**: marca con descripción y tres columnas (Explore: Home y Search; Your library: My lists, Ratings & reviews, My profile y Settings; Information: Terms and Conditions e idioma), más una fila inferior con la atribución de TMDB y el copyright.
  2. **Celular**: marca con descripción corta y lista de filas (Terms and Conditions e Idioma con el idioma actual), con la atribución y el copyright debajo. Las columnas de navegación no se repiten porque la barra inferior ya cubre Home, Search, Lists y Profile.
  3. **Idioma**: con sesión es un enlace a `/settings#t-idioma` (solo se cambia en Preferencias). Sin sesión, el canvas solo define la pastilla de escritorio; en celular se usa la pastilla compacta `EN | ES` ya existente, y se suman las filas Sign up y Log in porque no hay barra inferior.
  4. **Omitido**: el enlace «Ask FilmAI» del canvas no se implementa porque el chatbot (sección 10) aún no tiene ruta; la clave sigue excluida del catálogo (D11). Se agrega cuando exista la pantalla.
  5. **Visibilidad**: sigue montado en el layout raíz y se oculta en las pantallas de acceso (`isAccessPath`), de modo que aparece en todas las páginas con encabezado (Settings, Profile, My reviews, Terms, errores y reset-password).
  6. **Tema**: usa los tokens del sistema (`line`, `fg-2`, `fg-3`), así que sigue el tema claro/oscuro.
  7. **Copia**: reutiliza las claves `footer.main.*` y `nav.*`; solo se agrega `footer.main.languageLink` (nombre accesible del enlace de idioma) en `copia-propuesta.csv`.
- **Pruebas**: `tests/footer.test.tsx` (enlaces, con/sin sesión, ocultamiento) y `e2e/i18n-flows.spec.ts` actualizado (390 y 1280 px).
- **Archivos afectados**: `frontend/components/Footer.tsx` (nuevo), `frontend/components/LocaleControls.tsx` (eliminado), `frontend/app/layout.tsx`, `docs/i18n/copia-propuesta.csv`, catálogos generados, `docs/04_Lineamientos_UI.md`, `openspec/specs/i18n-core/spec.md`.

---

## 12/10/2026 — Enlace «Ask FilmAI» en el footer (provisorio)

- **Fecha**: 12/10/2026
- **Descripción**: se agrega al footer el enlace «Ask FilmAI» del canvas aunque el chatbot todavía no exista, por pedido explícito. Reemplaza el punto 4 de la entrada «Footer del canvas en escritorio y celular» (que lo omitía).
- **Decisiones**:
  1. **Ubicación**: columna Explore en escritorio y fila entre Terms and Conditions e Idioma en celular, con y sin sesión.
  2. **Ruta provisoria**: `routes.askFilmAI = "/chat"`. No hay pantalla, así que hoy responde 404 (Not Found).
  3. **Copia**: nueva clave `footer.main.askFilmAI` en `copia-propuesta.csv` («Preguntale a FilmAI» / «Ask FilmAI»); la fila `chatbot` de `claves.csv` sigue excluida (D11).
- **Pendiente**: al desarrollar el chatbot (sección 10), definir la ruta final de la pantalla, actualizar `routes.askFilmAI` y retirar la nota de ruta provisoria; revisar la clave del catálogo.
- **Pruebas**: `tests/footer.test.tsx` verifica el enlace (escritorio y celular, con y sin sesión).
- **Archivos afectados**: `frontend/components/Footer.tsx`, `frontend/lib/routes.ts`, `frontend/tests/footer.test.tsx`, `docs/i18n/copia-propuesta.csv`, catálogos generados.

---

## 12/10/2026 — Selector de idioma único EN | ES

- **Fecha**: 12/10/2026
- **Descripción**: el selector «English | Español» (Settings y footer de escritorio sin sesión) pasa al mismo estilo que el selector `EN | ES` de las pantallas de acceso y del footer móvil, para tener un único componente en todo el sistema. Se actualizó el canvas (Footer, Settings escritorio y móvil, nota de decisiones de idioma).
- **Decisiones**:
  1. `LanguageSwitcher` pierde la prop `compact`: siempre muestra `EN` / `ES` (píldora de 40 px, activo con `bg-selected`).
  2. El nombre completo («English», «Español») se conserva como `aria-label` del radio, así que lectores de pantalla y pruebas no cambian.
  3. Las claves `settings.language.english` / `spanish` siguen en el catálogo, ahora solo como etiqueta accesible.

4. Regla de ubicación sin sesión (confirmada el 12/10/2026): si la pantalla no tiene navbar (Landing, Log in, Sign up, Account confirmation), el selector va arriba a la derecha; si tiene navbar (Terms, 404, error inesperado), va en el footer. Con sesión no hay selector fuera de Settings. Se probó ponerlo también en el navbar de Terms y se descartó; Terms queda como estaba.
5. El canvas gana la variante sin sesión del footer móvil (`Footer-Movil.dc.html`, prop `sesion`) y el padding superior de 75 px del contenido de la Landing en escritorio, que ya estaban en el código.

- **Archivos afectados**: `frontend/components/LanguageSwitcher.tsx`, `frontend/components/Footer.tsx`, `frontend/components/access/AccessShell.tsx`, `docs/04_Lineamientos_UI.md`.
- **Nota sobre el canvas**: My profile, Settings y Ratings & reviews se marcaron como «hay que rehacer» (el artboard es la fuente de verdad); no se implementó nada en esta entrada.

---

## 12/10/2026 — «Ingresar» / «Registrarse» en lugar de «Iniciar sesión» / «Crear cuenta»

- **Fecha**: 12/10/2026
- **Descripción**: en celular, con el texto en español, «Iniciar sesión» y «Crear cuenta» no entran en una fila del navbar junto al logo (se partían en dos líneas en el 404 sin sesión). Se acortan los rótulos del glosario en español: Log in → **Ingresar**, Sign up → **Registrarse**. El inglés no cambia.
- **Decisiones**:
  1. Se modifican las claves `nav.account.logIn` y `nav.account.signUp` en `docs/i18n/claves.csv` (`es_original` y `es_curado`); los catálogos se regeneran.
  2. El glosario de `docs/i18n/guia.md` y los textos de `docs/04_Lineamientos_UI.md` que nombran esos botones se actualizan.
  3. **Sin cambios**: los casos de uso (CU-001, CU-003) y las frases con verbo («Iniciá sesión de nuevo», «Creá una cuenta gratis»), que no son rótulos de botón.
- **Corrección relacionada**: el botón de registro deshabilitado por formulario incompleto mostraba el cursor `wait` (progress) porque `primaryButtonClass` aplica `disabled:cursor-wait` y le ganaba a `disabled:cursor-not-allowed`. Ahora usa `not-allowed` mientras el formulario es inválido y `wait` solo mientras envía.
- **Archivos afectados**: `docs/i18n/claves.csv`, `docs/i18n/guia.md`, `docs/04_Lineamientos_UI.md`, catálogos generados, `frontend/app/(public)/register/page.tsx`.

---

## 12/10/2026 — Terms and Conditions en celular

- **Fecha**: 12/10/2026
- **Descripción**: la pantalla `/terms` se ajusta al artboard «Terms · mobile»: índice «On this page» plegable (`<details>`), enlace de regreso (con sesión a Settings, sin sesión a la portada), título de 48 px, secciones con h2 de 28 px y márgenes del canvas. En escritorio no cambia: sigue pendiente la miga de pan Profile › Settings › Terms del artboard de escritorio.
- **Archivos afectados**: `frontend/app/terms/page.tsx`, `frontend/components/TermsBackLink.tsx`, `frontend/tests/terms-back-link.test.tsx`, `frontend/e2e/acceso.spec.ts`.

---

## 12/10/2026 — Estado de la interfaz frente al canvas en el plan de desarrollo

- **Fecha**: 12/10/2026
- **Descripción**: `docs/05_Plan_de_Desarrollo.md` gana la sección «Estado de la interfaz frente al canvas de Claude Design», con una fila por sección del canvas y cuatro estados (✅ completa, 🟡 parcial, 🔁 rehacer, ⬜ falta), para que se vea qué pantallas ya coinciden con el diseño y cuáles hay que desarrollar o actualizar. Se corrigieron filas desactualizadas (rutas de A-02, A-06 y A-07, y Q-02, que ya está implementada) y se marcaron P-02, P-04 y P-06 como «UI a rehacer».
- **Archivos afectados**: `docs/05_Plan_de_Desarrollo.md`, `docs/decisiones.md`. La nota «Interfaces: código vs pendientes» del canvas refleja el mismo estado.

---

## 13/10/2026 — CI en las ramas `develop/**` y PRs hacia `develop/ui-design`

- **Fecha**: 13/10/2026
- **Descripción**: el CI pasa a correr en los PRs hacia una rama `develop/**` y en los push a esas ramas. Hasta ahora solo corría en `main`, `develop` y `feat/**`, así que `develop/ui-design` (creada el 12/10/2026, después de que `develop` se integró a `main` y se borró) no tenía ninguna verificación automática. Gonza trabaja las pantallas del catálogo (C-05 Home, C-06 Buscar, C-07 Ficha y el modal de C-08) en ramas propias, con PR hacia `develop/ui-design`, y las mergea él mismo con el CI en verde, como dice la sección 8 de `AGENTS.md`.
- **Motivo**: sin esto, un PR hacia `develop/ui-design` se mergeaba sin correr ruff, los tests de Django, Vitest, Playwright ni el build. Para un `pull_request`, GitHub toma el workflow del commit de merge, así que este mismo PR ya corre con el disparador nuevo y verifica por primera vez los commits del 12/10/2026.
- **Test salteado en el CI**: al correr por primera vez sobre `develop/ui-design`, falló `frontend/e2e/documentacion-admin.spec.ts` (del 12/10/2026). Ese test usa el backend real (`docker compose exec backend ...`) y el job de Playwright solo levanta Next.js, con la API simulada. Se saltea cuando existe la variable `CI` (`test.skip(!!process.env.CI, ...)`) y sigue corriendo en local con Docker levantado. El backend de esa pantalla ya tiene cobertura en la suite de Django. Si se quiere en el CI, hay que levantar Docker Compose en el job de Playwright.
- **Archivos afectados**: `.github/workflows/ci.yml`, `frontend/e2e/documentacion-admin.spec.ts`, `docs/decisiones.md`.

---

## 13/10/2026 — Home de descubrimiento (C-05): SDD y decisiones

- **Fecha**: 13/10/2026
- **Descripción**: Gonza abre el SDD de C-05 en `openspec/changes/home-catalogo/` (proposal, design y tasks). Decisiones del usuario:
  1. **Orden de las pantallas del catálogo**: Home → Ficha (C-07 con el modal de C-08) → Buscar (C-06). La ficha es el destino de todas las tarjetas y la necesita L-04; Buscar reusa piezas del Home.
  2. **Ruta de la ficha**: `/movie/[id]` y `/tv/[id]`, con el helper `routes.title(tipo, id)`. Mismo nombre que la API (`/api/catalogo/movie/<id>/`) y que TMDB, y Next.js responde 404 (Not Found) solo ante un tipo inválido porque esa carpeta no existe. Se descartó `/title/[tipo]/[id]`, que obliga a validar el tipo a mano. El tipo va en la URL en las dos opciones porque TMDB numera películas y series por separado.
  3. **Recomendado para ti**: `GET /api/catalogo/recommended/?tipo=all|movie|tv`, con sesión. Por tipo, los 3 géneros más repetidos entre las calificaciones activas de 7 o más (empate: el de la calificación más reciente); `discover` con los géneros unidos con OR, `popularity.desc` y `vote_count.gte=100`; se excluyen los pares `(id_tmdb, tipo)` de «Vistas»; hasta 15 de la primera página. Devuelve los nombres de los géneros usados para el subtítulo de la fila. Verificado contra TMDB el 13/10/2026: con OR quedan 14.610 películas y con AND 841; sin mínimo de votos, 9 de 20 películas tenían menos de 100 votos y aparecía un anime adulto sin la marca `adult`.
  4. **Novedades de series**: `discover` gana el parámetro `min_votes` (`vote_count.gte`) y la fila lo usa con 50: sin mínimo, 10 de 20 series de 2026 tenían menos de 50 votos; con 50 quedan 150 y con 100 solo 73. `now-playing` no admite ese filtro y queda como está.
  5. **Hero**: en «Todo», el primer título de tendencias con imagen de fondo («#N en tendencias»); en «Películas» y «Series», el primero de ese tipo que no sea el Hero de «Todo» («Destacada de la semana»). Regla pedida el 03/10/2026 en el canvas.
  6. **Botón «Ask FilmAI»** en el Home ya, solo con sesión, hacia `/chat` (404 (Not Found) hasta B-04), como el enlace del footer.
  7. **El selector vive en la URL** (`/home?type=movie|tv`), para que se conserve al volver de una ficha.
  8. **Tamaño de las filas**: Tendencias y Novedades, 20 (una página de TMDB); Recomendado, hasta 15.
  9. **«Todo» alterna película y serie** en Recomendado y Novedades. El usuario pidió revisar más adelante, con datos reales, separar filas por tipo al estilo Netflix (descartado el 30/09/2026 por largo en celular y siete pedidos al cargar; además deja el selector casi sin uso y el canvas dibuja filas mezcladas).
  10. **Barra de navegación sobre el Hero** en escritorio, solo en `/home`, como el artboard. Toca `components/Navbar.tsx` (Marcos).
  11. **Errores**: la fila que falla se oculta y un único toast avisa; si fallan todas, mensaje con «Try again».
- **Entrega**: cuatro PRs contra `develop/ui-design`: SDD y docs, backend, piezas compartidas (`TypeSelector`, `MediaCard`, `MediaRow`) y la página.
- **Archivos afectados**: `openspec/changes/home-catalogo/`, `docs/04_Lineamientos_UI.md` (§2: el Home pasa a «Mixta»; §3.3 y §5), `docs/decisiones.md`.

---

## 13/10/2026 — Recomendado para ti: implementación del backend (C-05, PR 2)

- **Fecha**: 13/10/2026
- **Descripción**: se implementa `GET /api/catalogo/recommended/` según el SDD (`openspec/changes/home-catalogo/design.md` §2) y el parámetro `min_votes` de `GET /api/catalogo/discover/`. Decisiones de implementación:
  1. **Servicio aparte** en `catalogo/services/recomendado.py`, sin HTTP ni idiomas: la vista le pasa el servicio de TMDB ya localizado (`servicio_localizado`) y una función que traduce ids de género a nombres. Así los resultados llevan `campos_en_ingles` como el resto del catálogo, y el servicio se prueba con un TMDB falso.
  2. **Nombres de géneros reusados**: la lógica de `GenresView` (nombre vacío en español → inglés) pasa a `_generos_localizados(tipo, idioma)` en `catalogo/views.py`, que usan las dos vistas.
  3. **`min_votos` entra en la clave de caché solo cuando se usa**: las consultas de `discover` sin mínimo (C-03, C-04c) conservan la clave que ya tenían en Redis.
  4. **Desempate de géneros**: por la calificación más reciente, aprovechando el orden del modelo (`-fecha, -id`) y que `Counter.most_common` respeta el orden de aparición en los empates.
- **Tests**: `catalogo/tests_recomendado.py` (16 casos, con recortes de respuestas reales de TMDB del 13/10/2026) y 3 en `catalogo/tests.py` (`min_votos` en el cliente y la caché, y `min_votes` en la vista). Suite completa: 725 tests.
- **Archivos afectados**: `catalogo/services/recomendado.py`, `catalogo/views.py`, `catalogo/urls.py`, `catalogo/client.py`, `catalogo/cache.py`, `catalogo/tests_recomendado.py`, `catalogo/tests.py`, `contracts/openapi.yaml`, `openspec/specs/recommendations-api/spec.md`, `openspec/specs/tmdb-endpoints/spec.md`, `openspec/changes/home-catalogo/tasks.md`.

---

## 13/10/2026 — Piezas compartidas del catálogo en el frontend (C-05, PR 3)

- **Fecha**: 13/10/2026
- **Descripción**: se agregan las piezas que reusan el Home, Search (C-06) y el detalle de listas (L-03), según el SDD (`openspec/changes/home-catalogo/`, fase 2) y las medidas del canvas (tarjeta de 132 px en celular y 176 px en escritorio, título de fila de 30/40 px).
  1. **`lib/catalog.ts`**: `normalizeTitle` convierte un item de TMDB (de `trending`, `discover`, `now-playing` o `recommended`) en un `Title` de la app. Descarta lo que no es película ni serie (TMDB puede mezclar personas en `trending/all`) y deja la nota en `null` cuando es 0: el 13/10/2026, 9 de 100 títulos de tendencias no tenían votos y «★ 0,0» confundiría. Marca `tituloEnIngles`/`sinopsisEnIngles` a partir de `campos_en_ingles`.
  2. **`tmdbImage(path, size)`**: arma URLs de imágenes de TMDB con la misma validación que `posterUrl` de `lib/reviews.ts` (solo rutas de TMDB o `https://image.tmdb.org`). `posterUrl` queda como está; se puede unificar al rehacer Mis reseñas.
  3. **`routes.title(tipo, id)`** → `/movie/{id}` o `/tv/{id}`. Responde 404 (Not Found) hasta C-07.
  4. **`TypeSelector`**, **`MediaCard`** y **`MediaRow`** en `components/features/`. La nota se lee con una etiqueta oculta («TMDB rating: 7.7 out of 10») y la estrella con el número quedan `aria-hidden`. La fila es una lista (`ul`/`li`) con snap en celular y flechas que mueven el 90 % del ancho visible en escritorio, sin animación con `prefers-reduced-motion`. Vacía y sin cargar no se dibuja; cargando muestra 5 esqueletos.
  5. No hizo falta copia nueva: se usan `common.content.*`, `common.media.*` y `home.carousel.*`, ya sembradas.
- **Tests**: Vitest, con recortes de respuestas reales de TMDB del 13/10/2026 (`tests/catalog-fixtures.ts`): `catalog.test.ts` (9), `media-card.test.tsx` (6), `type-selector.test.tsx` (2) y `media-row.test.tsx` (4). Suite completa: 165.
- **Archivos afectados**: `frontend/lib/catalog.ts`, `frontend/lib/routes.ts`, `frontend/components/features/{TypeSelector,MediaCard,MediaRow}.tsx`, `frontend/tests/{catalog-fixtures.ts,catalog.test.ts,media-card.test.tsx,type-selector.test.tsx,media-row.test.tsx}`, `openspec/changes/home-catalogo/tasks.md`.

---

## 13/10/2026 — Home de descubrimiento en `/home` (C-05, PR 4) y cierre de C-05

- **Fecha**: 13/10/2026
- **Descripción**: se implementa la página `/home` según el SDD y los artboards «Home · desktop» y «Home · mobile» del canvas: Hero, Recomendado (con sesión), Tendencias, Novedades, selector en la URL, invitación a registrarse sin sesión y botón «Ask FilmAI» con sesión. El login y el alta con Google llevan a `/home` (A-04 cerrada). Decisiones de implementación:
  1. **Selector con la History API** (`window.history.replaceState`) en lugar de `router.replace`: Next.js lo sincroniza con `useSearchParams` sin volver a pedir la página al servidor. Con `router.replace` cada clic esperaba esa ida y vuelta; en Playwright tardaba más de 5 s.
  2. **Cada fila pide sus datos** con `useCatalog` (`lib/use-catalog.ts`), que guarda en memoria las respuestas públicas ya recibidas (volver a una opción del selector no repite el pedido) y nunca lo que falló ni Recomendado. Una fila que falla se oculta y un único toast (`id: "home-carga"`) muestra el error traducido por código; si fallan todas, el mismo mensaje con «Reintentar» (`common.actions.retry`). No hizo falta copia nueva.
  3. **Barra sobre el Hero**: en `/home` y en escritorio, `components/Navbar.tsx` pasa a `md:absolute`; el Hero empieza arriba de todo.
  4. **Tarjeta con `relative`**: la etiqueta `sr-only` de la nota es `absolute` y, sin un ancestro posicionado dentro de la fila, escapaba del `overflow` del `ul` y estiraba la página a ~3.900 px con 20 tarjetas. El test de Playwright usa 20 tarjetas y verifica que el documento no sea más ancho que la ventana (falla sin el arreglo).
  5. **Datos de la línea del Hero en celular**: año y nota en un renglón y los géneros en el siguiente (`order-last`), para que ningún «·» quede colgando.
  6. **Tipo por defecto en tendencias de un tipo** y **descarte de repetidos** en `normalizeTitles`. Verificado el 13/10/2026: TMDB manda `media_type` en `trending/movie` y `trending/tv`, pero no en `now_playing` ni en `discover`.
  7. **`formatList`** en `lib/format.ts` para el subtítulo de Recomendado («Thriller, Drama, and Crime» / «Suspense, Drama y Crimen»).
  8. **Títulos largos en el Hero** (reportado por el usuario con «Spider-Man: Brand New Day» en Movies): el texto del Hero estaba colgado del borde inferior de una capa `absolute` y, con varios renglones a 152 px, crecía hacia arriba encima del selector. Ahora solo la imagen es `absolute`; el texto va en el flujo y se empuja hacia abajo, con 48 px mínimos bajo el selector en escritorio, y la sección se agranda. En celular la altura del Hero pasa de fija (560 px) a mínima. Un test de Playwright con un título largo real («Law & Order: Special Victims Unit») falla con la versión anterior.
  9. **Tamaño del título según su largo** (pedido del usuario el 14/10/2026: aun sin superponerse, un título largo quedaba muy pegado al selector, mientras que en All y TV shows se veía bien). `tamanioTitulo()` en `lib/home.ts` cuenta caracteres visibles: hasta 16 conserva el tamaño del canvas (152/72 px), de 17 a 28 usa 112/56 px y más largos 88/44 px; además `text-balance` reparte los renglones. A 152 px entran unos 19 caracteres por renglón en escritorio, así que «Spider-Man: Brand New Day» (25) queda en un renglón a 112 px. Se descartó medir el texto con JavaScript y achicarlo hasta que entre: más complejo y el título cambia de tamaño al cargar. En el camino apareció un detalle de `cn()`: `tailwind-merge` borra un `leading-*` que venga antes de una clase de tamaño de letra, así que el interlineado va al final.
- **Cierre de C-05**: con este PR se completan las cuatro entregas del SDD (#69 a #72). Según AGENTS.md §9, se elimina `openspec/changes/home-catalogo/`; las specs canónicas son `recommendations-api` y `home-ui`. Queda pendiente actualizar con Marcos la nota «Interfaces: código vs pendientes» del canvas (Home ✅).
- **Tests**: Vitest `home.test.ts` (7: regla del Hero, mezcla, `?type=`, `formatList`) y `home-page.test.tsx` (6: sin sesión, con sesión, fila que falla, `?type=movie`, selector en la URL, todo falla y reintento); un caso nuevo en `catalog.test.ts` (repetidos). Playwright `e2e/home.spec.ts` (6, escritorio y celular, API simulada con recortes reales de TMDB); `e2e/i18n-flows.spec.ts` espera `/home` después del login.
- **Archivos afectados**: `frontend/app/home/page.tsx`, `frontend/components/features/{HomeView,HomeHero,MediaCard}.tsx`, `frontend/components/Navbar.tsx`, `frontend/lib/{home,use-catalog,catalog,format}.ts`, `frontend/app/(public)/login/page.tsx`, `frontend/app/complete-signup/page.tsx`, tests y e2e, `openspec/specs/home-ui/spec.md`, `docs/05_Plan_de_Desarrollo.md`, `docs/decisiones.md`; se elimina `openspec/changes/home-catalogo/`.

---

## 14/10/2026 — Ficha de detalle (C-07): SDD y decisiones

- **Fecha**: 14/10/2026
- **Descripción**: Gonza abre el SDD de C-07 en `openspec/changes/title-page/`, que incluye el modal de calificar (mitad frontend de C-08) y las acciones de listas (L-04). Decisiones del usuario:
  1. **L-04 la construye Gonza dentro de C-07** (era de Marcos): está en la misma pantalla y «Watched» está atado a la calificación (regla «calificada ⇒ vista» del 30/09/2026 y el 409 al quitarla). La API de L-01 ya trae la pertenencia con `item_id`, el alta y la baja con `?borrar_calificacion=true`.
  2. **Reseñas de la comunidad públicas**: `GET /api/reviews/?id_tmdb=&tipo=` deja de pedir sesión; el `POST` la sigue pidiendo. Coincide con la nota del canvas («las calificaciones y reseñas son públicas y se ven en la ficha»).
  3. **Orden y filtro por nota** en esas reseñas, como el canvas: `orden` (`fecha-desc`, `fecha-asc`, `nota-desc`, `nota-asc`) y `nota_min`/`nota_max`. Para que el cursor no dependa de un offset entre miles de notas iguales, los órdenes por nota usan una clave única anotada (`valor * 10^9 + id`). La respuesta suma `total_comunidad` (sin filtros) para «Showing X of N».
  4. **El origen de la miga de pan viaja en la URL**: `?from=home|search|reviews|list-{id}`; sin parámetro, Home. Se descartó `sessionStorage`, que se pierde al recargar o abrir otra pestaña.
- **También**: endpoint nuevo `GET /api/catalogo/{movie|tv}/{id}/credits/` con directores (en series, `created_by`: verificado el 13/10/2026 que Breaking Bad no tiene director a nivel serie) y reparto con personaje; las calificaciones se muestran «★ N», no «X/10»; sin sesión, «Log in to rate or save» con `?next=` a la misma ficha.
- **Entrega**: cinco PRs contra `develop/ui-design`: SDD y docs, backend, modal y confirmaciones, acciones de listas, y la página.
- **Archivos afectados**: `openspec/changes/title-page/`, `docs/04_Lineamientos_UI.md` (§5c), `docs/05_Plan_de_Desarrollo.md` (L-04), `docs/decisiones.md`.

---

## 14/10/2026 — Ficha: créditos y reseñas públicas con orden y filtro (C-07, PR 2)

- **Fecha**: 14/10/2026
- **Descripción**: backend de la ficha según el SDD (`openspec/changes/title-page/design.md` §2).
  1. **`GET /api/catalogo/{movie|tv}/{id}/credits/`** (público): `{directores, reparto: [{nombre, personaje}]}`, hasta 50 en el orden de TMDB. En series los «directores» son `created_by`. Servicio en `catalogo/services/creditos.py`; los créditos ya estaban en la caché de Redis.
  2. **Reseñas de la comunidad públicas**: `CalificacionesView.get_permissions` devuelve `AllowAny` para `GET`; el `POST` sigue con `IsAuthenticated`. Sin sesión no se excluye nada; con sesión se sigue sacando la propia. El test `test_los_anonimos_no_leen_resenas` pasa a `test_los_anonimos_leen_las_resenas_de_todos`.
  3. **Orden y filtro**: `ComunidadQuerySerializer` valida `orden`, `nota_min` y `nota_max`. Los órdenes por nota usan la clave anotada `valor * 10^9 + id`, con `Cast` a entero de 64 bits **antes** de multiplicar: `valor` es un entero de 32 bits en Postgres y sin el `Cast` la cuenta se pasaba de rango (`integer out of range`); `ExpressionWrapper` solo declara el tipo del resultado.
  4. **`total_comunidad`** en la respuesta (sin filtros); `ResenaCursorPagination` lo agrega solo si la vista lo fija, así «Mis reseñas» no cambia.
- **Tests**: `catalogo/tests_ficha.py` (4, créditos con recortes reales de TMDB) y en `tests_reviews.py` la lectura anónima, la escritura que sigue cerrada y `ComunidadOrdenYFiltroTests` (7, incluido el recorrido por cursor sobre 25 notas iguales).
- **Archivos afectados**: `backend/catalogo/{reviews,views,urls,serializers_reviews,pagination_reviews}.py`, `backend/catalogo/services/creditos.py`, tests, `contracts/openapi.yaml`, `openspec/specs/{reviews-api,tmdb-endpoints}/spec.md`, `openspec/changes/title-page/tasks.md`.

---

## 14/10/2026 — Modal de calificar y confirmaciones de la ficha (C-07, PR 3)

- **Fecha**: 14/10/2026
- **Descripción**: componentes de `components/features/title/` según el canvas y el doc 04 §5d. No llaman a la API: avisan con `onSubmit`/`onConfirm` y la ficha (PR 5) decide qué pedir y qué toast mostrar; si la promesa falla, el error queda a la vista y el diálogo sigue abierto.
  1. **`DialogShell`**: `<dialog>` nativo con `showModal()`, como `components/Modal.tsx` de Marcos (fondo inerte, Escape, foco de vuelta a quien lo abrió), con el diseño del canvas: tarjeta centrada en escritorio y hoja con agarre en celular. No se reusó `Modal` porque su caja y su título no coinciden con el canvas.
  2. **`StarRating`**: `radiogroup` de WAI-ARIA con foco itinerante (solo la elegida entra en el orden de Tab), flechas, Home y End; al previsualizar una nota menor, las de la elegida que quedan afuera se ven tenues; dos filas de cinco en celular (objetivos de 44 px).
  3. **`RatingDialog`**: «Rate {title}» o «Edit rating», «Rating: ★ N» en vivo, «Before: ★ N» al cambiar una nota existente, aviso de Vistas solo si la producción no está, reseña opcional con `maxLength` 1000 y contador, «Remove rating» solo al editar. En celular, Cancel y la acción van en dos columnas y «Remove rating» centrado debajo (canvas).
  4. **`ConfirmDialog`**: `alertdialog` con el foco inicial en Cancelar (Enter no borra por error), vista previa de la reseña en dos renglones con «Read more» si es larga. El botón de peligro usa el rojo del sistema con texto oscuro (`--on-accent`, ~5,4:1); con blanco el contraste quedaba en 3,6:1.
  5. Toda la copia ya estaba sembrada (`title.rating.*`, `title.review.*`, `common.*`).
- **Tests**: Vitest `star-rating.test.tsx` (5), `rating-dialog.test.tsx` (6) y `confirm-dialog.test.tsx` (3). Suite: 196.
- **Archivos afectados**: `frontend/components/features/title/{DialogShell,StarRating,RatingDialog,ConfirmDialog}.tsx`, tests, `openspec/changes/title-page/tasks.md`.

---

## 14/10/2026 — Acciones de listas en la ficha (C-07 / L-04, PR 4)

- **Fecha**: 14/10/2026
- **Descripción**: `TitleActions` y `ListsMenu` en `components/features/title/`, con `lib/title-lists.ts` (tipo `ListaFicha` y cambios de pertenencia), según el canvas.
  1. **Calificar**: «Rate» o «★ N» (en celular, «Your rating N» a todo el ancho); la etiqueta accesible con nota sale de `title.rating.editSummary` con `t.markup` («Your rating: 9 out of 10. Edit»).
  2. **Favorite / Watched / Watchlist**: botones con `aria-pressed` que llaman a la API de L-01 (`POST …/items/`, `DELETE …/items/{item_id}/`) y avisan con el toast de cada lista. En celular van en una grilla de cuatro con «Lists».
  3. **Quitar de Vistas algo calificado**: la API responde 409 `rating_blocks_removal_from_watched`; se pide confirmar con `ConfirmDialog` (texto de `title.rating.removeBoth/OnlyDescription` y la reseña como vista previa) y se reintenta con `?borrar_calificacion=true`, que borra calificación, reseña e ítem juntos. La ficha se entera con `onCalificacionBorrada`.
  4. **«Add to list»**: panel bajo el botón en escritorio y hoja en celular, con las listas propias como casillas (`aria-pressed`), sus cantidades y «New list» en el lugar: el nombre vacío se rechaza antes de llamar a la API, `list_name_duplicated` muestra «You already have a list with that name.» y los errores de campo salen de `extraerErroresPorCampo`. Crear hace `POST /api/lists/` y después el alta del ítem.
  5. **Foco**: los botones se arman con una función y no con un componente definido adentro de otro, que React volvería a montar en cada redibujo y dejaría sin foco a quien usa el teclado. Un test lo cubre (falla con la versión anidada).
- **Tests**: Vitest `title-actions.test.tsx` (11). Revisado contra el canvas en escritorio y celular.
- **Archivos afectados**: `frontend/components/features/title/{TitleActions,ListsMenu}.tsx`, `frontend/lib/title-lists.ts`, `frontend/tests/title-actions.test.tsx`, `openspec/changes/title-page/tasks.md`.

---

## 14/10/2026 — Página de la ficha (C-07, PR 5)

- **Fecha**: 14/10/2026
- **Descripción**: `/movie/[id]` y `/tv/[id]` con `TitleView` y `CreditsSection` según los artboards de la ficha. La página es pública; con sesión suma la calificación propia y las listas.
  1. **Se parte en dos PRs** para respetar el tope de revisión: este trae la página, los créditos y las acciones conectadas; el PR 6 trae las reseñas (la propia y la comunidad) y el cierre de C-07.
  2. **Origen en la URL**: `routes.title(tipo, id, from)`; el Home pasa `from=home` en tarjetas y Hero. `?from=list-{id}` pide el nombre de la lista (`GET /api/lists/{id}/`) y usa `routes.list(id)` (`/lists/{id}`), que Marcos puede cambiar al hacer L-03. En celular la miga se reemplaza por un enlace «‹ {origen}» sobre la franja, con fondo semitransparente para que se lea sobre imágenes claras.
  3. **Título por largo** con la regla del Home y tamaños propios (120/88/64 px en escritorio, 48/40/32 en celular) y `break-words` para que una palabra larga no se salga de la columna angosta del celular.
  4. **Datos**: en celular las temporadas y episodios y la nota bajan a su propio renglón, como en el Hero del Home, para que ningún «·» quede colgando.
  5. **Edición de la nota**: `planEdicion()` manda solo lo que cambió; vaciar una reseña que existía se hace con `DELETE …/texto/` aparte, porque la API rechaza un texto vacío. Después de calificar o quitar la nota se recargan las listas: el servidor suma o saca de Vistas y hace falta el `item_id` nuevo.
  6. **Copia nueva** en `copia-propuesta.csv`: «Created by»/«Creación», temporadas y episodios (plural ICU), «Back to {label}», «Log in to rate or save», «Load more reviews» y el vacío de reseñas.
  7. La barra de navegación va sobre la franja en la ficha, también en celular (canvas).
- **Tests**: Vitest `title.test.ts` (7) y `title-view.test.tsx` (7). Los de la página se escribieron después del código; se verificó que detectan fallas rompiendo a propósito el borrado del texto y la recarga de listas (fallan los dos tests esperados). Revisado con datos reales de TMDB en escritorio y celular, con y sin sesión.
- **Archivos afectados**: `frontend/app/{movie,tv}/[id]/page.tsx`, `frontend/components/features/title/{TitleView,CreditsSection}.tsx`, `frontend/components/features/{MediaCard,MediaRow,HomeView,HomeHero}.tsx`, `frontend/components/Navbar.tsx`, `frontend/lib/{title,routes,catalog}.ts`, catálogos generados, `docs/i18n/copia-propuesta.csv`, tests, `openspec/changes/title-page/tasks.md`.

---

## 14/10/2026 — Reseñas de la ficha y cierre de C-07 (PR 6)

- **Fecha**: 14/10/2026
- **Descripción**: `ReviewsSection` en `components/features/title/` según el canvas, y cierre de C-07 (con la mitad visual de C-08 y L-04).
  1. **«Your review»** arriba, solo si la calificación propia tiene texto: avatar, «★ N», fecha («today» si es de hoy), texto, «Edit» (abre el modal) y «Delete review» (confirmación y `DELETE …/texto/`; la nota queda).
  2. **Comunidad pública** con orden y filtro por nota sobre los parámetros del PR 2 (`orden`, `nota_min`, `nota_max`; «Below 5» es `nota_max=4`), encabezado «From the community (N)» o «Showing X of N» con números formateados por idioma, «Load more reviews» sobre el cursor (solo se reusa la query del `next`, nunca su origen), vacío y vacío filtrado.
  3. **Avatares**: `/api/avatars/` pide sesión, así que sin sesión cada reseña muestra la inicial del usuario; con sesión, el avatar del catálogo que ya carga `AccountProvider`.
  4. «today» se calcula armando la fecha AAAA-MM-DD a mano y no con `toLocaleDateString`: los formatos viven solo en `lib/format.ts` (AGENTS.md §10).
  5. **«Read more» solo si el texto se corta** (pedido del usuario el 14/10/2026: una sinopsis que entra entera no debe ofrecerlo). `useDesborde()` (`lib/use-desborde.ts`) mide el texto recortado (`scrollHeight` contra `clientHeight`) y vuelve a medir con un `ResizeObserver`; reemplaza las cuentas de caracteres (300 en la sinopsis, 280 en las reseñas, 140 en la vista previa de las confirmaciones), que no sabían del ancho de la pantalla. Verificado con la sinopsis real de Breaking Bad: entra en escritorio (sin botón) y se corta en celular (con botón).
- **Cierre de C-07**: entregas #73 a #78. Según AGENTS.md §9 se elimina `openspec/changes/title-page/`; la spec canónica nueva es `title-page-ui` (y se actualizaron `reviews-api` y `tmdb-endpoints`). Queda pendiente actualizar con Marcos la nota «Interfaces» del canvas (Home y Ficha ✅).
- **Tests**: Vitest `reviews-section.test.tsx` (7, incluido «Read more» con y sin desborde) y Playwright `e2e/ficha.spec.ts` (6, escritorio y celular, API simulada con memoria y datos reales de TMDB): sin sesión, calificar con reseña y borrar el texto, quitar de Vistas algo calificado, ordenar y filtrar la comunidad, crear una lista nueva, sin desborde horizontal.
- **Archivos afectados**: `frontend/components/features/title/{ReviewsSection,TitleView}.tsx`, tests y e2e, `openspec/specs/title-page-ui/spec.md`, `docs/05_Plan_de_Desarrollo.md` (C-07, C-08, L-04 y la tabla de interfaces), `docs/decisiones.md`; se elimina `openspec/changes/title-page/`.

## 14/10/2026 — Ajustes de la ficha: toggles, miga de pan y carga (C-07)

- **Fecha**: 14/10/2026
- **Descripción**: tres pedidos del usuario después de probar la ficha.
  1. **Toggles de listas más evidentes.** Activos, Favorite, Watched y Watchlist rellenan el ícono con el color de acento, como la estrella de la nota propia. Antes solo se rellenaba el corazón y el ojo de Watched no cambiaba. En el ojo, la pupila toma el color del botón; en el reloj, las agujas. El doc 04 (§5c, «Acciones directas — comportamiento») ya pedía «relleno sólido» para los tres; el canvas solo lo hacía con el corazón.
  2. **Miga de pan arriba a la izquierda.** En escritorio estaba en la columna del título, encima de la imagen de fondo, y en fondos claros o cargados (Breaking Bad) casi no se leía. Pasa a la esquina superior izquierda, debajo de la barra y alineada con el póster, sobre la misma píldora con velo del enlace «‹ Home» del celular. Así cumple el doc 04 («top-left del content area»).
  3. **Estado de carga completo.** Mientras llega el detalle, la página muestra el esqueleto del fondo, el póster, el título, los datos, los cinco botones, los géneros, la sinopsis y tres reseñas (doc 04, «Estados»), con `aria-busy` en el `main`. Corrige además un error: con sesión, si las listas llegaban antes que el detalle, aparecía «Log in to rate or save».
- **Medición de la primera visita**: la API tarda entre 1 y 1,6 s en una producción que no está en la base, contra 0,015 s después. La llamada a TMDB sola tarda ~0,5 s. El resto es la materialización síncrona (detalle canónico, créditos, keywords, traducción y escritura), que corre antes de responder. El usuario aprobó sacarla del pedido y pasarla a Celery; va en un PR aparte (backend).
- **Tests**: Vitest `title-view.test.tsx` suma «mientras carga el detalle muestra el esqueleto y no invita a ingresar» (falla con la versión anterior). Playwright `e2e/ficha.spec.ts` sin cambios. Capturas revisadas en escritorio y celular.
- **Archivos afectados**: `frontend/components/features/title/{TitleActions,TitleView,ReviewsSection}.tsx`, `frontend/tests/title-view.test.tsx`, `docs/04_Lineamientos_UI.md` (§5c), `openspec/specs/title-page-ui/spec.md`, `docs/decisiones.md`.

## 14/10/2026 — La ficha materializa en segundo plano (C-04a)

- **Fecha**: 14/10/2026
- **Descripción**: las vistas de detalle (`/api/catalogo/movie/<id>/`, `tv/<id>/`) dejan de enriquecer la producción dentro del pedido. Llaman a `materializar_en_segundo_plano()`, que encola la tarea de Celery `catalogo.materializar_produccion` solo si la fila no existe o le falta el detalle. Si la fila está completa no encola nada, con el mismo criterio de no llenar la cola que ya usa `_encolar_embedding`. La tarea llama a `materializar()` y nunca lanza: si falla, registra el error y la próxima visita la vuelve a encolar. Aprobado por el usuario después de medir la primera visita.
- **Motivo**: la primera visita a una producción que no estaba en la base tardaba entre 1 y 1,6 s en responder. ~0,5 s eran la llamada a TMDB de la vista y el resto, el enriquecimiento (detalle canónico, créditos, keywords, traducción y escritura). Después del cambio, la primera visita responde en 0,2-0,8 s (solo TMDB) y el worker materializa en ~1,3-1,5 s sin que nadie espere. Las visitas siguientes siguen en ~0,015 s y no encolan nada.
- **Qué no cambia**: calificar y agregar a una lista materializan por su cuenta antes de escribir (`reviews.py`, `listas/views.py`), así que no dependen de que la tarea haya terminado. Si el usuario califica mientras corre la tarea, las dos materializaciones son idempotentes y la carrera la resuelve `_obtener_o_crear`. El contrato de C-03 (passthrough de TMDB aunque falle algo de nuestro lado) ahora también cubre un broker caído.
- **Alternativas descartadas**: encolar en cada visita (cola llena de trabajo repetido) y dejarlo síncrono con solo un esqueleto de carga (la espera seguía).
- **Tests**: `VistasDeDetalleMaterializanTests` reescrita (primera visita encola sin escribir, series con su tipo, fila completa no encola, fila sin enriquecer se reencola, fallo del broker no rompe la respuesta) y `MaterializarProduccionTareaTests` nueva (materializa y encola el embedding; un fallo se registra y no se propaga). Suite completa: 740 tests en verde. Verificado contra Docker: el worker recibe y completa las tareas, y las visitas a filas completas no encolan.
- **Archivos afectados**: `backend/catalogo/{tasks,views}.py`, `backend/catalogo/services/materialization.py`, tests de `catalogo`, `openspec/specs/catalog-materialization/spec.md`, `docs/05_Plan_de_Desarrollo.md` (C-04a), `docker-compose.yml` (comentario del worker), `docs/decisiones.md`.

## 14/10/2026 — Entrar a Vistas saca de Pendientes

- **Fecha**: 14/10/2026
- **Descripción**: cuando una producción entra a «Vistas» de un usuario, sale de sus «Pendientes» en la misma transacción. Lo que ya viste dejó de estar pendiente. Lo propuso el usuario y eligió la variante entre cuatro: «Watched y calificar», «solo el botón Watched», «prohibir las dos a la vez» y «dejarlo como está».
  1. **Rige por los dos caminos de entrada.** El botón Watched (`POST /api/lists/{vistas}/items/`) y calificar (`POST /api/reviews/`, que ya agrega a Vistas por la regla del 30/09/2026). Los dos pasan por `listas/services.py` (`quitar_de_pendientes`), así el módulo de listas sigue siendo el único que escribe en `Tiene`.
  2. **Solo en el momento en que entra.** Si ya estaba en Vistas no se toca Pendientes. Así volver a agregarla a Pendientes para verla de nuevo sigue permitido, y calificarla después no la saca.
  3. **Quitar de Vistas no la devuelve a Pendientes.** No se guarda dónde estaba antes, y adivinarlo confunde.
  4. **No se repara lo existente.** Las producciones que hoy están en las dos listas se quedan así, porque pueden ser un «quiero volver a verla» legítimo.
  5. **Ficha:** un solo toast, «Added to Watched and removed from Watchlist», y el modal de calificar avisa que también sale de Watchlist.
- **Alternativas descartadas**: prohibir estar en las dos listas (un 409 al agregar a Pendientes algo visto) haría perder el «volver a verla»; limitar la regla al botón Watched dejaría algo calificado como visto y pendiente a la vez.
- **Tests**: backend `VistasSacaDePendientesTests` (7, por HTTP con la materialización real y TMDB simulado; 3 fallan con el código anterior y 4 cuidan los límites de la regla). Frontend: dos tests en `title-actions.test.tsx` y uno en `rating-dialog.test.tsx`; los dos de la regla fallan con los componentes anteriores.
- **Archivos afectados**: `backend/listas/{services,views}.py`, `backend/catalogo/tests_reviews.py`, `frontend/components/features/title/{TitleActions,RatingDialog,TitleView}.tsx`, tests, `docs/i18n/copia-propuesta.csv` y mensajes generados, `docs/02_Especificación de Requerimientos.md` (CU-011), `docs/04_Lineamientos_UI.md` (§5c), specs `list-endpoints`, `reviews-api` y `title-page-ui`, `docs/decisiones.md`.

## 14/10/2026 — SDD de Buscar (C-06, PR 1)

- **Fecha**: 14/10/2026
- **Descripción**: SDD en `openspec/changes/search-catalogo/` (proposal, design, tasks).
  1. **Página, no overlay.** `/search`, como lo dibuja el canvas (navbar con «Search» como página actual). Se actualizaron doc 04 §5b y sus menciones al overlay.
  2. **Texto con género o nota sobre los primeros 100.** Verificado contra TMDB: `search/movie` y `search/tv` ignoran género y nota («dune» con `with_genres=878&vote_average.gte=9` sigue dando 1115 resultados). Con texto y alguno de esos filtros, el backend toma hasta 5 páginas por tipo (la primera y después el resto en paralelo, cada una cacheada 1 h), filtra y pagina de a 20. Sin esos filtros, una llamada por tipo. Lo eligió el usuario entre tres opciones: «filtrar los primeros 100», «con texto, solo año» y «filtrar solo la página actual».
  3. **Cualquier texto hasta 50.** Doc 02 decía alfanumérico sin signos; títulos como «Ocean's Eleven», «WALL·E» o «¿Qué pasó ayer?» los necesitan. Lo eligió el usuario.
  4. **«All» alterna películas y series**, página N de cada una, como el Home. Se descartó `search/multi`: en la página 1 de «dune» trae 9 personas de 20 y su total las cuenta.
  5. **Año con texto**: `primary_release_year` y `first_air_date_year`, que son estrictos. `year` es flojo: «dune» con 2021 trae la de 1984.
  6. **Géneros en «All»**: equivalencias de película a serie (Acción y Aventura → 10759, Ciencia ficción y Fantasía → 10765, Bélica → 10768), verificadas con las listas de TMDB. `genres/?tipo=all` suma los cinco géneros solo de series sin par (Kids, News, Reality, Soap, Talk).
  7. **Nota con al menos 50 votos**: sin ese mínimo, «Below 5» se llena de títulos sin votos. Es el mismo umbral que usa el Home para series.
  8. **Sin botón «Buscar»**: la búsqueda arranca 350 ms después de dejar de escribir (canvas). Se actualizó CU-010 en doc 02.
- **Fuera de alcance**: materializar lo que muestra la búsqueda (pendiente de C-04a para listados) y el bloque «Dónde verla» de la ficha (propuesto el 14/10/2026, se decide después de C-06).
- **Archivos afectados**: `openspec/changes/search-catalogo/`, `docs/02_Especificación de Requerimientos.md` (CU-008, CU-010), `docs/04_Lineamientos_UI.md` (§5b y menciones al overlay), `docs/decisiones.md`.

## 14/10/2026 — API de Buscar (C-06, PR 2)

- **Fecha**: 14/10/2026
- **Descripción**: `GET /api/catalogo/browse/` (`catalogo/services/browse.py`, `BrowseView`) y `genres/?tipo=all`, según el SDD.
  1. **Cliente y caché.** `search(..., anio=)` manda `primary_release_year` o `first_air_date_year`. `discover` suma `max_rating` (`vote_average.lte`) y `sin_generos` (`without_genres`). Los tres entran a la clave de caché solo cuando se usan, así lo que ya estaba en Redis conserva su clave (mismo patrón que `min_votos`, C-05).
  2. **Ventana en paralelo.** La página 1 primero y el resto con `ThreadPoolExecutor`; en «All», los dos tipos a la vez. `httpx.Client` y el cliente de Redis se pueden compartir entre hilos (verificado en httpx 0.28.1) y la ventana no toca la base. Si una página falla, falla la respuesta (502): un conteo parcial pasaría por real.
  3. **Grilla por defecto (hallazgo contra TMDB real).** Sin texto, `discover/tv` por popularidad arrancaba con programas diarios (Barbara Karlich - Talk, Watch What Happens Live, The Tonight Show). Sin texto, `discover` pide siempre al menos 50 votos, y en series excluye News (10763) y Talk (10767) salvo que se elija un género. Con eso arranca con Law & Order: SVU, Reacher, The Office. En películas, el mínimo no cambia los primeros puestos.
  4. **Medido contra TMDB real (Docker).** Sin texto, 1,2 s en frío. Con texto, ~0,45 s. Con texto y filtro en «All», la peor ventana en frío (batman, Acción) tardó 2,2 s: dos rondas en paralelo más, en español, el respaldo en inglés de cada página. La misma búsqueda con otro género sale de caché en 0,017 s. Se acepta, porque pasa solo la primera vez que alguien combina ese texto con un filtro en una hora.
  5. **Géneros sin traducir.** TMDB devuelve en inglés, también en `es-MX`, los cinco géneros solo de series (Kids, News, Reality, Soap, Talk). El frontend les pone nombre desde la copia de i18n (PR 3).
- **Tests**: `catalogo/tests_browse.py` (28) sobre páginas reales de TMDB del 14/10/2026 (`catalogo/test_datos/tmdb_buscar.json`: «dune» en películas y series, «the office» en series, `discover` y géneros), más 4 de cliente y caché en `tests.py`. Todos fallaban antes del cambio.
- **Archivos afectados**: `backend/catalogo/{client,cache,views,urls}.py`, `backend/catalogo/services/browse.py`, `backend/catalogo/tests_browse.py`, `backend/catalogo/test_datos/tmdb_buscar.json`, `backend/catalogo/tests.py`, `openspec/specs/tmdb-endpoints/spec.md`, `openspec/changes/search-catalogo/{design,tasks}.md`, `docs/decisiones.md`.

## 14/10/2026 — Página de Buscar (C-06, PR 3)

- **Fecha**: 14/10/2026
- **Descripción**: `/search` (`components/features/SearchView.tsx`, `lib/search.ts`) según el canvas «Search · desktop».
  1. **La búsqueda vive en la URL** (`q`, `type`, `genre`, `year`, `rating`, `page`, en inglés como el `?type=` del Home). Se cambia con `history.replaceState`: no vuelve a pedir la página al servidor, y «Atrás» sale de Buscar. La nota se escribe `9`…`5` y `lt5`, y `lib/search.ts` la traduce a `9+` y `m5` de la API.
  2. **Escribir espera 350 ms**; Enter busca enseguida. Cualquier cambio vuelve a la página 1.
  3. **Cerrar / Escape** usa `performance.getEntriesByType("navigation")`: si el documento se cargó en otra página, se llegó navegando dentro de la app y se vuelve atrás; si se abrió directo en `/search`, va al Inicio. Con un `<dialog>` abierto, Escape es de él.
  4. **Cambiar el tipo** conserva el género solo si es uno de los 8 con el mismo id en películas y series; los demás se descartan, porque en el otro tipo no existen.
  5. **Géneros sin traducir**: los cinco solo de series que TMDB devuelve en inglés también en `es-MX` (Kids, News, Reality, Soap, Talk) toman el nombre de la copia (`search.genres.*`: Infantil, Noticias, Reality, Telenovelas, Entrevistas).
  6. **`MediaCard`** suma `fluid`, para ocupar su columna de la grilla, y `showUnrated`, para el «No ratings» del canvas. El Home no cambia.
  7. **Vacío**: «Nada para “texto”» (o «Nada con estos filtros») con «Limpiar filtros»; si no hay filtros activos, el botón dice «Borrar búsqueda».
- **Tests**: Vitest `search.test.ts` (9, URL ⇄ estado ⇄ API) y `search-view.test.tsx` (11: pedido inicial, contador y tarjetas, espera de 350 ms, Enter, filtros y géneros traducidos, cambio de tipo, paginación, vacío, error y Reintentar, Escape, tope de 50). Se suma el e2e de la ficha «marcar Watched algo que está en Watchlist lo saca de Watchlist» (regla del PR #81). Capturas con datos reales de TMDB en escritorio y celular, sin desborde horizontal.
- **Archivos afectados**: `frontend/app/search/page.tsx`, `frontend/components/features/{SearchView,MediaCard}.tsx`, `frontend/lib/search.ts`, tests y e2e, `docs/i18n/copia-propuesta.csv` y mensajes generados, `openspec/changes/search-catalogo/tasks.md`, `docs/05_Plan_de_Desarrollo.md`, `docs/decisiones.md`.

## 14/10/2026 — Buscar en celular, vuelta desde la ficha y cierre de C-06 (PR 4)

- **Fecha**: 14/10/2026
- **Descripción**: hoja de filtros del celular y vuelta a la última búsqueda, según el canvas «Search · mobile» y el doc 04 §5b.
  1. **`FiltersSheet`** sobre `DialogShell` (la hoja de la ficha): Género y Año, la calificación de TMDB como botones (Cualquiera, 9+ … 5+, <5, cada uno con su nombre largo como nombre accesible), «Limpiar» y «Ver resultados». Cada cambio se aplica al momento, con los resultados detrás. El botón «Filtros» muestra la cantidad de filtros activos y la anuncia en su nombre accesible. En celular se esconden los selects de escritorio.
  2. **`TypeSelector compact`**: en celular comparte la fila con «Filtros». Sin relleno lateral y con letra de 14 px, como el canvas, «Películas» y «Series» no se tocan. El Home no cambia.
  3. **Vuelta desde la ficha**: Buscar guarda su URL en `sessionStorage` (`filmai:ultima-busqueda`) y la miga «Buscar» de la ficha la lee en un efecto, no al renderizar, para que coincida con el HTML del servidor. Solo acepta rutas de Buscar; sin almacenamiento, `/search`.
  4. **Recorrido de navegación de Marcos** (`e2e/errores-menu.spec.ts`): esperaba el 404 de `/search` («hasta que exista»). Se ajustó en el PR 3 para esperar el buscador.
- **Hallazgo del e2e**: en desarrollo, `getByRole("button", { name: "Next" })` también matchea «Open Next.js Dev Tools» (la comparación es por subcadena); el clic iba a ese botón. Se usa `exact: true`.
- **Cierre de C-06**: PRs #82 a #85. Según AGENTS.md §9 se elimina `openspec/changes/search-catalogo/`; la spec canónica nueva es `search-ui`, y se actualizó `tmdb-endpoints` en el PR 2.
- **Tests**: Vitest suma 3 de `lib/search` (última búsqueda, incluido sin `sessionStorage`), 3 de `SearchView` (guarda la búsqueda, hoja con el badge y los filtros, Escape con la hoja abierta) y 1 de `TitleView` (la miga vuelve a la búsqueda). Playwright `e2e/buscar.spec.ts` (4): texto y tarjetas en escritorio y celular, filtros y página hacia la API, hoja de filtros; sin desborde horizontal.
- **Archivos afectados**: `frontend/components/features/{FiltersSheet,SearchView,TypeSelector}.tsx`, `frontend/components/features/title/TitleView.tsx`, `frontend/lib/search.ts`, tests y e2e, copia de i18n y mensajes generados, `openspec/specs/search-ui/spec.md`, `docs/05_Plan_de_Desarrollo.md`, `docs/decisiones.md`; se elimina `openspec/changes/search-catalogo/`.

## 14/10/2026 — Buscar encuentra lo anunciado

- **Fecha**: 14/10/2026
- **Descripción**: pedido del usuario: poder buscar producciones anunciadas en TMDB que no salen este año.
  1. **El selector de año** va de cinco años adelante a 1900 (`ANIOS_ANUNCIADOS` en `lib/search.ts`). TMDB ya tiene producciones con fecha hasta 2031 (Avatar 5).
  2. **Sin mínimo de votos para un año futuro.** La grilla sin texto pide al menos 50 votos para que no la llenen títulos sin votos, pero lo que no se estrenó no tiene votos: 2027 tiene 946 películas en TMDB y ninguna con 50 (verificado). Con un año futuro y sin filtro de nota, `discover` va sin mínimo. Con nota, el mínimo se mantiene, porque una nota sin votos no dice nada. El año actual sale de `timezone.localdate()` (zona de Argentina).
- **Verificado contra TMDB real**: 2028 trae 135 títulos (The Batman: Part II, Fast Forever…).
- **Tests**: 3 en `tests_browse.py` (año futuro sin mínimo, año actual con mínimo, año futuro con nota conserva el mínimo; los tres fallaban antes) y el de `aniosDisponibles` actualizado.
- **Archivos afectados**: `backend/catalogo/services/browse.py`, `backend/catalogo/tests_browse.py`, `frontend/lib/search.ts`, `frontend/tests/search.test.ts`, doc 04 §5b, specs `search-ui` y `tmdb-endpoints`, `docs/decisiones.md`.

## 14/10/2026 — Buscar carga al bajar

- **Fecha**: 14/10/2026
- **Descripción**: idea del usuario: paginar a demanda, cargando más resultados al bajar. Eligió «automático al bajar» entre tres opciones: automático, un botón «Cargar más» y dejar la paginación clásica del canvas.
  1. **`useCatalogPaginas`** (`lib/use-catalog.ts`): pide varias páginas de una consulta y comparte la caché con `useCatalog`. Devuelve las páginas en orden hasta la primera que falta, `cargandoMas` y el error, que solo se reintenta con otro `intento`.
  2. **Un centinela con `IntersectionObserver`**: cuando el final de la grilla está a 600 px, `page` en la URL pasa a N+1 y se agrega esa página. `page` ahora significa cuántas páginas se cargaron, con un tope de 25: también acota lo que dispara un link con `page` alto. Con pocos resultados la grilla no llena la pantalla y la página siguiente se pide sola.
  3. **Sin repetidos**: `normalizeTitles` descarta un título que llega en dos páginas, si la popularidad cambió entre pedidos.
  4. **Error en una página siguiente**: lo cargado queda y aparece Reintentar al pie.
  5. **Volver desde la ficha** (hallazgo probando contra Docker): las páginas vuelven de la caché, pero el scroll quedaba en 0, porque la URL cambia con `history.replaceState` y Next no restaura ese scroll. Ahora, al hacer clic en una tarjeta se guardan la URL y `scrollY` en `sessionStorage`. Al volver a la misma URL con todas las páginas cargadas, se restaura un cuadro después. Verificado con «Atrás» y con la miga: 4240 px antes y después.
  6. **Carrera cazada por el CI**: con pocos resultados, el aviso «llegó al final» del observador llegaba después de elegir un filtro y avanzaba con la búsqueda vieja que recordaba su closure, borrando el filtro (`?genre=878&page=2` sin `rating`). El callback ahora compara la URL actual normalizada con la búsqueda de su render y, si cambió, no hace nada; el observador nuevo, creado con la búsqueda actual, sigue cargando.
- **Tests**: `use-catalog-paginas.test.tsx` (3: orden aunque lleguen desordenadas, caché compartida, error y reintento). `search-view.test.tsx` reemplaza el de paginación por 5 (pide al acercarse el final, un aviso tardío no pisa un filtro nuevo, junta dos páginas sin repetidos y no pide más en la última, error en la página 2, restaura el scroll), con `IntersectionObserver` simulado porque jsdom no lo tiene. `search.test.ts` suma 2 del scroll guardado. El e2e baja hasta el final y espera `page=2`.
- **Archivos afectados**: `frontend/lib/{use-catalog,search}.ts`, `frontend/components/features/SearchView.tsx`, tests y e2e, doc 04 §5b, spec `search-ui`, `docs/decisiones.md`.

## 14/10/2026 — «A estrenar» en vez de años futuros

- **Fecha**: 14/10/2026
- **Descripción**: el usuario prefirió una sola opción «A estrenar» (en inglés «Upcoming») en el selector de año, en lugar de listar años futuros hasta 2031. Reemplaza el punto 1 de «Buscar encuentra lo anunciado»: el selector vuelve a ir del año actual a 1900.
  1. **API**: `browse/?a_estrenar=true`, que reemplaza a `anio`. Sin texto, `discover` filtra desde mañana con el parámetro de fecha de cada tipo (`primary_release_date.gte` / `first_air_date.gte`; `discover(desde_fecha=)` en el cliente, con clave de caché solo si se usa) y sin mínimo de votos, salvo que haya nota. Con texto va a la ventana de los primeros 100, porque la búsqueda por nombre de TMDB tampoco filtra por fecha, y deja lo que tiene fecha posterior a hoy; lo que no tiene fecha queda afuera. La fecha sale de `hoy()` (`timezone.localdate()`, zona de Argentina).
  2. **Frontend**: en la URL va como `year=upcoming`. `anioDesdeOpcion` y `opcionDeAnio` (`lib/search.ts`) traducen entre el selector y el estado, y `consultaApi` manda `a_estrenar=true`. Cuenta como filtro activo en el badge del celular.
  3. Se conserva la regla de «año futuro sin mínimo de votos» para quien pida un año futuro por la API.
  4. **Tarjetas**: la línea de datos de `MediaCard` pasa a `flex-wrap` (como el canvas). Con «Sin calificaciones», el texto se partía en dos columnas apretadas; ahora baja entero al renglón siguiente cuando no entra.
- **Verificado contra TMDB real**: 4118 títulos a estrenar (Avengers: Doomsday, Neuromante, The Mongoose…), 458 series; «avatar» con «A estrenar» trae Avatar 4 y Avatar 5.
- **Tests**: backend, 4 en `tests_browse.py` (desde mañana sin mínimo, con nota conserva el mínimo, ventana por fecha con los dos títulos reales de «dune» posteriores al 14/10/2026, valor inválido) y 1 de cliente y caché. Frontend, 2 en `search.test.ts` y 1 en `search-view.test.tsx`. Todos fallaban antes del cambio.
- **Archivos afectados**: `backend/catalogo/{client,cache,views}.py`, `backend/catalogo/services/browse.py`, tests de `catalogo`, `frontend/lib/search.ts`, `frontend/components/features/{SearchView,FiltersSheet}.tsx`, tests, copia de i18n y mensajes, doc 04 §5b, specs `search-ui` y `tmdb-endpoints`, `docs/decisiones.md`.

## 14/10/2026 — Décadas antes de 1990 en el año de Buscar

- **Fecha**: 14/10/2026
- **Descripción**: el selector de año tenía 127 opciones, del año actual a 1900. El usuario eligió entre cuatro variantes: años sueltos del actual a 1990 y, antes, décadas hasta la de 1900. Las otras eran solo décadas, años desde 2000 con décadas antes, y dejarlo como estaba. Quedan 46 opciones más «Cualquiera» y «A estrenar».
  1. **Etiqueta**: «Década de 1980» en español, «1980s» en inglés (`search.filters.decade`). Un formato corto como «Años 10» sería ambiguo entre 1910 y 2010.
  2. **API**: `browse/?decada=1980` reemplaza a `anio`. Sin texto, `discover` va del 1/1/1980 al 31/12/1989 (`discover(desde_fecha=, hasta_fecha=)`), con el mínimo de 50 votos. Con texto va a la ventana, filtrada por ese rango. Una década fuera de 1900…la actual, o que no termina en 0, da 400 `invalid_choice` (con `allowedValues` como textos, que es lo que pide el contrato de errores).
  3. **`explorar()`** resuelve el período a un rango `desde`/`hasta` («A estrenar»: desde mañana; década: su rango) y a una sola regla `sin_minimo` (lo futuro sin nota). `_lado` y la ventana ya no saben de dónde vino el rango.
  4. **URL**: `year=1980s`. `anioDesdeOpcion` ignora lo que no es una década válida.
- **Verificado contra TMDB real (con ≥50 votos)**: 1980s, 2561 películas (Terminator, Los cazadores del arca perdida, Volver al futuro); 1950s, 943 (12 Angry Men, Vertigo); 1920s, 187 (Nosferatu); 1900s, 48 (Viaje a la Luna).
- **Tests**: backend, 3 en `tests_browse.py` (década sin texto con rango y mínimo, ventana con las 9 películas reales de «dune» de los 80, décadas inválidas) y 1 de cliente y caché. Frontend, 2 en `search.test.ts` y el test del selector, que ahora verifica que la última opción es «Década de 1900».
- **Archivos afectados**: `backend/catalogo/{client,cache,views}.py`, `backend/catalogo/services/browse.py`, tests de `catalogo`, `frontend/lib/search.ts`, `frontend/components/features/{SearchView,FiltersSheet}.tsx`, tests, copia de i18n y mensajes, doc 04 §5b, specs `search-ui` y `tmdb-endpoints`, `docs/decisiones.md`.

## 14/10/2026 — Buscar con texto ordena por votos y popularidad

- **Fecha**: 14/10/2026
- **Descripción**: el usuario notó resultados «medio randoms o desconocidos» arriba al buscar por nombre. TMDB ordena su búsqueda por relevancia: en «the office» ponía tres películas con 0 votos antes que la serie con 5579. El usuario eligió ordenar por votos, pero pidió que los estrenos esperados no se hundieran (no tienen votos). Solución: ordenar por el **mayor entre los votos y la popularidad de TMDB × 100** (`PESO_POPULARIDAD`).
  1. **Por qué mixta.** Comparado con datos reales: los votos solos hunden Avengers: Doomsday (0 votos). La popularidad sola es ruidosa, porque mide lo de esta semana: «it» empezaba con It's Always Sunny y una serie de 3 votos. Con la mixta, en «avengers» quedan los clásicos y Doomsday 5.º; en «avatar», Avatar 1.º y Avatar: Seven Havens (a estrenar) 2.º; en «it», It 1.º. «Coincidencia exacta del título primero» se descartó, porque subía «Batman (1 voto)» y «Matrix (0)».
  2. **Con texto siempre la ventana.** Para ordenar de verdad hay que tener los primeros 100 de cada tipo, no una página de 20. Ya no hay «una llamada cuando no hay filtros». La primera búsqueda tarda un poco más y después sale de la caché (1 h por página). La carga al bajar con texto termina en 100 por tipo.
  3. **«Todo» con texto** mezcla películas y series por ese puntaje, de a 40 por página. Sin texto sigue alternando, como el Home.
  4. Los empates conservan el orden de relevancia de TMDB (`sorted` es estable).
- **Tests**: `tests_browse.py` reescribe los de texto: siempre 5 páginas con el año, total y páginas de la ventana, «Dune: Part Three» (0 votos, popularidad 32) 5.ª de 100 con el orden exacto de los primeros 5, «Todo» mezclado en orden y de a 40. A la captura `tmdb_buscar.json` se le sumó la popularidad real de cada título, por id, sin cambiar lo demás.
- **Verificado contra TMDB real**: «the office» → The Office (5579 votos) primero; «it» → It; «avengers» → los cuatro clásicos y Doomsday 5.º.
- **Archivos afectados**: `backend/catalogo/services/browse.py`, `backend/catalogo/tests_browse.py`, `backend/catalogo/test_datos/tmdb_buscar.json`, doc 04 §5b, spec `tmdb-endpoints`, `docs/decisiones.md`.

## 15/10/2026 — SDD de Perfil, Settings y Mis reseñas según el canvas

- **Fecha**: 15/10/2026
- **Descripción**: SDD en `openspec/changes/perfil-canvas/` para rehacer `/profile`, `/settings` y `/my-reviews` según el canvas (secciones 9 y 6), más la miga de Términos en escritorio. Estas pantallas eran de Marcos en el reparto del 13/10/2026. El 15/10 las tomó Gonza, porque Marcos no las había empezado (sin ramas ni PRs; lo último suyo, del 12/10, fueron acceso y Términos en celular).
  1. **Errores encontrados al revisarlas**: Perfil y Mis reseñas mezclan idiomas, porque parte del texto está escrito a mano (AGENTS.md §10); Mis reseñas deja dos tarjetas de carga para siempre, no tiene miga, filtros ni links a la ficha, y usa el modal viejo de calificar.
  2. **Solo tema oscuro por ahora** (decisión del usuario). El tema claro está roto en toda la app: solo cambian el fondo y el acento, porque los tokens propios (superficies, líneas, textos, velos) existen solo para oscuro. Settings deja de ofrecer el selector y `AccountProvider` aplica oscuro aunque la cuenta tenga «claro» guardado. La preferencia `tema` sigue en la API para cuando se haga la paleta clara del canvas.
  3. **Se mantiene «Perfil público»** aunque el canvas no lo tiene (decisión del usuario): el día de mañana puede servir para que cada uno decida si sus calificaciones y reseñas son públicas. Como hoy las reseñas de la comunidad ya son públicas en la ficha, conserva el aviso de que se guarda pero todavía no cambia nada.
  4. **Filtros de Mis reseñas en el backend** (`reviews/mias/`: `q`, `texto`, `clase`, `nota_min`/`nota_max`, `orden`, con `total` y `total_propias`). Con paginación por cursor no se puede filtrar del lado del cliente. El tipo va como `clase`, porque `id_tmdb` + `tipo` ya cambian la respuesta a «la calificación de una ficha».
- **Entrega**: cinco PRs (SDD, backend, Settings, Perfil, Mis reseñas).
- **Archivos afectados**: `openspec/changes/perfil-canvas/`, `docs/05_Plan_de_Desarrollo.md`, `docs/decisiones.md`.

## 15/10/2026 — Filtros de «Mis reseñas» en el backend (perfil según el canvas, PR 2)

- **Fecha**: 15/10/2026
- **Descripción**: `GET /api/reviews/mias/` acepta `q`, `texto` (`con`/`sin`), `clase` (`movie`/`tv`), `nota_min`/`nota_max` y `orden`, validados con `MisResenasQuerySerializer`, y devuelve `total` (con filtros) y `total_propias` (sin filtros) para «Ver N resultados» y para distinguir «no calificaste nada» de «nada con estos filtros».
  1. **Búsqueda sin acentos**: se activa la extensión `unaccent` de Postgres (migración `catalogo.0007_unaccent`) y `django.contrib.postgres` en `INSTALLED_APPS`, para usar `titulo__unaccent__icontains`. Filtrar en Python no sirve con paginación por cursor. Busca en el título canónico y en las traducciones; para las traducciones usa `Exists`, porque un JOIN repetiría la calificación si hubiera varias.
  2. **`clase` y no `tipo`**: en esta ruta, `id_tmdb` + `tipo` ya devuelven la calificación de una ficha, y medio par sigue siendo 400 (lo cuida un test).
  3. **Orden por nota con cursor estable**: la misma clave única que la comunidad de la ficha (C-07), sobre la calificación: `valor × 10⁹ + id`.
- **Tests**: `catalogo/tests_mis_resenas_filtros.py` (11): sin filtros con los dos totales, búsqueda con mayúsculas y acentos, título traducido, con y sin reseña, clase, nota, orden por nota y fecha, cursor estable con 25 empates, filtros combinados, valores inválidos y `tipo` solo. Diez fallaban antes; el de `tipo` solo protege lo que ya andaba.
- **Para el entorno local**: la migración nueva se aplica con `docker compose exec backend python manage.py migrate`.
- **Archivos afectados**: `backend/catalogo/{reviews,serializers_reviews,pagination_reviews}.py`, `backend/catalogo/migrations/0007_unaccent.py`, `backend/filmai/settings.py`, `backend/catalogo/tests_mis_resenas_filtros.py`, spec `reviews-api`, `openspec/changes/perfil-canvas/tasks.md`, `docs/decisiones.md`.

## 15/10/2026 — Settings según el canvas (perfil, PR 3)

- **Fecha**: 15/10/2026
- **Descripción**: `/settings` rehecho según «Settings · desktop / mobile», más la miga de Términos en escritorio.
  1. **Estructura del canvas**: miga Profile › Settings (en celular, «‹ Profile»); Language («Interface language» con EN | ES); Privacy; Notifications; Legal → Términos; Account con «Deactivate account». Títulos en la tipografía de cartel y filas separadas por líneas, como el canvas.
  2. **Interruptores**: componente nuevo `components/ui/switch.tsx`, un `button` con `role="switch"` y `aria-checked`, nombrado por la etiqueta de su fila (`aria-labelledby`). Reemplaza las casillas de verificación.
  3. **Solo oscuro**: no hay selector de tema, y `AccountProvider` aplica siempre `dark` (antes una cuenta con «claro» guardado veía la app rota).
  4. **Textos honestos**: las notificaciones conservan «Preferencia para futuros correos» en lugar del texto del canvas («Every week we email you…»), porque hoy no se manda ningún correo. «Perfil público» conserva el aviso de que todavía no cambia nada.
  5. **Baja**: usa `ConfirmDialog` de la ficha (`alertdialog`, foco en Cancelar, el error queda a la vista) con el texto aprobado en este registro, que es más largo que el del canvas.
  6. **Ancla del idioma**: el título de Language conserva el id fijo `t-idioma`, porque el footer con sesión lleva a `/settings#t-idioma` (`routes.language`); lo cazó el e2e de i18n.
  7. **Términos**: `TermsBackLink` decide los dos lugares según la sesión. En celular, el enlace de siempre. En escritorio, con sesión la miga Profile › Settings › Terms, y sin sesión «Back to the landing page».
- **Tests**: `switch.test.tsx` (2), `terms-back-link.test.tsx` reescrito para los dos enlaces (jsdom no aplica CSS), la baja en `profile.test.tsx` con `alertdialog`. `e2e/preferencias.spec.ts` reescrito: un «claro» guardado no saca el `dark` y no hay selector; el interruptor guarda y se anuncia; la baja con su texto aprobado. El e2e de i18n pasa con el ancla.
- **Archivos afectados**: `frontend/app/settings/page.tsx`, `frontend/app/terms/page.tsx`, `frontend/components/{TermsBackLink,AccountProvider}.tsx`, `frontend/components/ui/switch.tsx`, tests y e2e, copia de i18n y mensajes, `openspec/changes/perfil-canvas/tasks.md`, `docs/decisiones.md`.

## 15/10/2026 — Perfil según el canvas (perfil, PR 4)

- **Fecha**: 15/10/2026
- **Descripción**: `/profile` rehecho según «My profile · desktop / mobile». Se conserva la lógica de antes: borrador con aviso de cambios sin guardar, disponibilidad del usuario mientras se escribe, cambio de contraseña y el enlace para crearla en cuentas de Google sin contraseña local.
  1. **Estructura del canvas**: encabezado con avatar, nombre en tipografía de cartel, `@usuario`, correo y fecha de alta; «Datos personales» como `dl` (dos columnas en celular); «Editar perfil» cambia esa sección por el formulario «Editar datos», con correo, fecha de nacimiento y género de solo lectura (candado y aviso); «Contraseña» desplegable (`aria-expanded`).
  2. **Avatar en un diálogo**: `components/features/profile/AvatarDialog.tsx` sobre `DialogShell` de la ficha (tarjeta en escritorio, hoja en celular), con los avatares como `radiogroup` y el foco en el elegido. La elección queda en el borrador y se guarda con «Guardar cambios», como antes. Reemplaza a `AvatarSelector`, que se borra.
  3. **«Tu cuenta» en celular**: en celular la barra no tiene menú de la cuenta, así que el Perfil lista Calificaciones y reseñas, Preferencias, Términos y «Cerrar sesión», que pide confirmación con `ConfirmDialog` (el mismo texto que el menú de escritorio).
  4. **Todo el texto sale del catálogo**: se suman 11 claves aprobadas a `docs/i18n/copia-propuesta.csv` y `app/profile/page.tsx` y `lib/profile-draft.ts` dejan la lista de excepciones de i18n. Se borran `colorDisponibilidad` y `ADVERTENCIA_BAJA` (sin uso desde Settings); el test del catálogo fija el texto de la baja directamente.
- **Tests**: `avatar-dialog.test.tsx` (nuevo, reemplaza a `avatar-selector.test.tsx`), `profile.test.tsx` y `reviews.test.ts` actualizados. `e2e/perfil.spec.ts` y `e2e/hotfix-perfil.spec.ts` adaptados a los nombres nuevos (editar, avatar y guardar).
- **Archivos afectados**: `frontend/app/profile/page.tsx`, `frontend/components/features/profile/AvatarDialog.tsx`, `frontend/components/AvatarSelector.tsx` (borrado), `frontend/lib/profile-draft.ts`, `frontend/scripts/i18n/rules.mjs`, mensajes y copia de i18n, tests y e2e, `openspec/changes/perfil-canvas/tasks.md`, `docs/decisiones.md`.

## 15/10/2026 — Calificaciones y reseñas según el canvas (perfil, PR 5, cierra el cambio)

- **Fecha**: 15/10/2026
- **Descripción**: `/my-reviews` rehecha según «Ratings & reviews · desktop / mobile». Con este PR se cierra `perfil-canvas`.
  1. **Filtros en la URL, con los nombres de Buscar**: `q`, `review=with|without`, `type=movie|tv`, `rating=9…5|lt5` y `sort=newest|oldest|highest|lowest`. El diseño hablaba de `texto`/`clase`/`nota`/`orden`, pero esos son los nombres de la API; en la URL se usan los mismos que en `/search` (`type`, `rating`) para que las dos pantallas se lean igual. `lib/my-reviews.ts` traduce: «Menos de 5» es `nota_max=4` (las notas son enteras) y «N o más», `nota_min=N`. El texto se aplica a los 350 ms, como en Buscar.
  2. **Miga de vuelta con filtros**: la lista guarda su URL en `sessionStorage` y la miga «Calificaciones y reseñas» de la ficha vuelve ahí, como «Buscar» vuelve a la última búsqueda.
  3. **Escritorio y celular**: en escritorio, cuatro selectores y «Limpiar filtros»; «Editar» y un menú «Más acciones» (`role="menu"`, flechas y Escape). En celular, «Filtros y orden» abre una hoja que aplica al momento y cierra con «Ver N resultados», cada filtro activo es un chip que lo quita, y un solo botón por fila abre las tres acciones en una hoja.
  4. **Diálogos de la ficha**: editar usa `RatingDialog` y `planEdicion`; borrar el texto y quitar la calificación, `ConfirmDialog` con los textos y toasts de la ficha. Se borran `MisResenas`, `ReviewCard`, `ReviewModal` y `cambiosResena`.
  5. **Lo editado queda en su lugar** aunque deje de coincidir con los filtros (por ejemplo, borrar el texto con «Con reseña» activo): que la fila desaparezca bajo el foco desorienta. La próxima carga lo acomoda. Quitar la calificación sí saca la fila y lleva el foco al título.
  6. **«Agregar reseña» lleva a la ficha** (como el canvas), con `?from=reviews`. Los títulos también.
  7. **Estados**: `total_propias = 0` muestra «Todavía no calificaste ninguna película ni serie» con un enlace a Buscar y sin filtros; filtros sin resultados ofrecen limpiarlos (conservando el orden). Las «tarjetas de carga eternas» eran tarjetas con `content-visibility: auto` que el navegador no pintaba fuera de pantalla; el diseño nuevo no las usa.
  8. **Título de la pestaña**: «Calificaciones y reseñas», como el `h1` (antes «Mis reseñas»).
- **Copia nueva** (`docs/i18n/copia-propuesta.csv`): estado vacío y su acción, carga, error, «Cargar más calificaciones» y el chip de la nota.
- **Tests**: `my-reviews.test.ts` (URL ⇄ filtros ⇄ API, conteo, miga) y `my-reviews-view.test.tsx` (12: filtros, pausa del texto, vacío, sin coincidencias, chips, hoja, error, editar, borrar texto, quitar con foco, hoja de acciones). `e2e/mis-resenas.spec.ts` reescrito con un backend en memoria que filtra y pagina (6). Se borran los tests de las tarjetas y el modal viejos.
- **Archivos afectados**: `frontend/app/my-reviews/page.tsx`, `frontend/components/features/reviews/`, `frontend/lib/{my-reviews,reviews}.ts`, `frontend/components/features/title/TitleView.tsx`, componentes viejos (borrados), `frontend/scripts/i18n/rules.mjs`, mensajes y copia de i18n, tests y e2e, spec `profile-ui` (reescrita para las tres pantallas), `docs/05_Plan_de_Desarrollo.md`, `openspec/changes/perfil-canvas/` (eliminado), `docs/decisiones.md`.

## 15/10/2026 — API de listas para el canvas: detalle, filtros, nota de TMDB y orden (L-02/L-03, backend)

- **Fecha**: 15/10/2026
- **Descripción**: el backend de listas se ajusta a los artboards «Lists» y «List detail» antes de hacer sus pantallas (las pantallas quedan para después). Decisiones de Marcos en el chat:
  1. **`GET /api/lists/{id}/`**: devuelve el mismo resumen que `GET /api/lists/` para una lista propia, predeterminada o personalizada. Ya lo pedía la ficha para la miga «Lists › {nombre}» con `?from=list-{id}` y recibía 405 (Method Not Allowed), que descartaba sin aviso: la miga quedaba sin el nombre.
  2. **Nota de TMDB en cada ítem**: `calificacion_promedio` en `GET /api/lists/{id}/items/`, la «★ 8.5» de la tarjeta. TMDB manda 0 cuando no hay votos; la API devuelve `null` y la UI muestra «Unrated».
  3. **Filtros y orden en el backend** (la paginación es por cursor: filtrar en el cliente solo vería lo cargado): `q` (título canónico o traducido, sin acentos ni mayúsculas, como «Mis reseñas»), `clase` (`movie`/`tv`), `nota` (los tramos de Buscar `9+`…`5+` y `m5`) y `orden` (`agregado-desc` por defecto, `agregado-asc`, `titulo-asc`, `nota-desc`, `nota-asc`). La respuesta suma `total`, lo que pasa los filtros, para «Showing X of N».
  4. **La nota es la de TMDB, no la del usuario**. Un título sin nota de TMDB no entra en ningún tramo (tampoco en «Below 5») y al ordenar por nota queda al final en los dos sentidos.
  5. **Claves únicas para el cursor**: por nota, nota×1000 (TMDB trae tres decimales) seguida del id del ítem, como `clave_nota` en «Mis reseñas»; por título, el título que se ve en el idioma efectivo, sin acentos ni mayúsculas, con el id del ítem y collation «C», para que el orden de la base y la comparación del cursor coincidan. Esto cierra la limitación anotada antes («el orden por título usa el canónico en inglés»).
  6. **Reordenar listas**: se implementa. `Lista.orden` (migración `0007_lista_orden`, que numera las existentes por id) y `PUT /api/lists/order/` con `{"ids": [...]}`, el orden completo de las personalizadas, que sirve igual para el arrastre y para «Move left / Move right» del canvas. Las predeterminadas siguen fijas adelante y las nuevas entran al final. Es tolerante con otra pestaña desactualizada: ids que no son personalizadas del usuario se ignoran y las que faltan quedan al final en su orden anterior. Ids repetidos o no positivos: 400 (Bad Request) en `ids`.
- **Tests**: `backend/listas/tests_detalle_orden.py` (22: detalle propio, predeterminada, ajena 404 (Not Found), sin sesión 401 (Unauthorized); nota y `null`; búsqueda con acentos y traducciones; tipo; tramos sin los no calificados; combinados; cada orden; título en el idioma; cursor sin repetir ni saltear con empates en los tres órdenes; 400 por campo; orden de listas, nuevas al final, ids ajenos y faltantes, repetidos).
- **Pendiente**: el doc 03 tiene que sumar `Lista.orden` (queda en la lista para revisar con Gonza, ver la entrada siguiente).
- **Miga de la ficha**: con el `GET` funcionando, la miga que viene de una lista predeterminada mostraba el nombre guardado («Favoritos», en el idioma de alta de la cuenta). Ahora las predeterminadas se nombran por su `clave` con `enums.defaultList.*`; las personalizadas, por su nombre. Test en `title-view.test.tsx`.
- **Archivos afectados**: `backend/listas/{models,views,serializers,pagination,urls}.py`, `backend/listas/migrations/0007_lista_orden.py`, `backend/listas/tests_detalle_orden.py`, `contracts/openapi.yaml` (regenerado), `openspec/specs/list-endpoints/spec.md`, `frontend/components/features/title/TitleView.tsx`, `frontend/tests/title-view.test.tsx`, `docs/decisiones.md`.

## 15/10/2026 — Pendiente para pair programming: alinear los docs 02 y 03 con el código (resuelto el 18/10/2026)

- **Fecha**: 15/10/2026
- **Descripción**: el análisis del 15/10 encontró que los docs 02 y 03 quedaron atrás del código. Marcos decidió **no corregirlos solo**: se revisan con Gonza en pair programming. **Estado (18/10/2026): resuelta** con las decisiones de Marcos y Gonza de esa fecha; cada punto de la lista tiene abajo su resolución, y el detalle está en la entrada «18/10/2026 — Docs 02 y 03 alineados con el código». Los cambios que sumó la funcionalidad nueva del 18/10 (país, plataformas, tema) se revisan con Gonza.
  - **Doc 02**: CU-010 y el RF de búsqueda hablan de «panel» y «grid paginada» (hoy es la página `/search` con scroll infinito; solo se actualizaron el paso 2 y parte de las observaciones). CU-008: filtro «calificación mínima 0–10» (hoy tramos 9+…5+ y <5; año con «Upcoming» y décadas). CU-008 2.A y CU-019 4.A: respaldo al catálogo local si TMDB cae (no implementado: 502 (Bad Gateway)). CU-008 y doc 03: «se materializa todo lo que muestra el catálogo» (hoy solo la ficha; C-04a 🟡). CU-021: avisar al administrador si la sincronización falla entera (no implementado). CU-005 y CU-015: «reseñas recientes» en el perfil (ni el código ni el canvas las muestran). CU-006: «edición inline» y «confirmación de cancelación» (hoy formulario «Edit details», contraseña aparte y aviso al salir). CU-009: el detalle de lista muestra «fecha de agregado» (el canvas muestra tipo, año y nota de TMDB). CU-012: falta reordenar listas. Sección «Gestión de reseñas propias desde perfil» (03/10): nota «X/10», títulos sin enlace, vacío que vuelve al perfil, sin filtros. «Multiidioma › Estado»: solo quedan `complete-signup` y `NavigationGuard` en español.
  - **Doc 03**: `perfilPublico` describe visibilidad de reseñas y listas (las reseñas son públicas desde el 14/10 y el switch no cambia nada). `tema` claro/oscuro (la app es solo oscura). Falta `fecha_enriquecimiento` en el doc y en el JSON. Falta `Lista.orden` (entrada anterior). Los diagramas siguen pendientes de regenerarse desde el JSON.
  - **Resolución punto por punto (18/10/2026)**:
    - **CU-010 y RF de búsqueda**: la doc pasa a describir la página `/search` con scroll infinito (al código). _Resuelto._
    - **CU-008, filtros**: se documentan los tramos de nota (9 o más … 5 o más, menos de 5) y el año con «A estrenar» y décadas (al código). _Resuelto._
    - **CU-008 2.A y CU-019 4.A, respaldo local**: el doc describe el respaldo de Redis (real); el de la base de datos queda como **mejora futura** (entrada del 18/10/2026 sobre el respaldo). _Resuelto._
    - **Materialización (CU-008 y doc 03)**: la doc dice lo que hace el código (ficha en el momento y listados en segundo plano; C-04a parcial). _Resuelto._
    - **CU-021, aviso al administrador si la sync falla**: **mejora futura**; hoy queda en el log. _Resuelto (como mejora futura)._
    - **CU-005 y CU-015, «reseñas recientes»**: se quitan del perfil y se remite a `/my-reviews`. _Resuelto._
    - **CU-006**: se documenta el formulario «Edit details», la contraseña aparte y el aviso al salir, y se suma el país editable. _Resuelto._
    - **CU-009, fecha de agregado**: se **implementa** en el código (MediaCard del detalle de lista, formato numérico compacto según el idioma) y la doc lo describe. _Resuelto._
    - **CU-012, reordenar listas**: la doc lo suma (al código). _Resuelto._
    - **«Gestión de reseñas propias desde perfil»**: se reescribe con «★ nota», títulos que enlazan a la ficha, filtros en la URL y vacío que invita a buscar (al código). _Resuelto._
    - **«Multiidioma › Estado»**: `complete-signup` y `NavigationGuard` ya están migrados; solo falta el chatbot (al código). _Resuelto._
    - **Doc 03, `perfilPublico`**: se aclara que hoy se guarda sin efecto y que las reseñas son públicas; el efecto real es **mejora futura**. _Resuelto._
    - **Doc 03, `tema`**: se elimina `Usuario.tema` (modelo, API, doc y JSON); la app es solo oscura. _Resuelto._
    - **Doc 03, `fecha_enriquecimiento` y `Lista.orden`**: agregados al doc y al JSON. _Resuelto._
    - **Doc 03, diagramas**: el JSON se actualizó (con `pais`, `Lista.orden` y `fecha_enriquecimiento`, sin `tema`). El repositorio **no tiene un script ni un renderizador** del JSON; la imagen se regenera con la herramienta de diagramas que lee ese formato. _JSON resuelto; imagen pendiente de la herramienta._
- **Archivos afectados**: `docs/decisiones.md`.

## 15/10/2026 — 404 sin sesión: frase completa con la mención del asistente

- **Fecha**: 15/10/2026
- **Descripción**: el 404 sin sesión cortaba la invitación en «Create a free account»; el canvas seguía con «…to rate films and keep your lists.». Marcos pidió la frase completa y sumar el asistente: «New to FilmAI? Create a free account to rate films, keep your lists, and get personalized picks from the FilmAI assistant.» / «¿Primera vez en FilmAI? Creá una cuenta gratis para calificar películas, guardar tus listas y recibir recomendaciones del asistente de FilmAI.». Va como una sola clave con `t.rich` (`errors.pages.signUpInvite`, el enlace en `<register>`), en lugar de dos fragmentos concatenados que impedían ordenar la frase en cada idioma; se retiran `newToFilmAI` y `createFreeAccount`. El canvas («404 and error», escritorio y celular) se actualizó igual.
- **Archivos afectados**: `docs/i18n/copia-propuesta.csv`, `frontend/messages/{en,es}/common.json` (y sus `.d.json.ts`), `frontend/app/not-found.tsx`, `frontend/tests/errors-and-account-menu.test.tsx`, `frontend/e2e/errores-menu.spec.ts`, `docs/decisiones.md`.

## 15/10/2026 — Canvas: el código como fuente de verdad en Home, Ficha y Search; propuesta de alta con Google

- **Fecha**: 15/10/2026
- **Descripción**: a pedido de Marcos, el canvas pasa a reflejar lo que el código ya decidió (versiones 317 y 318 del canvas):
  1. **Home**: el título del Hero se achica según su largo (≤16 caracteres, 152 px; ≤28, 112 px; más, 88 px; en celular 72/56/44 px, con alto mínimo de 560 px en vez de fijo). Un ajuste «tituloHero» (corto, mediano, largo) lo prueba.
  2. **Ficha**: la miga pasa arriba a la izquierda, sobre una píldora con velo; en celular, «‹ origen» con el mismo velo. Favorite, Watched y Watchlist activos rellenan el ícono con el color de acento (la pupila y las agujas toman el fondo del botón).
  3. **Search**: el scroll infinito reemplaza «Previous / Page 1 of 2 / Next» (tarjetas vacías mientras carga más; ajuste «cargandoMas»). El año ofrece «Upcoming», los años del actual a 1990 y las décadas de 1980 a 1900.
  4. **Alta con Google** (`/complete-signup`): artboards nuevos «Complete sign-up (Google)», escritorio y celular, en la sección 7, con selector EN/ES que cambia la copia y estados vacío, completo y usuario en uso. Es una **propuesta pendiente de aprobación de Marcos**; si se aprueba, pasa a código con claves `auth.completeSignUp.*` y la pantalla sale de `legacyFiles`.
- **Archivos afectados**: canvas «FilmAI — Sistema y catálogo» (`Home`, `Home-Movil`, `Ficha`, `Ficha-Movil`, `Buscar`, `Buscar-Movil`, `Error-SinSesion`, `Error-SinSesion-Movil`, `CompletarRegistro`, `CompletarRegistro-Movil`, `canvas.json`), `docs/decisiones.md`.

## 15/10/2026 — Reutilización de componentes y helpers (revisión end-to-end)

- **Fecha**: 15/10/2026
- **Descripción**: Marcos pidió revisar el proyecto completo para reutilizar componentes y aprobó informe + refactor. Se unificó lo de riesgo bajo, sin cambiar comportamiento:
  - **Backend**: un solo `_ORDENES` y los helpers `_clave_nota` y `_filtrar_nota` en `catalogo/reviews.py`; `ProduccionLocalizadaMixin` (título, póster y `campos_en_ingles`) compartido por `MiResenaSerializer` y `ListaItemSerializer`; `filmai/paginacion.py` `CursorConTotal`, base de los cursores de reseñas y de ítems de lista (`extras()` para `total_comunidad`/`total_propias`). **Bug corregido**: `MisResenasQuerySerializer` no tenía `FronteraErroresMixin`, así que sus 400 (Bad Request) salían con `params: {}` (sin `allowedValues`); test nuevo.
  - **Frontend**: `lib/review-filters.ts` (órdenes, su valor en la API, etiquetas y `parametrosNota`) para la comunidad de la ficha y «Calificaciones y reseñas»; `tmdbImage` acepta `w185` y se borra `posterUrl`; `components/features/filters/SheetParts.tsx` (`SheetHeader`, `SegmentedPills`, `SheetFooter`) y `etiquetaNota` para las dos hojas de filtros; `components/ui/StarIcon.tsx` (7 usos); `components/ui/ErrorRetry.tsx` (8 usos, cada uno conserva su botón); `MediaCardSkeleton`; `lib/last-view.ts` (`crearUltimaVista`) y el parser `de()` compartido. Los `<option>` de la comunidad usan ahora los mismos valores internos que «Calificaciones y reseñas» (`highest`, `9`); la API recibe lo mismo.
  - **Quedan propuestos, sin hacer** (riesgo medio, con estado): unificar el flujo de guardar/borrar calificación de `TitleView` y `MyReviewsView` en `lib/review-actions.ts`, y un `useCursorList` + `useSentinel` para los scrolls infinitos.
- **Tests**: Django 826 OK; Vitest 273 (nuevo `review-filters.test.ts`); Playwright de ficha, búsqueda, reseñas, home, perfil, preferencias y errores en verde (`e2e/ficha.spec.ts` actualizado a los valores nuevos de los `<option>`).
- **Archivos afectados**: `backend/catalogo/{reviews,serializers_reviews,pagination_reviews}.py`, `backend/catalogo/services/traducciones.py`, `backend/filmai/paginacion.py`, `backend/listas/{serializers,pagination}.py`, tests de catálogo; `frontend/lib/{review-filters,last-view,search,my-reviews,reviews,catalog}.ts`, `frontend/components/ui/{StarIcon,ErrorRetry}.tsx`, `frontend/components/features/filters/SheetParts.tsx`, `frontend/components/features/{MediaCard,SearchView,FiltersSheet,HomeHero}.tsx`, `frontend/components/features/reviews/`, `frontend/components/features/title/`, `frontend/app/{profile,settings}/page.tsx`, tests y `e2e/ficha.spec.ts`, `docs/decisiones.md`.

## 15/10/2026 — Alta con Google según el canvas, multiidioma completo y pendientes

- **Fecha**: 15/10/2026
- **Descripción**: Marcos aprobó los artboards «Complete sign-up (Google)» (escritorio y celular) y pidió pasarlos a código, con tests unitarios y end-to-end y multiidioma.
  1. **`/complete-signup`** se rehízo según el canvas: chip «Signing up with Google», título y descripción, username con `@`, disponibilidad en vivo («Available» / en uso) y ayuda, fecha y género en dos columnas (una en celular), términos en recuadro, botón oficial de Google (GIS, tema `outline`, ancho del formulario hasta 400 px) inerte hasta que el formulario es válido, y «Cancel and go back to log in», que descarta el alta pendiente. Si el backend rechaza un campo, aparece arriba «Fix the highlighted field and press the Google button again.» y el campo queda marcado; el aviso desaparece al corregirlo. En celular, `AccessShell` tiene la variante `poster="band"`: franja de pósters de 160 px con el logo encima.
  2. **Errores por código**: `completarRegistroGoogle` devuelve el error como código (`CodedError`) y la pantalla lo traduce al renderizar, así que el mensaje cambia si el usuario cambia de idioma con el selector EN | ES (guía de i18n, «Un formulario bilingüe debe guardar el código»).
  3. **Reutilización**: `useUsernameAvailability` (`lib/use-username-availability.ts`), `GoogleMark` (`components/access/GoogleMark.tsx`) y `maxFechaNacimiento` (`lib/validation.ts`) salen del registro y los usan las dos pantallas. `GoogleButton` acepta `theme` y `fullWidth`; el login y el resto no cambian.
  4. **Multiidioma completo**: `NavigationGuard` (aviso de salir sin guardar del perfil) toma su copia de `profile.leaveDialog.*`. Con eso, `legacyFiles` queda vacía. La copia nueva (`auth.completeSignUp.*`, `profile.leaveDialog.*`) está en `docs/i18n/copia-propuesta.csv`; la del diálogo traduce la que ya existía en español, porque el canvas no tiene ese diálogo.
  5. **Mejoras futuras**: el perfil público y los correos de notificación quedan como mejoras futuras. Sus controles siguen en Settings con el aviso de efecto pendiente, sin cambios.
  6. **Pendiente de evaluación**: el refactor de riesgo medio propuesto en la revisión de reutilización (`lib/review-actions.ts` y `useCursorList` + `useSentinel`) queda como Q-07 en el doc 05.
- **Tests**: Vitest 283 (`complete-signup.test.tsx` reescrito con 10 casos; nuevo `navigation-guard.test.tsx` en inglés y español). Playwright: nuevo `e2e/alta-google.spec.ts` (alta completa hasta el Home, username en uso con el error que sigue al idioma, cancelar y redirección sin alta pendiente, en 1440 y 390 px), con el SDK de Google reemplazado por uno de prueba. `playwright.config.ts` define un `NEXT_PUBLIC_GOOGLE_CLIENT_ID` de prueba para que el botón se dibuje.
- **Archivos afectados**: `frontend/app/complete-signup/page.tsx`, `frontend/app/(public)/register/page.tsx`, `frontend/components/{GoogleButton,NavigationGuard}.tsx`, `frontend/components/access/{AccessShell,Logo,GoogleMark}.tsx`, `frontend/lib/{google-auth,validation,use-username-availability}.ts`, `frontend/scripts/i18n/rules.mjs`, `frontend/messages/`, `frontend/playwright.config.ts`, `frontend/tests/{complete-signup,navigation-guard}.test.tsx`, `frontend/e2e/alta-google.spec.ts`, `docs/i18n/{copia-propuesta.csv,guia.md}`, `docs/05_Plan_de_Desarrollo.md`, canvas (notas «Interfaces: código vs pendientes» y de la propuesta de Google).

## 16/10/2026 — UI de Listas (L-02 y L-03) según el canvas

- **Fecha**: 16/10/2026
- **Descripción**: Marcos aprobó pasar a código los artboards «Lists» y «List detail» (escritorio y celular) y fijó cuatro decisiones:
  1. **Reordenar con `@dnd-kit`** (`core`, `sortable`, `utilities`). En escritorio se arrastra desde la manija (`ManijaSensor`, 4 px); en celular, con una pulsación larga de 250 ms sobre la tarjeta (`PulsacionLargaSensor`, tolerancia de 8 px): si el dedo se mueve antes, es scroll y no arrastre. También con teclado en la manija (Espacio, flechas, Espacio) con anuncios traducidos. Las predeterminadas no se arrastran y quedan fijas arriba. En las tarjetas arrastrables se anulan el menú y la vista previa del sistema al mantener presionado (`-webkit-touch-callout: none`, `user-select: none`, `contextmenu` anulado en pantallas táctiles, `draggable="false"` en el enlace). Si `PUT /api/lists/order/` falla, vuelve al orden anterior y avisa.
  2. **Menú ⋯**: en escritorio, Rename / Move left / Move right / Delete; en celular (hoja inferior), Rename / Move up / Move down / Delete. Dos claves nuevas: `common.lists.moveUp` y `common.lists.moveDown`.
  3. **Quitar de «Watched» un título calificado**: el backend responde 409 (Conflict) con `rating_blocks_removal_from_watched`; el detalle muestra la misma confirmación que la ficha («también se borra tu calificación y reseña») y reintenta con `?borrar_calificacion=true`.
  4. **Q-07**: el detalle copia el patrón de cursor + `IntersectionObserver` de «Calificaciones y reseñas» y no se extraen `useCursorList` ni `useSentinel` en este PR. Quedan dos pantallas con cursor (Mis reseñas, Lists) y tres con centinela (Search, Mis reseñas, Lists); Q-07 lo anota.
- **Detalles de implementación**: las predeterminadas se nombran por su clave (`enums.defaultList.*`), sin ⋯ ni en la vista general ni en el detalle. Los filtros del detalle (`q`, `type`, `rating`, `sort`) viven en la URL; la nota «Menos de 5» se manda como `nota=m5` y las demás como `N+`. El error de un nombre repetido o reservado llega por código y se traduce al renderizar. `cambiar()` del detalle parte de la URL actual (`window.location.search`) y no de lo renderizado: «Clear filters» y la espera de 350 ms del texto se cruzaban y devolvían los filtros ya quitados. `ConfirmDialog` admite `descripcion` opcional (la confirmación de quitar un ítem solo lleva título, como el canvas). `@testing-library/dom` se declara como devDependency: era peer de `@testing-library/react` y el lockfile lo perdía al instalar dependencias nuevas.
- **Copia nueva** (`docs/i18n/copia-propuesta.csv`): `lists.count.tvShows`, `common.lists.moveUp/moveDown`, `lists.name.placeholder/counter`, `lists.reorder.*` (instrucciones y anuncios), `lists.overview.loadError/loading`, `lists.detail.loadError/loading/loadMore/searchPlaceholder/displayedCount/sortPrefix/resultsAction/filtersTitle/removeChipLabel`.
- **Tests**: Vitest (`tests/lists-lib.test.ts`, `tests/lists-view.test.tsx`, `tests/list-detail-view.test.tsx`); Playwright (`e2e/listas.spec.ts`) en 1440×900 y 390×844 con touch real por CDP: que deslizar antes de 250 ms hace scroll sin arrastrar, que la pulsación larga reordena, que el contextmenu queda anulado, y los flujos de crear, duplicado, renombrar, eliminar, mover, filtros en la URL, scroll infinito, quitar ítem y Watched con calificación.
- **Docs**: doc 04 §5e (reordenamiento y menús), doc 05 (sección 8, L-02, L-03, Q-03, Q-04, Q-07). El canvas (sección «8 · Lists» y la nota «Interfaces: código vs pendientes») se ajusta aparte, por etapas.
- **Archivos afectados**: `frontend/app/lists/page.tsx`, `frontend/app/lists/[id]/page.tsx`, `frontend/components/features/lists/{ListsView,ListCard,ListActionsMenu,ListNameDialog,ListDetailView,ListFiltersSheet}.tsx`, `frontend/components/features/title/ConfirmDialog.tsx`, `frontend/lib/{lists,list-sensors}.ts`, `frontend/messages/{en,es}/common.json` (y `.d.json.ts`), `docs/i18n/copia-propuesta.csv`, `frontend/package.json` y `package-lock.json`, `frontend/tests/lists-*.test.ts(x)`, `frontend/tests/list-detail-view.test.tsx`, `frontend/e2e/listas.spec.ts`, `docs/04_Lineamientos_UI.md`, `docs/05_Plan_de_Desarrollo.md`.

## 16/10/2026 — Fix: «Clear filters» en Calificaciones y reseñas devolvía los filtros quitados

- **Fecha**: 16/10/2026
- **Descripción**: al escribir el detalle de Listas apareció una carrera que también estaba en `MyReviewsView`. «Clear filters» vaciaba el texto y la URL, pero la espera de 350 ms del texto disparaba `cambiar({ q: "" })` con los filtros renderizados (todavía viejos, porque `useSearchParams` tarda en reflejar `history.replaceState`) y volvía a escribir tipo y nota en la URL. Se reprodujo en el navegador (`/my-reviews?q=zzz&type=tv&rating=8` terminaba en `?type=tv&rating=8`). `cambiar()` ahora parte de `window.location.search`. Es el mismo criterio del detalle de Listas.
- **Tests**: `tests/my-reviews-view.test.tsx` (nuevo caso con `useSearchParams` atrasado, que falla sin el fix) y verificación en Playwright en el navegador.
- **Archivos afectados**: `frontend/components/features/reviews/MyReviewsView.tsx`, `frontend/tests/my-reviews-view.test.tsx`, `docs/decisiones.md`.

## 16/10/2026 — «Forgot your password?» va debajo del campo Password

- **Fecha**: 16/10/2026
- **Descripción**: en Log in, el enlace «Forgot your password?» (EN/ES) estaba a la derecha de la etiqueta en escritorio. Marcos pidió que quede debajo del campo Password, alineado a la derecha, como ya estaba en celular. `PasswordField` renderiza `labelAction` debajo del input en todos los anchos (se quitó el posicionamiento absoluto de `sm:`). El canvas (`Login.dc.html`) se ajustó igual.
- **Archivos afectados**: `frontend/components/access/fields.tsx`, `docs/decisiones.md`, canvas (`Login.dc.html`).

## 16/10/2026 — Listas: filtros del detalle a ancho de contenido y sin toast al reordenar

- **Fecha**: 16/10/2026
- **Descripción**: Marcos pidió dos ajustes en Listas. (1) En el detalle de una lista, las cajas Tipo, Nota de TMDB y Orden ocupaban todo el ancho de la fila (`flex-auto`), casi igual que el buscador. Ahora miden lo que su contenido (`flex-none`; el buscador no cambia) y «Clear filters» pasó de la fila del buscador al final de la fila de filtros, junto a lo que limpia. (2) Se eliminó el toast «Orden guardado» (`lists.feedback.orderSaved`, clave retirada del catálogo): el nuevo orden ya se ve en pantalla; el toast de error y la reversión se mantienen.
- **Observación sobre datos locales**: al revisar por qué una tarjeta de una lista abría otra ficha, se vio que la tarjeta enlaza bien (`/{tipo}/{id_tmdb}`) y que 21 producciones de la BD local eran sintéticas de `manage.py seed` (títulos de Faker, `id_tmdb` bajos y póster `https://…`), con ids que coinciden con otros títulos reales de TMDB; 14 de los 69 ítems en listas eran de esas. No es un bug del enlace ni del backend; no ocurre con producciones materializadas desde TMDB.
- **Archivos afectados**: `frontend/components/features/lists/{ListDetailView,ListsView}.tsx`, `frontend/messages/{en,es}/common.json` (y `.d.json.ts`), `docs/i18n/claves.csv`, `frontend/tests/lists-view.test.tsx`, `frontend/e2e/listas.spec.ts`, `docs/decisiones.md`.

## 16/10/2026 — Buscar: buscador 20 % más chico y «Clear filters» junto a los filtros

- **Fecha**: 16/10/2026
- **Descripción**: Marcos pidió reducir el buscador de Buscar un 20 % y poner «Clear filters» a la derecha de los filtros, como en Listas. En escritorio el campo pasó de 72 a 58 px de alto y de 34 a 27 px de texto (icono, márgenes y botón de borrar proporcionales); el ancho y el celular no cambian. «Clear filters» aparece al final de la fila Género/Año/Nota solo con filtros activos y quita género, año y nota sin tocar el texto (el del estado vacío se mantiene).
- **Archivos afectados**: `frontend/components/features/SearchView.tsx`, `frontend/tests/search-view.test.tsx`, `docs/decisiones.md`.

## 16/10/2026 — Datos locales: producciones reales y actividad con sentido

- **Fecha**: 16/10/2026
- **Descripción**: la BD de desarrollo tenía producciones de Faker y calificaciones/reseñas con texto de relleno, así que abrir una tarjeta mostraba otra ficha. A pedido de Marcos se borraron las 21 producciones sintéticas (con sus ítems, calificaciones y reseñas en cascada), se materializaron 60 títulos reales desde TMDB (`materializar`, por género y votos) y se regeneró la actividad de `usuario001/002/003`: entre 14 y 15 calificaciones cada uno, cercanas a la nota de TMDB con afinidad por género; reseñas en el idioma de cada cuenta; Vistas coherente con lo calificado (regla «calificada ⇒ Vistas»), Favoritos con lo calificado 9 o más, Pendientes sin lo ya visto y dos listas personalizadas temáticas por usuario. Se conservaron la lista «Hola muy buenos dias» y su ítem (manuales). Es solo la BD local: no hay migración ni cambio de código.
- **Archivos afectados**: ninguno del repositorio (datos locales), `docs/decisiones.md`.

## 15/10/2026 — El seed completo usa producciones reales de TMDB

**Descripción:** las producciones sintéticas de Faker tenían `id_tmdb` bajos que chocaban con títulos reales de TMDB, y al tocar una tarjeta la ficha mostraba otra producción. `seed` ahora trae de TMDB los más votados por género (9 de películas y 6 de series, 4 por género) con `materializar` y arma actividad con sentido: calificaciones cercanas a la nota de TMDB con afinidad por género, reseñas en el idioma de cada cuenta, «calificada ⇒ Vistas», Favoritos con nota ≥ 9, Pendientes sin lo visto, dos listas temáticas por cuenta y 1 de cada 7 reseñas inactiva. No borra producciones reales; solo las sintéticas. Se aborta sin borrar nada si TMDB deja menos de 20 reales. `--sintetico` conserva el comportamiento anterior (offline, con el umbral de protección) y lo usan los tests de idioma. `--solo-resenas` no cambia (sigue con factories).

**Archivos:** `backend/usuarios/seed_real.py` (nuevo), `backend/usuarios/management/commands/seed.py`, `backend/usuarios/test_seed_real.py`, `backend/usuarios/test_seed_idioma.py`, `README.md`, `openspec/specs/development-seed/spec.md`.

## 16/10/2026 — Renovación de la sesión y aviso al vencer

- **Fecha**: 16/10/2026
- **Descripción**: el frontend nunca usaba la cookie `refresh`. A las 8 horas del login vencía la cookie `access` y la app sacaba al usuario sin explicación (al login en las pantallas protegidas, o lo mostraba deslogueado en las públicas), aunque el refresh de 7 días seguía válido. El RNF #5 del doc 02 ya pedía la renovación.
  1. **Renovación silenciosa** (`lib/api.ts`): si un pedido vuelve 401, `apiFetch` llama a `POST /api/auth/token/refresh/` (con CSRF, como toda mutación) y repite el pedido una vez. Varios 401 simultáneos comparten una sola renovación, porque el backend rota la `refresh` y anula la anterior. Se repite el pedido aunque la renovación falle, porque otra pestaña pudo haber renovado las cookies compartidas. Las rutas `/api/auth/` no renuevan. Con esto la sesión dura 7 días desde el último uso (decisión del usuario: se mantienen los 7 días).
  2. **Aviso al vencer**: si ni renovando hay sesión, `apiFetch` emite el evento `filmai:sesion-vencida`. `AccountProvider` muestra «Tu sesión venció. Iniciá sesión de nuevo.» y, en una pantalla protegida, lleva al login con `?next=`. Solo avisa si hubo sesión (cookies al cargar o un perfil cargado), no a quien nunca entró.
  3. **Sin cookies no se pide el perfil**: el layout (servidor) mira si llegó `access` o `refresh` y se lo pasa a `AccountProvider`. Sin ninguna de las dos no se pide `/api/profile/`, que solo contestaría 401 (el error rojo en la consola del visitante). Se vuelve a preguntar después de pasar por una pantalla de acceso, porque el alta con Google no llama a `recargar()`; el login sí.
  4. **Middleware**: deja pasar a una pantalla protegida si hay `access` o `refresh`; con solo `refresh`, la página renueva al cargar.
- **Descartado**: guardar el token en `localStorage` y mandarlo como `Authorization: Bearer` (sugerencia del asistente de Chrome por el encabezado `WWW-Authenticate: Bearer` que DRF pone en cualquier 401). Las cookies httpOnly no son legibles desde JavaScript; en `localStorage` un XSS podría robar el token.
- **Tests**: `api-session.test.ts` (renueva y repite con CSRF, una sola renovación para varios 401, evento si no se puede, `auth/` no renueva), `session-account.test.tsx` (sin cookies no pide el perfil, aviso y login al vencer, sin aviso a quien nunca entró) y dos recorridos en `e2e/cuenta.spec.ts` (solo `refresh` renueva y no saca; vencida del todo lleva al login con el aviso).
- **Archivos afectados**: `frontend/lib/api.ts`, `frontend/components/AccountProvider.tsx`, `frontend/app/layout.tsx`, `frontend/middleware.ts`, mensajes y copia de i18n, tests y e2e, `docs/05_Plan_de_Desarrollo.md`, `docs/decisiones.md`.

## 16/10/2026 — Revisión de calidad: accesibilidad y responsive (Q-01, Q-04)

- **Fecha**: 16/10/2026
- **Descripción**: auditoría de la app real con sesión y sin ella, en 375, 768 y 1440 px: axe-core (WCAG 2.1 AA y buenas prácticas), desbordes, tamaño de objetivos táctiles, letra de los campos y foco visible con Tab, sobre 15 pantallas y 4 diálogos abiertos. Contraste: sin problemas. Se corrigió:
  1. **Desbordes**: los filtros del detalle de lista a 768 px (la fila ahora pasa a la línea siguiente; los filtros conservan su ancho de contenido) y los botones «Iniciar sesión / Registrarse» del encabezado a 375 px (menos separación y relleno en celular).
  2. **Objetivos táctiles de 44 px en celular** (decisión del usuario: se sigue el doc 05 Q-04 y no los 40 px del canvas, solo en celular; en escritorio quedan como el canvas): opciones de las hojas de filtros, selector de tipo, selector de idioma, interruptor de Settings (el botón mide 44 de alto y la pista sigue siendo de 52 × 32), selects y botones de la reseña propia en la ficha, «Leer más», «Cambiar avatar», acciones de Mis reseñas y botones del menú de listas de la ficha.
  3. **Letra de 16 px en los campos en celular**: los selects de reseñas de la ficha (14 px) y los buscadores de Mis reseñas y del detalle de lista (15 px). Con menos, iOS hace zoom al tocarlos.
  4. **Títulos de pestaña**: login y registro con sus metadatos; la ficha pone el nombre de la película o serie cuando llega (el servidor de Next no puede pedirlo: en Docker no llega al backend); el 404 lo exporta en `not-found.tsx` (ponerlo desde el componente no sirve: Next 15 transmite los metadatos después de hidratar y lo pisa). La landing sigue diciendo «FilmAI».
  5. **Tema oscuro desde el servidor**: `viewport` del layout con `colorScheme: "dark"` y `themeColor` (#0d0d14), y `color-scheme: dark` en `.dark`. Antes se aplicaba con JavaScript y el primer pintado de los controles nativos era claro.
  6. **Animaciones con `transform`**: la barra de navegación (antes `width`) y la perilla del interruptor (antes `left`).
  7. **Casilla de términos sin zonas muertas** (registro y alta con Google): todo el recuadro es la etiqueta.
  8. **`touch-action: manipulation`** global en los controles.
  9. **Landmarks en las pantallas de acceso**: el selector de idioma va en un `header` y el collage en un `aside`.
  10. **Miga de la ficha** con al menos 24 px de alto.
- **Verificación**: la misma auditoría después de los cambios: axe de 9 avisos a 0, desbordes de 2 a 0, objetivos de menos de 44 px en celular de 106 a 0, campos de menos de 16 px en celular de 7 a 0, y títulos correctos en todas las pantallas.
- **Falsos positivos descartados**: el foco de las tarjetas de películas y de listas se dibuja en el póster o en un pseudo-elemento; se verificó con capturas.
- **Fuera de alcance**: prueba con lector de pantalla real (NVDA/VoiceOver), forzar errores de API para Q-03 y el chatbot (no existe todavía).
- **Archivos afectados**: `frontend/app/{layout.tsx,globals.css}`, `frontend/app/(public)/{login,register}/`, `frontend/app/complete-signup/page.tsx`, `frontend/app/profile/page.tsx`, `frontend/components/{Navbar,LanguageSwitcher,NavigationProgress}.tsx`, `frontend/components/access/AccessShell.tsx`, `frontend/app/not-found.tsx`, `frontend/components/ui/switch.tsx`, `frontend/components/features/{TypeSelector.tsx,filters/SheetParts.tsx,lists/ListDetailView.tsx,reviews/,title/}`, `frontend/tests/title-view.test.tsx`, `docs/05_Plan_de_Desarrollo.md`, `docs/decisiones.md`.

## 16/10/2026 — Fix: la caché del catálogo guarda por idioma

- **Fecha**: 16/10/2026
- **Descripción**: en el Home con la interfaz en inglés, la fila de tendencias mostraba títulos en español («Animales», «Madre siniestra») y la de recomendados, en inglés. La API traduce bien según `Accept-Language`; el problema era la caché de `lib/use-catalog.ts`, que guardaba las respuestas por ruta sin el idioma. Cuando el idioma cambia sin recargar la página (el de la cuenta al iniciar sesión, o el selector: `persistLocale` + `router.refresh`), las filas cacheadas seguían con el idioma anterior; Recomendado no se cachea y por eso salía bien.
  1. La clave de la caché es `idioma|ruta`, con el idioma de `useLocale()` de next-intl. Al cambiar de idioma se vuelve a pedir; al volver al anterior se usa lo guardado.
  2. Vale para `useCatalog` y `useCatalogPaginas` (Home, Buscar y ficha).
- **Tests**: `use-catalog-paginas.test.tsx` suma dos casos (cambio de idioma en `useCatalog` y en las páginas de Buscar); fallan con la caché anterior. Verificado en la app: Home en español → selector a inglés → «Animals».
- **Archivos afectados**: `frontend/lib/use-catalog.ts`, `frontend/tests/use-catalog-paginas.test.tsx`, `docs/decisiones.md`.

## 16/10/2026 — Respaldo cuando TMDB no responde y materialización de los listados (CU-008 2.A, CU-019 4.A, C-04a)

- **Fecha**: 16/10/2026
- **Descripción**:
  1. **Respaldo en Redis** (decisión del usuario, frente a armar las respuestas desde Postgres). Cada respuesta de TMDB se guarda además bajo `tmdb:respaldo:…` por 30 días. Si TMDB no está disponible —error de servidor, conexión rechazada o tiempo agotado, límite de pedidos o reintentos agotados— `TMDBClientCache` sirve esa copia y deja un aviso en el log. Un 404 o un 400 no usan el respaldo (dicen algo cierto del pedido), y sin copia el error sigue como antes (CU-019 4.A.2). La lista de cambios de la sync nocturna no tiene respaldo: ahí el fallo tiene que verse. Cubre todo lo que ya se pidió alguna vez (Home, Buscar, ficha, reparto, géneros); lo que nunca se consultó sigue dando error. Redis guarda sus datos en el volumen `redisdata`, así que el respaldo sobrevive a un reinicio.
  2. **Los listados materializan lo que muestran** (decisión del usuario: se cumple lo que dicen docs 02 y 03 en vez de cambiarlos). `trending`, `now-playing`, `discover`, `search` y `browse` encolan en Celery lo que no está fresco en la base, con una sola consulta por listado. Cada título se encola como mucho una vez cada 10 minutos (`cache.add`): el Home lo abren muchas personas y, con TMDB caído, la cola se llenaría de tareas repetidas que fallan. Las llamadas de la tarea pasan por la caché, así que repetirla cuesta poco. Si encolar falla, el listado se responde igual.
- **Verificado en la app**: abrir tendencias, estrenos y una búsqueda llevó el catálogo de 281 a 326 producciones; con un cliente apuntando a un puerto cerrado y la copia normal vencida, las tendencias salieron del respaldo.
- **Tests**: `catalogo/test_respaldo_tmdb.py` (6: error de servidor, sin conexión, sin copia, 404, TTL de 30 días, la lista de cambios sin respaldo) y `catalogo/test_materializar_listados.py` (9: tipos y personas, tipo del listado, frescura por id y tipo, vencidas y sin enriquecer, una vez cada 10 minutos, listados vacíos, y las vistas: tendencias, discover y un fallo al encolar). Los tests sin base de datos de los listados (`tests_browse.py`, `EndpointIntegrationTest`) parchean el encolado, como ya hacían con la ficha.
- **Archivos afectados**: `backend/catalogo/{cache.py,views.py}`, `backend/catalogo/services/materialization.py`, `backend/catalogo/{test_respaldo_tmdb.py,test_materializar_listados.py,tests.py,tests_browse.py}`, specs `tmdb-cache` y `catalog-materialization`, `docs/05_Plan_de_Desarrollo.md`, `docs/decisiones.md`.

## 16/10/2026 — Q-03: estados de carga, vacío, error y aviso tras acciones

- **Fecha**: 16/10/2026
- **Descripción**: revisión de Q-03 (doc 05) sobre la app real con la cuenta de prueba: 46 escenarios en 8 pantallas (Home, Buscar, ficha, Listas, detalle de lista, Mis reseñas, Perfil y Settings) más 5 chequeos puntuales. Las fallas se provocaron interceptando en el navegador los pedidos a la API: error 500 (o el 502 que manda el backend cuando TMDB falla), sin red (pedido cortado), lento (3,5 s) y vacío; las acciones exitosas fueron al backend real y se deshicieron. Funcionaba bien la mayoría: siluetas de carga sin «no hay nada» antes de tiempo, vacíos con salida (Buscar, Mis reseñas, listas), errores con «Reintentar» que vuelven a pedir, acciones fallidas que conservan lo escrito y no marcan nada como guardado, y avisos tras cada acción. Se corrigió:
  1. **Sin red se veía «Failed to fetch»** (en la ficha y en los avisos de cualquier acción) o el genérico «No pudimos completar la acción». `apiFetch` convierte el rechazo de `fetch` en un `ApiError` con el código propio del front `network_error`: «No pudimos conectarnos. Revisá tu conexión e intentá de nuevo.» (como `unknown`, no está en el contrato del backend).
  2. **Reseñas de la comunidad**: si fallaban, el error no tenía «Reintentar»; ahora usa `ErrorRetry` y vuelve a pedir.
  3. **Ficha**: si fallaban las listas del usuario, Favorita, Vista y Pendiente desaparecían sin aviso. Ahora se avisa con «Reintentar».
  4. **Home con todo vacío** quedaba en blanco: ahora lo dice y ofrece explorar.
  5. **Home con todo caído** mostraba el mismo error dos veces (el aviso de «algo no cargó» salía antes de que terminaran los pedidos): el aviso espera a que terminen.
  6. **Perfil y Settings** que no cargan decían «No pudimos completar la acción»: `AccountProvider` usa el mensaje del propio error (servidor o conexión).
- **Se deja como está, a propósito**: el reparto que no carga se omite (es secundario y no rompe la ficha); el interruptor de Settings no muestra aviso al guardar (el propio interruptor es la confirmación; al fallar avisa y vuelve atrás).
- **Pendiente sin corregir**: la copia de los errores mezcla «Intentá» y «Probá», y varios dicen solo «Ocurrió un error» sin decir qué no cargó.
- **Tests**: `api-session.test.ts` (sin red), `session-account.test.tsx` (mensaje de la cuenta), `reviews-section.test.tsx` (reintentar), `title-view.test.tsx` (listas que no cargan) y `home-page.test.tsx` (todo vacío; un solo error cuando todo falla). Cada uno falla con el código anterior.
- **Archivos afectados**: `frontend/lib/api.ts`, `frontend/components/AccountProvider.tsx`, `frontend/components/features/HomeView.tsx`, `frontend/components/features/title/{ReviewsSection,TitleView}.tsx`, mensajes y copia de i18n, tests, `docs/05_Plan_de_Desarrollo.md`, `docs/decisiones.md`.

## 16/10/2026 — Ajustes de la revisión del PR #111

- **Fecha**: 16/10/2026
- **Descripción**: cuatro detalles menores que salieron al revisar el PR #111 (respaldo de TMDB, listados y Q-03):
  1. **La marca de 10 minutos no bloquea un reintento**: `materializar_listado_en_segundo_plano` borra la marca de `cache.add` si `delay()` falla (broker caído). Antes ese título no se volvía a encolar hasta que vencía la ventana.
  2. **Un aviso de respaldo cada 5 minutos por endpoint**: con TMDB caído, cada pedido servido desde el respaldo dejaba un warning. `TMDBClientCache` marca `tmdb:respaldo-aviso:<endpoint>` con `SET NX` por 5 minutos y solo avisa si la marca es nueva; si Redis falla al marcar, avisa igual.
  3. **Ficha**: la carga inicial de las listas del usuario también limpia `errorListas` al responder bien (antes solo lo hacía `recargarListas`), así que el aviso de una ficha anterior no queda colgado.
  4. Línea en blanco que faltaba antes de la entrada del respaldo en este archivo.
  5. **Test inestable en CI**: `title-view.test.tsx` leía `document.title` apenas aparecía el encabezado, pero el título se asigna en un efecto posterior; falló una vez en CI. Ahora lo espera con `waitFor`.
- **Tests**: `test_respaldo_tmdb.py` (un solo aviso en tres pedidos seguidos con TMDB caído), `test_materializar_listados.py` (si encolar falla, el siguiente listado lo vuelve a encolar) y `title-view.test.tsx` (al pasar a otra ficha cuyas listas cargan, el aviso desaparece; falla con el código anterior).
- **Archivos afectados**: `backend/catalogo/cache.py`, `backend/catalogo/services/materialization.py`, `backend/catalogo/{test_respaldo_tmdb.py,test_materializar_listados.py}`, `frontend/components/features/title/TitleView.tsx`, `frontend/tests/title-view.test.tsx`, `docs/decisiones.md`.

## 18/10/2026 — Respaldo local del catálogo si TMDB cae: mejora futura (a discutir con Gonza)

- **Fecha**: 18/10/2026
- **Cuestión**: CU-008 2.A y CU-019 4.A prometen que, si no hay conexión con TMDB, «el sistema recupera el catálogo almacenado localmente». Hoy eso se cumple solo en parte.
- **Estado actual**:
  - **Redis** (`TMDBClientCache`, `backend/catalogo/cache.py`): guarda la última respuesta de cada consulta 30 días (`RESPALDO_TTL`; 7 días para `watch_providers`) y la sirve si TMDB falla (error de servidor, límite de uso o transporte), con un aviso en el log cada 5 minutos como máximo. Cubre solo consultas ya hechas, con los mismos parámetros (página, filtros e idioma van en la clave).
  - **PostgreSQL** (`Produccion`): guarda las producciones materializadas (seed, fichas abiertas, listados encolados), pero Home, Buscar y los filtros no la leen. Con TMDB caído, una consulta nueva responde 502 (Bad Gateway) aunque el título esté en la base.
- **Problema**: un respaldo desde la BD no garantiza completitud.
  1. Cobertura parcial: solo están las producciones materializadas, no el catálogo de TMDB. El usuario no distingue un listado parcial del completo.
  2. Faltan datos para filtrar y ordenar: el modelo no guarda la nota de TMDB, los votos ni la popularidad. Sin eso no se resuelven los tramos de calificación, la popularidad ni las tendencias de Home.
  3. La relevancia de la búsqueda por nombre de TMDB no se replica con `icontains`.
  4. Datos de hasta un día de antigüedad (sync diaria C-04b).
  5. Trending, «en cartelera» y «a estrenar» dependen de rankings de TMDB.
- **A considerar al decidirlo**: columnas nuevas y migración (nota, votos, popularidad) con relleno de lo ya guardado; un servicio que traduzca filtros y orden a consultas; caer a la BD ante `TMDBError` y marcar la respuesta con `origen: "local"`; aviso en la UI («Mostrando resultados guardados») y diseño en el canvas; tests de cada filtro. Estimación: un PR mediano (2 a 3 días). Si se implementa, conviene limitarlo a Buscar con texto y a la ficha, sin prometer el catálogo completo.
- **Decisión (18/10/2026, Marcos)**: por ahora, **mejora futura**. El doc 02 describe el respaldo de Redis (real) y marca el de la BD como mejora futura. Queda para un análisis exhaustivo con Gonza.
- **Archivos afectados**: `docs/decisiones.md` (y el doc 02, CU-008 y CU-019, al resolver las inconsistencias).

## 18/10/2026 — Docs 02 y 03 alineados con el código (CU-005, 006, 008, 009, 010, 012, 015, 019, 021)

- **Fecha**: 18/10/2026
- **Descripción**: Marcos y Gonza resolvieron la lista de inconsistencias de la entrada del 15/10/2026 («Pendiente para pair programming»). Criterio general: **los docs se corrigen para decir lo que hace el código**, salvo lo indicado.
  1. **Doc 02, CU-008 y CU-010**: la búsqueda es la página `/search` con scroll infinito (ya no «panel» ni «grid paginada»). Los filtros documentados son el tipo, el género, la nota de TMDB por tramos (9 o más … 5 o más, menos de 5, con al menos 50 votos) y el año con «A estrenar», años sueltos hasta 1990 y décadas.
  2. **Doc 02, CU-008 2.A y CU-019 4.A**: describen el respaldo de Redis (30 días; 7 para las plataformas) y marcan el respaldo desde la base de datos como mejora futura, según la entrada del 18/10/2026 sobre el respaldo local (no se duplica acá).
  3. **Materialización (doc 02 CU-008 y doc 03)**: la ficha materializa en el momento y los listados lo hacen en segundo plano (Celery); C-04a queda parcial, sin prometer todo TMDB.
  4. **CU-021**: avisar al administrador si la sincronización falla entera es **mejora futura**; hoy queda en el log.
  5. **CU-005 y CU-015**: se quitan las «reseñas recientes» del perfil y se remite a `/my-reviews`.
  6. **CU-006**: se documenta el formulario «Edit details», la contraseña por separado, el aviso al salir con cambios sin guardar y el país editable.
  7. **CU-009**: se **implementó** la fecha de agregado, discreta, en la MediaCard de cada producción dentro del detalle de una lista, con formato numérico compacto según el idioma (`18/10/2026` en español, `10/18/2026` en inglés) y la etiqueta «Agregada el» / «Added on» (`common.media.addedOnLabel`). El doc lo describe así.
  8. **CU-012**: se documenta el reordenamiento de listas personalizadas (`Lista.orden`, `PUT /api/lists/order/`).
  9. **«Gestión de reseñas propias desde perfil» y doc 04, sección 5i**: se reescriben con lo que hace `/my-reviews` (nota «★ 9», títulos que enlazan a la ficha, filtros en la URL, vacío que invita a buscar).
  10. **«Multiidioma › Estado»**: `legacyFiles` quedó vacía el 15/10/2026; falta solo el chatbot.
  11. **Doc 03**: `perfilPublico` se aclara como «se guarda sin efecto; las reseñas son públicas» (efecto real: mejora futura). `fecha_enriquecimiento` y `Lista.orden` se agregan al texto y al JSON. `tema` se elimina (ver entrada «Tema claro descartado»). Se suma `pais` (ver entrada del país).
  12. **Diagramas del doc 03**: se regeneró el **JSON** (`pais`, `Lista.orden`, `fechaEnriquecimiento`; sin `tema`). El repositorio no incluye un script ni un renderizador de ese JSON (el formato es el de la herramienta de diagramas externa que lo produjo), así que la **imagen no se pudo regenerar** desde acá; el doc 03 lo anota y el JSON es la fuente de verdad hasta entonces.
- **Revisión con Gonza**: los cambios a los docs 02 y 03 por la funcionalidad nueva de este día (país, plataformas, tema eliminado) **se revisan con Gonza**; los demás ya salieron de la decisión conjunta.
- **Archivos afectados**: `docs/02_Especificación de Requerimientos.md`, `docs/03_Modelos de Datos y de Diseño.md`, `docs/03_DiagramaClases_DiagramaTablas.json`, `docs/04_Lineamientos_UI.md`, `docs/05_Plan_de_Desarrollo.md`, `docs/decisiones.md`.

## 18/10/2026 — País de la cuenta (`Usuario.pais`)

- **Fecha**: 18/10/2026
- **Descripción**: la cuenta guarda el país para mostrar en la ficha las plataformas disponibles allí.
  1. **Lista**: ISO 3166-1 alfa-2, **hardcodeada** en `contracts/enums.json` (`paisCodes`, 249 códigos), que lee el backend (`usuarios/paises.py`) y copia el frontend (`frontend/i18n/enums.json`). No hay tabla de países. Los nombres salen de `Intl.DisplayNames` en el idioma activo.
  2. **Campo**: `Usuario.pais` (VARCHAR(2), obligatorio, sin valor por defecto). Obligatorio en el registro, el alta con Google (`/complete-signup`, `CAMPOS_FALTANTES_GOOGLE`) y el perfil. **Sin preselección**: el selector arranca en «Elegí tu país» y no adivina por el navegador. En el registro va junto al nombre de usuario.
  3. **Migraciones**: `0009_remove_usuario_tema` y `0010_usuario_pais`. La segunda agrega la columna nula, asigna a las cuentas existentes un país por rotación determinista `[AR, BR, US, ES, GB, PT, CN, MX][id % 8]` (CN a propósito: TMDB casi no tiene plataformas allí y ejercita el estado «no disponible») y la vuelve obligatoria. Las factories y el seed usan la misma rotación.
  4. **Error**: `country_invalid` (400 (Bad Request)) cuando el país falta o no está en la lista, en el registro, el alta con Google, el perfil y el endpoint de plataformas; si falta en el registro, `required`.
  5. **Docs**: doc 02 (RF de alta y perfil, CU-001, CU-005, CU-006), doc 03 (`Usuario.pais` y JSON), doc 04 (registro, perfil, 6.2), doc 05 (A-01, A-05, A-06, P-01, P-02), spec `error-contract`.
- **Revisión con Gonza**: los cambios a los docs 02 y 03 se revisan con él.
- **Archivos afectados**: `backend/usuarios/{models.py,serializers.py,paises.py,adapter.py,admin.py,factories.py}`, `backend/usuarios/migrations/{0009_remove_usuario_tema.py,0010_usuario_pais.py}`, `contracts/{enums.json,error-codes.json,openapi.yaml}`, `frontend/components/CountrySelect.tsx`, `frontend/app/{(public)/register,complete-signup,profile}/page.tsx`, `docs/i18n/copia-propuesta.csv`, los docs 02 a 05 y `openspec/specs/error-contract/spec.md`.

## 18/10/2026 — Plataformas donde ver una producción (watch providers) y atribución a JustWatch

- **Fecha**: 18/10/2026
- **Descripción**:
  1. **Endpoint**: `GET /api/catalogo/{movie,tv}/{id_tmdb}/providers/?pais=XX`, público. El país lo manda el cliente (no sale de la sesión) para que siga siendo cacheable. Responde `{pais, enlace, suscripcion, gratis, alquiler, compra}`; `gratis` une `free` y `ads` de TMDB. Sin `pais` válido: 400 (Bad Request) `country_invalid`, sin llamar a TMDB.
  2. **Solo en Redis**: no hay tabla. Se cachea por título (una respuesta de TMDB trae todos los países) con TTL de 12 horas y respaldo de 7 días (`RESPALDO_TTLS`, en vez de los 30 del resto).
  3. **Ficha**: bajo los géneros, la línea «Stream or rent [logos] N options in {país}» (en español, «Ver o alquilar … N opciones en {país}») abre un panel con Stream, Free, Rent y Buy. **Los logos no son enlaces** (TMDB no da enlaces por plataforma): hay un solo enlace «See all options on TMDB». Con sesión se usa el país de la cuenta; sin sesión, la región del navegador si está en la lista; sin ninguno, la sección no aparece. Si no hay datos: «Not available to stream, rent or buy in {país} yet.».
  4. **Atribución obligatoria**: los datos son de JustWatch y TMDB exige citarlos; el panel muestra «Data by JustWatch» con enlace a justwatch.com. No debe quitarse.
  5. **Docs**: doc 02 (RF nuevo, CU-008), doc 03, doc 04 (5c), doc 05 (C-09), doc 06 (sección «Uso en FilmAI: Dónde verla») y los specs `title-page-ui`, `tmdb-endpoints` y `tmdb-cache`.
- **Archivos afectados**: `backend/catalogo/{cache.py,client.py,urls.py,views.py,services/plataformas.py,tests_plataformas.py}`, `backend/filmai/errores/catalogo.py`, `frontend/components/features/title/{WatchProviders.tsx,TitleView.tsx}`, `docs/i18n/copia-propuesta.csv` (`title.providers.*`), los docs 02 a 06 y los specs `title-page-ui`, `tmdb-endpoints`, `tmdb-cache`.

## 18/10/2026 — Pendiente: sumar el uso del país a los Términos y Condiciones

- **Fecha**: 18/10/2026
- **Descripción**: el país de la cuenta se usa para mostrar las plataformas disponibles en la ficha (el backend pide a TMDB los datos de todos los países y filtra por el país del usuario; el país no se envía a TMDB). Ese uso **debe quedar listado en los Términos y Condiciones**, y hoy **no lo está**: la sección 9 («Datos personales» / «Personal data») enumera correo, fecha de nacimiento y género, y la sección 7 («Contenido de terceros») nombra a TMDB pero no a JustWatch. Falta sumar el país a la sección 9 y, conviene, la atribución a JustWatch a la sección 7, en español e inglés.
- **Dónde está el texto**: en el código, `frontend/content/legal/terms.es.md` y `terms.en.md` (versionados para que los revise un abogado; se muestran en `/terms`); en los docs solo se lo referencia (doc 02, CU-001, «Términos y Condiciones (12/10/2026)»; doc 04, sección 5f «Implementación»). Al editarlo, pasar el cambio por el abogado y revisar si hay que volver a pedir la aceptación.
- **Estado**: pendiente. No se tocó el texto legal en este cambio (alcance solo documentación).
- **Archivos afectados**: `docs/decisiones.md` (a futuro, `frontend/content/legal/terms.{es,en}.md`).

## 18/10/2026 — Tema claro descartado: la app es solo oscura y se elimina `Usuario.tema`

- **Fecha**: 18/10/2026
- **Descripción**: el tema oscuro es parte de la identidad de FilmAI, así que se descartó el tema claro (antes quedaba como opción futura «Apariencia»). Se eliminó `Usuario.tema` del modelo (migración `0009_remove_usuario_tema`), de la API de Preferencias y del contrato, y de la doc: doc 03 (texto y JSON), doc 04 (Preferencias sin «Apariencia», 7.1, contraste), doc 05 (P-03, P-04), `PRODUCT.md` y el spec `profile-ui` (no hay selector ni campo). Una cuenta con tema guardado simplemente pierde el dato.
- **Archivos afectados**: `backend/usuarios/{models.py,cuenta.py,serializers.py}`, `backend/usuarios/migrations/0009_remove_usuario_tema.py`, `contracts/openapi.yaml`, `frontend/app/settings/page.tsx`, `docs/03_*`, `docs/04_Lineamientos_UI.md`, `docs/05_Plan_de_Desarrollo.md`, `PRODUCT.md`, `openspec/specs/profile-ui/spec.md`.

## 18/10/2026 — Esqueletos de carga estáticos (sin shimmer ni `animate-pulse`)

- **Fecha**: 18/10/2026
- **Descripción**: los esqueletos de carga ya no pulsan ni brillan: se quitó `animate-pulse` (y la constante `PULSO`) de Home, MediaCard, filas, Listas, detalle de lista, Mis reseñas y la ficha. Quedan como bloques de color fijo. Doc 04 (ficha, 6.5 y 7.1), doc 05 (Q-03) y el spec `title-page-ui` lo reflejan. Además, la barra dorada de navegación (`NavigationProgress`) perdió el resplandor (`box-shadow`): queda una línea lisa de 3 px (18/10/2026, `frontend/components/NavigationProgress.tsx`).
- **Archivos afectados**: `frontend/components/features/{HomeHero,MediaCard,MediaRow}.tsx`, `frontend/components/features/lists/{ListDetailView,ListsView}.tsx`, `frontend/components/features/reviews/MyReviewsView.tsx`, `frontend/components/features/title/{ReviewsSection,TitleView}.tsx`, `docs/04_Lineamientos_UI.md`, `docs/05_Plan_de_Desarrollo.md`, `openspec/specs/title-page-ui/spec.md`.

## 18/10/2026 — Favicon dorado propio (reemplaza icons8)

- **Fecha**: 18/10/2026
- **Descripción**: el favicon pasa a ser la «F» dorada (`#f5c518`) sobre fondo oscuro, en `frontend/public/favicon.svg` (un `rect` de fondo con esquinas redondeadas y un `path` con la letra) y `frontend/public/favicon.jpeg` para el ícono de Apple. Se declara en `app/layout.tsx` (`icons.icon` y `icons.apple`) y reemplaza `icons8-movies-32.png`, que se eliminó. `PRODUCT.md` y el doc 04 (7.1) lo reflejan.
- **Archivos afectados**: `frontend/public/{favicon.svg,favicon.jpeg}`, `frontend/public/icons8-movies-32.png` (eliminado), `frontend/app/layout.tsx`, `PRODUCT.md`, `docs/04_Lineamientos_UI.md`.

## 18/10/2026 — Se elimina la carpeta `odd/tasks`

- **Fecha**: 18/10/2026
- **Descripción**: la carpeta `odd/tasks/` (con `modulo-6-resenas-admin.md`) estaba expirada y se eliminó. Ningún doc ni spec la referencia; las tareas vigentes están en el doc 05.
- **Archivos afectados**: `odd/tasks/modulo-6-resenas-admin.md` (eliminado).

## 18/10/2026 — Fecha de agregado en las listas: ícono de «agregar a lista» y fecha

- **Fecha**: 18/10/2026
- **Descripción**: la fecha sola no dejaba claro que era la de agregado a la lista. Se compararon cuatro opciones en el canvas (ícono de reloj, prefijo «Added», ícono de «agregar a lista» y fecha relativa) y Marcos eligió el **ícono de «agregar a lista» seguido de la fecha** numérica compacta (`18/10/2026` en español, `10/18/2026` en inglés). El ícono es `ListPlus` de lucide y la etiqueta, para el tooltip y los lectores de pantalla, es «Agregada a esta lista el {fecha}» / «Added to this list on {date}» (`common.media.addedOnLabel`). Se borraron las otras propuestas del canvas y el control `fecha` de «List detail».
- **Archivos afectados**: `frontend/components/features/MediaCard.tsx`, `docs/i18n/copia-propuesta.csv`, `frontend/messages/`, `frontend/tests/{media-card,list-detail-view}.test.tsx`, docs 02 (CU-009) y 04, canvas («List detail», escritorio y celular).

## 18/10/2026 — El país quedaba repartido entre el PR #113 y el #114

- **Fecha**: 18/10/2026
- **Descripción**: el CI del PR #114 falló en `test_exportacion_reproducible_coincide_con_el_contrato_versionado`: `contracts/enums.json` traía `paisCodes`, pero `contrato_enums()` no lo generaba (el arreglo había quedado por error en el #115). Al revisar el #113 solo, que nunca corrió el CI porque su base (`chore/limpieza-favicon`) no dispara el workflow, aparecieron más partes en el PR equivocado: `country_invalid` no estaba en el catálogo de errores (un país inválido daba 500 (Internal Server Error) en vez de 400 (Bad Request)), `catalogo/test_admin.py` seguía mandando `tema` y `openapi.yaml` ya incluía los endpoints de plataformas del #114. Se corrigió en el #113 y se llevó hacia arriba con merges; en el #114 se conserva su `openapi.yaml`, con los endpoints de plataformas.
- **Lección**: en una pila de PRs, cada rama tiene que pasar la suite sola. Si la base de un PR no dispara el CI, correr la suite a mano antes de apilar encima.
- **Archivos afectados**: `backend/listas/identidades.py`, `backend/filmai/errores/catalogo.py`, `backend/catalogo/test_admin.py`, `contracts/openapi.yaml`, `docs/decisiones.md`.

## 18/10/2026 — Revisión automática de PRs con PR-Agent y DeepSeek

- **Fecha**: 18/10/2026
- **Descripción**: se reinstaura una revisión automática de PRs, ahora informativa (no bloquea el merge; el gate sigue siendo el CI). Usa PR-Agent (imagen Docker fijada en `0.48.0-github_action`) con `deepseek-flash` (alias de DeepSeek V4.1 Flash) vía la API de DeepSeek (`https://api.deepseek.com`, secret `DEEPSEEK_API_KEY`, pago: USD 0,15–0,30 por millón de tokens de entrada sin caché y 0,60–1,20 de salida, según el horario). Corre en `opened`, `reopened`, `ready_for_review` y `synchronize`; omite drafts, bots y forks; cancela la ejecución previa del mismo PR; tiene permisos mínimos (`contents: read`, `pull-requests: write`, `issues: write`). Hace review y sugerencias en línea, sin describe.
- **Descartado**: OpenCode Zen. Se probó en el PR #117 y sus modelos `-free` (DeepSeek y MiMo) rechazan las llamadas por API con «OpenCode's free tier can only be used from within OpenCode», aunque la documentación los liste como gratuitos.
- **Por qué**: el 18/09/2026 se desactivó AI Review por 93 % de falsos positivos sin contexto del proyecto. Esta vez el contexto (stack, convenciones i18n, qué no reportar) vive en `.pr_agent.toml` y se ignoran archivos generados. Si vuelve el ruido, desactivar el workflow.
- **Archivos afectados**: `.github/workflows/pr-review.yml`, `.pr_agent.toml`, `AGENTS.md` (sección 8), `docs/decisiones.md`.

## 18/10/2026 — Textos de la interfaz: `traducciones/`, sin catálogo transitorio y sin claves muertas

- **Fecha**: 18/10/2026
- **Descripción**: se cierra la deuda de multiidioma que dejaba la copia transitoria (OT-70) y se ordena dónde viven los textos.
  - **`docs/i18n/` pasa a `traducciones/` (raíz del repo)**. `docs/` guarda documentación del proyecto y de la facultad; estos archivos son datos que leen el generador de catálogos y los tests (`generate.py`, `i18n-catalogs.test.ts`, `test_reservados.py`). El montaje de `docker-compose.yml` pasa a `./traducciones:/traducciones:ro`. Las entradas anteriores de este archivo siguen citando `docs/i18n/`: es historia y no se reescribe.
  - **Se elimina `ot70-catalogo-transitorio.csv` y el grupo `legacy.*`**. De sus 77 filas, 33 las usaba el código y 44 no: se borraron. De las 33: 9 pasan a una clave que ya existía con el mismo texto (`auth.landing.description`, `nav.main.profile`, `nav.main.settings`, `nav.account.deactivateConfirmTitle`, `nav.account.deactivate`, `common.passwordReset.backToLogin`, `common.fields.passwordConfirm`, y las dos unificaciones de abajo); 4 reutilizan una clave del canvas cuyo texto curado pasa a ser el aprobado el 08/10/2026; 20 son claves nuevas en `claves-extra.csv` (`settings.*`, `auth.confirmation.loading`, `auth.newPassword.*`). La columna `fuente` del CSV viejo, con rutas que ya no existían, desaparece con él.
  - **Los parches de texto salen de `generate.py`**. El generador corregía a mano el voseo («su cuenta» → «tu cuenta») y el `*` de la ayuda de contraseña. Ahora esas correcciones están escritas en el CSV, que es la única fuente de verdad. También se quita la clave `common.brand`, que sembraba el generador y nadie leía.
  - **`copia-propuesta.csv` pasa a `claves-extra.csv`** y sus columnas `es_propuesto`/`en_propuesto` a `es`/`en`: «copia» calcaba «copy» y «propuesta» ya no era cierto (las 195 filas estaban aprobadas). Se mantiene separado de `claves.csv`: `claves.csv` es la trazabilidad del canvas (`es_original`, `pantallas`, `grupo`) y `claves-extra.csv` son textos que el canvas no trae (códigos de error, nombres reservados, pantallas heredadas).
- **Colisiones con el canvas (Settings)**: el canvas tenía claves propias para las ayudas de notificaciones y la advertencia de baja, pero la app usaba los textos aprobados («Preferencia para futuros correos…», porque hoy no se envía ningún correo; y la baja con «Asegurate de querer dar de baja la cuenta…»). La pantalla usa ahora la clave del canvas y el texto aprobado quedó en `es_curado`/`en_curado`; el original se conserva en `es_original`.
- **Unificaciones de texto**: el botón de baja pasa de «Dar de baja cuenta» a «Dar de baja la cuenta» (`nav.account.deactivateTitle`) y la pantalla de nueva contraseña de «Nueva contraseña» a «Contraseña nueva» (`common.password.newLabel`, la que ya usa Perfil). Los docs 02 y 04 se ajustaron.
- **Claves sin uso, borradas**: 38 filas de `claves.csv` (34 claves) y `settings.language.updated`. Se verificó cada una contra el código de `frontend/` y `backend/`: la clave completa, el namespace más la hoja, y las construidas con plantillas. Eran: la pantalla de acceso a documentación (`auth.adminAccess.*`; la arma Django con su propia copia en `backend/filmai/documentation.py`), el selector de tema (la app es solo oscura desde el 15/10/2026), la paginación numerada y el carrusel con «ver más» (la búsqueda carga más resultados y las filas usan `previousRowLabel`/`nextRowLabel`), duplicados de textos que hoy salen de `errors.codes.*` (`termsRequiredError`, `confirmMismatch`), la fila «Community reviews» y el aviso de calificar desde la Home (no se implementaron), y plurales de contadores que no se muestran. `home.recommendation.promptTitle` (acceso al chatbot) se conserva con estado `chatbot`, junto con las otras 21 filas del chatbot. No se tocaron `errors.codes.*` ni `enums.*`: están atados al contrato con el backend.
- **Skills para Claude Code**: `.claude/skills` pasa a ser un enlace simbólico versionado a `../.agents/skills` (antes estaba en `.gitignore`), porque el equipo trabaja en Linux/WSL. `skills-lock.json` se queda en la raíz: la herramienta `npx skills` lo busca ahí.
- **Archivos afectados**: `traducciones/` (movida desde `docs/i18n/`), `frontend/scripts/i18n/generate.py`, `frontend/app/{layout.tsx,profile/layout.tsx,settings/layout.tsx,settings/page.tsx,confirm-email/[key]/page.tsx,reset-password/[uid]/[token]/page.tsx}`, `frontend/messages/`, `frontend/i18n/enums.json` (solo formato), `frontend/tests/{i18n-catalogs,i18n-metadata,i18n-render,profile}.test.*`, `frontend/e2e/{i18n-flows,i18n-locale,preferencias,hotfix-perfil}.spec.ts`, `backend/listas/test_reservados.py`, `docker-compose.yml`, `.gitignore`, `.claude/skills`, `AGENTS.md`, `README.md`, docs 02 y 04, specs `i18n-core` y `emails`.
- **Verificación**: Vitest 375 tests, Django 873 tests, Ruff, ESLint, Prettier, `generate.py --check`, `npm run i18n:check` y `next build` sin errores. Playwright: de 4 specs afectadas, 16 recorridos pasaron y 3 de `i18n-flows` fallaron una vez con los 4 specs en paralelo (timeouts por compilación bajo demanda) y pasaron al repetirlos de a uno.
