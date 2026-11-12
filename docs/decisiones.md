# Decisiones y Cambios — FilmAI

Registro de decisiones de diseño y cambios relevantes del proyecto, ordenado por tema y, dentro de cada tema, por fecha.

El 11/11/2026 se condensó: de 323 entradas quedaron los hitos que explican o justifican el estado actual. Se sacaron las decisiones revertidas o reemplazadas (cuando ayudan a entender el presente quedan en una línea «Antes:»), los ajustes menores de interfaz, los logs de verificación y los detalles de cada PR. La versión completa sigue en el historial de git (commit `8367861`).

**Formato de una entrada nueva**: agregarla al final de la sección de su tema, con título `### DD/MM/AAAA — Título breve`, una descripción (qué se decidió, por qué, alternativas descartadas y riesgos aceptados) y una línea `Archivos:` con los principales.

## Índice

1. [Proceso y herramientas](#proceso-y-herramientas)
2. [Infraestructura](#infraestructura)
3. [Modelo de datos](#modelo-de-datos)
4. [Cuentas y autenticación](#cuentas-y-autenticación)
5. [Perfil](#perfil)
6. [Catálogo y TMDB](#catálogo-y-tmdb)
7. [Búsqueda y recomendaciones](#búsqueda-y-recomendaciones)
8. [Listas](#listas)
9. [Reseñas y calificaciones](#reseñas-y-calificaciones)
10. [Chatbot](#chatbot)
11. [Multiidioma](#multiidioma)
12. [Correos](#correos)
13. [Interfaz](#interfaz)
14. [Seguridad](#seguridad)
15. [Calidad y tests](#calidad-y-tests)

---

## Proceso y herramientas

### 10/09–18/10/2026 — Grafo de conocimiento y skills compartidas

graphify (`graphify-out/`, versionado) se actualiza al cerrar cada tarea, antes del commit, para que los agentes consulten la arquitectura sin lecturas masivas. `.agents/skills/` es la única fuente de skills para todos los agentes, para evitar copias que divergen; desde el 18/10 `.claude/skills` es un enlace simbólico versionado a esa carpeta.
Archivos: `AGENTS.md`, `graphify-out/`

### 15/09–11/11/2026 — Revisión de PRs: el CI es la única puerta

- **18/09**: se eliminó AI Review (93 % de falsos positivos, sin contexto del proyecto) y se desinstaló CodeRabbit (prueba vencida).
- **21/09**: se dejó la revisión humana entre Marcos y Gonza; en módulos separados agregaba espera sin hallazgos. Cada uno mergea con el CI en verde, con merge commit (el squash rompía los PRs apilados), y le deja al otro un resumen. El peso pasa a los tests, a las specs y a este registro.
- **18/10**: vuelve una revisión automática solo informativa, PR-Agent con DeepSeek, con el contexto del proyecto en `.pr_agent.toml` (lo que le faltaba a AI Review). Se descartó OpenCode Zen: su capa gratuita rechaza llamadas por API. Desde el 04/11, como máximo 3 pasadas por PR.
- **06/11–11/11**: GitHub bloqueó la cuenta dueña del repo por facturación al vencer el beneficio estudiantil y ningún job arrancaba; se desactivaron `CI` y `PR Review` y la puerta fue la verificación local con los pasos de `ci.yml`. El 11/11 se recuperó el beneficio y se reactivaron.

Archivos: `.github/workflows/ci.yml`, `.github/workflows/pr-review.yml`, `.pr_agent.toml`, `AGENTS.md`

### 08/10–13/10/2026 — Rama única `develop`

Todo el trabajo pasó a una sola rama de integración, `develop`: se integraron las entregas sueltas del multiidioma y se borraron 47 ramas y 16 worktrees después de comprobar que su contenido ya estaba en `develop`. El CI corre también en `develop/**`, porque los PRs hacia esas ramas se mergeaban sin ruff, tests ni build. Lección del 18/10: si la base de un PR apilado no dispara el CI, correr la suite a mano antes de apilar encima.
Archivos: `.github/workflows/ci.yml`

### 15/10–18/10/2026 — Los docs dicen lo que hace el código

Los docs 02 y 03 se revisaron contra el código en pair programming entre Marcos y Gonza, con un criterio acordado: la documentación describe lo que hace el código. Quedaron como mejora futura el respaldo del catálogo desde la base, el aviso al administrador si la sync falla entera y el efecto real de «Perfil público».
Archivos: `docs/02_Especificación de Requerimientos.md`, `docs/03_Modelos de Datos y de Diseño.md`

### 24/10–02/11/2026 — Hallazgos verificados y solo Marcos y Gonza como autores

Las revisiones con subagentes son de solo lectura, y cada hallazgo (igual que cada comentario de PR-Agent, que en #133 a #136 fueron mayormente falsos positivos) se verifica contra el código y se acuerda antes de aplicarlo. Commits y PRs no llevan atribución a IA: `.claude/settings.json` la vacía y `.husky/commit-msg` la borra. El 02/11 se reescribió la historia de las ramas con `git filter-repo` (árboles verificados idénticos) para quitar a `Copilot` y `github-actions[bot]` como contributors; AGENTS.md prohíbe aceptar sugerencias de bots con el botón de GitHub.
Archivos: `.husky/commit-msg`, `AGENTS.md`

### 04/11/2026 — Chatbot repartido en Motor y Canal

El chatbot se cortó en `responder()`, su único punto de contacto. **Motor (Gonza)**: búsqueda semántica, tools, perfil, anonimizador, orquestador y set dorado. **Canal (Marcos)**: persistencia, vista SSE, panel e historial. `chatbot/eventos.py` fija el contrato: `responder()` emite `Estado` y `Texto`, al final un `Resultado(texto, tarjetas)` o `ErrorDelTurno`, y no guarda nada (tiempo máximo, candado y guardado son de la vista). `orquestador_falso.py` cumple el contrato con un guion para que el Canal no espere al Motor. Descartado: repartir en backend y frontend, porque los dos habrían tocado la vista y el contrato SSE.
Archivos: `backend/chatbot/eventos.py`, `backend/chatbot/orquestador_falso.py`

### 11/11/2026 — Registro condensado y pendientes en el plan

Este archivo se condensó (ver la introducción). `docs/auditoria-seguridad-resumen.md` se borró porque la auditoría está cerrada; lo que seguía abierto (lo de «al desplegar» y las decisiones de seguridad sin tomar) pasó a la sección «Pendientes (11/11/2026)» de `docs/05_Plan_de_Desarrollo.md`, que ordena los 9 pendientes del proyecto por importancia y viabilidad e incluye notas para la población masiva de la base.
De paso se corrigió en `traducciones/guia.md` un párrafo que daba al chatbot por no implementado.
Archivos: `docs/decisiones.md`, `docs/05_Plan_de_Desarrollo.md`, `traducciones/guia.md`

---

## Infraestructura

### 14/09/2026 — Celery, entrypoint parametrizable e imagen pgvector

`entrypoint.sh` termina en `exec "$@"` para que cada servicio elija su comando, y las migraciones quedan detrás de `RUN_MIGRATIONS` (en `false` en el worker, así migra un solo contenedor). La base pasa a `pgvector/pgvector:pg16` (Debian; el tag Alpine no existía). Redis separado por rol: DB 0 caché de TMDB, DB 1 broker, DB 2 resultados, y serialización solo JSON. En desarrollo el worker corre con `watchmedo auto-restart`, porque Celery no recarga código y editar una tarea seguía ejecutando la versión vieja sin avisar.
Archivos: `backend/entrypoint.sh`, `docker-compose.yml`, `backend/filmai/celery.py`

### 12/09–30/09/2026 — OpenAPI como contrato único

OpenAPI con Swagger UI en `/api/docs/` es el contrato de la API; URLs con barra final y errores consistentes para 404 (Not Found), 405 (Method Not Allowed) y 429 (Too Many Requests). La documentación quedó restringida a staff para no exponer la API (ver «Acceso de staff a la documentación» en Seguridad). El contrato SSE del chat, que drf-spectacular no cubre, se versiona aparte en `contracts/sse-chat.md`.
Archivos: `backend/filmai/urls.py`, `backend/filmai/documentation.py`

### 24/10/2026 — Docker de desarrollo con techo de memoria

WSL se colgó tres veces llenando el swap. Celery corre con `--concurrency=2` y recicla hijos de más de 300 MB; cada servicio tiene `mem_limit` igual a `memswap_limit`, así el kernel mata dentro del contenedor y no traba WSL, y no hay `restart: unless-stopped`, para evitar reinicios en ciclo.
Archivos: `docker-compose.yml`

### 26/10/2026 — Next 15.5.28 y Django 5.2 LTS por seguridad

Next 15.5.28 corrige una ejecución remota de código en el optimizador de imágenes; se quedó en la serie 15 para no mezclar el salto a 16 con un parche. Django pasa a 5.2 LTS porque la 5.1 dejó de recibir parches. allauth queda con versión exacta porque se usa una API interna.
Archivos: `backend/requirements.txt`, `frontend/package.json`

### 06/11–07/11/2026 — Encolado en Celery: dependencias de Redis

`celery` sin extras dejaba instalar kombu 5.7, que exige `redis>=6.4` y `packaging` solo en su extra `[redis]`: con `redis<6` ninguna tarea llegaba al worker y no se veía ningún error. Se declara `kombu[redis]>=5.7,<6` con `redis>=6.4,<7`; se descartó `celery[redis]`, que bajaba Celery a 5.3.1. Un test corre el chequeo de versión de kombu, porque los demás simulaban `.delay()`.
Archivos: `backend/requirements.txt`

---

## Modelo de datos

### 13/08/2026 — Un único `Usuario` y unicidades en la base

Se eliminaron `Persona` y `Administrador`: queda un solo `Usuario` como `AUTH_USER_MODEL`, y los administradores son `is_staff`/`is_superuser` del Django Admin (la herencia multitabla era especulativa y chocaba con el modelo de usuario). `is_active` se deriva de `estado` (pendiente → activa → baja), única fuente de verdad. Unicidades en la base: `(id_tmdb, tipo)` (TMDB repite ids entre películas y series), `(usuario, produccion)` en calificaciones, `(usuario, nombre)` en listas y `(lista, produccion)` en ítems. La reseña es `OneToOne` con la calificación y `Mensaje.texto` es `TextField`.
Archivos: `backend/usuarios/models.py`, `backend/catalogo/models.py`

---

## Cuentas y autenticación

### 22/08/2026 — dj-rest-auth + django-allauth

Registro local y Google OAuth con `dj-rest-auth` y `django-allauth`, para no reimplementar OAuth ni la verificación de correo. Contraseñas con bcrypt (RNF #2).
Archivos: `backend/filmai/settings.py`, `backend/usuarios/adapter.py`

### 24/08/2026 — Login sin enumeración, confirmación y recuperación

El login muestra un único mensaje ante cualquier fallo de credenciales. El enlace de confirmación vale 24 horas (allauth solo admite días enteros; se descartó un token propio) y la vista distingue `expirado`, `invalido` y `ya_confirmada`. Recuperación: la misma respuesta exista o no la cuenta, solo las activas reciben correo, el enlace dura 1 hora y caduca al cambiar la contraseña; hasta 5 pedidos diarios por correo y, desde el 28/10, 10 por hora por IP. Los límites usan Redis en todos los entornos.
Archivos: `backend/usuarios/views.py`, `backend/usuarios/serializers.py`

### 26/08/2026 — Google OAuth en dos pasos

«Ingresar» abre el selector de Google; «Registrarse» pide primero los datos faltantes y después Google. El `id_token` es de un solo uso, así que el completado pide uno nuevo. Datos faltantes y correo duplicado se validan antes de `complete_social_login`, que con auto-signup puede crear el usuario y dejar filas huérfanas. Si el correo ya tiene cuenta local se pide ingresar con contraseña: no se vinculan cuentas automáticamente. Google solo precarga nombre y apellido; después manda el perfil de FilmAI. Desde el 15/10 `/complete-signup` sigue el canvas y su error se guarda como código, para traducirlo si cambia el idioma.
Archivos: `backend/usuarios/serializers.py`, `frontend/lib/google-auth.ts`, `frontend/app/complete-signup/page.tsx`

### 11/09/2026 — Recursos iniciales del usuario en una transacción

Las listas predeterminadas y el chat se crean en la misma transacción que el `Usuario`: si algo falla, no queda una cuenta incompleta. Un chat por usuario (`Chat.usuario` único). `reparar_recursos_usuarios` repara datos viejos.
Archivos: `backend/usuarios/signals.py`, `backend/usuarios/provisioning.py`

### 12/10/2026 — Aceptación de los Términos y Condiciones

Crear una cuenta (local o con Google) exige aceptar los Términos: `Usuario.fecha_aceptacion_terminos` la fija el servidor, y las cuentas anteriores quedan en nulo porque no se inventa una aceptación. El texto legal vive en Markdown por idioma, fuera del catálogo de traducciones, para que un abogado lo revise sin tocar código.
Archivos: `backend/usuarios/models.py`, `frontend/content/legal/`

### 16/10/2026 — Renovación silenciosa de la sesión

El frontend nunca usaba la cookie `refresh`: a las 8 horas vencía `access` y la app sacaba al usuario sin explicación. Ahora, ante un 401 (Unauthorized), `apiFetch` llama a `POST /api/auth/token/refresh/` y repite el pedido una vez; varios 401 simultáneos comparten la renovación porque el backend rota la `refresh`. La sesión dura 7 días desde el último uso; si no se puede renovar, se avisa «Tu sesión venció» y se lleva al login con `?next=`. Descartado: el token en `localStorage` con `Authorization: Bearer`, porque un XSS podría robarlo. Antes (26/09): access de 8 horas y refresh de 7 días sin renovación.
Archivos: `frontend/lib/api.ts`, `frontend/components/AccountProvider.tsx`

### 20/10/2026 — Las cuentas pendientes vencen (F4)

Registrar un correo ajeno lo bloqueaba para siempre. Ahora una cuenta pendiente libera correo y nombre al vencer el enlace (al registrar encima y con una tarea diaria); el plazo no se renueva al reenviar, y el correo avisa que no se abra el enlace si uno no se registró. Riesgo aceptado: durante hasta 48 horas, si la víctima confirma, la cuenta queda con la contraseña del atacante. Recomendación para el despliegue: elegir la contraseña al confirmar el correo.
Archivos: `backend/usuarios/pendientes.py`

### 20/10/2026 — JWT con 10 segundos de tolerancia de reloj

El reloj de WSL2 retrocedía y un token recién emitido quedaba «en el futuro» (tests intermitentes; pasaría en producción con relojes desincronizados). `LEEWAY` de 10 s no debilita un access de 8 horas.
Archivos: `backend/filmai/settings.py`

### 28/10/2026 — Nombres de usuario reservados (issue #137)

Registro, alta con Google y cambio de nombre rechazan nombres que imitan al equipo (`admin`, `root`, `soporte`, `filmai`…), también con dígitos, números como letras («Adm1n») o prefijos y sufijos decorativos, con `username_not_allowed` y sin revelar la lista. Solo evita la suplantación: los permisos dependen de `is_staff`/`is_superuser`.
Archivos: `backend/usuarios/validators.py`

### 07/11/2026 — Fecha de nacimiento con el formato del idioma

El `<input type="date">` nativo ordena día y mes según el locale del navegador, y `lang` no lo cambia. `DateField` (máscara y calendario) usa DD/MM/AAAA en español y MM/DD/YYYY en inglés, y envía el ISO armado con la fecha local (`toISOString()` daba el día siguiente a la noche en UTC−3). Nuevo código `date_inexistent` para fechas como 31/02. El máximo de hoy menos 13 años pasó al calendario. Descartado: tres cajas día/mes/año y un calendario propio.
Archivos: `frontend/components/access/DateField.tsx`, `frontend/lib/format.ts`

---

## Perfil

### 24/09/2026 — Perfil propio y contraseña que revoca sesiones

`GET/PUT /api/profile/`; el nombre de usuario es único sin distinguir mayúsculas también en PostgreSQL, y el conflicto da 409 (Conflict). Cambiar o restablecer la contraseña invalida los JWT en todos los dispositivos: el token queda atado al hash vigente, también el refresh. El restablecimiento bloquea la fila para que un enlace no se consuma dos veces.
Archivos: `backend/usuarios/perfil.py`, `backend/usuarios/authentication.py`

### 24/09–08/10/2026 — Baja lógica sin pérdida de datos

La baja pone `estado = baja`, invalida los refresh y cierra la sesión de forma atómica; no borra listas, calificaciones, reseñas ni chats (se corrigió CU-007). Solo un administrador reactiva, y correo y nombre de usuario siguen ocupados. Las cuentas pendientes o dadas de baja se rechazan en todos los ingresos, y Google resuelve la cuenta por el `sub` vinculado, no por el correo. Desde el 26/10 sus reseñas se muestran anónimas (ver Reseñas).
Archivos: `backend/usuarios/cuenta.py`

### 26/09/2026 — Avatares predefinidos con ids estables

No hay subida de fotos. El catálogo de avatares tiene ids estables que no se reutilizan, así agregar archivos no cambia elecciones previas, y la API valida contra el mismo catálogo que el selector.
Archivos: `scripts/sync_avatars.py`, `backend/usuarios/avatares.py`

### 15/10/2026 — Perfil y Settings según el canvas

Se conserva «Perfil público» aunque el canvas no lo tiene, como base para que cada uno decida si sus reseñas son públicas; hoy se guarda sin efecto y lo dice, igual que las notificaciones por correo (mejoras futuras). En celular, como la barra inferior no tiene menú de cuenta, el Perfil lista los accesos y «Cerrar sesión».
Archivos: `frontend/app/profile/page.tsx`, `frontend/app/settings/page.tsx`

---

## Catálogo y TMDB

### 25/08/2026 — Catálogo híbrido

Trending, discover y search se sirven en vivo desde TMDB con caché en Redis; PostgreSQL guarda los datos del usuario y lo que necesita la búsqueda semántica. Se descartó la base como única fuente: sincronizar todo TMDB no escala. La sync con Celery es mantenimiento, no prerrequisito, y solo toca campos de TMDB.
Archivos: `backend/catalogo/services/`

### 08/09/2026 — Corpus semántico global y progresivo

El corpus es compartido y crece con lo que el catálogo sirve, no solo con lo que alguien listó o calificó: los datos personales reordenan por SQL, nunca recortan lo buscable. Se puebla con un seed diverso (contra el arranque en frío), con lo expuesto en los listados y con la cola larga a pedido.
Archivos: `backend/catalogo/services/`

### 12/09/2026 — Catálogo público

La API exige sesión por defecto, pero el catálogo se sirve sin autenticación (`AllowAny`), porque Home y Buscar muestran contenido sin sesión; así una cookie vencida no lo rompe. Límite de 60 pedidos por minuto.
Archivos: `backend/catalogo/views.py`

### 14/09–16/10/2026 — `materializar()` como único camino de escritura

Toda producción se guarda en `ProduccionAudiovisual` por `materializar()`, que reusan la sync, el seed, listas y reseñas; se identifica por `(id_tmdb, tipo)`. Propaga sus errores y quien la llama decide (la ficha nunca deja de mostrarse por un fallo propio). El INSERT va en `transaction.atomic()` para rescatar la fila tras el `IntegrityError` de una carrera, sin llamadas externas dentro de la transacción. `services/adapter.py` es la única traducción `movie`/`tv` ↔ `pelicula`/`serie`.

- **Ficha en segundo plano (14/10)**: la primera visita tardaba 1–1,6 s por la materialización síncrona. Ahora el detalle encola la tarea solo si la fila no existe o está incompleta; la tarea nunca lanza y la próxima visita reencola si falló (primera visita: 0,2–0,8 s). Calificar y agregar a una lista materializan por su cuenta.
- **Listados (16/10)**: para cumplir los docs 02 y 03, trending, now-playing, discover, search y browse encolan lo que no está fresco en la base, con una sola consulta por listado y cada título como mucho una vez cada 10 minutos (`cache.add`). Si encolar falla, el listado se responde igual.

Archivos: `backend/catalogo/services/materialization.py`, `backend/catalogo/services/adapter.py`, `backend/catalogo/tasks.py`

### 15/09/2026 — Las series se acreditan por `created_by`

En TV los directores son por episodio y `/tv/{id}/credits` no trae ningún `Director` (verificado con Breaking Bad). `_directores()` usa `created_by` en series, con respaldo al crew. Se corrigió antes de tener vectores reales porque los directores integran el texto embebido. Aceptado: muchas series quedan con `duracion` nula porque TMDB no trae `episode_run_time`.
Archivos: `backend/catalogo/services/materialization.py`, `backend/catalogo/client.py`

### 15/09–28/10/2026 — Sync nocturna con frescura según `/changes`

La sync llama a `materializar()` por ítem, porque un ítem de listado no trae cuatro de las seis secciones del texto embebido. Una fila se refresca si nunca se enriqueció (`fecha_enriquecimiento`), si su id figura en `/movie/changes` o `/tv/changes` del día, o a los 90 días como red de seguridad. Antes (15/09): ventana fija de 30 días, que re-pedía ~333 filas por noche sin saber si cambiaron. El refresco corre antes que el descubrimiento para no enriquecer dos veces lo que está en cartelera. `CELERY_TIMEZONE = TIME_ZONE` (sin eso las 3 AM eran UTC). El backfill de embeddings corre a las 4 AM con tope de 100 filas.

El 28/10 se volvió robusta: un listado caído ya no tumba toda la sync (cada uno en su `try`), los campos más largos que la columna se recortan según el `max_length` del modelo en vez de perder la ficha, el backfill renueva la fecha a mano porque `.update()` no dispara `auto_now`, y el relleno de traducciones guarda un cursor en la caché para no trabarse en las mismas filas. Pendiente: avisar al administrador si la sync falla entera (CU-021).
Archivos: `backend/catalogo/tasks.py`, `backend/catalogo/services/traducciones.py`, `openspec/specs/catalog-daily-sync/spec.md`

### 19/09/2026 — Seed del catálogo por género × década × tipo

Un corpus de éxitos del mes solo recomienda éxitos del mes. `manage.py seed_catalogo` recorre `/discover` en 210 combinaciones de género × década (desde 1970) × tipo por `vote_count.desc`, en round-robin sobre un orden barajado con semilla fija: si la corrida se corta, la cobertura queda pareja. Respeta la pared de 500 páginas (la 501 da 400 (Bad Request)) y es resumible sin estado, salteando lo fresco con el umbral de la sync. Medido: ~0,7 s por producción.
Archivos: `backend/catalogo/management/commands/seed_catalogo.py`, `openspec/specs/catalog-seed/spec.md`

### 08/10/2026 — TMDB según el idioma

El español pide `es-MX` (títulos de distribución latinoamericana) y el inglés `en-US`, con un cliente por idioma y `language` en la clave de Redis. Fuera del inglés, si título o sinopsis llegan vacíos se completan campo por campo con la versión inglesa y se marcan en `campos_en_ingles` (el frontend pone `lang="en"`). Las traducciones viven en `ProduccionTraduccion` (única por producción e idioma) y los géneros por id; la producción canónica y los embeddings siguen en inglés. Limitación aceptada: el orden por título usa el canónico.
Archivos: `backend/catalogo/client.py`, `backend/catalogo/services/traducciones.py`, `backend/catalogo/models.py`

### 16/10–18/10/2026 — Respaldo en Redis si TMDB no responde

Cada respuesta de TMDB se guarda además 30 días bajo `tmdb:respaldo:…` (7 días las plataformas). Si TMDB falla (error de servidor, conexión, tiempo agotado o límite de pedidos), se sirve esa copia con un aviso en el log como mucho cada 5 minutos por endpoint. Un 404 (Not Found) o un 400 (Bad Request) no usan el respaldo porque dicen algo cierto del pedido; la sync nocturna tampoco, para que el fallo se vea. Riesgo aceptado: lo que nunca se consultó sigue dando 502 (Bad Gateway). El respaldo desde la base quedó como mejora futura: no tiene todo TMDB, ni nota, votos, popularidad, relevancia de búsqueda o rankings de tendencias.
Archivos: `backend/catalogo/cache.py`

### 18/10–27/10/2026 — País de la cuenta y plataformas donde ver

`Usuario.pais` (ISO 3166-1 alfa-2, obligatorio, sin preselección) se pide en el registro, el alta con Google y el perfil; los 249 códigos están en `contracts/enums.json` (sin tabla) y los nombres salen de `Intl.DisplayNames`. `GET /api/catalogo/{movie,tv}/{id}/providers/` se cachea 12 h por título; la atribución «Data by JustWatch» es obligatoria por TMDB. Desde el 27/10 (issue #124, decisión de Gonza) exige sesión y usa el país de la cuenta, ignorando `?pais=`: sin sesión el país salía del navegador y terminaba en EE. UU. Solo se aceptan enlaces `https://` en el `link` de TMDB.
Archivos: `backend/usuarios/paises.py`, `backend/catalogo/services/plataformas.py`, `frontend/components/features/title/WatchProviders.tsx`

### 24/10/2026 — Parámetros validados y topes de llamadas a TMDB (F6 y F7)

`trending` llevaba parámetros sin validar al path de TMDB; ahora usa listas cerradas. Dos topes: 30 llamadas a TMDB por pedido (el máximo legítimo, Buscar en «Todo» y en español, son 20) y 300 por IP por minuto, contadas en el momento con un contador atómico en Redis (cobrarlas al final dejaba pasar pedidos en paralelo); fuera de un pedido HTTP no hay tope. F7: un id que TMDB no conoce ya no deja una producción vacía (se borra el cascarón sin datos) y uno fuera del rango de `integer` responde 400 (Bad Request) en vez de 500 (Internal Server Error).
Archivos: `backend/catalogo/presupuesto.py`, `backend/catalogo/services/materialization.py`

### 12/11/2026 — Títulos que TMDB borra: lápida (#180)

Para cumplir el tope de 6 meses de los términos de TMDB, la tarea de refresco vuelve a pedir cada producción. Cuando TMDB responde 404 (Not Found) dos noches distintas, la fila se borra si nadie la usa. Si alguien la calificó, la reseñó o la tiene en una lista, queda como lápida: solo `id_tmdb` y `tipo`, sin contenido de TMDB ni embedding, y `disponible_en_tmdb = False`. Solo cuenta el 404; cualquier otro error se reintenta. `Calificacion`, `Resena` y `Tiene` pasan a `PROTECT`, así que el borrado nunca se lleva lo que hizo un usuario, y la lápida vuelve si TMDB restaura el título. No aparece en recomendaciones, búsquedas ni en el chatbot. En las listas y en Mis reseñas se ve una tarjeta gris «Title no longer available», sin enlace, con la nota y la reseña, y se puede quitar o borrar como siempre. Alternativas descartadas: dejar la fila como está (no cumple los términos) y borrarla siempre (el usuario pierde su actividad). Lo decidió Gonza; se implementa en el PR 2 del cambio.
Archivos: `openspec/changes/tmdb-cumplimiento/design.md`, `openspec/changes/tmdb-cumplimiento/tasks.md`, `openspec/changes/tmdb-cumplimiento/specs/tmdb-compliance/spec.md`, `openspec/changes/tmdb-cumplimiento/proposal.md`, `docs/05_Plan_de_Desarrollo.md`

---

## Búsqueda y recomendaciones

### 08/09–14/09/2026 — Embeddings asíncronos, idempotentes y con invariantes en la base

La materialización guarda la producción y encola el embedding en Celery con `transaction.on_commit()`; la búsqueda solo usa los `ready`. Antes (25/08) se generaba en el pedido; se cambió para no bloquear el catálogo por Ollama y poder reintentar y hacer backfill. Las garantías van en Postgres porque escribe un worker que puede fallar a mitad de camino: `OneToOneField` con CASCADE, `CheckConstraint` que impide un `ready` sin vector e índice HNSW (`vector_cosine_ops`). `generar_embedding` resiste la entrega «al menos una vez» de Celery: no recalcula si no cambian `source_hash` ni `model_version`, reclama la fila con un `UPDATE … WHERE estado IN ('pending','failed')` y llama al proveedor fuera de la transacción. El texto canónico ordena los arrays antes de hashear, porque TMDB no garantiza el orden. Desde el 07/11 el encolado va con `robust=True`: si falla se registra y el backfill recupera el vector, en vez de devolver 500 (Internal Server Error).
Archivos: `backend/catalogo/tasks.py`, `backend/catalogo/models.py`, `backend/catalogo/services/embeddings.py`

### 30/09–13/10/2026 — Home de descubrimiento y «Recomendado para ti»

Un único selector Todo · Películas · Series arriba de las filas, el mismo de Buscar (se descartaron filas por tipo: largas en celular y siete pedidos al cargar). La ficha va en `/movie/[id]` y `/tv/[id]`, como la API y TMDB, que numera películas y series por separado. Recomendado toma los 3 géneros más repetidos entre las calificaciones de 7 o más y pide `discover` con OR y al menos 100 votos, sin lo que está en «Vistas». Medido contra TMDB: con AND quedaban 841 películas frente a 14.610, y sin mínimo de votos 9 de 20 tenían menos de 100. El tipo vive en la URL y se cambia con `history.replaceState`, porque `router.replace` volvía a pedir la página al servidor (más de 5 s).
Archivos: `backend/catalogo/services/recomendado.py`, `frontend/components/features/HomeView.tsx`

### 14/10/2026 — Buscar (C-06)

`/search` es una página, no un overlay. TMDB ignora género y nota en sus búsquedas por texto (verificado), así que el backend trae hasta 5 páginas por tipo en paralelo, filtra y pagina; si una página falla, falla todo, porque un conteo parcial pasaría por real. Se descartó `search/multi` porque mezcla personas. La nota exige al menos 50 votos y la grilla sin texto excluye News y Talk, que la llenaban de programas diarios.

- **Orden con texto**: TMDB ordena por relevancia y ponía arriba títulos con 0 votos. Se ordena por el mayor entre los votos y la popularidad × 100: los votos solos hundían los estrenos esperados y la popularidad sola es ruidosa. Con texto siempre se piden los primeros 100 de cada tipo.
- **Carga al bajar**: scroll infinito con un centinela (`IntersectionObserver`); `page` en la URL dice cuántas páginas se cargaron (tope 25) y al volver desde la ficha se restaura el scroll.
- **Año**: «A estrenar», los años del actual a 1990 y décadas de 1980 a 1900; «A estrenar» va sin el mínimo de votos, porque lo no estrenado no tiene.

Archivos: `backend/catalogo/services/browse.py`, `frontend/components/features/SearchView.tsx`, `frontend/lib/search.ts`

### 28/10/2026 — Latencia de Buscar medida, sin arreglo

Con la caché de Redis en frío, `browse/` y `search/` tardan entre 200 y 655 ms; en caliente, 18-25 ms. La variación se explica por la caché y la latencia de TMDB, no por el render ni la base. Se evaluaron subir el TTL, precalentar combinaciones y servir lo vencido mientras se refresca; se decidió no hacer nada hasta tener métricas de uso real.
Archivos: `backend/catalogo/cache.py`

### 04/11–07/11/2026 — Búsqueda semántica real (B-06) y carga anticipada del modelo

`generar_vector` llama a Ollama (`bge-m3`) y `buscar_semantico` a pgvector con `hnsw.ef_search = 100` (con 40, el default, pedir 50 devolvía 40 o menos sin avisar). Un reclamo en `processing` vence a los 5 minutos y el backfill lo devuelve a `pending` (Q-09). Error de diseño corregido el 05/11: si la carga del modelo superaba los 3 s, el chat cortaba y la búsqueda fallaba siempre; ahora el panel llama a `POST /api/chat/preparar/` al abrirse (202 (Accepted), encola `calentar_modelo`) y `buscar_semantico` espera hasta 20 s si el modelo no está cargado. Mediciones: consultas de 80 a 125 ms; backfill de 0,5 a 1 s por ficha; cargas en frío de más de 20 s con poca memoria. En desarrollo se usa el Ollama de Windows (la memoria sale de Windows y no del WSL); con Docker Desktop, `host.docker.internal:11434` llega directo. Antes (28/10): la medición daba ~1,9 s de carga en frío y un puente `alpine/socat` como única vía.
Archivos: `backend/catalogo/services/semantica.py`, `backend/catalogo/services/embeddings.py`, `docker-compose.yml`

---

## Listas

### 19/09/2026 — Resumen de listas y nombres permitidos

`GET /api/lists/` devuelve por lista los contadores (total, películas y series) y hasta cinco pósters recientes, para mostrar tamaño y composición sin cargar los ítems. Los nombres personalizados admiten solo letras Unicode, números y espacios (máximo 80), únicos por usuario sin distinguir mayúsculas.
Archivos: `backend/listas/views.py`, `backend/listas/serializers.py`

### 08/10/2026 — `Lista.clave` separa identidad de etiqueta

`Lista.clave` (`favoritos`, `pendientes`, `vistas`; nula en las personalizadas) identifica las listas del sistema, para traducir la etiqueta y para que un renombrado no rompa «calificada implica vista». Una personalizada con una etiqueta del sistema en cualquier idioma da 409 (Conflict) `list_name_reserved`. La migración `listas.0006` corta con un mensaje claro si hay datos inválidos y agrega `uq_lista_usuario_clave` y `ck_lista_tipo_clave` (predeterminada ⇔ con clave).
Archivos: `backend/listas/models.py`, `contracts/enums.json`

### 14/10/2026 — Entrar a Vistas saca de Pendientes

Cuando una producción entra a «Vistas» (por el botón o al calificar) sale de «Pendientes» en la misma transacción. Rige solo al entrar: volver a ponerla en Pendientes sigue permitido, y quitarla de Vistas no la devuelve. Descartado: prohibir estar en las dos listas (se pierde el «volver a verla»).
Archivos: `backend/listas/services.py`

### 15/10–18/10/2026 — Detalle, filtros y reordenamiento

`GET /api/lists/{id}/` con filtros y orden en el backend, porque con paginación por cursor el cliente solo ve lo cargado; las claves del cursor son únicas (nota × 1000 + id; título en el idioma efectivo con collation «C»). Los ítems traen la nota de TMDB (`null` sin votos). Reordenar: `Lista.orden` y `PUT /api/lists/order/` con el orden completo de las personalizadas; las predeterminadas quedan fijas adelante. En la interfaz se reordena con `@dnd-kit`: manija en escritorio, pulsación larga de 250 ms en celular (si el dedo se mueve antes, es scroll) y teclado; si el `PUT` falla, vuelve al orden anterior y avisa. Cada ítem muestra la fecha de agregado (CU-009).
Archivos: `backend/listas/views.py`, `frontend/components/features/lists/ListsView.tsx`, `frontend/components/features/lists/ListDetailView.tsx`

---

## Reseñas y calificaciones

### 21/09/2026 — Moderación en el Django Admin

Se modera con `activa=False`, sin borrar la fila; la calificación no se edita y el borrado físico desde el Admin está deshabilitado. Así no se rompe la relación 1:1 con la calificación y CU-016/CU-017 se cubren sin interfaz propia.
Archivos: `backend/catalogo/admin.py`

### 26/09/2026 — API de reseñas

Borrar la reseña elimina solo el texto y la calificación sobrevive, porque el texto es opcional: por eso hay `DELETE /api/reviews/{id}/texto/` y `DELETE /api/reviews/{id}/`. Una reseña moderada sale de la comunidad pero su autor la sigue viendo. El borrado del usuario es físico: `activa` solo significa «moderada por un administrador». `calificacion_promedio` es el `vote_average` de TMDB, sin mezclar notas propias. Se califica por `materializar()`, así se puede calificar desde un resultado que ninguna ficha abrió.
Archivos: `backend/catalogo/reviews.py`, `openspec/specs/reviews-api/spec.md`

### 30/09/2026 — Calificada implica vista

Calificar agrega a «Vistas» y borrar la calificación la saca; sacar de «Vistas» un título calificado da 409 (Conflict) y, tras confirmar, borra la calificación en la misma transacción (`?borrar_calificacion=true`). Se puede marcar como vista sin calificar. La escritura en `Tiene` pasa por `listas/services.py`, así listas sigue siendo su único dueño. Aceptado: si se marcó vista y después se calificó, borrar la nota la saca igual, porque `Tiene` no guarda el motivo. Antes (26/09): las reseñas no tocaban «Vistas»; se cambió porque la ficha podía mostrar una nota con el ojo apagado.
Archivos: `backend/listas/services.py`, `backend/listas/migrations/0004_calificadas_en_vistas.py`

### 14/10–15/10/2026 — Reseñas públicas y «Calificaciones y reseñas»

Las reseñas de la comunidad son públicas (leer sin sesión; escribir la pide), con orden por fecha o nota y filtro por nota. Los órdenes por nota usan la clave `valor × 10⁹ + id` para un cursor estable. `GET /api/reviews/mias/` filtra en el backend (`q`, `texto`, `clase`, `nota_min`/`nota_max`, `orden`) y devuelve `total` y `total_propias`, para distinguir «no calificaste nada» de «nada con estos filtros». La búsqueda sin acentos usa la extensión `unaccent` de Postgres sobre el título canónico y las traducciones. El origen de la miga de la ficha viaja en la URL (`?from=`), no en `sessionStorage`, que se pierde al recargar.
Archivos: `backend/catalogo/reviews.py`, `backend/catalogo/migrations/0007_unaccent.py`, `frontend/components/features/title/TitleView.tsx`

### 26/10/2026 — Las reseñas de cuentas dadas de baja se muestran anónimas

Entre dejarlas, anonimizarlas u ocultarlas se eligió anonimizar desde la API (nombre y avatar en `null`, «Usuario dado de baja»). Ocultarlas perdía contenido y cambiaba los conteos; dejarlas chocaba con el derecho de supresión de la Ley 25.326. Los datos se conservan (CU-007).
Archivos: `backend/catalogo/serializers_reviews.py`

### 28/10/2026 — El texto de una reseña moderada queda bloqueado (F10)

El autor levantaba la moderación borrando el texto y escribiéndolo de nuevo. Decisión de Marcos: mientras esté moderada, editar o borrar el texto responde 409 (Conflict) `review_moderated`; cambiar la nota sigue permitido y un admin que la reactiva devuelve el control. Descartado: que el texto nuevo nazca moderado (no hay cola de revisión en el Admin) y un modelo aparte que recuerde la moderación. Riesgo aceptado, a revisar al desplegar: quitar la calificación entera (CU-015 pide borrado permanente) y volver a calificar crea una reseña visible.
Archivos: `backend/catalogo/reviews.py`, `backend/catalogo/models.py`

---

## Chatbot

### 18/08/2026 — Retrieval: tool calling, pgvector y BGE-M3

El LLM consulta por tools (TMDB y búsqueda semántica); los gustos del usuario salen por SQL y entran anonimizados al prompt, sin vector store. Embeddings locales con BGE-M3 en Ollama: gratis y multilingüe (sinopsis en inglés, consultas en español); se descartó `nomic-embed-text` por ser solo inglés. pgvector en el PostgreSQL existente, `vector(1024)` con HNSW. Se embebe título, géneros, directores, elenco, keywords y sinopsis; nota, fecha, duración y tipo son filtros SQL. Motivo: personalizar sin pagar embeddings, cubrir consultas conceptuales que `discover` no expresa y evitar alucinaciones.
Archivos: `docs/05_Plan_de_Desarrollo.md`, `docs/06_TMDB_API_Referencia.md`

### 08/10/2026 — Arquitectura: DeepSeek, SSE sobre ASGI y contexto por SQL

DeepSeek por su API compatible con OpenAI, detrás de un adaptador que permite cambiar de proveedor desde el `.env`. SSE sobre ASGI desde el inicio, con el código sync envuelto en `sync_to_async`: bajo ASGI esperar al modelo no ocupa un worker. Pregunta y respuesta se guardan juntas al terminar, así una solicitud cancelada (CU-014) no deja nada. El contexto personal (gustos de 7 o más con extracto de reseña, disgustos de 4 o menos, vistas y favoritos) se arma por SQL en cada mensaje: precomputarlo exigía señales que las operaciones masivas no disparan y no ahorra frente a la latencia del LLM. Límites: 500 caracteres por mensaje, 10 mensajes de historial y 4 vueltas de tools.
Archivos: `backend/chatbot/orquestador.py`, `backend/chatbot/contexto.py`

### 09/10/2026 — Idioma del turno, tarjetas y sin cola

El idioma del turno se fija antes de abrir el stream y vale para tools y tarjetas; la prosa sigue el idioma en que escribió el usuario (desde el 06/11 lo detecta código, ver Multiidioma). `Mensaje.tarjetas` guarda lo que se mostró (máximo 3), sin FK ni materialización, para no pagar cuatro llamadas a TMDB por título dentro de un turno que debe cumplir el RNF #6. Sin cola de mensajes: complicaba la cancelación, el guardado al final y el límite.
Archivos: `backend/chatbot/views.py`, `backend/chatbot/models.py`

### 28/10/2026 — Revisión de la arquitectura y modelo `deepseek-flash`

Semántica con BGE-M3 en Ollama, previa medición de RAM (1,24 GB cargado); plan B, embeddings por API cambiando solo quién calcula el vector. Se descartó usar embeddings por API desde el inicio (otra key, cupo gratis de 1.000 pedidos por día, el texto va a Google). El chatbot es solo flotante (FAB y panel), sin página `/chat`. Se desarrolló con SDD en `openspec/changes/chatbot/` (ya archivado). Modelo: medianas de 1,8 s una respuesta simple y 3,2 s con una tool usando `deepseek-flash` con thinking apagado; con thinking o con `deepseek-v4-pro`, 1 a 2 s más. Thinking queda apagado explícitamente (la API lo trae encendido), configurable por `.env`.
Archivos: `backend/filmai/settings.py`, `openspec/specs/chat-api/spec.md`

### 28/10/2026 — SDD del chatbot: decisiones de diseño vigentes

- **Errores**: un solo error visible durante el stream, `chat_unavailable` (proveedor caído, cuota, tiempo, tope de vueltas o fallo al guardar), con la causa en el log. Antes del stream, los códigos existentes más `chat_request_in_progress`, 409 (Conflict). Descartado un código por causa: cinco textos que no cambian lo que hace el usuario.
- **CSRF** con `JWTCookieAuthentication` en una vista DRF, para que el rechazo salga con el sobre de errores. **ASGI**: `daphne` en desarrollo y uvicorn en producción, sin `channels` (SSE es HTTP común). Sin endpoint de cancelación: Django cancela la vista al desconectarse el cliente.
- **Una solicitud a la vez**: candado con `cache.add` y token propio, que solo libera quien lo tomó; el turno tiene un máximo de 25 s. El tope por hora se cuenta después del candado, así un 409 (Conflict) no gasta cupo.
- **Cierre**: primero se guarda (con `asyncio.shield`, junto con la liberación del candado) y después salen `tarjetas` y `fin`.
- **Puente async único** con `sync_to_async`: el contexto viaja al hilo, así el tope de llamadas a TMDB por pedido (F6) rige también en las tools.
- **Memoria**: últimos 10 mensajes, solo texto; `ya_recomendados` guarda hasta 30 títulos. Antes: cada respuesta llevaba «[Tarjetas: …]»; se sacó el 05/11 porque el modelo la imitaba como texto en vez de llamar a `mostrar_tarjetas`.
- **Markdown** sanitizado; los links y las imágenes que escribe el modelo se muestran como texto (una imagen inyectada por prompt haría pedir una URL ajena). Solo enlazan las tarjetas, armadas por el frontend desde ids.

Archivos: `contracts/sse-chat.md`, `openspec/specs/chat-api/spec.md`

### 31/10/2026 — Anonimizador con dos alcances

Lo que habla del usuario (perfil, reseñas, `mis_listas`) se anonimiza estricto: nombre, apellido y usuario a `[usuario]`, y todo correo a `[correo]`. En la conversación, nombre y apellido se reemplazan solo si van juntos; un nombre suelto se conserva. Los resultados de TMDB no se anonimizan. Antes (28/10): se reemplazaba todo nombre suelto y el LLM no recibía nada que identificara al usuario; se cambió porque Mark no podía pedir una película de Mark Ruffalo. Riesgo aceptado: un nombre suelto escrito por el usuario llega a DeepSeek, que guarda los datos en China. El saludo con el nombre lo arma el frontend.
Archivos: `backend/chatbot/anonimizar.py`

### 04/11/2026 — Configuración del LLM y proveedor como adaptador

Como con TMDB, `settings.py` lee cada valor con un default y el código solo lee `settings`; la única variable obligatoria es `LLM_API_KEY`. `LLM_PROVEEDORES` es una lista (hoy de uno) y el orquestador solo conoce el protocolo `ProveedorLLM`. `LLM_PROVIDER=openai_compatible` indica el formato de API, no la empresa: DeepSeek usa el SDK `openai` con otra `base_url`. Sumar un respaldo es agregar una entrada.
Archivos: `backend/filmai/settings.py`, `backend/chatbot/llm.py`

### 05/11/2026 — Tools: lo que cambió al consultar TMDB

`similares_a` usa `/recommendations`, porque `/similar` da resultados malos (_Paddington 2_ traía _El Señor de los Anillos_). `buscar_por_persona` usa `combined_credits`, porque `/discover/tv` ignora `with_people` sin avisar. `duracion_max` filtra solo películas (TMDB casi no tiene la duración de series). Las búsquedas de recomendación excluyen las Vistas y las consultas directas (`buscar_por_titulo`, `detalle`, `mis_listas`) las conservan marcadas, para que «algo como Interstellar» funcione aunque ya la hayas visto. Antes (28/10): toda tool sacaba las Vistas. Esquemas sin `strict`: en DeepSeek no valida en la URL normal y en `/beta` hace que el modelo mande nulls.
Archivos: `backend/chatbot/tools/`, `backend/catalogo/client.py`

### 05/11–06/11/2026 — Orquestador y reglas del prompt

El prompt pide texto y `mostrar_tarjetas` en la misma respuesta; si llegan juntos, el turno termina sin otra llamada (de 6,5 s a 4,5 s). Tope: 4 vueltas de tools y una llamada final. `responder()` retiene los primeros 200 caracteres de cada vuelta y los descarta si la vuelta pide buscar, porque el modelo escribía «I'll look that up.» y el contrato no permite retirar texto enviado. Si menciona la duración, la da para todos los títulos.
Archivos: `backend/chatbot/orquestador.py`, `backend/chatbot/prompts.py`

### 06/11/2026 — Persistencia del turno y vista SSE

`guardar_turno()` guarda pregunta, respuesta y `ya_recomendados` (sin repetidos) en una transacción. El historial usa cursor de 20 sin `total`, para ahorrar un `COUNT(*)` por página. `MensajesView` es una clase DRF con `get` del historial y un `post` sync que hace todos los chequeos y devuelve un `StreamingHttpResponse` sobre un generador async: así el `POST` queda en el OpenAPI con el sobre de errores y no ocupa un hilo mientras el modelo escribe. Una cuenta dada de baja con la cookie viva recibe 401 (Unauthorized) `session_revoked`. Hueco aceptado: si el navegador corta antes del primer evento, el candado se libera solo a los 60 s. Pendiente: comando de arranque con uvicorn al desplegar.
Archivos: `backend/chatbot/views.py`, `backend/chatbot/servicio.py`, `backend/chatbot/limites.py`

### 07/11–08/11/2026 — Set dorado y veredicto del RNF #6

`golden.yaml` tiene 14 preguntas y `manage.py chatear --golden` las corre contra el orquestador real midiendo tiempos. Las expectativas se revisan a mano: las respuestas cambian entre corridas y un «pasó» automático daría una confianza que no corresponde. Con `deepseek-flash` **el RNF #6 se cumple** con thinking apagado (peor caso 8,7 s con agregación y 4,3 s simple) y encendido (11,6 s y 4,9 s). Thinking queda apagado por defecto (35 % menos de tiempo total). Pendiente: el modelo nombra títulos sin llamar a `mostrar_tarjetas` (3 de 8 recomendaciones con tarjetas con thinking apagado). El 08/11 se archivó el SDD y `main` se llevó a `develop` por fast-forward, con el chatbot incluido.
Archivos: `backend/chatbot/golden.yaml`, `backend/chatbot/management/commands/chatear.py`

### 12/11/2026 — Red de tarjetas y argumentos validados

**Red de tarjetas**: si el turno termina sin tarjetas y la respuesta nombra títulos que devolvió una búsqueda para recomendar (`descubrir`, `similares_a`, `buscar_por_persona`, `buscar_semantico`), el orquestador las arma con hasta 3 de ellos, en el orden en que aparecen. La comparación ignora mayúsculas y acentos y exige borde de palabra («Moon» no cuenta dentro de «Moonlight»). Un título de 3 letras o menos («Her», «It», «Up») cuenta solo en negrita (**Her**): suelto, «Her latest film…» al empezar una oración era una tarjeta. Si un título cae dentro de otro más largo del mismo texto, gana el largo: «Probá Dune: Part Two» no arma tarjeta para «Dune», salvo que «Dune» también aparezca suelto (decisiones de Gonza, 12/11). Las consultas directas (`buscar_por_titulo`, `detalle`, `mis_listas`) no cuentan, así que «¿cuánto dura Interstellar?» sigue sin tarjeta, y lo visto tampoco entra porque esas búsquedas ya lo sacan. Se eligió esto y no pedirle al modelo otra llamada: no suma demora y no puede volver a fallar. Se probó también subir la regla de `mostrar_tarjetas` al primer lugar del prompt, y se descartó: en dos corridas el modelo la llamó sola en una vuelta intermedia (con `develop` nunca pasó), gastó vueltas y 3 turnos llegaron al tope.
**Argumentos validados**: `ejecutar()` revisa los argumentos de cada tool contra su esquema con `jsonschema` antes de correrla, y si están mal devuelve `invalid_arguments` con el campo y los valores válidos, para que el modelo corrija en la vuelta siguiente. Antes, «Ciencia ficción» dejaba vacía la búsqueda semántica y `descubrir` buscaba sin el filtro. Un `null` cuenta como no mandado. Cierra el pendiente de la revisión de seguridad del 05/11 de validar `tipo` e `id_tmdb`. Cambio aceptado: una tarjeta mal armada ya no se descarta sola, rechaza el pedido entero; si era la última vuelta, la red arma las tarjetas desde el texto.
**Medición** (set dorado, 12/11, thinking apagado, 4 corridas por versión, 8 preguntas que recomiendan, 32 turnos por versión): con `develop`, 3 turnos nombraron títulos sin mostrarlos (`portugues` una vez, `por_persona` dos). Con el cambio, los 27 turnos que terminaron tienen tarjetas, y la red las armó en 2. El «3 de 8» del 08/11 no se repitió: después de los ajustes del prompt de #171 a #173 el modelo las muestra solo casi siempre, así que la red es una garantía más que un arreglo diario. Ningún turno recibió `invalid_arguments`.
**Pendiente aparte**: el tope de 4 vueltas de tools corta turnos que el modelo estira con búsquedas de más (`ingles_mas_corto`, `semantico`, `como_arrival_mas_liviano`): 2 de 32 turnos con `develop` y 5 de 32 con el cambio, 3 de ellos en las dos corridas con el ajuste de prompt descartado. No lo causa la red ni la validación, que no cambian lo que recibe el modelo.
**Secuelas** (regla nueva del prompt, al final de «Títulos vistos»): si el modelo va a recomendar una secuela o una temporada posterior y el usuario no vio la anterior, recomienda la anterior; si ya la vio, no lo aclara, porque las búsquedas de recomendación sacan lo visto. Va al final de esa sección y no al principio de «Cómo trabajar» porque mover la regla de tarjetas al principio cambió la conducta del modelo. La prueba es `secuela_sin_la_anterior` del set dorado. En 2 corridas (12/11, `gonzag8`, que no vio Dune ni Blade Runner) recomendó empezar por Duna antes de Duna: Parte dos las dos veces, pero en una recomendó Blade Runner 2049 sin mencionar Blade Runner: la cumple a medias. Topes de vueltas en esas corridas: 3 de 16 turnos de las 8 preguntas de antes (5 de 32 en la medición anterior), sin cambios visibles en el resto.
Archivos: `backend/chatbot/orquestador.py`, `backend/chatbot/tools/__init__.py`, `backend/chatbot/tools/turno.py`, `backend/chatbot/prompts.py`, `backend/chatbot/golden.yaml`

---

## Multiidioma

### 07/10/2026 — Red de caracterización antes del multiidioma

Antes del contrato de códigos se congelaron como referencias el HTTP y el cuerpo de los endpoints, los cuatro correos y el esquema OpenAPI; solo se regeneran con una variable explícita. Así el cambio de contrato se hizo sabiendo qué se rompía.
Archivos: `backend/filmai/tests_contrato.py`, `openspec/specs/api-characterization/spec.md`

### 08/10/2026 — Diseño del multiidioma e idioma de la cuenta

Inglés y español, inglés por defecto; next-intl con mensajes ICU, sin prefijo de idioma y con rutas en inglés. Con sesión manda `Usuario.idioma` y la cookie `filmai_locale` es su espejo; sin sesión, la cookie; el backend resuelve cuenta → `Accept-Language` → `en`. El backend no traduce respuestas: emite códigos, y solo los correos y TMDB usan el idioma. La copia en español usa voseo. La documentación de dominio sigue en español porque la leen docentes. Antes: el plan migraba tres pantallas piloto y aceptaba una interfaz mixta; el 15/10 toda la interfaz quedó en el catálogo.
Archivos: `backend/filmai/idioma.py`, `frontend/lib/format.ts`

### 08/10/2026 — Contrato de errores por código

Todo error de la API viaja en un sobre `{code, params, errors}` (cada error con `field`, `code` y `params`), con códigos en inglés snake_case de un catálogo único que se exporta a `contracts/error-codes.json`. El frontend traduce por código y nunca lee `detail`; `debug` solo existe con `DEBUG=True`. El HTTP depende del contexto (credenciales: 400 (Bad Request) en el login y 401 (Unauthorized) en la autenticación). Los errores de TMDB se mapean a `upstream_*`; el 429 (Too Many Requests) propio lleva `retry_after_seconds`. En la suite, toda respuesta 4xx/5xx se valida y un código no registrado hace fallar el test. El login de una cuenta pendiente o dada de baja da 403 (Forbidden) con su código solo si la contraseña es correcta, para no revelar el estado a quien no controla la cuenta.
Archivos: `backend/filmai/exceptions.py`, `backend/filmai/errores/`, `openspec/specs/error-contract/spec.md`

### 08/10–12/10/2026 — Frontend multiidioma y selector de idioma

Formatos solo desde `lib/format.ts` (`en-US`/`es-AR`); `apiFetch` manda `Accept-Language` y los errores se traducen por código. Rutas visibles en inglés, centralizadas en `lib/routes.ts` junto con los enlaces de los correos. Catálogos generados desde CSV aprobados, con controles de paridad y de literales en Vitest, ESLint y Playwright. Con sesión, el idioma se cambia en Preferencias y define el de los correos; sin sesión, un selector `EN | ES` (sin banderas) escribe la cookie, arriba a la derecha en las pantallas sin navbar y en el footer en las demás.
Archivos: `frontend/lib/routes.ts`, `frontend/components/LanguageSwitcher.tsx`

### 18/10/2026 — Textos de la interfaz en `traducciones/`

Los textos pasan de `docs/i18n/` a `traducciones/` en la raíz, porque son datos que leen el generador y los tests, no documentación. Se eliminó el catálogo transitorio (`legacy.*`) y las correcciones que el generador hacía a mano pasaron al CSV, única fuente de verdad. `claves.csv` guarda la trazabilidad del canvas y `claves-extra.csv` lo que el canvas no trae.
Archivos: `traducciones/`, `frontend/scripts/i18n/generate.py`

### 06/11/2026 — El chatbot detecta el idioma del mensaje

DeepSeek respondía en español a mensajes en inglés aunque el prompt pidiera «el idioma del mensaje»: pesaba el perfil, con reseñas en español. Solo funcionó nombrar el idioma. `chatbot/idioma.py` detecta `es` o `en` contando palabras comunes, `ñ`, `¿`, `¡` y tildes, y el prompt cierra con «reply in English» o «respondé en español»; sin señal usa el idioma del turno. Heurística y no librería: determinista, testeable y sin dependencias.
Archivos: `backend/chatbot/idioma.py`

---

## Correos

### 24/08/2026 — Correos transaccionales con Resend

`EMAIL_BACKEND` propio sobre la API de Resend. Sin dominio propio Resend solo entrega al dueño de la cuenta: en desarrollo `RESEND_TEST_RECIPIENT` redirige todo ahí. Con `DEBUG=False`, esa variable o la falta de `RESEND_API_KEY` frenan el arranque en vez de fingir un envío. Riesgo vigente: hasta verificar un dominio, solo el dueño de la clave recibe correos reales.
Archivos: `backend/filmai/email_backends.py`

### 08/10–12/10/2026 — Servicio único, correos localizados y diseño del canvas

Los cuatro flujos pasan por `enviar_correo`, con plantillas por caso e idioma y una base HTML común. El idioma es el guardado del destinatario, si no el del pedido, si no inglés. Diseño del canvas sobre una tabla con estilos en línea, fuentes con alternativas del sistema (Gmail ignora las web), marca sin SVG (muchos clientes lo eliminan) y solo tema oscuro. Vigencias: 24 horas para confirmar el correo y 1 hora para restablecer la contraseña.
Archivos: `backend/filmai/correos/servicio.py`, `backend/templates/correos/base.html`

### 30/10–06/11/2026 — Pendientes: correos por Celery (Q-08) y Brevo como respaldo (#181)

`enviar_correo()` llama a Resend dentro del pedido HTTP; pasará a una tarea con reintentos con espera creciente, porque un correo fallido no tiene backfill que lo recupere. Resend gratis da 100 correos por día y los topes son por IP: una sola IP puede agotar el cupo y dejar sin confirmación ni reset a los usuarios legítimos. Se usará Brevo (300 por día) cuando Resend no pueda entregar, con un backend que recorra proveedores como `LLM_PROVEEDORES`: 429 (Too Many Requests), 5xx y timeout pasan al siguiente; un 400 (Bad Request) no. Descartados Amazon SES (dominio, DKIM y sandbox), Mailjet y Mailtrap (menos cupo). Plan en `openspec/changes/brevo-respaldo/`.
Archivos: `backend/filmai/email_backends.py`, `docs/05_Plan_de_Desarrollo.md`

---

## Interfaz

### 24/08–26/08/2026 — Librerías base de la interfaz

Toasts con `sonner`. Shadcn quedó sobre `@base-ui/react` y no sobre Radix como decía el plan.
Archivos: `frontend/components.json`

### 15/10–18/10/2026 — App solo oscura y esqueletos estáticos

El tema claro estaba roto (los tokens propios existían solo para oscuro). El 18/10 se descartó porque el tema oscuro es parte de la identidad de FilmAI, y se eliminó `Usuario.tema` del modelo, la API y los docs (migración `0009_remove_usuario_tema`). El layout declara `colorScheme: "dark"` desde el servidor para que los controles nativos no se pinten claros al cargar. Los esqueletos de carga son bloques fijos, sin `animate-pulse`.
Archivos: `backend/usuarios/models.py`, `frontend/app/layout.tsx`

### 16/10/2026 — Estados de carga, vacío y error (Q-03)

Se revisaron 46 escenarios en 8 pantallas forzando errores, red caída, lentitud y vacíos. Sin red se veía «Failed to fetch»: `apiFetch` convierte el rechazo en el código propio `network_error` con un mensaje traducido. La caché del catálogo del frontend guarda por `idioma|ruta`, porque las filas seguían en el idioma anterior al cambiarlo sin recargar.
Archivos: `frontend/lib/api.ts`, `frontend/lib/use-catalog.ts`

### 16/10–28/10/2026 — Accesibilidad y responsive (Q-01, Q-04)

Objetivos táctiles de 44 px en celular (se sigue el doc 05 y no los 40 px del canvas) y letra de 16 px en los campos para que iOS no haga zoom. El 28/10: `scroll-padding` para que la barra inferior no tape el foco, `<h1>` del Inicio siempre presente, diálogos nativos (`<dialog>`), regiones vivas montadas desde el inicio (si nacen con el texto no siempre se anuncian) y notas «de 10» para lectores de pantalla. Solo el borde de los campos sube a 3:1 de contraste con un token propio (`--field-border`). axe-core sin infracciones en las pantallas principales. Falta revisar el chatbot.
Archivos: `frontend/app/globals.css`, `frontend/e2e/a11y-axe.spec.ts`

### 22/10–24/10/2026 — Rendimiento medido en build de producción

`AccountProvider` deja de pedir la cuenta en cada navegación (de 14 a 4 pedidos en tres navegaciones); dnd-kit va en un chunk precargado en tiempo ocioso; el catálogo público responde con `Cache-Control: public, max-age=300` y `gzip_page` solo ahí (no global, por BREACH); las imágenes de TMDB usan `srcset` y las del LCP `fetchPriority="high"`; el Inicio reserva la fila «Recomendado» (CLS de 0,07–0,14 a 0–0,01). El Hero del Inicio llega en el HTML del servidor, cacheado 5 minutos; con error o más de 500 ms devuelve `null` y lo pide el navegador, así que nunca rompe la página.
Archivos: `frontend/components/AccountProvider.tsx`, `frontend/app/home/page.tsx`, `frontend/lib/catalogo-servidor.ts`

### 04/11/2026 — Pantallas grandes y navegación

En monitores de 1920 px el contenido quedaba en 1360 px: desde 1440 px la raíz escala con `clamp(100%, …, 130%)` (en % para respetar la letra del usuario), los tamaños pasaron a rem y un solo `page-container` alinea navbar, contenido y footer. La navbar queda fija en escritorio, translúcida al 85 % (con 75 % el contraste caía por debajo de 4,5:1). En celular sin sesión no se podía llegar a Buscar: la barra inferior muestra Home, Search y Log in.
Archivos: `frontend/app/globals.css`, `frontend/components/Navbar.tsx`, `frontend/components/MobileTabs.tsx`

### 06/11/2026 — Panel del chat y FAB

Panel modal en escritorio y celular, con «Cancelar» en el lugar del botón de enviar; al cancelar se quita la burbuja de la pregunta, porque el servidor no guardó nada. La conversación es `role="log"` sin anunciar cada fragmento; una región aparte anuncia la respuesta completa. El FAB aparece en todas las pantallas salvo las de acceso; en el footer, «Ask FilmAI» abre el panel con sesión y lleva a `/login?next=…` sin ella. La bienvenida sortea 3 de 14 sugerencias sin títulos fijos.
Archivos: `frontend/components/ChatProvider.tsx`, `frontend/components/features/chat/ChatPanel.tsx`, `frontend/lib/chat-sugerencias.ts`

### 11/11/2026 — Canvas igualado al código y sin mesas repetidas

Se comparó cada mesa del canvas con el repo; donde había interfaz desarrollada, mandó el código. En el canvas se borraron Main («A · Cartel») y las dos mesas de pantallas grandes, que repetían la Home (la regla de 7 tarjetas desde 1440 px quedó en el título de la sección), y se quitó el tema claro de todas las mesas. Se ajustaron Settings (Privacy y ayudas «Preference for future…»), el chat (modal, «Cancel» en el botón de enviar y sugerencias sin títulos), los textos de la ficha, Home, Lists, el perfil, Terms, el registro y el correo de confirmación. Se sumaron Reset password y variantes por tweak: ficha sin sesión y de serie, perfil con cuenta de Google y diálogo de salir sin guardar, y Search sin resultados por filtros. El error por fila de la Home no existe en el código: falla la fila, se oculta y aparece un toast, y solo cuando fallan todas se ve el error con «Try again». El canvas pasó a mostrar ese comportamiento. Del canvas pasaron al código el cierre de Terms («Questions? Write to us at …», con el correo en el frontmatter `contact`) y «Order saved.», que se anuncia solo a lectores de pantalla al mover una lista desde el menú.
Archivos: `frontend/content/legal/terms.{en,es}.md`, `frontend/lib/legal.ts`, `frontend/app/terms/page.tsx`, `frontend/components/features/lists/ListsView.tsx`, `traducciones/claves-extra.csv`

### 12/11/2026 — Revisión de la navbar fija (#157)

Una revisión del código encontró dos efectos de la navbar fija en escritorio, y Gonza eligió arreglarlos junto con dos menores invisibles. (1) Next solo lleva arriba la página nueva si su comienzo quedó fuera de la pantalla (`topOfElementInViewport` en `layout-router.js`): con menos scroll que el alto de la barra (84 px), la barra tapaba el principio de la página nueva. `ScrollArribaAlNavegar`, en el layout, la lleva arriba en cada cambio de `pathname`, salvo al entrar y con un ancla. Con atrás o adelante (`popstate`) devuelve el scroll anotado de esa URL: el navegador lo restauraba solo, pero cuando todavía se veía la página de la que se salía, y si era más corta quedaba recortado (900 px en /terms volvían como ~530). Reintenta en cada cuadro, hasta ~1 s, porque Next pinta la página anterior un render después de cambiar `pathname`; corta si la persona mueve la página. (2) El menú «…» de las tarjetas de Lists estaba en una caja con `z-10`, que encerraba su capa de cierre (z-40) debajo de la barra (z-30): tocar la barra no lo cerraba y quedaban dos menús abiertos. Se sacó el `z-10`; `relative` alcanza para quedar encima del enlace de la tarjeta. (3) `scroll-padding-top` solo en páginas con navbar (`html:has(header[data-navbar])`), no en login ni registro. (4) `useFondo` usa un `IntersectionObserver` sobre la imagen grande y solo en escritorio: el scroll ya no mide la página en cada evento, y el fondo se actualiza aunque la imagen cambie de alto sin scroll. Quedó sin tocar, por decisión de Gonza, el margen de los títulos de Terms al saltar desde el índice.
Archivos: `frontend/components/ScrollArribaAlNavegar.tsx`, `frontend/app/layout.tsx`, `frontend/components/Navbar.tsx`, `frontend/components/features/lists/ListCard.tsx`, `frontend/app/globals.css`, `frontend/e2e/navbar-fija.spec.ts`, `frontend/e2e/listas.spec.ts`

---

## Seguridad

### 22/08–26/08/2026 — JWT solo en cookies httpOnly, con CSRF explícito

Refresh y access dejaron `localStorage` (superficie XSS): viajan solo en cookies httpOnly y se autentica con `JWTCookieAuthentication`. Como la cookie viaja sola, se exige `X-CSRFToken` en las mutaciones en vez de confiar solo en `SameSite=Lax`. Se descartó `SameSite=None; Secure`: front y API son mismo sitio y rompería el desarrollo por http. El middleware de Next.js solo mira si existe la cookie; firma y vencimiento los valida el backend, así el frontend no comparte `SECRET_KEY`.
Archivos: `backend/filmai/settings.py`, `frontend/lib/api.ts`

### 12/10/2026 — Acceso de staff a la documentación de la API

La página 403 (Forbidden) de `/api/docs/` la sirve Django, con un formulario que exige `is_staff`. Contraseña incorrecta, cuenta inexistente o cuenta común reciben el mismo aviso, con costo de hash igualado para no revelar qué cuentas existen. Límite de 10 fallos por IP cada 60 minutos con 429 (Too Many Requests).
Archivos: `backend/filmai/documentation.py`

### 18/10–28/10/2026 — Auditoría de seguridad

Se usó la skill `security-audit` de Cloudflare sin modificarla: 11 hallazgos reproducidos en un sandbox Docker aislado (6 medios y 5 bajos, ninguno alto), todos resueltos al 28/10, cada uno con su test. Los informes no se versionan porque describen cómo explotar fallas. Lo que quedó para el despliegue está en «Pendientes» de `docs/05_Plan_de_Desarrollo.md`.
Archivos: `.agents/skills/security-audit/`

### 20/10/2026 — Redis con contraseña, solo en loopback y sin pickle (F1)

Redis publica solo en `127.0.0.1`, exige contraseña y la caché usa JSON en vez de pickle. Con `DEBUG=False` el arranque falla si una URL de Redis no lleva contraseña.
Archivos: `docker-compose.yml`, `backend/filmai/cache.py`

### 20/10/2026 — Límites por cuenta e IP y `NUM_PROXIES` (F2 y F3)

Login, registro y reenvío tienen límites por cuenta o correo y por IP, con 429 (Too Many Requests); el límite por cuenta cuenta todos los intentos, para no revelar si la contraseña era correcta. Riesgo aceptado: quien conozca un correo puede bloquear su login un minuto. `NUM_PROXIES`, obligatorio en producción, define qué IP de `X-Forwarded-For` se usa. Redis desaloja solo claves con vencimiento, nunca la cola de Celery. Pendiente: confirmar la topología de proxies al desplegar.
Archivos: `backend/usuarios/throttles.py`, `backend/filmai/settings.py`

### 20/10/2026 — El admin no deja escalar a un staff (F5), clave fuera del log y `next` seguro (F8, F9)

Con `change_usuario` un staff podía hacerse superusuario o fijar la contraseña de otro: ahora no ve a los superusuarios, no edita sus propios permisos ni a otro staff. La clave del enlace de confirmación ya no va al log. `/login?next=` aceptaba `//host`: ahora se resuelve con `new URL()` y solo se acepta si el origen no cambia (se prefirió el parser a una lista de patrones prohibidos, que siempre deja pasar alguna variante).
Archivos: `backend/usuarios/admin.py`, `frontend/lib/safe-next.ts`

### 26/10/2026 — Acceso endurecido tras la segunda revisión

Los modelos de allauth y simplejwt y `Group` quedan solo para superusuarios. `SESSION_LOGIN: False`, porque la sesión de Django valía en `/admin/`. Una cuenta nueva con Google exige `email_verified` del token firmado. Login, registro, Google y reset aceptan solo JSON (415 (Unsupported Media Type) con formularios), contra el login CSRF. `/admin/login/` bloquea 60 minutos tras 10 fallos por IP. F11: `login` y `password/reset` sin barra final caían en vistas sin límites; se registraron a mano. El correo no se cifra como columna (login y unicidad lo buscan por valor): RNF #2 y #12 se cumplen con cifrado en reposo de la base al desplegar.
Archivos: `backend/usuarios/admin.py`, `backend/filmai/documentation.py`, `backend/filmai/urls.py`

### 26/10/2026 — Topes de escritura: tasa común por usuario y techos de cantidad

60 escrituras por minuto por usuario, compartidas por reseñas, listas, perfil y preferencias; 100 listas personalizadas y 1000 ítems por lista, ambos con 409 (Conflict). El techo de ítems no rige en las predeterminadas porque calificar agrega a «Vistas». Se recuenta con `select_for_update` para cerrar la carrera. Pendiente de decidir: techo también en Favoritos y Pendientes.
Archivos: `backend/filmai/throttles.py`, `backend/listas/models.py`

### 28/10/2026 — Postgres en loopback, `entrypoint.sh` seguro, reset con tope por IP y clave de TMDB fuera de los logs

Postgres pasó de todas las interfaces a `127.0.0.1:5432`, como Redis. `entrypoint.sh` metía la contraseña del superusuario dentro de código Python (una comilla lo rompía o inyectaba código, y se veía en la lista de procesos); ahora un heredoc `<<'PY'` la lee de `os.environ`, y si falta una variable el backend no arranca. El reset de contraseña respondía 500 (Internal Server Error) con `{"email": 5}`: ahora 400 (Bad Request) y 10 por hora por IP. TMDB v3 recibe la clave en la query y httpx la logueaba: `httpx`/`httpcore` quedan en WARNING y el error de transporte la tapa. Descartado: `Authorization: Bearer`, que exige el token v4. Riesgo vigente: enumeración de cuentas por tiempo de respuesta en el reset.
Archivos: `docker-compose.yml`, `backend/entrypoint.sh`, `backend/usuarios/throttles.py`, `backend/catalogo/client.py`

---

## Calidad y tests

### 18/08–10/09/2026 — Lint, formato y CI

Ruff como linter y formatter único en el backend; Prettier, ESLint y un hook de Husky en el frontend. El 25/08 un warning entró a `main` por un merge desde GitHub, que no corre hooks locales, y se agregó CI; desde el 10/09 corre también los tests de Django contra PostgreSQL 16. Formato limpio en ambos proyectos es condición para cerrar una tarea.
Archivos: `backend/pyproject.toml`, `.husky/pre-commit`, `.github/workflows/ci.yml`

### 15/09–26/09/2026 — Un test con todo mockeado prueba el llamado, no el efecto

Tres bugs pasaron con la suite en verde y los destaparon tests de integración: un fixture de créditos de TV con un `Director` que la API nunca devuelve, el backfill reencolando `ready` que la tarea nunca reclamaba y `materializar()` devolviendo la fecha como string, que daba 500 (Internal Server Error) al agregar a una lista una producción nueva.
Archivos: `backend/catalogo/tests.py`

### 26/09–03/10/2026 — Tests del frontend: Playwright y Vitest

Playwright recorre los flujos con la API simulada y Vitest (Testing Library, jsdom) prueba componentes; ambos corren en el CI, que suma `npm run build` y fija el locale.
Archivos: `frontend/playwright.config.ts`, `.github/workflows/ci.yml`

### 15/10/2026 — Seed con producciones reales de TMDB

Las producciones sintéticas tenían `id_tmdb` bajos que chocaban con títulos reales, y una tarjeta abría otra ficha. `seed` materializa los más votados por género y arma actividad coherente (notas cercanas a TMDB, reseñas en el idioma de cada cuenta, «calificada ⇒ Vistas», Favoritos con nota de 9 o más). Aborta sin borrar si TMDB deja menos de 20 reales; `--sintetico` conserva el modo offline para los tests.
Archivos: `backend/usuarios/seed_real.py`, `backend/usuarios/management/commands/seed.py`

### 15/10/2026 — Reutilización de componentes y Q-07

Refactor de riesgo bajo: `CursorConTotal` común a los cursores de reseñas y listas, y piezas de filtros compartidas en el frontend. Quedó como Q-07 el de riesgo medio (`review-actions` y `useCursorList` + `useSentinel`), sin evaluar todavía.
Archivos: `backend/filmai/paginacion.py`, `frontend/lib/review-filters.ts`

### 28/10/2026 — e2e estables ante la hidratación

Lo que se escribe antes de que la página hidrate se pierde, y `networkidle` no lo garantiza: los e2e llenan dentro de `expect(...).toPass()` hasta ver una señal que solo aparece hidratada, con timeouts internos cortos. El CI sube el trace de Playwright cuando falla.
Archivos: `frontend/e2e/i18n-flows.spec.ts`, `.github/workflows/ci.yml`

### 05/11–07/11/2026 — CI más rápido y Playwright local con 2 workers

Bajo `manage.py test` se usa el hasher MD5 (producción sigue con bcrypt): el job de backend pasó de 7m33s a 1m49s. Un push nuevo a un PR cancela la corrida anterior y Playwright se reparte con `--shard` en dos jobs. En local se fijan 2 workers: con 6, WSL se quedaba sin memoria y los e2e fallaban por tiempo.
Archivos: `.github/workflows/ci.yml`, `frontend/playwright.config.ts`
