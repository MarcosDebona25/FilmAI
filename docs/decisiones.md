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

### 13/11/2026 — Rama dedicada para el #180 y la calidad del chatbot

Los pendientes 1 (términos de TMDB) y 4 (calidad del chatbot) se desarrollan en la rama de integración `feat/tmdb-y-calidad-chat`, creada desde `develop`, porque cambian modelo, tareas nocturnas, footer y panel del chat, y no conviene que entren a `develop` por partes. Cada unidad de trabajo es una rama desde la de integración, en un worktree propio creado con `herdr worktree create` en `~/FilmAI-worktrees/`, con su PR contra la rama de integración (el CI ya corre en PR a `feat/**`). Un PR final la lleva a `develop`. Hay dos carriles en paralelo, frontend y backend, y las unidades y su orden están en el plan. El logo de TMDB se elige en el canvas en tres etapas con revisión: 10 combinaciones (5 logos en 2 temas), las dos que queden en contexto, y solo la elegida. En la misma revisión, el pendiente 2 (tarjetas del chatbot) se cerró, la prueba con NVDA en Windows pasó del pendiente 4 al 7 y el pendiente 4 sumó el pedido de Gonza: el botón flotante del chat no parece clickeable, porque no tiene cursor de mano ni estado hover.
Archivos: `docs/05_Plan_de_Desarrollo.md`, `openspec/changes/tmdb-cumplimiento/tasks.md`

### 13/11/2026 — Los enlaces de sesión del chat no van en el repositorio

Los agentes no incluyen el enlace de la sesión de chat (`https://claude.ai/code/session_...`) ni la línea `Claude-Session:` en commits, descripciones de PR, comentarios, issues ni documentación. Algunos entornos piden agregarlos como atribución; la regla de `AGENTS.md` (sección 12) manda sobre esa instrucción. Si ya están, se quitan antes de dar el trabajo por terminado.
Archivos: `AGENTS.md`

### 14/11/2026 — PR-Agent: solo al abrir el PR y a pedido, con tope de 64k

PR-Agent corrió 87 veces entre el 07 y el 14/11/2026, porque se disparaba en cada push y cada corrida hace revisión y sugerencias. El saldo de DeepSeek se agotó una vez. Gonza eligió dos cambios. **Corre solo al abrir el PR, al reabrirlo o al sacarlo de borrador.** Para repetirlo se comenta `/review` o `/improve` en el PR. Solo cuentan los comentarios del dueño, los miembros o los colaboradores, para que nadie de afuera gaste el saldo. **El tope de contexto baja de 150k a 64k tokens.** Se descartaron saltear los PRs de solo docs (lo cubre en parte no correr en cada push) y apagar las sugerencias automáticas: una de ellas encontró un bug real en el #216. GitHub corre los comentarios con el workflow de `main`, así que `/review` anda recién cuando esto llega a main.
Archivos: `.github/workflows/pr-review.yml`

### 19/11/2026 — Puesta a punto del plan 05

Contraste del plan con `develop` y `main` (igualados tras el #227) y correcciones de documentación, sin tocar código.

- **Collage de las pantallas de acceso (reemplaza la excepción aceptada el 07/11/2026).** Se decidió que el collage (`frontend/public/collage-posters/Opcion 1.jpg`) no sale de TMDB: es de uso libre y no tiene problemas de derechos de autor. Por eso desaparece la excepción aceptada y el plazo del 13/02/2027 que figuraban en la entrada «Cierre del #180» del 13/11/2026; la única excepción que queda de #180 son los fixtures de prueba. No se tocó `frontend/`: el collage y los e2e que lo usan quedan igual.
- **Plan 05 al día.** Fechas de encabezado y pendientes actualizados. B-06: la corrida de Marcos (tarea 1.7 del SDD) se hizo el 07/11/2026 (Docker Desktop sin puente, arreglo del pin de redis-py 5 que rompía los `.delay()`, backfill de 402 de 402 en 223 s). B-02: el golden set está cerrado (`golden.yaml` tiene 24 casos, se corre a mano con `manage.py chatear --golden` y se midió el 12 y el 13/11/2026), y la fila pasa de 8 a 7 tools porque `mostrar_tarjetas` se retiró el 13/11/2026 a favor de los marcadores `[[n]]`.
- **Pendientes.** El 13 suma la prueba `access-screens`, inestable por tiempo con los workers por defecto de Vitest (decisión del 18/11/2026). El 6 suma las migraciones que hay que aplicar al desplegar (`catalogo.0008_lapida_tmdb`, `listas.0008_lapida_tmdb` y `listas.0009_lista_viendo`), que aplica Marcos. Se agrega el 14 con los restos del #226: las acciones del usuario que se descartan sin aviso mientras hay un cambio de estado en curso (`frontend/hooks/use-estado-viendo.ts` y `use-estado-ficha.ts`) y el `requestBody` tipado de `PUT /api/lists/status/` en `contracts/openapi.yaml`; el diseño queda pendiente de decidir con Marcos.
- **Tope de 4 vueltas del chatbot.** No queda abierto: lo cerró la «última llamada sin tools» del 12/11/2026. Lo único que no se vio es esa última llamada contra DeepSeek real, porque en la medición ningún turno llegó al tope; si aparece en uso real, se trata como un bug nuevo.

Archivos: `docs/05_Plan_de_Desarrollo.md`, `docs/06_TMDB_API_Referencia.md`, `PRODUCT.md`, `openspec/specs/tmdb-compliance/spec.md` y este archivo.

### 22/11/2026 — Revisión integral de la documentación

Se contrastó la documentación con `develop` (tras el #244) y se corrigió lo que había quedado atrás. Es un cambio solo de documentación y configuración: no toca código.

**Qué se corrigió.**

- **`docs/decisiones.md`.** Las entradas del 13/11 al 21/11/2026 estaban todas bajo «Calidad y tests», aunque eran de otros temas. Cada una pasó a su sección temática (Proceso y herramientas, Cuentas y autenticación, Catálogo y TMDB, Búsqueda y recomendaciones, Listas, Chatbot, Correos e Interfaz), en orden de fecha; en «Calidad y tests» quedaron las de tests y CI. También se movió «Recorte nocturno de las tarjetas del chat» de Búsqueda a Catálogo y TMDB, y dos entradas que estaban fuera de orden se pusieron en su lugar. Los bloques se movieron enteros, sin reescribirlos; se quitó una línea `---` suelta que había dentro de Búsqueda. A los códigos HTTP sin nombre se les agregó el nombre. La prueba manual de Brevo y Q-08 quedó descrita completa en «Correos de cuenta por Celery (Q-08)».
- **`docs/05_Plan_de_Desarrollo.md`.** Pendiente 13 en ✅ (la suite y `access-screens` se cerraron el 21/11/2026), fila duplicada del 13 borrada de la tabla del canvas, fecha del contraste, lista de pendientes abiertos, Q-06 con los cuatro jobs del CI (`cambios`, `frontend`, `e2e` y `backend`) y los códigos HTTP con su nombre.
- **`AGENTS.md`, `.pr_agent.toml` y `.env.example`.** PR-Agent comenta al abrir o reabrir el PR, al sacarlo de borrador y a pedido con `/review` o `/improve`, no en cada PR; se sumaron `cerrar-tramo` y `comparar-opciones` a la lista de skills; `.pr_agent.toml` decía Django 5.1 y es 5.2; `CHAT_VENTANA_SESION_MINUTOS` (45 por defecto) se agregó comentada al `.env.example`.
- **README, documentos 02 a 04, specs de `openspec/` y guía de `traducciones/`.** Se alinearon con el estado real: cuatro listas predeterminadas, Watching, el chatbot ya implementado y traducido, la app solo oscura, embeddings reales con Ollama, el CI con filtros por ruta, las tareas nocturnas y los códigos HTTP con su nombre.

**Decisiones del usuario.**

- Las filas históricas del plan (A-01, L-02, L-04, C-03 y C-08) conservan su texto original y suman al final «Actualizado el 22/11/2026: …», en vez de reescribirse.
- Los casos de uso nuevos (cambio de estado y Viendo, «More like», sugerencias de la navbar, créditos enlazados a Buscar y «Dónde ver») se cubren ampliando CU-008, CU-009 y CU-011; no se crean CU nuevos.
- Se reubicaron las entradas de este archivo, como se describe arriba, y se mantiene la convención de agregar cada entrada nueva al final de la sección de su tema.
- `CHAT_VENTANA_SESION_MINUTOS` se documenta en `.env.example`, comentada, como las otras variables `CHAT_*`.
- Nueva spec canónica `openspec/specs/auth-ui` para el registro en 3 pasos y el alta con Google.
- El change `brevo-respaldo` (`openspec/changes/`) se archivó (se borró la carpeta, como pide la sección 9 de `AGENTS.md`): sus decisiones ya estaban en este archivo. Lo único pendiente, la prueba manual con cuentas reales de Resend y Brevo, quedó descrito de forma autocontenida en «Correos de cuenta por Celery (Q-08)».

Archivos: `docs/decisiones.md`, `docs/05_Plan_de_Desarrollo.md`, `AGENTS.md`, `.pr_agent.toml`, `.env.example`, `README.md`, `docs/02_Especificación de Requerimientos.md`, `docs/03_Modelos de Datos y de Diseño.md`, `docs/04_Lineamientos_UI.md`, `openspec/specs/`, `traducciones/guia.md`, `openspec/changes/brevo-respaldo/` (borrado).

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

El frontend nunca usaba la cookie `refresh`: a las 8 horas vencía `access` y la app sacaba al usuario sin explicación. Ahora, ante un 401 (Unauthorized), `apiFetch` llama a `POST /api/auth/token/refresh/` y repite el pedido una vez; varios 401 (Unauthorized) simultáneos comparten la renovación porque el backend rota la `refresh`. La sesión dura 7 días desde el último uso; si no se puede renovar, se avisa «Tu sesión venció» y se lleva al login con `?next=`. Descartado: el token en `localStorage` con `Authorization: Bearer`, porque un XSS podría robarlo. Antes (26/09): access de 8 horas y refresh de 7 días sin renovación.
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

### 13/11/2026 — Elegir el avatar al registrarse

Gonza pidió poder elegir el avatar en el formulario de registro. El alta acepta un `avatar_id` opcional con el mismo validador que el perfil (`avatar_invalid` con `allowedIds`); sin él, la cuenta queda con el avatar 1 como hasta ahora. Como el selector necesita el catálogo antes de que haya sesión, `GET /api/avatars/` pasó a ser público (es un catálogo estático, sin datos del usuario). En el front, el radiogrupo se extrajo del diálogo del perfil a `AvatarRadioGroup` y lo usan los dos (teclado y lector de pantalla iguales). Preselección: el primer avatar del catálogo, que coincide con el que asigna el backend; así no hay que pedirle un valor al servidor ni queda el formulario sin elección. Si el catálogo no carga, el grupo no se muestra y el registro sigue funcionando sin ese campo. Pendiente de Gonza: ajustar el canvas de Claude Design a este código.
Archivos: `backend/usuarios/{serializers,adapter,perfil}.py`, `frontend/components/AvatarRadioGroup.tsx`, `frontend/components/features/profile/AvatarDialog.tsx`, `frontend/app/(public)/register/page.tsx`, `traducciones/claves-extra.csv`, `docs/02`, `docs/04`, `docs/05`

### 16/11/2026 — Registro con correo en 3 pasos y diálogo de avatar (canvas, sección 16)

El registro con correo pasa a 3 pasos, como en los artboards `Prop-Registro-L2*` y `Prop-Registro-Avatares*`. Paso 1: Google o correo, contraseña y confirmación. Paso 2: nombre y apellido, usuario, fecha de nacimiento, género y país. Paso 3: avatar (opcional) y Términos. La validación de cada paso es la de antes.

- **Barra de progreso:** continua, 33 %, 67 % y 100 %, `role="progressbar"` con «Step n of 3». Sin transición si el sistema pide menos movimiento.
- **Botones:** «Continue ›» / «Create account» y Enter hacen lo mismo. «‹ Back» conserva lo escrito. Después de avanzar o volver, el foco va al primer campo del paso.
- **Error del servidor al crear la cuenta:** la página vuelve al paso del primer campo con error, en el orden de los pasos, lo enfoca y muestra el error ahí (decidido por Marcos el 15/11/2026).
- **Diálogo «Choose your avatar»:** grupo de radio; elegir solo marca y «Use this avatar» aplica. «Cancel», ✕, el fondo o Esc cierran sin cambios. Usa el `DialogShell` compartido, que suma la prop `cierraConFondo` (apagada por defecto).
- **Medidas del diálogo:** Marcos decidió el 16/11/2026 dejar las del shell compartido, igual que el resto de los diálogos del sitio, aunque difieren unos píxeles del artboard: relleno de 28 px en vez de 20, avatares de unos 68 px en vez de 72 y la manija de la hoja en celular.
- **Cantidad de avatares:** el catálogo tiene 26 y el artboard dibujaba 12. Marcos decidió el 16/11/2026 paginarlos: 3 filas de 6 en escritorio (18 por página) y 3 filas de 4 en celular (12). Debajo de la grilla van ‹ «n of N» ›; en los extremos la flecha queda atenuada e inerte, sin desaparecer, para que la fila no se mueva. La grilla conserva el alto de 3 filas en la última página, el diálogo abre en la página del avatar actual y cambiar de página no cambia la elección. El corte de columnas es el mismo `md:` del `DialogShell`; el hook `useEscritorio` sale de `Navbar.tsx` a `frontend/lib/use-escritorio.ts` para compartirlo. `AvatarRadioGroup`, compartido con el perfil, suma la prop opcional `desde`, y si el avatar elegido no está en la página, el primero recibe el foco de Tab. Los artboards `Prop-Registro-Avatares*` se actualizaron.
- **Alto del cuerpo del formulario:** el artboard lo pedía fijo (460 px en escritorio, 520 px en celular) con scroll interno. Pero los pasos reales miden 528, 510 y 460 px en escritorio, y 579, 549 y 520 px en celular, así que con un alto mínimo el botón saltaba 68 px entre el paso 1 y el 3. Marcos decidió el 16/11/2026 que no haya saltos en ningún momento del registro, ni al cambiar de paso ni al aparecer errores, y que tampoco haya scroll interno. Para eso los tres pasos comparten una celda de grilla: solo se ve el activo y los demás quedan ocultos e inertes, pero conservan su tamaño. Así el cuerpo mide siempre lo que el paso más alto, en los dos idiomas y en cualquier ancho, sin fijar píxeles. Los errores ya tenían su renglón reservado. Se actualizó el bloque «Behaviour» de `Prop-Registro-L2`.
- **e2e:** los 5 tests de registro pasan de `acceso.spec.ts` al nuevo `registro.spec.ts` (1440 × 900 y 375 × 812, con axe).

Archivos: `frontend/app/(public)/register/page.tsx`, `frontend/components/access/SignupAvatarDialog.tsx`, `frontend/components/features/title/DialogShell.tsx`, `frontend/tests/access-screens.test.tsx`, `frontend/e2e/registro.spec.ts`, `frontend/e2e/acceso.spec.ts`, `frontend/e2e/i18n-flows.spec.ts`, `frontend/e2e/axe.ts`, `traducciones/claves.csv` y los catálogos generados.

### 16/11/2026 — Alta con Google en los pasos 2 y 3 del registro (canvas, sección 16)

`/complete-signup` deja de ser una pantalla aparte y pasa a ser los pasos 2 y 3 del registro, como en los artboards `Prop-Registro-Google*`. «Continue with Google» es el paso 1: la persona llega al paso 2 de 3 con la misma barra (se llena de 33 % a 67 %) y el mismo título «Create your account». Debajo del título, la marca de Google y «Your name and email come from your Google account.».

- **Paso 2:** usuario (disponibilidad en vivo), fecha de nacimiento, género y país. «Continue ›» valida el paso como en el registro con correo.
- **Paso 3:** avatar opcional con el mismo diálogo paginado y los Términos. La acción es el botón oficial de Google, inerte y al 40 % hasta aceptar los Términos, con «Accept the Terms and Conditions to continue.» debajo del recuadro. Va en una fila de 52 px para que «‹ Back» quede a la misma altura que con «Continue ›». En escritorio el botón mide 400 px, el máximo que acepta Google, centrado en la fila.
- **Back:** en el paso 3 vuelve al 2 y conserva lo escrito. En el paso 2 vuelve al origen (Sign up o Log in) y descarta el alta pendiente; reemplaza a «Cancel and go back to log in». Para saber el origen, la marca `google_signup_pending` de `sessionStorage` guarda `"register"` o `"login"` en lugar de `"1"` (la marca vieja se sigue aceptando).
- **Error del servidor:** si el usuario quedó tomado, vuelve al paso 2 con el error en el campo y el aviso «Fix the highlighted field and press the Google button again.». Los errores de Términos, avatar o generales se quedan en el paso 3, en un renglón reservado.
- **Sin saltos:** misma regla que el registro con correo. Los pasos 2 y 3 comparten una celda de grilla y nada se mueve en ningún momento (un e2e lo mide en escritorio y celular, en inglés y en español). El canvas ponía el aviso del servidor arriba del formulario, donde lo habría empujado: queda arriba del paso 2, en un lugar que el paso reserva siempre. Por eso, sin error, hay un espacio vacío sobre «Username». Se actualizaron los artboards `Prop-Registro-Google*` (versión 482).
- **Backend:** `GoogleSocialLoginSerializer` acepta `avatar_id` opcional, validado igual que en el alta con correo (`avatar_invalid`), y el adaptador lo guarda en la cuenta nueva. Una cuenta que ya existe conserva su avatar. El contrato `contracts/openapi.yaml` se regeneró.
- **Piezas compartidas:** la barra, la celda de paso, el recuadro de avatar, los Términos con renglón reservado y «‹ Back» salen a `frontend/components/access/signup-steps.tsx`, que usan las dos pantallas.

Archivos: `backend/usuarios/serializers.py`, `backend/usuarios/adapter.py`, `backend/usuarios/tests.py`, `contracts/openapi.yaml`, `frontend/app/complete-signup/page.tsx`, `frontend/app/(public)/register/page.tsx`, `frontend/components/access/signup-steps.tsx`, `frontend/lib/google-auth.ts`, `frontend/tests/complete-signup.test.tsx`, `frontend/tests/google-auth.test.ts`, `frontend/tests/access-screens.test.tsx`, `frontend/e2e/alta-google.spec.ts`, `traducciones/claves.csv`, `traducciones/claves-extra.csv` y los catálogos generados.

### 16/11/2026 — «Continue» del paso 2 mientras se verifica el nombre de usuario

PR-Agent marcó en #225 que, con la verificación del nombre de usuario en curso, «Continue» del paso 2 no hacía nada ni avisaba. Además, si la consulta fallaba (red o 429 (Too Many Requests)), el estado quedaba en «idle» y el paso no avanzaba nunca. Ahora solo bloquean «ocupado» y «reservado». Con la consulta en curso, el clic queda pendiente: el botón pasa a `disabled` con `aria-busy`, sin cambiar texto ni tamaño, y al llegar la respuesta avanza o muestra el error del campo. Editar un campo del paso cancela lo pendiente. Si la consulta falló, se deja avanzar: el backend valida el usuario al enviar y el formulario vuelve al paso 2 con el error. Vale igual para el registro con correo y para el alta con Google. Los otros dos comentarios de PR-Agent no aplicaban: el import de `useEscritorio` en `Navbar.tsx` sí se usa, y las claves de traducción ya estaban en `traducciones/claves.csv`.

Archivos: `frontend/app/(public)/register/page.tsx`, `frontend/app/complete-signup/page.tsx`, `frontend/tests/access-screens.test.tsx`, `frontend/tests/complete-signup.test.tsx`.

### 19/11/2026 — Arreglos de la revisión del #225 (registro en 3 pasos)

Revisión de Gonza sobre el #225, aplicada sobre la rama de Marcos (sin cambios suyos desde el 17/11):

- **`traducciones/claves.csv` vuelve a CRLF**, como en `develop` (la rama lo había pasado a LF y el diff mostraba el archivo entero). El diff contra `develop` son solo las 19 líneas nuevas; las 9 líneas que en `develop` ya eran LF se dejaron tal cual. No se agrega `.gitattributes`: queda como decisión aparte.
- **Copy de `auth.completeSignUp.fixHighlighted`** (fuente: `traducciones/claves-extra.csv`): el aviso sale en el paso 2, donde no está el botón de Google, así que ahora dice «volvé a confirmar con Google en el paso 3» (en inglés, «confirm with Google again in step 3»).
- **Accesibilidad**: región `sr-only` con `aria-live="polite"` que dice «Paso N de 3» al cambiar de paso (reusa `auth.signUp.stepOf`, sin clave nueva) en `SignupProgress`; un «Continue» con errores enfoca el primer campo inválido (también cuando la verificación del usuario termina en «en uso»); el `<select>` de género apunta con `aria-describedby` a su mensaje de error; en `/register`, el error del servidor sobre el avatar queda vinculado a «Choose» con `describedBy`.
- **`/complete-signup`**: un error general del paso 3 (p. ej. Google caído) se borra al volver al paso 2. Se limpia en «Back» y no en `irA(2)`, porque `irA(2)` también lo usa el rechazo del servidor para volver al campo con error y ahí `fallo` hay que conservarlo; los errores de campo del paso 2 se conservan hasta que el usuario los corrige.
- **No se cambia** «Continue with Google» en `/register` con una cuenta ya existente (va directo a `/complete-signup` sin probar antes el login; ya pasaba antes de este PR): queda como hallazgo y decisión de diseño aparte.

Archivos: `traducciones/claves.csv`, `traducciones/claves-extra.csv`, `frontend/messages/{en,es}/common.json`, `frontend/components/access/signup-steps.tsx`, `frontend/app/(public)/register/page.tsx`, `frontend/app/complete-signup/page.tsx`, `frontend/tests/access-screens.test.tsx`, `frontend/tests/complete-signup.test.tsx`.

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

Para cumplir el tope de 6 meses de los términos de TMDB, la tarea de refresco vuelve a pedir cada producción. Cuando TMDB responde 404 (Not Found) dos noches distintas, la fila se borra si nadie la usa. Si alguien la calificó, la reseñó o la tiene en una lista, queda como lápida: solo `id_tmdb` y `tipo`, sin contenido de TMDB ni embedding, y `disponible_en_tmdb = False`. Solo cuenta el 404 (Not Found); cualquier otro error se reintenta. `Calificacion`, `Resena` y `Tiene` pasan a `PROTECT`, así que el borrado nunca se lleva lo que hizo un usuario, y la lápida vuelve si TMDB restaura el título. No aparece en recomendaciones, búsquedas ni en el chatbot. En las listas y en Mis reseñas se ve una tarjeta gris «Title no longer available», sin enlace, con la nota y la reseña, y se puede quitar o borrar como siempre. Alternativas descartadas: dejar la fila como está (no cumple los términos) y borrarla siempre (el usuario pierde su actividad). Lo decidió Gonza; se implementa en el PR 2 del cambio.
Archivos: `openspec/changes/tmdb-cumplimiento/design.md`, `openspec/changes/tmdb-cumplimiento/tasks.md`, `openspec/changes/tmdb-cumplimiento/specs/tmdb-compliance/spec.md`, `openspec/changes/tmdb-cumplimiento/proposal.md`, `docs/05_Plan_de_Desarrollo.md`

### 12/11–13/11/2026 — El aviso de una sync fallida se decide al desplegar (CU-021) y revisión de los pendientes

El aviso al administrador cuando la sync falla entera deja de ser un pendiente propio y pasa a «Lo que se resuelve al desplegar»: sin despliegue no hay a quién avisar, y en local el fallo se ve en el log de Docker. No se elige herramienta. Cómo registrar y auditar las tareas programadas se decide en esa etapa, con más conocimiento del tema. El plan deja las opciones relevadas sin preferencia: correo a `ADMINS`, historial de corridas en el admin de Django, seguimiento de errores con monitoreo de tareas (Sentry o GlitchTip), heartbeat externo y logs centralizados con alertas. Por el mismo motivo, la línea de seguridad de ese punto dice «seguimiento de errores (herramienta a definir)» en lugar de «Sentry». Se anotó que un historial con una fila por corrida no crece de forma relevante (unos 2 MB en 10 años) y que el detalle por ítem iría al log, no a la base. CU-021 ya lo marcaba como mejora futura; C-04b sigue 🟡 por esto.

El mismo día se cerró la revisión de la lista de pendientes. Perfil público y notificaciones por correo pasan a ser un pendiente propio, el último (9): amplían el alcance y se decide con Gonza si entran; si no, se sacan sus controles de Settings. El pendiente 2 deja de mostrar el tope de vueltas como abierto, porque lo cerró #189. En el pendiente 7 se anotó que los `.eml` de revisión están desactualizados, y en el canvas se quitó la franja dorada de los cuatro correos, que el código ya no tiene desde el 06/11/2026 (#175).
Archivos: `docs/05_Plan_de_Desarrollo.md`

### 13/11/2026 — Primer clic en una ficha más rápido

Medido en frío (sin las claves `tmdb:*` del título en Redis, tras 8 s sin tráfico): el detalle tardaba ~540 ms y los créditos ~210 ms; con caché, 20-30 ms. Tres causas y un efecto: (1) httpx cierra las conexiones ociosas a los 5 s y reabrir TLS contra TMDB cuesta ~300 ms; (2) el respaldo en inglés usaba otro `httpx.Client` y abría su propia conexión; (3) las tarjetas del chat no encolaban la materialización, así que su ficha siempre abría en frío; (4) Redis estaba al 99 % (254/256 MB) porque los créditos se guardaban enteros (hasta 260 KB) y dos veces (copia normal y de respaldo), aunque la ficha usa 50 actores y los directores.

Cambios: las conexiones ociosas duran 60 s y los dos idiomas comparten un solo cliente HTTP (`crear_http_client`, inyectable en `TMDBClient`); al guardar un turno del chat se encola `materializar_listado_en_segundo_plano` con sus tarjetas (si el broker falla, se registra y el turno sigue); `loading.tsx` en `/movie/[id]` y `/tv/[id]` muestra el esqueleto de `TitleView` (extraído a `TitleSkeleton`) en el instante del clic; los créditos se guardan recortados (50 actores con personaje y los directores) y en una sola clave de 30 días cuya frescura de 24 h se mide con su TTL (`UNA_SOLA_CLAVE`), así se conserva el respaldo sin duplicar. La clave pasó de `credits` a `creditos_ficha`: las entradas viejas ya no se leen y vencen solas (`redis-cli --scan --pattern 'tmdb:credits:*'` y `'tmdb:respaldo:credits:*'` las listan si se quieren borrar antes).

Medición (10 títulos, Redis vacío, 8 s ociosos, mismo script antes y después): detalle 540 ms → 180 ms; créditos de 833 KB en Redis a 20 KB (42 veces menos, 20 claves a 10); el tiempo de los créditos queda en ~200 ms porque es una llamada propia a TMDB cuando la caché está vacía. Con caché, la ficha sigue en 20-30 ms.
Archivos: `backend/catalogo/client.py`, `backend/catalogo/cache.py`, `backend/catalogo/services/tmdb.py`, `backend/chatbot/servicio.py`, `frontend/components/features/title/TitleSkeleton.tsx`, `frontend/components/features/title/TitleView.tsx`, `frontend/app/movie/[id]/loading.tsx`, `frontend/app/tv/[id]/loading.tsx`

### 13/11/2026 — Cuota nocturna de la tarea de refresco (#180)

El diseño refrescaba hasta 300 filas por noche (`CELERY_REFRESCO_LIMIT`). Ese tope no crece con el catálogo, que solo va a crecer, y si se cargan 10 000 títulos en un mismo día unas 1 200 filas pasarían los 180 días. Ahora la tarea calcula cada noche cuántas filas refresca: `min(CELERY_REFRESCO_TECHO, max(rotación, plazos))`. La rotación es `ceil(total ÷ 150)` y renueva siempre las filas más viejas, así el catálogo da una vuelta cada 150 días y una carga masiva queda repartida después de su primera vuelta. Los plazos son la menor cantidad por noche con la que ninguna fila llega a los 180 días: con las 10 000 cargadas juntas, 334 por noche durante 30 noches. El techo (1000) evita que una noche rara ocupe el worker, y el resumen avisa si los plazos piden más. Cuesta un `COUNT` y un `GROUP BY` sobre `fecha_enriquecimiento`, que se indexa. El cálculo es una función pura que se testea sin base. Descartados: subir el tope fijo (hay que volver a ajustarlo) y escalonar las fechas al cargar (no cubre las cargas que no pasan por el seed).
Archivos: `openspec/changes/tmdb-cumplimiento/design.md`, `openspec/changes/tmdb-cumplimiento/specs/tmdb-compliance/spec.md`, `openspec/changes/tmdb-cumplimiento/tasks.md`, `openspec/changes/tmdb-cumplimiento/proposal.md`, `docs/05_Plan_de_Desarrollo.md`

### 13/11/2026 — Créditos de TMDB: logo, aviso y nombre (#180, PR 1)

Se eligió en el canvas el logo `logo5.svg` (horizontal corto) y se implementó: una sección «Credits» al final de `/terms` (`id="credits"`) con el logo como enlace a `https://www.themoviedb.org` y el aviso exacto «This product uses the TMDB API but is not endorsed or certified by TMDB.» (en español, «Este producto usa la API de TMDB, pero TMDB no lo respalda ni lo certifica.»), y en el pie el mismo aviso, el logo chico y un enlace «Credits» a `/terms#credits`. La cláusula 7 de los términos usa el mismo aviso y conserva su frase de responsabilidad. El logo se sirve como `<img>` desde `frontend/public/tmdb/logo5.svg`, copia idéntica byte por byte de `docs/tmdb-legales/logo5.svg` (un test lo compara), sin filtros ni `currentColor`; solo se fija el alto (20 px en Terms desktop, 18 px en celular, 16 px en el pie), así se mantiene la proporción. Es menos prominente que la marca FilmAI y no aparece en el header, el hero, el chat ni junto a un título.

- **Solo tema oscuro**: la tarea pedía comparar en «los dos temas», pero el tema claro se descartó el 18/10/2026. Con Marcos (13/11/2026) se comparó solo en oscuro: 5 combinaciones en lugar de 10, y no hay prueba en tema claro. Si algún día vuelve el tema claro habrá que revisar cómo se lee el degradé verde-celeste sobre fondo claro (se cambiaría el fondo del bloque, nunca el logo).
- **Claves**: las del bloque quedaron en `tmdb.credits.{title,notice,logoAlt}` y no en `legal.credits.*`, porque `generate.py` descarta el namespace `legal` (el texto legal vive en `content/legal/*.md`). `footer.main.tmdbAttribution` conserva su nombre con el aviso nuevo y se suma `footer.main.creditsLink`.
- **Correos**: no se tocan. «Datos e imágenes de películas y series provistos por TMDB» nombra bien a TMDB y no afirma aval; el aviso se exige «en la aplicación».
- **Auditoría de nombres**: sin hallazgos. Las coincidencias de `TMDb`, `Tmdb` y `themoviedb` en traducciones, catálogos, texto legal, correos, prompt del chat y `docs/` eran identificadores (`id_tmdb`) o URLs de la API (`api.themoviedb.org`, `developer.themoviedb.org`), no palabras visibles ni enlaces al sitio. La regla quedó en `scripts/i18n/naming.mjs`, que corre dentro de `npm run i18n:check` y en un test de Vitest: falla, nombrando el archivo o la clave, ante «TMDb», «Tmdb», «The Movie DB» o un enlace a `themoviedb` que no sea `https://www.themoviedb.org`.

Archivos: `frontend/components/TmdbCredits.tsx`, `frontend/components/Footer.tsx`, `frontend/app/terms/page.tsx`, `frontend/public/tmdb/logo5.svg`, `frontend/content/legal/terms.{en,es}.md`, `traducciones/claves.csv`, `frontend/messages/`, `frontend/scripts/i18n/naming.mjs`, `frontend/scripts/i18n/check.mjs`, `frontend/tests/tmdb-credits.test.tsx`, `frontend/tests/tmdb-naming.test.ts`, `frontend/tests/footer.test.tsx`, `frontend/e2e/tmdb-creditos.spec.ts`, `docs/04_Lineamientos_UI.md`

### 13/11/2026 — Refresco nocturno, lápida y tope de caché implementados (#180, PR 2)

Se implementó la fase 2 del cambio `tmdb-cumplimiento`. `catalogo.refrescar_vencidos` corre a las 03:30 (`catalogo/services/vencimiento.py`, tarea en `catalogo/tasks.py`) con la cuota del 13/11: `cuota_nocturna(total, por_dia, techo)` es pura y la consulta cuesta dos queries (un `COUNT` y un `GROUP BY` por el día de enriquecimiento, solo de las filas que cumplen 180 días en los próximos 30), con un índice nuevo sobre `fecha_enriquecimiento`. El día se cuenta desde las 00:00 de la fecha de enriquecimiento, así que el error va siempre del lado seguro (pide algo más por noche, nunca menos). Settings: `DIAS_REFRESCO_TMDB = 150` y `CELERY_REFRESCO_TECHO = 1000`. El resumen del log trae la cuota y cuál de los tres números la fijó (`rotacion`, `plazos` o `techo`), refrescadas, no encontradas, borradas, lápidas, fallidas y cuántas filas siguen con más de 180 días (`WARNING` si hay alguna, o si el techo limitó la cuota); las filas sin fecha se informan aparte porque su edad real se desconoce.

La regla del 404 (Not Found) quedó como en el diseño: el primero anota `fecha_404`; el segundo, en una noche posterior, borra la fila si nadie la usa o la deja como lápida (sin contenido, sin traducciones ni embedding, `disponible_en_tmdb = False`). Un refresco exitoso restaura la fila y limpia `fecha_404` (se hace en `_enriquecer`, así lo hace cualquier camino de escritura). Detalles que el diseño no fijaba: (1) una lápida también rota cada 150 días y, si ya nadie la usa, el siguiente 404 (Not Found) la borra; (2) el borrado captura `ProtectedError` e `IntegrityError` (la clave foránea de Postgres es la última barrera si una calificación llega entre la lectura de Django y el `DELETE`); (3) `traducciones.pendientes()` ignora las lápidas, porque si no pediría su traducción a TMDB todas las noches y recibiría 404 (Not Found).

**`PROTECT` solo en `Calificacion.produccion` y `Tiene.produccion`.** El diseño decía «`Calificacion`, `Resena` y `Tiene`», pero `Resena` no tiene clave a la producción: apunta a `Calificacion` (1:1, `CASCADE`). Una reseña no existe sin su calificación, así que queda protegida de forma transitiva. Pasar `Resena.calificacion` a `PROTECT` habría roto el borrado de una calificación y el de un usuario sin proteger nada más (decidido con Marcos). Antes del cambio se revisó cada lugar que borra producciones: `_descartar_cascaron` ahora atrapa `ProtectedError` y conserva el cascarón (un 404 (Not Found) nunca se vuelve 500 (Internal Server Error)); `seed.py` borra ítems, calificaciones y reseñas antes que las producciones; el admin no registra `ProduccionAudiovisual`; y ningún test dependía del `CASCADE` (la suite completa pasó sin cambios).

**Dónde no aparece una lápida:** la búsqueda semántica (filtro `disponible_en_tmdb`, además de que el embedding se borra), `mis_listas` y el perfil del chatbot, y el relleno de traducciones. Recomendado y Explorar salen de TMDB, que ya no tiene el título; la ficha responde 404 (Not Found) por lo mismo. En las listas y en Mis reseñas el serializador agrega `disponible` (booleano, `false` en la lápida, con título y póster vacíos) y el frontend muestra la tarjeta gris «Title no longer available» / «Título no disponible» (clave nueva `common.content.titleUnavailable`, copia en español aprobada), sin enlace, con la nota y la reseña, y los controles de quitar y borrar de siempre. Opción descartada: inferir la lápida de un título vacío (frágil, y el PR 3 ya usa `titulo: null` en el chat).

**Una lápida no se puede calificar ni agregar a una lista (14/11/2026).** `materializar()` es la puerta común de ambos POST y trataba la lápida como fila completa (su fecha es de hoy), así que `POST /api/reviews/` y `POST /api/lists/<id>/items/` respondían 201 (Created) sobre un título sin contenido. Ahora, sin `forzar`, una lápida lanza `TMDBNotFound` y el pedido responde 404 (Not Found), igual que ante un id desconocido; solo el refresco nocturno (`forzar=True`) puede restaurarla. Tests en `catalogo/tests_lapida.py` (`LapidaNoSeAceptaDeNuevoTests`). La copia en español de la tarjeta pasó a «Título no disponible» (aprobada por Marcos).

Tope de caché: `catalogo/test_cache_tope.py` fija que ningún TTL de `ENDPOINT_TTLS`, `RESPALDO_TTL`, `RESPALDO_TTLS` ni el `max-age` del catálogo pasa de 180 días (el mayor hoy es de 30). Un test confirma que el refresco respeta `Retry-After` en un 429 (Too Many Requests), porque pasa por el mismo cliente. Esas dos pruebas ya pasaban antes del cambio: fijan lo que había.

Prueba manual (2.11) contra la base de desarrollo, con la migración aplicada de forma temporal y revertida al terminar: 585 filas, 4 sin fecha; cuota 4 (rotación 4, plazos 4); refrescó 4, ninguna falló; 16 llamadas a TMDB (4 por fila: detalle, créditos, keywords y la traducción) en 3,9 s. Con 10 000 filas y la cuota de 67 serían unas 270 llamadas por noche.

Archivos: `backend/catalogo/services/vencimiento.py`, `backend/catalogo/tasks.py`, `backend/catalogo/models.py`, `backend/catalogo/migrations/0008_lapida_tmdb.py`, `backend/listas/models.py`, `backend/listas/migrations/0008_lapida_tmdb.py`, `backend/catalogo/services/materialization.py`, `backend/filmai/settings.py`, `backend/catalogo/services/semantica.py`, `backend/catalogo/services/traducciones.py`, `backend/chatbot/tools/personales.py`, `backend/chatbot/contexto.py`, `backend/listas/serializers.py`, `backend/catalogo/serializers_reviews.py`, `frontend/components/features/UnavailableCard.tsx`, `frontend/components/features/reviews/MyReviewItem.tsx`, `frontend/components/features/lists/ListDetailView.tsx`, `traducciones/claves-extra.csv`

### 13/11/2026 — Cierre del #180: uso con IA, regla de 180 días, medición y excepciones (PR 4)

Cierra el #180 (términos de uso de TMDB). Cada parte tiene su entrada con el detalle, y esta no las repite: créditos y logo en «Créditos de TMDB: logo, aviso y nombre» (#194); cuota nocturna en «Cuota nocturna de la tarea de refresco» y la tarea, la lápida y el tope de caché en «Refresco nocturno, lápida y tope de caché implementados» (#193); el recorte de tarjetas en «Recorte nocturno de las tarjetas del chat y rehidratación» (#196).

- **Uso con IA (07/11/2026)**: los términos de TMDB piden un acuerdo comercial para usar su contenido en aplicaciones de ML o IA y en chatbots. FilmAI usa títulos, sinopsis y géneros en el chatbot (tools y prompt) y en los embeddings de BGE-M3. Se acepta porque es un proyecto académico (Seminario Integrador, UTN-FRSF) sin fines de lucro. La condición es no generar ingresos ligados al contenido de TMDB: cualquier anuncio, suscripción o plan pago obliga a hablar antes con el equipo comercial de TMDB (issue #180). No cambia código. Queda una línea en `PRODUCT.md`, en «Capacidades y restricciones».
- **Regla de 150/180 días**: el contenido de TMDB no puede guardarse más de 180 días sin refrescarse. La fecha de referencia es `fecha_enriquecimiento`, que ya existía (sin columna nueva), y una fila vence a los 150 días (`DIAS_REFRESCO_TMDB`): los 30 días hasta 180 cubren más de una semana de noches fallidas. La tarea de las 03:30 refresca cada noche la cuota que calcula (rotación, plazos y techo de 1000), así el catálogo da una vuelta cada 150 días y una carga masiva queda repartida. Se refresca y no se borra: la calificación, la reseña y los ítems de lista cuelgan de la producción.
- **Regla del 404 (Not Found), como quedó acordada (Gonza, 12/11/2026)**: solo cuenta un 404 (Not Found), y el segundo en una noche posterior. Sin referencias se borra la fila; con referencias queda una lápida y se ve «Title no longer available» en listas y Mis reseñas. Una lápida no se califica ni se agrega a una lista (ver la entrada de #193).
- **Recorte de tarjetas del chat**: acota la decisión del 09/10/2026 de guardar las tarjetas tal como se mostraron. Pasados 180 días quedan `{id_tmdb, tipo}`, y el historial las rehidrata desde el catálogo sin llamar a TMDB. Las conversaciones vivas se ven igual que antes.
- **Tasa de pedidos medida (4.1)**: con el contador de `registrar_llamada`, en un proyecto de compose aparte (`-p filmai-cierre`, sin tocar la base compartida) y con Redis vacío antes de cada fase, el pico fue de 6 a 7 pedidos por segundo en un proceso (seed de 200 títulos, sync, `rellenar_traducciones --limite 200` y refresco: 813, 457, 400 y 1020 pedidos). El cliente es síncrono, así que el ritmo lo fija la latencia de TMDB. Con el worker en concurrencia 2 más un seed manual serían unos 21 por segundo (estimado), por debajo del umbral de 30 (un margen sobre los 40 por segundo que fija el issue): no se agrega un limitador compartido. Los números están en `docs/06_TMDB_API_Referencia.md`. Una primera corrida dio 0 pedidos en tres fases porque `cache.clear()` vacía la caché local de Django con `DEBUG=True` y no el Redis de TMDB; se repitió con `flushdb` sobre el Redis aislado.
- **Verificaciones (4.2 y 4.3)**: ningún pedido a TMDB esquiva `catalogo/client.py` (la única referencia a `api.themoviedb.org` es el default de `TMDB_API_BASE_URL`, y el único otro `httpx.Client` habla con Ollama), y `image.tmdb.org` solo aparece en `frontend/lib/catalog.ts` y en tests y fixtures.
- **Excepciones aceptadas**: (1) el collage de las pantallas de acceso (`frontend/public/collage-posters/Opcion 1.jpg`) tiene pósters guardados desde el 13/08/2026 y llega a 6 meses el **13/02/2027**: antes de esa fecha hay que reemplazarlo o decidir de nuevo; (2) los fixtures de prueba (`frontend/e2e/api-simulada.ts`, `backend/catalogo/test_datos/tmdb_buscar.json`) son copias de respuestas de TMDB que nunca se sirven. Las dos se aceptaron el 07/11/2026.
- **Specs**: nueva `openspec/specs/tmdb-compliance/`; actualizadas `catalog-daily-sync`, `catalog-materialization`, `tmdb-cache`, `chat-api` y `chat-ui`. `openspec/changes/tmdb-cumplimiento/` se archivó (se borró).

Archivos: `docs/06_TMDB_API_Referencia.md`, `PRODUCT.md`, `docs/05_Plan_de_Desarrollo.md`, `openspec/specs/tmdb-compliance/spec.md`, `openspec/specs/catalog-daily-sync/spec.md`, `openspec/specs/catalog-materialization/spec.md`, `openspec/specs/tmdb-cache/spec.md`, `openspec/specs/chat-api/spec.md`, `openspec/specs/chat-ui/spec.md`

### 13/11/2026 — Filtro de contenido adulto en el cliente de TMDB

Gonza pidió que nada de lo que la app lista o recomienda traiga títulos para adultos. Todo lo de TMDB (Inicio, Buscar, chatbot, seed, sync, títulos parecidos) pasa por `TMDBClient._request`, así que el filtro vive ahí y cubre todos los caminos de una vez: `_sin_adultos` saca de `results`, `cast`, `crew` y `known_for` lo que TMDB marca `adult: true`; el detalle de un título adulto lanza `TMDBNotFound` (404 (Not Found) en la ficha, la materialización no guarda la fila y la sync lo trata como 404 (Not Found)). `discover`, `search` y `search_person` piden `include_adult=false` explícito (ya era el default de TMDB, pero un default ajeno no es una garantía).

TMDB **no marca `adult` el erotismo «softcore»** (verificado el 13/11/2026: la keyword 155477 trae 3.682 películas con `adult: false`, p. ej. «9 Songs» o «Emmanuelle»). `discover` agrega `without_keywords=155477` (se probó que anda en películas y series), y las consultas sobre el catálogo local (`buscar_semantico`, `candidatos` de títulos parecidos) excluyen las filas cuyo `keywords` incluye «softcore» (`models.KEYWORD_SOFTCORE`). Límite conocido: `search`, `trending` y `recommendations` no filtran por keyword, así que un softcore sin marca puede aparecer al buscarlo por nombre. Cerrarlo exigiría pedir las keywords de cada resultado (una llamada por título); no se hizo y queda como pregunta. Los títulos adultos que ya estuvieran en el catálogo local no se borran.

Archivos: `backend/catalogo/client.py`, `backend/catalogo/models.py`, `backend/catalogo/services/semantica.py`, `backend/catalogo/services/similares.py`, `backend/catalogo/test_filtro_adulto.py`, `backend/catalogo/tests_semantica.py`, `backend/catalogo/tests_similares.py`.

### 13/11/2026 — Recorte nocturno de las tarjetas del chat y rehidratación (#180, PR 3)

TMDB no deja guardar su contenido más de 180 días sin refrescarlo, y cada tarjeta de `Mensaje.tarjetas` lleva título, póster y año copiados de TMDB. La tarea `chatbot.recortar_tarjetas` corre a las 04:30 (después del refresco de las 03:30) y deja las tarjetas de los mensajes con más de 180 días como `{id_tmdb, tipo}`. Es idempotente: solo toca mensajes que todavía tienen `titulo` y escribe con `bulk_update`. `DIAS_DE_TARJETAS = 180` está en `settings.py`.

- **`ya_recomendados`**: cada entrada lleva `fecha` (ISO). La escribe `servicio.sumar_recomendados` con `fecha_de_hoy()`, cada vez que una tarjeta se muestra, y una repetida la renueva. La tarea les quita `titulo` y `anio` a las de más de 180 días o sin fecha (las anteriores a este cambio). Se escribe en `servicio.py` y no en el orquestador, así que no choca con la red de tarjetas que reescribe el #192.
- **Prompt**: `servicio.titulos_recordados` resuelve en una sola query los títulos de las entradas recortadas, con el título canónico (en inglés: el idioma pediría otra query por las traducciones). Un id que no está en el catálogo, o es una lápida, queda fuera de la línea «Ya recomendados» pero sigue en la lista que evita repetir. El orquestador solo cambia una línea de `_preparar`.
- **Historial**: `HistorialView.paginate_queryset` rehidrata en memoria las tarjetas recortadas de la página (`recorte.rehidratar`) en el idioma de quien lee, con `texto_localizado`. Son 3 queries por página sin importar cuántas tarjetas haya (mensajes, producciones y sus traducciones), y 0 extra si no hay recortadas. No llama a TMDB ni escribe. Una producción que falta o es lápida vuelve con `titulo: null` (`poster`, `anio` y `nota_tmdb` también `null`).
- **Panel**: una tarjeta con `titulo: null` se dibuja con `UnavailableCard` en su variante `compact` (fila con miniatura gris y «Title no longer available», sin enlace). Solo el historial admite título nulo: `esTarjeta` sigue exigiéndolo en el stream. No hay textos nuevos (la clave `common.content.titleUnavailable` ya existía).
- **Contrato**: `Tarjeta.titulo` pasa a `nullable` en `contracts/openapi.yaml` y se aclara en `contracts/sse-chat.md`.
- **Concurrencia**: `guardar_turno` escribe `contexto` con `select_for_update`, así que la tarea detecta los chats a recortar sin candado y relee cada uno con candado antes de escribirlo (una escritura por chat que cambia, no `bulk_update`). Lo señaló PR-Agent y era real: reescribir la copia leída antes podía pisar la tarjeta de un turno a las 04:30.
- **Costo conocido**: la tarea recorre los mensajes de más de 180 días que aún tienen título, y esa consulta no tiene índice sobre el JSON; con el volumen del MVP (un chat por usuario) es despreciable, y una vez recortados dejan de aparecer.

Archivos: `backend/chatbot/recorte.py`, `backend/chatbot/tasks.py`, `backend/chatbot/servicio.py`, `backend/chatbot/views.py`, `backend/chatbot/serializers.py`, `backend/chatbot/orquestador.py`, `backend/filmai/settings.py`, `backend/chatbot/tests_recorte.py`, `frontend/lib/chat.ts`, `frontend/components/features/UnavailableCard.tsx`, `frontend/components/features/chat/ChatTarjetas.tsx`, `contracts/`

### 21/11/2026 — Los títulos sin póster quedan fuera del descubrimiento

Decidido por Marcos (opción C). Medido ese día: 17 de 948 títulos de la base no tienen póster, y su tarjeta se veía rota.

- **Qué se decidió.** Siguen en la base y se encuentran por nombre (búsqueda con texto, `search/`) y por su ficha. No aparecen donde nadie los pidió: Home (`trending/`, `now-playing/`, `discover/`, «Recomendado»), Buscar sin texto y, desde antes, «More like» y las sugerencias de lista (D-5). `seed_catalogo` y lo que se materializa no cambian.
- **Dónde.** Una función, `tiene_poster`, y un helper, `con_poster`, en `services/browse.py`. Las vistas `Trending`, `NowPlaying` y `Discover` filtran la respuesta después de encolar la materialización (así lo materializado no cambia); `_lado` (Buscar sin texto) y `_de_un_tipo` («Recomendado») filtran al armar la lista. Las personas de `trending/` (`media_type` `person`) no son títulos y pasan. `search/`, Buscar con texto o con `persona` y las sugerencias de la navbar no filtran.
- **Paginación.** Los listados son páginas de TMDB, así que no se rellena: una página puede traer 1 o 2 ítems menos de 20 y `total_pages` y `total_results` siguen siendo los de TMDB. Se descartó rellenar pidiendo la página siguiente (más llamadas a TMDB, páginas que se solapan y desorden con «Todo», que alterna dos tipos) por un 1,8 % de títulos. `con_poster` devuelve una copia para no tocar el listado que guarda la caché.
- **Pruebas.** `catalogo/tests_sin_poster.py` (sin texto se descartan; con texto y en `search/` se encuentran; totales intactos; «Recomendado»). Los fixtures de `tests_browse.py`, `tests.py`, `test_cache_navegador.py` y `test_materializar_listados.py` ahora traen `poster_path`.

Archivos: `backend/catalogo/services/browse.py`, `backend/catalogo/services/recomendado.py`, `backend/catalogo/views.py`, `backend/catalogo/tests_sin_poster.py`, los tests con fixtures ajustados, `openspec/specs/tmdb-endpoints/spec.md` y este archivo.

### 21/11/2026 — Seed masivo: 500 cuentas, 80 % de reseñas y corpus versionado

Decidido por Marcos: poblar la base a lo grande para probar con volumen y que se parezca a producción.

- **Qué se decidió.** Comando nuevo `seed_masivo` (lógica en `backend/usuarios/seed_masivo.py`): 500 cuentas `masivo0001..` más `usuario001..003`, unas 38 calificaciones por cuenta (log-normal, de 3 a 300), 80 % con reseña (exacto, repartido al azar) y 1 de cada 7 reseñas inactiva. Mantiene los invariantes de `development-seed` y `reviews-api` (calificada ⇒ Vistas, Favoritos solo con 9 o más, un estado por título). Todo con `bulk_create`, un solo hash de contraseña y las listas y el chat por defecto creados a mano (el `bulk_create` no dispara la señal). Es determinista con `--semilla` y, sin `--reiniciar`, idempotente por correo. Las cuentas pendientes o de baja (3 %) no tienen actividad.
- **Reseñas solo en `seed_masivo`.** El 60 % de `seed --solo-resenas` y su texto de plantillas quedan intactos; `seed.py` no se tocó.
- **Corpus versionado.** Los textos viven en `backend/seed_data/resenas.jsonl.gz` (una línea por producción, idioma y banda; 2 textos por entrada; unos 430 títulos, 2 574 entradas y unos 300 KB comprimidos). Se versiona porque redactarlo cuesta tiempo y dinero del modelo y así cualquiera reproduce la misma base sin volver a generarlo. Va ordenado y con gzip de `mtime=0` para que los diffs sean chicos. No lleva datos de TMDB: solo id, tipo y las reseñas inventadas.
- **Redactado con Haiku.** Las reseñas las escribe un modelo (subagentes Haiku de Claude Code, con la cuota del plan Pro y no con API key), a partir de lotes de 25 títulos que genera `preparar_corpus_resenas` (título, año, géneros y sinopsis recortada, en una carpeta de trabajo fuera del repo) y se validan con `compilar_corpus_resenas`. Medido: unos 4 000 tokens por título (103 000 para un lote de 25, 300 reseñas, 3,5 minutos).
- **Banda de nota.** 1 a 4 baja, 5 a 7 media, 8 a 10 alta: el tono de la reseña debe ser coherente con la nota. El texto se elige por (título, idioma de la cuenta, banda).
- **Corpus híbrido y respaldo.** El corpus por título cubre unos 400 títulos, los más conocidos del catálogo; redactar los 10 000 costaría millones de tokens. Para el resto: (1) plantillas por género en `backend/seed_data/plantillas_genero.json` (24 géneros de TMDB × es/en × baja/media/alta × 4 frases, escritas con Haiku, válidas para cualquier título del género; se elige al azar uno de los géneros del título), y (2) si el archivo falta o el título no tiene género conocido, `seed_real.TEXTOS`. Faker se descartó para los textos: genera lorem ipsum, sin relación con la producción. El 80 % de reseñas no depende del origen del texto.
- **«Más conocidos».** `ProduccionAudiovisual` no guarda la cantidad de votos de TMDB. Ordenar por `calificacion_promedio` traía títulos desconocidos con 10 de nota y pocos votos, y por `pk` tampoco sirve (la base mezcla corridas de `seed` y `seed_catalogo`). Por eso `preparar_corpus_resenas --por-votos PAGINAS` lee `discover` ordenado por `vote_count.desc` de TMDB (3 películas por cada serie) y toma, en ese orden, los que están en la base. La popularidad con la que `seed_masivo` elige qué calificar sigue siendo una aproximación: promedio al cuadrado por un factor log-normal sembrado.
- **Tests.** `backend/usuarios/tests_seed_masivo.py` y `tests_corpus_resenas.py`.

Archivos: `backend/usuarios/seed_masivo.py`, `corpus_resenas.py`, `management/commands/seed_masivo.py`, `preparar_corpus_resenas.py`, `compilar_corpus_resenas.py`, los dos archivos de tests, `README.md`, `openspec/specs/seed-masivo/spec.md`, `docs/05_Plan_de_Desarrollo.md` y este archivo.

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

### 13/11/2026 — Buscar en la navbar, filtro por persona y títulos sin relevancia (diseño)

Diseño en `openspec/changes/busqueda-navbar/`, sin código todavía. Tres decisiones de Gonza:

- **Campo en la navbar de escritorio, a la derecha**, junto a la cuenta, con hasta 5 sugerencias; Enter o «See all results» lleva a `/search?q=…`. Sale el enlace «Search» de la izquierda; en celular `MobileTabs` no cambia y en `/search` el campo de la navbar no se muestra (la página tiene el suyo). La variante quedó elegida el 14/11 (entrada siguiente): la lupa que se despliega en un campo. Sugerencias desde un endpoint nuevo, `GET /api/catalogo/suggest/`, sobre `search/multi` de TMDB: una sola llamada por texto (cacheada 1 h), espera de 250 ms y mínimo de 2 caracteres, sin materializar y con su propio límite (`sugerencias`, 120/min). No se reusa `browse/`: con texto hace 10 llamadas (20 en español) y no devuelve personas. Combobox ARIA 1.2 con `aria-activedescendant`, como `CountrySelect`, y atajo `/`.
- **Filtro por persona**: las sugerencias incluyen actores y directores y llevan a Buscar con `person` y `role`. `browse/` lo resuelve con `combined_credits` (cacheado 24 h) y los demás filtros en memoria; `discover` con `with_people` no sirve (TMDB lo ignora en series). En series, «director» son los creadores (`job: "Creator"`), como ya muestra la ficha; los directores de episodios meterían ruido. El filtro activo se ve como un chip con ✕ arriba de los resultados.
- **Títulos sin relevancia**: con texto o persona solo se muestran los que tienen 5 votos o más o popularidad 5 o más, salvo que el título (traducido u original, sin tildes ni mayúsculas) sea igual al texto buscado; si ninguno pasa, se muestra todo. Lo demás no se muestra. **Se descartó un botón «See N more results»**: la gente lo aprieta y presta atención justo a lo irrelevante. Tampoco cuentan como señal `video`, la sinopsis ni `adult`.

Mediciones del 13/11 contra TMDB, en frío: `search/multi` entre 185 y 354 ms de mediana (máximo 613), `combined_credits` 208 ms (377 ms y 245 kB para Tom Hanks); en caliente, menos de 2 ms. Con el corte, «chihiro» pasa de 13 títulos a 3 y «the office» de 158 a 35; la popularidad conserva los estrenos sin votos (Dune: Part Three, The Batman: Part II). Preguntas abiertas en la propuesta: rol fijo por la sugerencia, gente de guion o producción, orden de la filmografía y enlaces desde el reparto de la ficha.
Archivos: `openspec/changes/busqueda-navbar/`, `docs/05_Plan_de_Desarrollo.md`

### 13/11/2026 — Títulos parecidos en listas y en la ficha (diseño)

Un solo motor (`catalogo/services/similares.py`) para dos filas: «Suggested for this list» al final del detalle de las listas personalizadas y Favoritos (no Pendientes ni Vistas), con «+ Add» y «Refresh», y «More like {title}» en la ficha, con y sin sesión. Una ficha es una lista de un título. Lo decidido por Gonza: desde 1 título, el nombre de la lista suma al vector si dice algo, se excluye «Vistas» (en la ficha, solo con sesión; también en Favoritos), películas y series mezcladas salvo en listas de un solo tipo, que traen solo ese tipo, y relleno con `/recommendations` de TMDB si hay pocos parecidos. El 13/11 respondió D-1 a D-9 con la recomendación del diseño, salvo D-6: la fila va siempre al final de la lista, también con filtros o búsqueda activa (y debajo del estado vacío del filtro), y las sugerencias salen siempre de la lista entera. La ficha muestra 20 tarjetas sin «Refresh»; la copia se aprueba con el canvas. Diseño: promedio de vectores en SQL (`avg()`; en Python tardaba 20 veces más con 1000 títulos), peso del nombre `max(0,15; 1/(n+1))`, exclusión en SQL con `hnsw.iterative_scan` (sin eso, excluir 1000 vecinos devolvía 0 de 100), umbral de distancia inicial 0,40 a calibrar, un pozo de 60 barajado con semilla que «Refresh» pagina sin recalcular, caché por firma de la lista (agregar, quitar o renombrar cambia la clave; calificar no) y por título en la ficha, sin datos del usuario. Si Ollama no tiene el modelo cargado no se espera: se omite el nombre y el pozo dura 5 minutos. Medido: consulta completa entre 20 y 35 ms con 6077 vectores. `/recommendations` agrupa por tema y no por país (para _Relatos salvajes_ trajo casi todo en inglés), por eso lo local va primero.
Archivos: `openspec/changes/recomendaciones-similares/`

### 13/11/2026 — Títulos parecidos: motor y endpoint de la ficha (PR 1)

`catalogo/services/similares.py` hace los tres pasos del diseño (semillas → pool → página) y `GET /api/catalogo/{movie|tv}/{id_tmdb}/similar/` lo usa con un título como semilla: hasta 20 tarjetas, con o sin sesión, el pool en la caché por título, idioma y modelo (24 h; 10 min si el título no tiene vector; 5 min si TMDB falló) y «Vistas» sacadas después de leerlo. Con sesión la respuesta es `private`; sin sesión, `public, max-age=300` con `Vary: Accept-Language`.

Donde el código real pidió algo distinto del diseño se eligió lo más simple que cumple la spec:

- **`Pool.entradas`, una sola lista**, en vez de `ids_locales` y `tmdb` por separado: el orden «locales cercanos, TMDB, locales lejanos» y la mezcla con pesos recorren las dos fuentes juntas. Cada entrada lleva `(id_tmdb, tipo)`, así «Vistas» se saca sin ir a la base y solo se leen las producciones de la página pedida.
- **`candidatos` con el ORM** (como `_ids_mas_cercanos` de B-06) y devolviendo `Candidato(pk, id_tmdb, tipo, distancia)`: el relleno necesita el par para no repetir. Los dos `SET LOCAL` y la consulta siguen en un `transaction.atomic()`. El test de los 1 000 vecinos fuerza el índice (`enable_seqscan = off`): sin `iterative_scan` devuelve 0 filas de 100.
- **`relleno_tmdb` devuelve `Relleno(tarjetas, completo)`**: quien arma el pool tiene que saber si TMDB falló para guardarlo solo 5 minutos.
- **Tope real de 6 llamadas**: `tope_de_llamadas(6)` en `catalogo/presupuesto.py` baja el tope del pedido mientras dura el relleno. Contar semillas no alcanzaba: cada llamada se reintenta hasta 3 veces. Ante un fallo de TMDB que no sea 404 (Not Found) no se prueba con las semillas que faltan.
- **Sesión opcional**: se reutiliza `LenientJWTCookieAuthentication`, que ya trataba una cookie vencida o inválida como «sin sesión» en el login; se mudó de `usuarios/views.py` a `usuarios/authentication.py` para no importar un módulo de vistas desde otra app. Sin ella, DRF respondía 401 (Unauthorized) antes de mirar `AllowAny`.
- **`SimilaresView` no hereda de `CatalogoBaseView`** (pública y cacheable para cualquiera, como ya pasaba con `ProvidersView` y `RecommendedView`) y por eso tampoco comprime con gzip.
- **La caché es la de Django** (`django.core.cache`): Redis con JSON en producción, memoria del proceso con `DEBUG=True`. El pool solo lleva tipos que JSON sabe escribir.

Medido el 13/11/2026 contra la base local (6 077 vectores), con el cliente de pruebas de Django dentro del contenedor (sin red ni navegador): pool en caché, 2 a 3 ms; en frío solo local, 12 a 14 ms; en frío con relleno de TMDB sin cachear, 205 a 232 ms (1,4 s la primera llamada del proceso, que abre la conexión TLS); en frío con TMDB ya en Redis, 20 ms. Con el piso de calidad, el vecino número 20 de un título está a 0,355 de mediana (p90 0,411): con `DISTANCIA_MAXIMA = 0.40`, el 14 % de 300 títulos al azar tiene menos de 20 cercanos y recibe relleno. Memento, Attack on Titan, Death Note y Breaking Bad tienen 100 vecinos bajo el umbral y no llaman a TMDB; _Relatos salvajes_ no está en el catálogo local y sale entera de TMDB, casi todo cine en inglés (el límite conocido de `/recommendations`).

Queda para decidir con Gonza (no se aplicó, cambia lo que se ve): la ficha muestra 20 de un pool de 60 mezclado con pesos bastante parejos (`1 / (1 + puesto / 10)`), así que entre los 20 de Memento aparecen «Aliens» o «Commando» mientras quedan afuera vecinos más cercanos. Como la ficha no tiene «Ver otras», podría mostrar los 20 más cercanos en orden.

Archivos: `backend/catalogo/services/similares.py`, `backend/catalogo/views.py`, `backend/catalogo/urls.py`, `backend/catalogo/presupuesto.py`, `backend/usuarios/authentication.py`, `backend/catalogo/tests_similares.py`, `backend/catalogo/tests_similares_api.py`, `contracts/openapi.yaml`

### 13/11/2026 — Títulos parecidos: sugerencias de una lista (PR 2)

`GET /api/lists/{id}/suggestions/?pagina=N` (`ListaSugerenciasView`, en `listas/views.py`) usa el mismo motor con los títulos de la lista como semillas. Vale para las listas personalizadas y Favoritos; Pendientes y Vistas dan 404 (Not Found) `not_found` (Vistas tiene sugerencias desde el 15/11/2026, ver esa fecha), igual que la lista de otra persona o una inactiva. `pagina` debe ser un entero mayor o igual a 1 (si no, 400 (Bad Request) `invalid`); una lista vacía responde 200 (OK) sin resultados y sin llamar a TMDB. Las decisiones de Gonza (D-1 a D-9, 13/11/2026) se aplican tal cual: una lista de una sola clase trae solo esa clase, Vistas se saca también en Favoritos, y el nombre pesa `max(0.15, 1/(n+1))`.

- **El nombre «dice algo»** (`nombre_dice_algo`): sin tildes ni números y sin las palabras de relleno del diseño, tiene que quedar una palabra de 3 letras o más. Favoritos nunca lo usa.
- **El vector del nombre nunca hace esperar** (`vector_del_nombre`): se guarda 30 días por nombre normalizado y modelo; si no está y el modelo no está cargado, se saltea, se pide la carga y el pool dura 5 minutos; si Ollama no responde se recuerda 60 s (`similares:ollama_no`) para que un Ollama caído cueste a lo sumo una consulta por minuto.
- **Firma de la caché**: `similares:lista:{id}:{firma}`, con `sha256(modelo, idioma, nombre normalizado, ids de los títulos ordenados)`. Agregar, quitar o renombrar cambia la clave y la vieja se vence sola; calificar (que agrega a Vistas) no la cambia, porque Vistas se saca después de leer el pool. La semilla de la mezcla es la clave entera.

Desvíos del diseño: la firma usa los ids que ya trae la consulta de los títulos (una sola consulta, del más nuevo al más viejo, de donde salen también las 3 semillas de TMDB) en vez del `string_agg` en SQL, porque esa lista hace falta igual y son a lo sumo 1 000 enteros; `Pool` ya llevaba `nombre_usado` y `completo`, así que el motor casi no cambió (solo se le sumaron las tres funciones del nombre). El error de `pagina` se arma con `ErrorValidacion` y no con un serializador, porque la spec pide el código `invalid` para cero, negativos y texto, y `IntegerField(min_value=1)` daría `min_value`.

Calibración con listas reales de la base de desarrollo (6 077 vectores): `DISTANCIA_MAXIMA` se queda en 0.40. El centroide comprime las distancias: desde 3 títulos, el vecino 100 está por debajo de 0.27, así que una lista de 3 o más títulos no necesita el relleno de TMDB; solo una de 1 o 2 títulos de nicho o sin vectores. Bajarlo a 0.35 mandaría a TMDB a la mitad de los títulos sueltos, y `/recommendations` favorece al inglés. El nombre cambia entre 0 y 2 de los primeros 10 (peso 0.15 desde 6 títulos). El promedio de una lista con temas distintos (Favoritos: acción, romance, series) se corre hacia lo más genérico pero no se rompe (cada semilla queda entre 0.17 y 0.26 del centroide); varios centroides queda como mejora futura, no hace falta ahora.

Medido con `bge-m3` cargado: en frío con el nombre sin guardar, 101 ms; con el nombre guardado, 21 ms; en frío sin nombre, 15 ms; con el pool guardado, 9 a 32 ms; con Ollama caído, 67 ms el primer pedido y 27 ms el segundo. La carga del modelo desde cero tardó 65 s en esta máquina: por eso el nombre no se espera.

Archivos: `backend/catalogo/services/similares.py`, `backend/listas/views.py`, `backend/listas/urls.py`, `backend/catalogo/tests_similares_nombre.py`, `backend/listas/tests_sugerencias.py`, `contracts/openapi.yaml`, `openspec/changes/recomendaciones-similares/design.md`

### 14/11/2026 — Buscar en la navbar: la variante es la lupa que se despliega

Gonza eligió el 14/11/2026, viendo un artifact con las 4 variantes, **una lupa que se despliega en un campo en el mismo lugar**. Reemplaza al campo siempre visible del plan del 13/11, que pasa a descartado: un campo fijo de 18–20 rem le quita lugar a los enlaces en anchos medianos (necesitaba la lupa como plan B por debajo de 1024 px de todos modos), y una sola variante en todos los anchos es más simple que dos.

- **Escritorio** (desde 768 px): una lupa a la derecha, antes de la cuenta. Al tocarla (o con `/`) se abre el campo en el mismo lugar, con las mismas sugerencias (títulos y personas), un ✕ y el foco adentro. Se cierra con Esc (con la lista cerrada), con el ✕ o al perder el foco **sin texto**; con texto se queda abierto para no tirar lo escrito. Celular y `/search` no cambian: sin lupa ni campo.
- **Accesibilidad de la lupa**: botón con nombre accesible, `aria-expanded`, `aria-controls` (al contenedor del campo) y `aria-keyshortcuts="/"`; al abrir, el foco va al campo; Esc o ✕ cierran y devuelven el foco a la lupa. El combobox del campo no cambia.
- **No cambia**: las personas en las sugerencias llevan a Buscar con el filtro por persona (chip con ✕), los títulos sin relevancia no se muestran (sin botón, con las dos excepciones) y el endpoint `suggest/`.
- **Alcance de estos cambios**: se actualizaron `design.md`, `proposal.md`, `tasks.md` y la spec `navbar-search` del cambio, y el backend de las fases 1, 3 y 4 de `tasks.md` va junto en una rama (`feat/buscar-backend`). El frontend sigue pendiente del canvas de Claude Design (a cargo de Gonza).
  Archivos: `openspec/changes/busqueda-navbar/`

### 14/11/2026 — Buscar: backend de sugerencias, filtro por persona y corte de relevancia

Las fases 1, 3 y 4 de `busqueda-navbar/tasks.md` (todo el backend) van en un solo PR (`feat/buscar-backend`), en ese orden y con tests con respuestas reales de TMDB capturadas el 14/11/2026 (`catalogo/test_datos/tmdb_buscar_personas.json`).

- **Corte de relevancia** (`services/browse.py`): `normalizar()` (minúsculas, sin tildes, espacios colapsados), `es_relevante(item, q)` con `MIN_VOTOS_RELEVANTE = 5` y `MIN_POPULARIDAD_RELEVANTE = 5`, y `con_corte()` (si nada pasa, todo). Se aplica con texto o persona, después de los filtros y antes de contar y paginar; no hace ninguna llamada nueva. Con la captura real, «chihiro» pasa de 13 títulos a 3, y el título exacto («Sato no Chihiro», 1 voto) vuelve a mostrarse. Los tests viejos de «dune» cambiaron de totales (p. ej. 100 → 48 películas): es el efecto buscado.
- **`GET /api/catalogo/suggest/?q=&tipo=`** (`SuggestView`, `services/sugerencias.py`): una llamada a `search/multi` (cliente y caché nuevos, TTL 1 h, con copia de respaldo), orden de TMDB, títulos con el corte y personas de `Acting` o `Directing` con popularidad 1 o más, como mucho 2 personas y 5 en total (con `tipo=person`, solo personas y hasta 5). No materializa y usa su propio límite, `sugerencias` (120/min). En español completa solo `title`/`name` vacíos con el inglés y solo de lo que se muestra (`CatalogoConRespaldo.completar_titulos`), así que casi nunca cuesta una llamada. **El corte a 5 respeta el orden de TMDB**: con «tom» TMDB pone tres series antes que Tom Holland y Tom Hanks queda afuera; no se reserva lugar para las personas. Si molesta, se cambia en `sugerir()` sin tocar el contrato.
- **Filtro por persona** (`browse/?persona=&rol=`): `get_person_detail` (`person/{id}`, 24 h) y `combined_credits` en paralelo, primera vez 2 llamadas y después 0 para cualquier página o filtro. `actor` = `cast` sin series de News o Talk; `director` = `Director` en películas y `Creator` en series (Vince Gilligan no figura como «director» de The X-Files por dirigir dos episodios); sin repetidos por `(tipo, id)`; género, año, década, a estrenar y nota en memoria; texto por contenido sin tildes; mismo orden y paginado que el texto. La respuesta agrega `persona: {id, name, rol, gender, profile_path}`, con `rol` igual al pedido (o `null`). Una persona que TMDB no conoce es 404 (Not Found) con el código nuevo `person_not_found` (`PersonaNoEncontrada`), y no el genérico `upstream_not_found`, para que la página ofrezca «Clear filters». Se agregó el código al catálogo de errores, a `contracts/error-codes.json` y `openapi.yaml`, y su texto (en/es) a `traducciones/claves-extra.csv` y a los catálogos generados del frontend, para que la paridad de errores siga en verde. `rol` sin `persona` se ignora.
- **Medición** (14/11/2026, contenedor del backend contra TMDB, 5 textos, extremo a extremo con el cliente de pruebas de Django): `suggest/` en frío 181–401 ms (mediana 195 ms en español; en inglés el primer pedido de cada proceso suma la conexión TLS: 1 160 y 641 ms los dos primeros), en caliente 1–7 ms. Con la espera de 250 ms de la navbar, ≈ 450–650 ms desde la última tecla en frío.
  Archivos: `backend/catalogo/services/browse.py`, `backend/catalogo/services/sugerencias.py`, `backend/catalogo/services/fallback.py`, `backend/catalogo/views.py`, `backend/catalogo/urls.py`, `backend/catalogo/client.py`, `backend/catalogo/cache.py`, `backend/catalogo/exceptions.py`, `backend/filmai/errores/catalogo.py`, `backend/filmai/settings.py`, `contracts/`, `traducciones/claves-extra.csv`, `openspec/specs/tmdb-endpoints/spec.md`, `docs/06_TMDB_API_Referencia.md`

### 14/11/2026 — Buscar: frontend de la lupa y del filtro por persona

Se implementó sin esperar el canvas, con el artifact de opciones como maqueta («si no me gusta, lo cambiamos», Gonza). Cubre las fases 5 y 6 de `busqueda-navbar/tasks.md`, salvo el campo «Person» dentro de los filtros (6.3), que se reemplazó por las sugerencias en el campo de Buscar (ver abajo).

- **`NavbarSearch.tsx`**: la lupa y el combobox ARIA 1.2 del design (250 ms, 2 caracteres, `AbortController`, caché por idioma y texto durante la visita). Las sugerencias van agrupadas en Personas y Títulos (con póster chico) y terminan en «See all results». No se dibuja en `/search`, donde `/` enfoca el campo de la página.
- **Chip de persona en Buscar**: foto, «Nombre · Rol» y ✕. El rol sale del género de TMDB con un `select` ICU anidado (en español: Directora/Director/Dirección, Actriz/Actor/Actuación). El nombre viene de la respuesta de `browse/`, nunca de la URL. Cuenta como un filtro activo y «Clear filters» lo quita. `person_not_found` muestra el estado vacío.
- **Enter y «See all results» buscan títulos, no personas** (Gonza, 14/11/2026, probándolo en local): con «nolan» salen «Facing Nolan» y otros títulos con ese nombre, no las películas de Christopher Nolan. Se deja así porque un título que se llame «Nolan» tiene que poder buscarse.
- **El campo de Buscar sugiere como la lupa y avisa «¿Buscabas a…?»** (Gonza, 14/11/2026; reemplaza la viñeta anterior y la tarea 6.3): escribir «ryan gosling» en `/search` daba 1 documental, aunque `suggest/` devuelve primero a «Ryan Gosling · Actor». Se eligió la opción 1: el campo de la página es el mismo combobox (hook `useSugerencias` y componente `SugerenciasLista`, compartidos con `NavbarSearch`, que no cambia). Elegir una persona pone su filtro y borra `q` (juntos se combinarían); elegir un título abre su ficha con `?from=search`; Enter sin opción activa sigue buscando el texto en títulos. La lista no tiene «See all results»: la página ya muestra todos. Con texto y sin persona filtrada, una línea sobre los resultados («Looking for {name}? See their titles», con foto y rol) ofrece a la primera persona de `suggest/` cuyo nombre (sin acentos ni mayúsculas) contiene todas las palabras del texto; su botón pone persona y rol y borra `q`. El campo pasó de `type="search"` a `type="text"` con `role="combobox"` (el rol reemplaza al de `searchbox`). Descartadas: solo sugerencias en el campo (no resuelve que el nombre escrito termine en un resultado útil), Enter que elija a la persona si el nombre es exacto (un título homónimo quedaría inalcanzable) y un campo «Person» aparte dentro de los filtros (no resuelve escribir el nombre en el campo principal).
- El atajo `/` solo funciona en escritorio (desde 768 px): en celular la lupa está oculta pero montada, y sin ese corte la tecla abría un campo invisible (lo marcó PR-Agent).
- Specs canónicas: nueva `navbar-search`, y `search-ui` suma «Person filter» y `person`/`role` en «Page and state».
  Archivos: `frontend/components/NavbarSearch.tsx`, `frontend/components/SugerenciasLista.tsx`, `frontend/lib/use-sugerencias.ts`, `frontend/lib/sugerencias.ts`, `frontend/components/features/SearchView.tsx`, `openspec/specs/navbar-search/`, `openspec/specs/search-ui/`

### 15/11/2026 — Lupa de la navbar: desplegable rico y campo en píldora (canvas, sección 13)

Se aplicó la sección 13 del canvas a la lupa construida en #216. El campo mide `clamp(12rem, 24vw, 20rem)` (la animación de apertura ya no fija 20rem, llega al ancho real) y toma la forma del canvas: píldora, lupa redonda, foco con borde `--fg-3` más anillo de 2 px y ✕ de 40 px. El desplegable de la navbar pasa a la variante rica (prop `rica` de `SugerenciasLista`): lista de 26rem alineada al borde derecho del campo, filas de 84 px con póster de 48 × 72 y nota con ★ (el backend ya mandaba `vote_average`), fotos de persona de 48 px y, sin foto, dos iniciales (primera y última palabra; `inicialesDe`). El campo de Buscar sigue con la lista compacta, porque el canvas no la redibuja, pero comparte las dos iniciales.

Se dejaron como estaban, porque el canvas no los dibuja: la pista «/» del campo vacío, los estados de hover, vacío y cargando, y el borde del campo abierto sin foco (`--field-border` en lugar de `--line`, que no se midió para el contraste de borde de campo). El helper de axe de los e2e quedó exportado en `frontend/e2e/axe.ts` para los specs nuevos.

Archivos: `frontend/components/NavbarSearch.tsx`, `frontend/components/SugerenciasLista.tsx`, `frontend/lib/sugerencias.ts`, `frontend/app/globals.css`, `frontend/e2e/axe.ts`, `frontend/e2e/navbar-lupa.spec.ts`, `frontend/tests/navbar-search.test.tsx`.

### 15/11/2026 — Créditos de la ficha enlazados a Buscar (fase 7 de la búsqueda)

`credits/` suma el `id` de TMDB de cada persona: `directores` pasa de lista de nombres a `[{id, nombre}]` (el único consumidor es el frontend, que cambia en el mismo commit) y cada persona del reparto suma `id`. El recorte que se guarda en Redis conserva el `id`; las copias guardadas antes no lo tienen, así que esas fichas muestran los nombres como texto hasta que la copia se renueva (24 h). No se cambió la clave de caché porque la forma nueva se arma después de leerla y no hay mezcla de formatos. En «Director and cast», cada nombre con `id` lleva a Buscar con el chip de esa persona (`director` para directores y creadores, `actor` para el reparto); sin `id` queda como texto. El canvas no dibuja estos enlaces: conservan peso y color, con subrayado al pasar el mouse y anillo de foco.

Archivos: `backend/catalogo/services/creditos.py`, `backend/catalogo/cache.py`, `backend/catalogo/tests_ficha.py`, `backend/catalogo/test_creditos_cache.py`, `frontend/components/features/title/CreditsSection.tsx`, `frontend/lib/title.ts`, `frontend/tests/credits-section.test.tsx`, `frontend/tests/title-fixtures.ts`, `frontend/e2e/ficha-creditos.spec.ts`, `openspec/specs/title-page-ui/spec.md`, `openspec/changes/busqueda-navbar/tasks.md`.

### 15/11/2026 — Cierre del change `busqueda-navbar`

Con la lupa rica, los enlaces desde los créditos y el diálogo «Dónde ver», el pendiente 10 queda cerrado y el change se archiva (se borra `openspec/changes/busqueda-navbar/`). Lo vigente queda en las specs canónicas: `navbar-search` suma el campo en píldora de `clamp(12rem, 24vw, 20rem)` y la lista rica (filas de 84 px, póster de 48 × 72, ★), `search-ui` y `title-page-ui`. Los comentarios que apuntaban al `design.md` del change ahora apuntan a esas specs y a las entradas del 13/11/2026 de este archivo. La tarea 2.0 (canvas de Gonza) quedó hecha con la sección 13 del canvas.
Checklist `vercel-quality` (tarea 5.7) sobre el diff de la rama: sin incumplimientos MUST/NEVER nuevos. Quedan anotados dos heredados de #216: la animación de ancho al desplegar la lupa (la pide el canvas; va con `motion-safe`) y el campo de 15 px, que no dispara el zoom de iOS porque la lupa no aparece por debajo de 768 px. Los nombres del reparto como enlaces en línea no llevan área de 44 px: es texto corrido, como cualquier enlace dentro de un párrafo.
Archivos: `openspec/changes/busqueda-navbar/` (borrado), `openspec/specs/navbar-search/spec.md`, `docs/05_Plan_de_Desarrollo.md`, `backend/catalogo/services/sugerencias.py`, `backend/catalogo/tests_sugerencias.py`, `backend/catalogo/tests_browse_persona.py`, `backend/catalogo/tests_browse_relevancia.py`, `frontend/lib/sugerencias.ts`.

### 15/11/2026 — Sugerencias de lista también en Vistas (canvas, sección 14)

Marcos decidió que la banda de sugerencias aparezca en Favoritos, en las listas personalizadas y en Vistas («Watched»); en Pendientes no. `ListaSugerenciasView` deja de responder 404 (Not Found) para Vistas y lo mantiene para Pendientes. En Vistas, el vector y la firma de la caché salen de los 20 títulos agregados más recientemente (ver la entrada del 19/11/2026) y el relleno de TMDB, de los 3 más recientes; no se usa el nombre de la lista, como en Favoritos; lo ya visto no se sugiere. Esto reemplaza lo dicho en la entrada del 13/11/2026 (Pendientes y Vistas sin banda). La paginación `?pagina=N` ya existía: la respuesta trae `pagina` y `paginas`, y hay otra página mientras `pagina < paginas`, que es lo que usa «Show more suggestions».

Archivos: `backend/listas/views.py`, `backend/listas/tests_sugerencias.py`.

### 15/11/2026 — Banda de sugerencias en las listas (canvas, sección 14)

La banda «Suggested for this list» del canvas (`Prop-Sugerencias-Lista` y su versión de celular) va al final del detalle de Favoritos, Vistas y las listas personalizadas; no se dibuja en Pendientes, en una lista vacía ni cuando no hay nada que sugerir. «+ Add» agrega el título a la lista: se suma a la grilla y a los contadores, y se anuncia. «Show more suggestions» pide `?pagina=N+1`, agrega lo nuevo debajo y se oculta en la última página (`pagina >= paginas`). En el celular el póster mide 64 × 96, como dice el bloque «Behaviour» (el dibujo del artboard usa 56 × 84).
Lo que el canvas no dibuja se resolvió así: si falla la primera carga la banda no aparece, y si falla «Show more» sale un toast y el botón queda para reintentar; si la lista cambió entre páginas, el siguiente «Show more» vuelve a la página 1 del pool nuevo y saltea lo ya mostrado; en listas largas la banda se pide recién cuando la grilla no tiene más páginas; y cuando el backend no usa el nombre de la lista (`nombre_usado` falso) la frase es «Based on its N titles, without what you already watched.».
Archivos: `frontend/components/features/lists/ListSuggestions.tsx`, `frontend/components/features/lists/ListDetailView.tsx`, `frontend/lib/lists.ts`, `traducciones/claves.csv`, `frontend/messages/{en,es}/common.json`, `frontend/tests/list-suggestions.test.tsx`, `frontend/tests/list-detail-view.test.tsx`, `frontend/e2e/listas-sugerencias.spec.ts`, `frontend/e2e/axe.ts`.

### 15/11/2026 — «More like {title}» en la ficha (canvas, sección 14)

La ficha suma la fila «More like {title}» («Parecidos a {title}») después de «Director and cast» y antes de las reseñas. Reutiliza `MediaRow` del Inicio sin cambios (opción A del canvas: «igual a las filas del Inicio»), con sus esqueletos al cargar y el deslizamiento de borde a borde en el celular. Pide `GET /api/catalogo/{tipo}/{id}/similar/` cuando la fila está a 400 px del viewport, una vez que terminó el pedido de créditos, y no se dibuja si viene vacía o falla. Una respuesta sin `results` cuenta como vacía: antes rompía la ficha. No se guarda en la visita, porque con sesión la respuesta depende de Vistas. Las tarjetas conservan el `?from=` de la ficha.
Quedaba por confirmar con el canvas (resuelto el 16/11/2026, ver esa fecha): el artboard dibuja dos flechas redondas de 44 px en el encabezado (‹ deshabilitada en la primera página), mientras que la fila del Inicio usa bandas laterales que aparecen con el mouse o el foco; quedó la del Inicio. Tampoco hay artboard de celular para esta fila.
Archivos: `frontend/components/features/title/SimilarTitles.tsx`, `frontend/components/features/title/TitleView.tsx`, `frontend/lib/lists.ts`, `traducciones/claves.csv`, `frontend/messages/{en,es}/common.json`, `frontend/tests/similar-titles.test.tsx`, `frontend/e2e/ficha-similares.spec.ts`.

### 15/11/2026 — Cierre del change `recomendaciones-similares`

Con la banda de las listas y la fila de la ficha, el pendiente 5 queda cerrado y el change se archiva (se borra `openspec/changes/recomendaciones-similares/`). Sus specs pasan a canónicas, alineadas con lo que decidió el canvas: `similar-titles` (motor y endpoints; Vistas con sugerencias), `list-detail-ui` (spec nueva: la banda, «+ Add» y «Show more suggestions» en lugar de «Refresh», que ya no existe) y `title-page-ui` (requisito «More like this title»). Los comentarios que apuntaban al `design.md` del change ahora apuntan a `similar-titles` y a las entradas del 13/11/2026 de este archivo.
Archivos: `openspec/changes/recomendaciones-similares/` (borrado), `openspec/specs/similar-titles/spec.md`, `openspec/specs/list-detail-ui/spec.md`, `openspec/specs/title-page-ui/spec.md`, `docs/05_Plan_de_Desarrollo.md`, `backend/catalogo/services/similares.py`, `backend/catalogo/tests_similares.py`, `backend/catalogo/tests_similares_api.py`, `backend/catalogo/tests_similares_nombre.py`, `backend/listas/tests_sugerencias.py`.

### 16/11/2026 — Dudas del canvas en la banda de sugerencias y en «More like» (sección 14)

Marcos resolvió dos contradicciones entre el texto y el dibujo de los artboards:

- **Póster de la banda en el celular: 64 × 96.** El bloque «Behaviour» de `Prop-Sugerencias-Lista-Movil` dice 64 × 96 y el dibujo mide 56 × 84. Vale el texto, que es lo que ya estaba implementado: mantiene la escala de los pósters (48 × 72 en la lupa, 74 × 111 en la banda de escritorio).
- **Flechas de «More like {title}»: las mismas que las filas del Inicio.** El artboard `Prop-Similares-Ficha` dibuja dos botones redondos de 44 px en el encabezado, con ‹ deshabilitada en la primera página. Se quedan las bandas laterales de `MediaRow` (aparecen con el mouse o el foco, desaparecen cuando no hay más hacia ese lado y en el celular se desliza con el dedo), para que todas las filas del sitio se comporten igual.

No cambia código. El artboard de la ficha queda desactualizado en las flechas; se corrigió en el canvas el mismo día (banda › a la altura de los pósters, sin los botones del encabezado).
Archivos: `docs/decisiones.md`.

### 16/11/2026 — Foco al agregar la última sugerencia de la banda

PR-Agent marcó en el PR #224 que, al agregar la última sugerencia de la última página, la banda desaparece junto con el botón «+ Add» que tenía el foco y el foco cae en `<body>`: quien navega con teclado o lector de pantalla pierde el lugar (WCAG 2.4.3). Ahora, en ese caso, el foco va al título de la lista (`h1`), igual que al quitar una tarjeta. Si quedan sugerencias, sigue yendo al «+ Add» vecino; si se agotó la página pero hay más, a «Show more».
Archivos: `frontend/components/features/lists/ListSuggestions.tsx` (prop `onAgotada`), `frontend/components/features/lists/ListDetailView.tsx`, `frontend/tests/list-suggestions.test.tsx` y `frontend/tests/list-detail-view.test.tsx`.

### 19/11/2026 — Arreglos de la revisión del #224 (sugerencias de lista)

**Tope de semillas en Vistas: 20.** «Vistas» se llena sola al calificar y crece sin techo; con todos sus títulos el centroide se diluía hasta parecerse a «todo el catálogo» (pocos cercanos, y cada reconstrucción pedía relleno a TMDB, hasta 6 llamadas), la firma de la caché cambiaba con casi cada calificación y un solo título sin embedding mantenía el pool en 5 minutos. Ahora `ListaSugerenciasView` toma solo los últimos `MAXIMO_SEMILLAS_VISTAS = 20` por `fecha_agregado` descendente para el vector y la firma; los 3 más recientes de esos 20 siguen siendo las semillas del relleno de TMDB. **Por qué 20**: alcanza para que el gusto reciente se note (el título 21 ya no representa lo que la persona mira hoy), es lo bastante chico para que el promedio no se aplane, y deja la firma estable ante lo que queda fuera del tope (agregar o quitar un título viejo no la cambia). Favoritos y las listas personalizadas no tienen tope: las arma la persona a mano y no crecen sola. Lo ya visto fuera del tope igual no se sugiere (`vistos()` lo saca al armar cada página). La entrada del 15/11/2026 decía «los 3 más recientes» para todo; se corrigió para que diga lo que hace el código.

**Frontend.** Mientras se agrega un título, los otros «+ Add» llevan `aria-disabled` (y el clic no hace nada) en vez de ignorarlo sin aviso; se usa `aria-disabled` y no `disabled` para que el botón enfocado no pierda el foco. El vecino que recibe el foco se calcula con lo último dibujado (una referencia que sigue a `datos`) y no con el `datos` de antes del `await`, por si un «Show more» terminó en el medio. Con un orden distinto de «Recently added», agregar desde las sugerencias vuelve a pedir la primera página en vez de dejar el título al final de la grilla (el lugar real lo decide el backend). La frase de la banda en Vistas pasa a «Based on what you watched most recently.» / «Según lo que viste hace poco.»: no repite «sin lo que ya viste» y no cuenta títulos que ya no entran en el cálculo (clave nueva `lists.suggestions.basisRecent` en `claves-extra.csv`).

**Queda afuera**: la exclusión de «Viendo» (la lista todavía no existe en `develop`; se resuelve en el #226).

Archivos: `backend/listas/views.py`, `backend/listas/tests_sugerencias.py`, `frontend/components/features/lists/ListSuggestions.tsx`, `frontend/components/features/lists/ListDetailView.tsx`, `frontend/tests/list-suggestions.test.tsx`, `frontend/tests/list-detail-view.test.tsx`, `traducciones/claves-extra.csv`, `frontend/messages/`, `openspec/specs/similar-titles/spec.md`, `openspec/specs/list-detail-ui/spec.md`.

### 21/11/2026 — «More like» de la ficha: relevancia estricta, sin mezcla (issue #231)

Decidido por Marcos. La ficha mostraba los 20 primeros de un pool mezclado con pesos (`mezclar_con_pesos`), así que un título muy parecido podía quedar fuera de los 20 mientras entraban otros más lejanos.

- **Ficha.** `armar_pool` recibe `estricto` (por defecto `False`). La ficha lo pasa en `True` y el pool queda en el orden en que se arma: locales cercanos (distancia ≤ 0,40) por distancia, relleno de TMDB, locales lejanos por distancia, hasta 60; la vista muestra los 20 primeros. Sin piso de relevancia: si hay pocos cercanos se completa con TMDB y después con lejanos, como antes.
- **Listas.** No cambian: siguen con la mezcla con pesos y «Show more suggestions».
- **Caché.** La clave de la ficha pasó a `similares:titulo:{tipo}:{id}:{idioma}:{modelo}:estricto`. Con el sufijo no se sirve un pool mezclado guardado por la versión anterior (dura hasta 24 h); los viejos expiran solos.
- **Diagnóstico con «The Avengers» (574) en la base de desarrollo** (739 títulos, 577 con vector `ready`): tiene vector `ready`; sus 20 vecinos están entre 0,161 y 0,326, todos por debajo de 0,40, así que son los 20 cercanos y TMDB no aportó. Los vecinos más cercanos son Infinity War y Endgame (0,16), pero después aparecen títulos poco relacionados (The Fifth Element, The Awakening, Matchbox the Movie) con distancias casi iguales. Dos causas: el catálogo local es chico (faltan Age of Ultron, Civil War, etc.) y, como hay 20 cercanos, el relleno de TMDB (que traería las películas del universo) nunca se pide. Con la mezcla se perdía además el orden. El umbral de 0,40 es holgado para este modelo, y el texto embebido (`construir_texto_canonico`: título, géneros, directores, reparto, keywords, sinopsis) no se tocó. Queda para otro issue decidir si bajar `DISTANCIA_MAXIMA` o dar prioridad a TMDB en la ficha.

Archivos: `backend/catalogo/services/similares.py`, `backend/catalogo/views.py`, `backend/catalogo/tests_similares.py`, `backend/catalogo/tests_similares_api.py`, `openspec/specs/similar-titles/spec.md` y este archivo.

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

### 16/11/2026 — Watching (canvas, sección 15): backend y estado único por título

Segunda unidad del PR 4. Implementa las reglas que se decidieron el 15/11/2026.

- **Estado único:** Watchlist (`pendientes`), Watching (`viendo`, nueva) o Watched (`vistas`), o ninguno; Favoritos sigue aparte. Solo `listas/services.py::poner_estado` escribe esas tres listas: las bloquea, pone el título en una y lo saca de las otras dos. La usan el alta de ítems en esas listas, calificar y el endpoint nuevo. Reemplaza a `agregar_a_vistas` y `quitar_de_pendientes`; `quitar_de_vistas` queda solo para borrar la nota (R4). Ya no se puede «volver a anotar en Pendientes algo visto» dejándolo en Vistas, como permitía la regla del 14/10/2026: cambiar a Pendientes lo saca de Vistas.
- **Calificar mueve a Watched; después el estado es libre y la nota se conserva.** Se retiraron el 409 (Conflict) `rating_blocks_removal_from_watched` (catálogo de errores, contratos, golden y traducciones) y el flag `?borrar_calificacion`. Quitar un título de Vistas responde 204 (No Content) y la nota queda. Si un cliente viejo manda el flag, se ignora.
- **`PUT /api/lists/status/`** con `{id_tmdb, tipo, estado}`. `estado` es obligatorio aunque sea `null`, así un olvido no borra el estado. Responde `{estado, estado_anterior, listas}`, donde `listas` es lo mismo que `GET /api/lists/?id_tmdb=&tipo=`, y el Undo es mandar `estado_anterior`. Repetir el estado actual no cambia nada. El título se materializa solo si `estado` no es `null`.
- **Migración `listas.0009_lista_viendo`:** crea Viendo en todas las cuentas, pasa a Vistas las calificaciones activas sin estado y, si un título está en Pendientes y en Vistas, deja solo la lista donde se agregó último (en un empate gana Vistas). Dos decisiones de implementación: una lista propia que ya se llamaba «Viendo» pasa a «Viendo 2» (o al primer número libre) y conserva sus ítems, porque si no la restricción de nombre único rompía la migración; y «Watching» y «Viendo» quedan como nombres reservados. La reversa no hace nada (está documentado en la migración). Marcos confirmó estas decisiones el 16/11/2026, junto con que pasar un título a Pendientes lo saca de Vistas (antes podía estar en las dos).
- **Viendo cuenta como visto** en `vistos()` (`catalogo/services/recomendado.py`). Así queda fuera de «Recomendado» del Inicio, de las sugerencias de lista, de «More like» y de las recomendaciones del chatbot. Su contexto suma la línea «Viendo», con las 10 más recientes. Las sugerencias de lista responden 404 (Not Found) en Pendientes y Viendo; Vistas sigue en 404 (Not Found) hasta que entre el PR 2.
- **Orden de las predeterminadas:** Favoritos, Pendientes, Viendo, Vistas. El alta de usuario y `reparar_recursos_usuarios` crean las 4.
- **Frontend mínimo:** `enums.defaultList.viendo` (Watching / Viendo), ícono `Play` en la tarjeta de la lista y mocks de e2e con 4 predeterminadas. La interfaz de Watching llega en las unidades siguientes, que también borran el diálogo del 409 (Conflict), hoy código muerto.

Archivos: `backend/listas/` (models, services, views, serializers, urls, exceptions, identidades, migración 0009, tests nuevos `test_estado.py` y `test_migracion_viendo.py`), `backend/catalogo/reviews.py`, `backend/catalogo/services/recomendado.py`, `backend/chatbot/contexto.py`, `backend/usuarios/` (provisioning, seeds y `reparar_recursos_usuarios`), `backend/filmai/` (errores y contrato), `contracts/`, `traducciones/`, `frontend/` (tipos, catálogos y mocks), `openspec/specs/{list-endpoints,reviews-api,error-contract}/spec.md` y `docs/04_Lineamientos_UI.md`.

### 17/11/2026 — Watching (canvas, sección 15): botón de estado, toast con Undo y calificar en la ficha

Tercera unidad del PR 4. Sigue el canvas «Watching · title page» (escritorio y celular).

- **Botón de estado** en `TitleActions`, después de Rate y Favorite: reemplaza a los botones Watched y Watchlist. Sin estado dice «Status» con +; con estado, el ícono y el nombre de Watchlist, Watching o Watched. Abre `StatusMenu` (menú pegado al botón en escritorio, hoja inferior con filas de 60 px en celular): los tres estados como `menuitemradio` y «Remove status». Es un `<dialog>` modal como «Add to list»; con ↑/↓/Home/End se mueve el foco, Escape cierra y el foco vuelve al botón.
- **Cambio optimista** (`useEstadoFicha`): el botón cambia al elegir, se llama a `PUT /api/lists/status/` y la respuesta trae las listas definitivas. Si falla, vuelve atrás con el toast «Couldn’t update the status. Try again.» sin Undo. Mientras hay un cambio en camino el botón no abre otro, así un Undo nunca pisa al siguiente. El toast sale cuando responde el servidor (como la demo del canvas, que no muestra «Moved to…» antes de un error).
- **Toast con Undo** (`StatusToast`): `toast.custom` de sonner con `id` fijo (el segundo cambio reemplaza al primero), `duration: 6000` solo para este toast y barra de tiempo. Undo vuelve un paso con el mismo endpoint y muestra «Back to X» 2 s sin Undo. «Remove status» tiene el mismo toast («Status removed»). Región en vivo cortés: un texto solo para lectores de pantalla dice «… Undo available for 6 seconds.»; Undo se alcanza con Tab y no roba el foco. Al salir de la ficha el toast se cierra y el cambio queda.
- **Calificar**: `TitleView` lee el estado de las listas antes de crear la calificación (el backend la mueve a Vistas). Desde Watchlist o Watching, «Rated ★ 8 · Moved to Watched» con Undo, que restaura el estado y conserva la nota. Desde Watched o sin estado, «Rated ★ 8» sin Undo; con reseña se mantiene el aviso de siempre («Rating and review posted.»). Editar o borrar una calificación no cambia el estado y usa los avisos de antes.
- **Ubicación de los toasts**: `AppToaster` reemplaza al `<Toaster>` del layout: arriba al centro en escritorio y, en celular, abajo y 12 px sobre la barra de pestañas (4,75 rem). El mismo `<Toaster>` cambia de posición con el ancho, así no se pierden avisos. Una regla en `globals.css` corrige que Sonner deje el aviso corrido a la izquierda hasta 600 px.
- **Retirado**: el diálogo del 409 (Conflict) `rating_blocks_removal_from_watched` y el uso de `?borrar_calificacion` en `TitleActions` (el de `ListDetailView` queda para la unidad de listas), `onCalificacionBorrada` y los avisos de Watched/Watchlist de la ficha (`title.feedback.watchedAdded`, `watchlistAdded`, `…Removed` y `watchedAddedFromWatchlist` ya no se usan en la ficha).
- **Refactor menor**: `useEscritorio` pasó de `Navbar` a `lib/use-escritorio.ts`; `ListsMenu` y `StatusMenu` comparten `lib/use-menu-dialogo.ts`, que además devuelve el foco al botón _después_ de cerrar el diálogo (antes se pedía mientras seguía modal, y el navegador lo ignoraba).
- **Casos que el canvas no cubría, confirmados por Marcos (16/11/2026)**: con reseña desde Watched o sin estado se mantiene el aviso de siempre; el toast sale cuando responde el servidor (el botón cambia al instante); calificar un título sin estado no ofrece Undo, igual que desde Watched.
- **Textos nuevos**: `title.status.*` (15 claves) en `traducciones/claves.csv`, catálogos regenerados. Los nombres de los estados salen de `enums.defaultList.*`.

Archivos: `frontend/components/features/title/{TitleActions,TitleView,StatusMenu,StatusToast,use-estado-ficha,ListsMenu}`, `frontend/components/{AppToaster,Navbar}.tsx`, `frontend/app/{layout.tsx,globals.css}`, `frontend/lib/{title-status,use-escritorio,use-menu-dialogo}.ts`, `frontend/e2e/{viendo-ficha.spec,ficha.spec,axe,a11y-axe.spec}.ts`, tests de Vitest (`title-status`, `estado-ficha`, `title-actions`, `title-view`), `traducciones/claves.csv`, `frontend/messages/`, `openspec/specs/title-page-ui/spec.md`.

### 17/11/2026 — Watching (canvas, sección 15): lista Watching, menú ⋯ por tarjeta y /lists en 4, 2 y 1 columnas

Cuarta unidad del PR 4. Sigue los canvas «Watching · list page» y «Watching · Lists» (escritorio y celular).

- **Watching es la página genérica de lista** (`ListDetailView`), sin ícono ni texto arriba del buscador. El conteo pasó a la línea del título (en todas las listas): «N items · X movies · Y TV shows» al lado del título, y en celular solo «N items».
- **Menú «⋯» por tarjeta** (`WatchingCardMenu`, solo en Watching, en lugar del «✕»): 36 px visibles y 44 px de área en celular, `aria-haspopup="menu"`, `aria-expanded`, etiqueta «More for {title}». Ítems: «Mark as finished» (`PUT /api/lists/status/` con `vistas`), «Rate it…» y «Remove from Watching» (`null`). Es un `<dialog>` modal que reutiliza `useMenuDialogo`, `CLASE_DIALOGO_MENU` y `alTeclearMenu` (extraídos de `StatusMenu`): así Escape, el clic afuera y la devolución del foco al «⋯» salen del mismo código que el menú de estado. Un solo menú abierto: lo decide `ListDetailView` con un único `menuAbierto`.
- **Toast con Undo** (`useEstadoViendo`): reutiliza `StatusToast` (id fijo, 6 s), al que se le sumó `accion` (el «Rate it», solo escritorio y solo en «moved to Watched»). La tarjeta sale al instante; si el servidor falla vuelve a su lugar con el toast de error sin Undo. Un cambio a la vez, como en la ficha. **Undo** llama al mismo endpoint con `estado_anterior`, cierra el toast sin otro aviso y pone la tarjeta en su índice anterior de la grilla. El servidor lo anota de nuevo con fecha nueva, así que al recargar queda primero con el orden «reciente»: la posición «anterior» es la de esa sesión. Al salir de la página el toast se cierra y el cambio queda.
- **Calificar desde Watching**: pide antes `GET /api/reviews/mias/`. Sin nota, `POST /api/reviews/` (el servidor la pasa a Vistas) y el aviso es el de la ficha, «Rated ★ 8 · Moved to Watched» con Undo, que devuelve el título a Watching y conserva la nota. Con nota previa se edita (`editarCalificacion`) y no se mueve nada. El «Rate it» del toast abre el mismo diálogo para un título que ya está en Watched: avisa «Rated ★ 8» sin Undo.
- **Estado vacío**: «Nothing in progress» + texto + «Open Watchlist», que va a la lista Pendientes (se busca su id con `GET /api/lists/` solo cuando Watching está vacía; mientras no llega, apunta a `/lists`). El resto de las listas vacías siguen con «Explore».
- **`/lists`**: 4 columnas desde 73,75 rem, 2 desde 40 rem y 1 debajo (`CLASE_GRILLA_LISTAS`), así las cuatro predeterminadas llenan la primera fila. La tarjeta apila hasta 4 pósters (antes 5) y 3 en celular; «N more» cuenta lo que no se ve en cada medida. Se corrigió que `Poster` perdía el `hidden` de los pósters 4 y 5 en celular (`block` le ganaba por orden en `twMerge`).
- **Retirado**: el flujo del 409 (Conflict) `rating_blocks_removal_from_watched` de `ListDetailView` y sus tests (quitar de Vistas conserva la nota desde el 16/11/2026), y las claves que quedaron sin uso: `title.feedback.{watchedAdded,watchlistAdded,watchedRemoved,watchlistRemoved,watchedAddedFromWatchlist}`, `common.media.{watched,watchlist}` y `title.watched.{removeConfirmTitle,remove}`.
- **Textos nuevos**: `lists.watching.*` (10 claves) en `traducciones/claves.csv`, catálogos regenerados.
- **Diferencias con el canvas, resueltas por Marcos (17/11/2026)**: la fecha de las tarjetas de Watching pasa a «Started {fecha}» con reloj (entrada siguiente). En cualquier lista vacía siguen ocultos el buscador y los filtros, como hace la industria con una colección vacía (los filtros solo se muestran cuando son la causa del vacío), y el conteo dice solo «0 items»; se corrigió el artboard del canvas (versión 486) en lugar del código. Textos aprobados: «Nada en curso» y «Abrir Pendientes».

Archivos: `frontend/components/features/lists/{ListDetailView,ListCard,ListsGridSkeleton,WatchingCardMenu,use-estado-viendo}`, `frontend/components/features/title/{StatusMenu,StatusToast}`, `frontend/e2e/{viendo-listas.spec,listas.spec}.ts`, tests de Vitest (`watching-list`, `lists-view`, `list-detail-view`), `traducciones/` (claves y extra), `frontend/messages/`, `frontend/i18n/enums.json`, `docs/04_Lineamientos_UI.md`, `openspec/specs/lists-ui/spec.md`.

### 17/11/2026 — Watching (canvas, sección 15): «Empezada el», conteo de lista vacía y estabilización de los e2e

Ajustes de diseño aprobados por Marcos y dos arreglos de pruebas inestables del PR 4.

- **Fecha en Watching**: en las tarjetas de la lista Watching (solo en esa) la fecha de `fecha_agregado` lleva el ícono de reloj y dice «Empezada el {fecha}» / «Started {fecha}» (tooltip y lectores de pantalla). `MediaCard` y `UnavailableCard` reciben `addedKind` (`"added"` por defecto, `"started"` en Watching). Clave nueva `common.media.startedOnLabel` en `traducciones/claves-extra.csv`.
- **Lista vacía**: con 0 ítems el conteo de la línea del título dice solo «0 items» / «0 ítems», sin «· 0 movies · 0 TV shows», en escritorio y celular, para todas las listas. Los filtros y el buscador siguen ocultos en una lista vacía.
- **e2e de la ficha (celular)**: `auditar` (`e2e/axe.ts`) fallaba a veces en `color-contrast` sobre el botón Undo porque axe corría mientras el toast de sonner todavía entraba, con opacidad parcial. Ahora espera a que terminen las transiciones y animaciones cortas (`document.getAnimations()`); la barra de tiempo del toast (6 s) no se espera para no perder el toast.
- **Scroll infinito de `ListDetailView`**: el centinela solo se dibuja cuando llegó el nombre de la lista (otro pedido). Si la primera página llegaba antes, `useSentinel` no encontraba el nodo y nunca observaba; la página 2 no se pedía. Ahora `reiniciar` cambia cuando llega la lista y el observador se crea con el nodo ya presente.

Archivos: `frontend/components/features/{MediaCard,UnavailableCard}.tsx`, `frontend/components/features/lists/ListDetailView.tsx`, `frontend/e2e/axe.ts`, `frontend/tests/{media-card,list-detail-view}.test.tsx`, `traducciones/claves-extra.csv`, catálogos de `frontend/messages/`.

### 17/11/2026 — PR 4 (#226): comentarios de PR-Agent

- **Conteo al deshacer en Watching (aplicado)**: `meterEnLaGrilla` sumaba 1 al conteo de la lista aunque la tarjeta no se insertara (datos todavía nulos o el ítem ya presente, por ejemplo tras volver a pedir la primera página). Ahora decide con los datos del último render (`datosAhora`) y solo suma cuando inserta. Test en `frontend/tests/watching-list.test.tsx`.
- **Editar una calificación en la ficha (aplicado)**: `TitleView` reemplazaba `mia` por la respuesta del `PUT`, que es parcial; se perdían `id` o el texto borrado. Ahora la mezcla sobre el estado previo (`{ ...sinTexto, ...respuesta }`), como `MyReviewsView`. Test en `frontend/tests/title-view.test.tsx`.
- **«Build roto» en `MyReviewsView` (no aplica)**: PR-Agent supuso que seguían las declaraciones viejas de `datos`, `estado` y `mas` porque el diff que vio no mostraba su borrado. El archivo no las tiene; `tsc`, ESLint y el build del CI pasan.

### 19/11/2026 — Arreglos de la revisión del #226 (Watching) y sugerencias con Viendo

Revisión de Gonza sobre el PR 4 del canvas, aplicada sobre `feat/viendo` antes de actualizarla con `develop` (que ya traía el #224).

- **El Undo conserva la fecha.** Cambiar de estado borra la fila y crea otra, y `auto_now_add` pone «ahora»: «Empezada el 01/10» pasaba a ser la de hoy al deshacer. `poner_estado` acepta `fecha_agregado` (solo para el ítem nuevo; si el título ya estaba en ese estado no la toca) y `PUT /api/lists/status/` la recibe opcional (ISO, no futura: una futura o mal formada es 400 (Bad Request), `null` equivale a omitirla). Para que la ficha sepa qué mandar, `GET /api/lists/?id_tmdb=&tipo=` (y la respuesta del PUT) suma `fecha_agregado` por lista: la fecha del ítem si la contiene, `null` si no. La lista Watching usa la de la tarjeta. Se prefirió esto a una respuesta `fecha_anterior`, que no cubría el Undo de calificar desde la ficha (esa respuesta no pasa por el endpoint de estado).
- **Diálogo de calificar.** Al editar una nota (`inicial`) ya no muestra «también se agrega a Vistas»: editar no mueve nada y, como la nota se conserva al cambiar de estado, un título calificado puede no estar en Vistas. Desde Viendo dice «Al calificarla, {title} pasa de Viendo a Vistas.» (`title.rating.watchedHelpFromWatching`, en `claves-extra.csv`). `RatingDialog` recibe `enViendo`; lo pasan `TitleView` (desde sus listas) y `ListDetailView` (tarjeta de Watching).
- **Undo tras calificar en la ficha.** `avisarCalificacion` aplica `conEstado(listas, "vistas")` antes del toast: un Undo antes de que llegue `recargarListas()` (o con la recarga fallida) ya encuentra algo que deshacer.
- **Chat.** `vistos()` sigue incluyendo Viendo (no se recomienda), pero `ContextoTurno.viendo` (de `en_viendo()`) marca esos títulos con `viendo: true` y sin `vista`; el prompt dice en una línea que lo está mirando (no recomendarlo como novedad ni decir que ya lo vio) y la descripción de `mis_listas` suma `viendo`.
- **Migración 0009.** También renombra las listas propias llamadas «Watching» (nombre reservado en inglés), a «Watching 2» o el primer número libre, además de «Viendo». Se editó la migración y no se hizo una nueva porque la 0009 aún no se aplicó en ningún entorno compartido.
- **Sugerencias de lista con Viendo (resultado de unir con el #224).** El #224 dejó todas las listas con sugerencias salvo Pendientes; este PR las quitaba también de Viendo y Vistas. Queda: **sin sugerencias en Pendientes y Viendo** (404 (Not Found) en el backend, sin fila en el front: `tieneSugerencias` excluye `pendientes` y `viendo`) y **Vistas sí tiene**, con el tope `MAXIMO_SEMILLAS_VISTAS` del #224. Viendo es lo que la persona está mirando, igual que Pendientes es lo que ya eligió ver. `useCursorList` (Q-07) suma `recargarPrimera` para el `recarga` que el #224 había puesto en el estado local de `ListDetailView`, y `title.feedback.watchedAdded` vuelve al catálogo (el aviso de agregar desde las sugerencias de Vistas).
- **Quedó afuera** (anotado en el comentario del PR): las acciones descartadas sin aviso mientras hay un cambio en curso (`use-estado-viendo.ts`, `use-estado-ficha.ts`) y el `requestBody` tipado de `/api/lists/status/` en `contracts/openapi.yaml` (pasa lo mismo en otros endpoints).

Archivos: `backend/listas/` (services, serializers, views, migración 0009 y sus tests), `backend/catalogo/services/recomendado.py`, `backend/chatbot/` (turno, prompts, esquemas y tests), `frontend/` (`use-estado-ficha`, `use-estado-viendo`, `RatingDialog`, `TitleView`, `ListDetailView`, `lib/{title-status,title-lists,lists,use-cursor-list}`, tests), `traducciones/claves-extra.csv`, `contracts/openapi.yaml`, `openspec/specs/{list-endpoints,list-detail-ui,similar-titles}/spec.md`.

### 19/11/2026 — Toast «Saving…» y bloqueo mientras se guarda (restos del #226)

Decidido por Marcos con la simulación del canvas (opción B).

- **Bloqueo.** Mientras hay un guardado de estado en curso, las acciones quedan deshabilitadas desde el primer toque: los ⋯ de todas las tarjetas de Watching, las filas de favorita y de listas de la ficha, el botón Rate y el Undo del toast. Antes el toque se descartaba en silencio. `guardando` pasó a ser estado de React en `useEstadoViendo` y `useEstadoFicha`; la bandera `enCurso` queda como red de seguridad para dos toques en el mismo tick.
- **Toast «Saving…».** Si el guardado tarda más de 200 ms (`MS_ANTES_DE_AVISAR`) sale un toast con spinner, sin Undo, que reemplaza al anterior (un solo aviso a la vez; el Undo viejo se pierde, aceptado). Si el servidor responde antes, no aparece. Una sola implementación compartida: `useAvisoGuardado`. El spinner respeta `prefers-reduced-motion`. Texto nuevo `title.status.saving` («Saving…» / «Guardando…»). Los diálogos, settings y chatbot no cambian.
- **Contrato.** `PUT /api/lists/status/` declara su `requestBody` (`CambioEstado`) con `@extend_schema`. Se fijaron los nombres de los dos enums `estado` (`EstadoEnum` de la cuenta y `EstadoListaEnum`) con `ENUM_NAME_OVERRIDES`, para que el generador no renombre el de la cuenta a `Estado199Enum`. Otros endpoints tienen el mismo hueco y no se tocaron.
- **Canvas.** Falta borrar la opción A del artboard «Watching · tap while saving» y sumar la ficha y el celular (lo hace Marcos con Claude).

Archivos: `frontend/components/features/title/{StatusToast,use-aviso-guardado,use-estado-ficha,TitleActions,ListsMenu,TitleView}`, `frontend/components/features/lists/{use-estado-viendo,WatchingCardMenu,ListDetailView}`, `traducciones/claves.csv` y catálogos generados, `frontend/tests/{estado-ficha,watching-list}.test.tsx`, `backend/listas/{views,serializers}.py`, `backend/filmai/settings.py`, `contracts/openapi.yaml`

### 21/11/2026 — Tarjeta de lista: nombre en una línea con la manija bajo el ⋯ (diseño 5E, #232)

Elegido por Marcos entre las variantes 5A–5F del canvas, partiendo de 4F.

- **Qué se eligió (5E).** El nombre pasa a 1,5 rem en celular y 1,75 rem desde `md`, en una sola línea con «…» y con `title` con el nombre completo. El menú `⋯` o la insignia «Default» quedan pegados a la esquina superior derecha. La manija de arrastre (solo escritorio, solo personalizadas, botón de 44 px con `aria-label`, sigue operándose con teclado) va apilada debajo del `⋯`, en la misma esquina, y no le quita ancho al nombre. El conteo no se parte (`whitespace-nowrap`; en escritorio deja libre el ancho de la manija).
- **Por qué.** El nombre competía por el ancho con la manija, el ícono, la insignia y el menú. Con 5E la manija sale de la fila del nombre y se conserva el arrastre por manija sin cambiar lo que el usuario ya aprendió.
- **Qué se descartó.** 5A (manija a la izquierda del nombre, como estaba), 5B (manija en la fila del conteo), 5C (manija en el pie, junto a los pósters), 5D (sin manija visible, aparece al pasar el mouse o enfocar) y 5F (sin manija, reordenar solo desde el menú).
- **Pruebas.** Vitest (`tests/lists-view.test.tsx`): `title` y truncado, conteo sin partir, manija solo en personalizadas y de escritorio, predeterminada sin manija ni menú. E2E (`e2e/listas.spec.ts`): nombres de 34 y 60 caracteres a 375, 768 y 1440 px, con el nombre en una línea, el conteo sin partir y la manija bajo el ⋯.
- **Canvas.** En «Lists» quedaron solo la tarjeta definitiva (5E) y se borraron 4F, 5A–5D y 5F con sus entradas del índice.

Archivos: `frontend/components/features/lists/ListCard.tsx`, `frontend/tests/lists-view.test.tsx`, `frontend/e2e/listas.spec.ts`, `docs/04_Lineamientos_UI.md` y este archivo.

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

- **Errores**: un solo error visible durante el stream, `chat_unavailable` (proveedor caído, cuota, tiempo o fallo al guardar; el tope de vueltas dejó de ser un error el 12/11, ver «Última llamada sin tools»), con la causa en el log. Antes del stream, los códigos existentes más `chat_request_in_progress`, 409 (Conflict). Descartado un código por causa: cinco textos que no cambian lo que hace el usuario.
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

El prompt pide texto y `mostrar_tarjetas` en la misma respuesta; si llegan juntos, el turno termina sin otra llamada (de 6,5 s a 4,5 s). Tope: 4 vueltas de tools y una llamada final (reemplazado el 12/11: si en esa llamada pide tools otra vez ya no es un error, ver «Última llamada sin tools»). `responder()` retiene los primeros 200 caracteres de cada vuelta y los descarta si la vuelta pide buscar, porque el modelo escribía «I'll look that up.» y el contrato no permite retirar texto enviado. Si menciona la duración, la da para todos los títulos.
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

### 12/11/2026 — Última llamada sin tools, red de tarjetas solo en negrita y arreglos invisibles

**Última llamada sin tools** (reemplaza la decisión del 05/11 sobre el tope de vueltas): si tras las 4 vueltas con tools el modelo sigue pidiendo tools, o si el turno termina sin una palabra de texto, `responder()` hace una llamada más al proveedor sin el parámetro `tools` (`llm.py` lo omite si la lista está vacía; no se usa `tool_choice`) y con un mensaje `system`: «Ya no podés buscar. Respondé al usuario con lo que ya encontraste, sin pedir más herramientas.» Esa respuesta sale como texto normal, separada con «\n\n» si ya había texto de vueltas anteriores (que no se repite), y la red de tarjetas arma las tarjetas desde lo que nombra. Las tools que pidió la vuelta que se pasó se corren igual, así que sus resultados y tarjetas entran. `ErrorDelTurno` solo si esa llamada también falla o vuelve vacía. Antes, pasarse del tope era un error visible: 5 de 32 turnos del set dorado. Cada uso queda en el log (`Última llamada sin tools: <motivo>`) y `chatear --golden` lo marca con `[última llamada sin tools]`. `ProveedorFalso` guarda en `esquemas` las tools de cada llamada.
**Medición** (set dorado, 12/11, `gonzag8`, `deepseek-flash` sin thinking, una corrida de 15 turnos): 0 turnos con error y 0 usos de la última llamada. Antes, el tope cortaba de 3 a 5 turnos de 16 a 32, pero en esta corrida ninguno se pasó (el máximo fue de 7 tools en 4 vueltas), así que la última llamada quedó probada solo con tests y sin una medición real contra DeepSeek. El `saludo` tardó 51,9 s por ser el primer turno de la corrida (arranque en frío), no por este cambio.
Archivos: `backend/chatbot/orquestador.py`, `backend/chatbot/llm.py`, `backend/chatbot/management/commands/chatear.py`
**Red de tarjetas, más estricta** (cambia la del 12/11 anterior): (1) solo cuenta un título escrito en **negrita**, de cualquier largo (antes, solo los de 3 letras o menos): un título suelto en la prosa puede ser una referencia y no una recomendación. Con esto desaparece el caso «Dune» dentro de «Dune: Part Two», porque `**Dune**` no está dentro de `**Dune: Part Two**`, y se sacó esa regla. Sigue ignorando mayúsculas, acentos y el apóstrofo curvo. (2) Un título que el usuario escribió en su propia pregunta no arma tarjeta («algo como Arrival»); para los de 3 letras o menos solo cuenta escrito igual, con su mayúscula, porque «is it scary?» no nombra a _It_ (decisión mía, no estaba en lo pedido). (3) Si una película y una serie se llaman igual y caen en la misma mención, se elige por pistas (película/movie/film contra serie/series/show/TV, en español e inglés): primero la más cercana a la mención dentro de 60 letras del texto del modelo, después las de la pregunta del usuario, y sin pistas, la primera que trajo la búsqueda. Una sola tarjeta por mención. El orden sale de `ctx.encontrados`, un `dict` que recuerda el orden de inserción; `ctx.recomendables` es un `set` y no lo tiene, así que solo filtra. (4) La respuesta se pasa a NFC antes de plegar: «e» + tilde suelta (U+0301) ahora coincide con «é».
Archivos: `backend/chatbot/orquestador.py`
**Arreglos invisibles** (no cambian lo que ve el usuario): (a) `anonimizar.py` pliega los apóstrofos curvos como el recto: «O’Connor» escrito con el teclado del celular no se anonimizaba. El diccionario `APOSTROFOS` pasó de `orquestador.py` a `anonimizar.py`, que el orquestador ya importaba. (b) `_CORREO` acepta `'`, `#`, `!` y `%` en la parte local: `o'neil@gmail.com` quedaba `o'[correo]`. (c) `_plano()` pasa a NFC antes de comparar, así un nombre guardado descompuesto (NFD) se anonimiza y la comparación usuario/nombre no se rompe. (d) `mis_listas` filtra `activa=True`, tanto al listar como al leer una por id, igual que las vistas de `listas`. (e) `esquemas.py` pone tope a lo que manda el modelo: `maxLength` de 200 en `titulo`, 500 en `consulta`, 100 en `nombre` y 20 en `lista`; `id_tmdb` de 1 a `ID_TMDB_MAXIMO`; años de 1800 a 2100 (también `anio_desde` y `anio_hasta`) y `duracion_max` de 1 a 1000. `ejecutar()` ya valida contra el esquema, así que un valor fuera de rango vuelve como `invalid_arguments`. (f) `armar_sistema()` escribe «Moon» y no «Moon (None)» si el título no tiene año. No se tocó `finish_reason="length"` ni el timeout del stream: siguen sin decidir.
Archivos: `backend/chatbot/anonimizar.py`, `backend/chatbot/orquestador.py`, `backend/chatbot/prompts.py`, `backend/chatbot/tools/personales.py`, `backend/chatbot/tools/esquemas.py`

### 13/11/2026 — Prompt más estricto, filtro «basada en libro», datos de series y log de diagnóstico

Cinco casos reales con `gonzag8` mostraron huecos del prompt. Todo cambió **sin reordenar las reglas existentes** (el 12/11 mover reglas cambió la conducta del modelo): las nuevas van en secciones propias («Al recomendar», «Referencias y datos») entre «Títulos vistos» y «Datos no confiables», y un test fija ese orden.

**1. Prompt.** (a) La fecha de hoy («Hoy es 13 de noviembre de 2026.» / «Today is …») va en la parte variable del `system`, junto al perfil, no al comienzo: si fuera adelante, el texto fijo cambiaría cada día y el caché del proveedor se perdería. `orquestador._preparar` la pasa con `timezone.localdate()` y los tests la fijan. Los meses van a mano, porque `strftime("%B")` depende del idioma del sistema operativo. (b) Estrenos: no afirmar fechas de estreno ni si algo «ya salió» o «sale pronto» salvo que lo traiga una tool en el turno; el caso fue Project Hail Mary, que salió el 15/03/2026 y el modelo trataba según lo que recordaba. (c) No anunciar cuántos títulos recomienda («hay dos que…»). (d) Un criterio que las búsquedas no filtran se aclara en una oración, sin presentarlo como cumplido. (e) Registro: «coloquial pero cuidado, apto para todo público», con ejemplos concretos en los dos idiomas (malas palabras suaves como «carajo» o «damn», y jerga como «pibe», «pibardos», «está re fuerte», «un caño») y sin comentarios sobre lo atractivos que son los actores; los ejemplos pesan más que la regla general (caso About Time: «un pibe con amnesia», «pibardos»). (f) Referencias: «esta serie» o «esa película» se resuelve con el título que el usuario nombró en su mensaje antes que con uno de la respuesta anterior (caso Cowboy Bebop contra Serial Experiments Lain); si queda ambigua, el modelo toma uno y lo aclara en una oración, sin hacer una pregunta que frene la respuesta. (g) Sin opiniones de calidad como hechos («un escalón abajo en calidad»). (h) Episodios, temporadas, duración, año, reparto y director salen solo de una tool del turno (caso Texhnolyze: el bot dijo 22 episodios y TMDB dice 20). (i) «¿Y las tarjetas?» o «mostrame esos»: mostrar los títulos de **la última respuesta**, buscándolos por nombre con `buscar_por_titulo`, nunca los de «Ya recomendados» (caso: tras recomendar Log Horizon, Btooom! y SAO Alicization sin tarjetas, el bot mostró Interestelar, Apolo 13 y Pasajeros, los tres últimos de esa lista, que es de toda la sesión).

**1 bis. Intención y vocabulario (agregado al final del PR).** Caso real: «¿cómo puedo empezar a ver la filmografía de Nolan?» se rechazó con «No te puedo ayudar con eso» (la regla de alcance leía «cómo puedo empezar» como un pedido de instrucciones); tras «¡eso te pedía!» el bot recomendó de memoria, sin tarjetas, y cerró con «¿Te armo las tarjetas de esas dos?». Reglas nuevas, todas sumadas sin mover ninguna: (a) en la regla de alcance, solo una aclaración: rechazar únicamente lo que claramente no es de películas ni series, y ante la duda entre rechazar y recomendar, recomendar; (b) en «Al recomendar», un pedido de filmografía, de orden de una saga o de lo de un director o actor, o un «por dónde arranco con X», es un pedido de recomendación y se resuelve con `buscar_por_persona`; (c) si recomienda, muestra los títulos en esa misma respuesta y nunca ofrece ni pregunta por mostrarlos; (d) al usuario no se le nombran palabras internas («tarjeta», «tool», «herramienta», `mostrar_tarjetas`): se dice «los títulos» o nada (la regla de «¿y las tarjetas?» sigue, porque sirve para entender al usuario). Caso nuevo en el set dorado: `filmografia_nolan`. **Medición** (DeepSeek real, 13/11): con el chat limpio el modelo ya recomendaba bien con y sin las reglas (4 de 4 con las reglas; 3 de 3 sin ellas), así que el rechazo solo aparece cuando el historial ya trae rechazos del mismo pedido (el modelo se copia). Con el historial real simulado (rechazo, «eso te pedía», rechazo repetido): sin las reglas 0 de 3 recomendaron y con ellas 2 de 3 (con `buscar_por_persona` y tarjetas); el tercero siguió rechazando. Un historial con rechazos pesa más que el prompt: sigue siendo un riesgo que no se resuelve acá (el chat real de `gonzag8`, con los rechazos guardados, rechazó 4 de 4 con las reglas).

**2. Filtro `basada_en_libro`** (pedido: «adaptaciones de libros»). Es un booleano de `descubrir` y `buscar_semantico` (esquema, validado por `ejecutar()`). En `descubrir` va a TMDB como `with_keywords=818` («based on novel or book»; `catalogo/client.py` y `cache.py` suman `con_keywords`; verificado el 13/11 que `/discover/movie` y `/discover/tv` lo respetan, a diferencia de `with_people` en series). En `buscar_semantico` filtra por `keywords__contains=["based on novel or book"]` (el `@>` de Postgres sobre el `ArrayField`), que es como C-04a guarda ese keyword. Alternativa descartada: pedirle al modelo que adivine por el título; no sirve y es justo lo que fallaba.

**3. Series.** `detalle` de una serie suma `temporadas` y `episodios` (`number_of_seasons` y `number_of_episodes` de TMDB), para que el modelo no los diga de memoria.

**4. Set dorado.** Dos casos nuevos en `golden.yaml`: `basada_en_libros` (Project Hail Mary) y `registro_cuidado` (About Time).

**5. Log de diagnóstico por turno.** `responder()` escribe una línea INFO (logger `chatbot.orquestador`, que ya estaba en `settings.py` a nivel INFO) al cerrar cada turno: `Turno: tools=descubrir(10),mostrar_tarjetas(3) vueltas=2 ultima_sin_tools=no tarjetas=mostrar_tarjetas`. Las tools van en el orden pedido con la cantidad de resultados (o `error`); `vueltas` son las llamadas del ciclo principal, que ofrecen tools (incluida la que contesta: un turno con una búsqueda y su respuesta da 2; la llamada final sin tools no cuenta); `ultima_sin_tools` avisa si hizo falta la llamada final sin tools; `tarjetas` es `mostrar_tarjetas`, `red` (la red de tarjetas del 12/11) o `ninguna`. **Sin el texto de la pregunta ni de la respuesta**: son datos personales y los logs se guardan; un test lo verifica. El nombre de una tool que no existe se loguea como `desconocida`, porque lo escribe el modelo y podría traer saltos de línea. Un turno con `ErrorDelTurno` no escribe la línea (esos errores ya se loguean aparte). `_correr_tools` ahora devuelve también el resumen para el log.

**6. «Ya recomendados»: se queda en 30 (decisión con datos).** Se probó acotarlo a los últimos 10 con la etiqueta «en charlas anteriores». Con el chat de `gonzag8` (17 recomendados) y el set dorado completo, 30 contra 10: en las dos corridas del set dorado ninguna recomendación nueva repitió un título ya recomendado y los 17 turnos salieron sin error y dentro de RNF #6, y el único caso que fallaba («¿y las tarjetas?») lo arregla la regla del punto 1(i): con ella, 2 de 2 corridas mostraron Log Horizon, Btooom! y Lain con 30 y 2 de 2 con 10. Acotar no mejoraba nada medible (en 2 de 3 corridas del pedido de libros con 30 el bot volvió a proponer Interestelar, Apolo 13 y Pasajeros, que son los tres últimos de la lista y seguirían dentro de los últimos 10) y hacía perder memoria de lo recomendado hace más de 10 títulos, así que no se tocó. Límite de la medición: Ollama estaba apagado, así que `buscar_semantico` falló (`error` en el log) y el caso `semantico` no sirve; el modelo tiene variación entre corridas y el set dorado no tiene un caso con historial a propósito.

Archivos: `backend/chatbot/prompts.py`, `backend/chatbot/orquestador.py`, `backend/chatbot/tools/busqueda.py`, `backend/chatbot/tools/esquemas.py`, `backend/chatbot/golden.yaml`, `backend/catalogo/client.py`, `backend/catalogo/cache.py`, `backend/catalogo/services/semantica.py`

### 13/11/2026 — Anonimizado de letras sin descomposición

`anonimizar()` plegaba las tildes con `NFD`, que no descompone las letras que no son «letra + tilde»: «Łukasz» guardado y «Lukasz» escrito (o al revés) no coincidían y el nombre viajaba al proveedor. Ahora `_plano()` pliega, una por una, `ı`, `ł`, `ø`, `đ`, `ð`, `ħ` y `ŧ` a su letra base. Las letras dobles `ß`, `æ`, `œ` y `þ` equivalen a «ss», «ae», «oe» y «th»: no pueden plegarse sin cambiar el largo del texto (rompería las posiciones del reemplazo), así que el patrón de cada nombre acepta las dos formas, sea cual sea la guardada. Limitación: no se cubren letras muy raras ni otros alfabetos (cirílico, griego). Los otros dos pendientes de esta tanda ya estaban hechos: `ejecutar()` valida `tipo` (`enum`) e `id_tmdb` (1 a `ID_TMDB_MAXIMO`) contra el esquema y devuelve `invalid_arguments` sin llamar a la tool ni a TMDB, y `mis_listas` filtra `activa=True` (en `Lista`, como en las vistas de `listas`, significa «no dada de baja»), ambos del 12/11.
Archivos: `backend/chatbot/anonimizar.py`, `backend/chatbot/tests_contexto.py`, `backend/chatbot/README.md`

### 13/11/2026 — Tarjetas del chatbot por marcadores `[[n]]`

Con thinking apagado, el modelo recomendaba en el texto y a veces no llamaba a `mostrar_tarjetas`; la red de #189 lo arreglaba adivinando desde el texto (negritas, pistas de «serie» o «película»), con reglas frágiles. Se compararon cuatro caminos:

| Opción                           | Qué hace                                                                                                                                                                   | Por qué no / sí                                                                                              |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Juez de tarjetas (#192, cerrado) | Un segundo llamado al modelo decide qué títulos del texto llevan tarjeta                                                                                                   | Suma una llamada por turno y el texto y las tarjetas siguen saliendo de dos lugares que pueden contradecirse |
| Salida estructurada JSON         | El modelo devuelve `{texto, tarjetas}`                                                                                                                                     | No se puede transmitir el texto en vivo por SSE hasta cerrar el JSON                                         |
| Juez sin búsqueda previa         | El juez también valida títulos de memoria                                                                                                                                  | Sigue sin resolver que el modelo recomiende sin buscar                                                       |
| **Marcadores `[[n]]` (elegida)** | Cada título de una tool lleva un `ref`; el modelo escribe `[[ref]]` en lugar del nombre y el backend lo cambia por `**Título** (año)` mientras transmite y suma la tarjeta | Texto y tarjetas salen del mismo dato; no cuesta una llamada extra; se conserva el streaming                 |

Decisiones de detalle:

- El `ref` es el orden de aparición en el turno (`ContextoTurno.candidatos()`), no el `id_tmdb`: TMDB repite ids entre película y serie.
- `FiltroDeMarcadores` (`backend/chatbot/marcadores.py`) retiene solo el final del texto que podría ser un marcador a medias (hasta unos 25 caracteres) y absorbe la negrita o el año que el modelo escribe alrededor (`**[[3]] (1999)**`). Hasta 3 tarjetas, en orden de aparición y sin repetir; un marcador por encima del tope deja el título en el texto, sin tarjeta. Un marcador sin candidato se elimina junto con su espacio y se loguea.
- Se elimina la tool `mostrar_tarjetas` (esquema, registro y prompt) y también la red de #189 con `ctx.recomendables`: con marcadores, un título en negrita sin marcador no arma tarjeta. Se mide `negritas_propias` en el log para vigilar si hace falta un respaldo. Las reglas del prompt no se reordenaron: se reemplazaron en su lugar.
- Las tarjetas del último mensaje del asistente entran como candidatos numerados («Tarjetas de tu último mensaje» en el `system`), para «¿y las tarjetas?» sin volver a buscar.
- Búsqueda forzada solo reactiva: si en la primera respuesta del turno el modelo recomienda sin haber llamado una tool (un `[[n]]` sin candidato o una negrita), se descarta ese intento y se repite una vez con `tool_choice="required"` (DeepSeek lo acepta con thinking apagado), solo si el turno lleva menos del 40 % de `LLM_TIMEOUT_SECONDS`. Si la llamada forzada falla, se muestra el primer intento. Costo: la primera vuelta de un turno sin tools se retiene entera antes de salir (un saludo ya no transmite en vivo, 1,3 a 1,6 s en total).
- El log por turno suma `marcadores_validos`, `marcadores_invalidos`, `negritas_propias` y `reintento_forzado`; `tarjetas=marcadores`.
- El set dorado acepta `historial` (mensajes previos con tarjetas, que se crean y se deshacen con cada pregunta) y suma `y_las_tarjetas`, `bebop_lain` y `de_memoria` (21 preguntas).
- El contrato SSE y el front no cambian: `tarjetas` sigue una vez al final y el texto ya llega con los títulos reemplazados.
- Convive con el recorte de #180 (#198): una tarjeta de más de 180 días queda como `{id_tmdb, tipo}`, sin título, y `_tarjetas_del_ultimo_mensaje` la descarta. En un chat retomado después de ese plazo, «¿y las tarjetas?» vuelve a buscar.

Medición con DeepSeek real (thinking apagado, usuario temporal sin historial, 27 turnos): tarjetas en todos los turnos que recomiendan, siempre 3 y siempre nombradas en el texto; 0 marcadores inválidos; 0 reintentos forzados en esos 27 turnos (en una corrida anterior hubo uno, «algo como Sword Art Online» de memoria, con +1 s aprox. frente a 5,9 a 6,8 s sin reintento); latencia p50 4,7 s y máxima 7,3 s frente a los 25 s del turno. Nolan: 3 corridas con 3 tarjetas (4,5 a 4,9 s); Sword Art Online: 3 corridas con 3 tarjetas (5,7 a 6,8 s). Una primera corrida mostró `****Matrix** (1999)**` por un marcador envuelto en negrita: se corrigió en el filtro. `buscar_semantico` falló en el entorno local (Ollama sin conexión) y el modelo se apoyó en las otras tools.
Archivos: `backend/chatbot/marcadores.py`, `orquestador.py`, `prompts.py`, `llm.py`, `tools/` (turno, personales, esquemas), `management/commands/chatear.py`, `golden.yaml`, `README.md`, `contracts/sse-chat.md`, `openspec/specs/chat-api/spec.md`

### 13/11/2026 — Historial por sesión, medición del turno y arreglos de la revisión de arquitectura

Salió de una revisión de arquitectura del chatbot. (1) **Historial por sesión**: `_historial` mandaba los últimos 10 mensajes sin importar su antigüedad, como turnos del asistente sin tool calls y con `**Título**`. Con 4 rechazos viejos guardados, el modelo los imitaba: el caso nuevo `nolan_tras_rechazos` del set dorado dio 3 rechazos en 3 corridas antes del arreglo y 3 respuestas correctas en 3 después (con un chat limpio, 4 de 4 bien). Ahora el modelo solo ve la sesión actual: se corta en el primer hueco mayor a `CHAT_VENTANA_SESION_MINUTOS` (45; el primer hueco se mide contra el mensaje que llega, así que un último mensaje de hace horas deja el historial vacío) y a lo del asistente se le quitan las `**` en la copia que viaja. Limitación: un chat con rechazos de hace 10 minutos sigue imitándolos. (2) `chatear` ya no guarda por defecto (`--guardar` lo pide, y entonces usa `guardar_turno()`, igual que la app, con tarjetas y `ya_recomendados`); se quitó `--sin-guardar`. (3) **Negritas**: el prompt decía «Markdown corto (negrita y listas)» pero `recomienda_sin_buscar` toma cualquier `**…**` por un título de memoria y fuerza la búsqueda. Los logs del contenedor no conservaban líneas `Turno:`; con el set dorado completo (22 turnos) hubo 0 `reintento_forzado=si` y 3 turnos con negritas propias, todos después de buscar (la señal solo mira la primera llamada sin tools), así que el costo hoy era nulo. Se resolvió por lo más simple: el prompt ya no pide negritas (los títulos ya salen en negrita por su `[[ref]]`) y la señal queda como estaba. En las 3 corridas siguientes `negritas_propias=0`. (4) Los logs de tools ya no llevan texto del usuario ni del modelo: un nombre de tool inexistente se loguea como «desconocida» y un argumento inválido, solo con el campo y la regla de `jsonschema` (el modelo sí recibe el detalle). (5) **Medición**: la llamada pide `stream_options={"include_usage": True}`, lee `finish_reason` y la línea `Turno:` suma `llamadas`, tokens de entrada y salida, `cache_acierto` y `cache_fallo` (`prompt_cache_hit_tokens` y `prompt_cache_miss_tokens` de DeepSeek), `cortado_por_largo` y segundos por llamada y total. Medido con DeepSeek real en el caso de Nolan: 8.200 a 10.700 tokens de entrada, 270 a 360 de salida, entre 58 % y 80 % de la entrada en caché, 4,7 a 5,8 s el turno.
**Queda para después**: deadline de 25 s propio dentro de `responder` (hoy lo impone solo la vista), partir `responder` en funciones más chicas, refrescar el estado tras un `network_error` en el front y que las tools devuelvan `ref` en vez de `id_tmdb`.
Archivos: `backend/chatbot/orquestador.py`, `llm.py`, `prompts.py`, `tools/__init__.py`, `management/commands/chatear.py`, `golden.yaml`, `README.md`, `backend/filmai/settings.py`

### 14/11/2026 — Chatbot: red de tarjetas sin marcadores y descargo solo para filtros concretos

Caso real: «si me gustó Demian de Hesse, ¿qué me recomendarías de ese estilo?». El modelo buscó (`tools=buscar_por_titulo,buscar_semantico×6`) y recomendó tres títulos en texto plano, sin `[[n]]`: `tarjetas=ninguna`. La búsqueda forzada no actúa si hubo tools y el texto ya se transmitió. **Decisión (Gonza)**: (1) **Red al final del turno**: si hubo tools, `marcadores_validos == 0` y el texto nombra candidatos del turno, se arman sus tarjetas en orden de aparición, hasta `TOPE_TARJETAS` (3), sin repetir y sin tocar el texto. Compara título y título original normalizados (sin tildes, mayúsculas ni puntuación) como palabra completa («Up» no matchea en «supuesto» ni dentro de «Up in the Air»); ante homónimos (película y serie) gana el que el texto acompaña con su año, si no el primero. El título original viaja en `ctx.originales` (no en las tarjetas ni en lo que ve el modelo). El log dice `tarjetas=red_sin_marcadores`. (2) **Descargo**: la regla del prompt sobre criterios que las búsquedas no pueden filtrar aplica solo si el usuario pidió un filtro concreto (año, duración, país, idioma, plataforma…); por un «estilo», una «onda» o un tema no se aclara nada. **Ajustes aprobados tras la revisión de PR-Agent (mismo día)**: la red no arma tarjeta para los títulos que el usuario nombró en su mensaje del turno (la referencia, p. ej. «algo como Fargo»), ni para los de Vistas (`ctx.vistas`), ni cuando justo después del título viene «:» o «Parte/Part» con número u ordinal («Dune: Parte Dos» no es «Dune», que podría no ser el candidato). Queda sin resolver la mención en negativo de un título que no es ni visto ni nombrado por el usuario. Medición con DeepSeek real (3 corridas del pedido de Demian): las 3 usaron marcadores (`tarjetas=marcadores`, 3 tarjetas cada una), así que la red no se disparó; está cubierta por tests con proveedor falso.
Archivos: `backend/chatbot/marcadores.py`, `orquestador.py`, `prompts.py`, `tools/turno.py`, `tools/busqueda.py`, `tests_marcadores.py`, `tests_orquestador.py`

### 14/11/2026 — Chatbot: una sola parte de cada saga

Pidiendo «ciencia ficción basada en libros», el chat marcó Duna y Duna: Parte dos como dos recomendaciones. Con el tope de 3 tarjetas (`TOPE_TARJETAS`), el cuarto título (Klara y el sol) quedó en el texto sin tarjeta, y nombrar las dos partes se veía raro (Gonza). El prompt suma una regla en «Al recomendar»: una sola parte de cada saga, la primera que el usuario no vio. Las otras partes no se marcan **ni se nombran**, porque la red de tarjetas del #214 convierte en tarjeta un título nombrado sin marcador. Los pedidos del orden de una saga o de una filmografía quedan afuera de la regla. No va en «Títulos vistos»: la regla de secuelas tiene que seguir siendo la última de esa sección (12/11/2026). Se agregó el caso `una_parte_por_saga` a `golden.yaml`.
Archivos: `backend/chatbot/prompts.py`, `backend/chatbot/tests_orquestador.py`, `backend/chatbot/golden.yaml`
**Refuerzo en código (Gonza)**: la regla del prompt funcionó 1 de 2 veces, así que el armado de tarjetas la hace cumplir con `belongs_to_collection` del detalle de película de TMDB (`TMDBClientCache.get_movie_detail`, caché de 24 h). `una_parte_por_saga` (en `marcadores.py`) recibe los títulos que el modelo marcó **sin el tope** (`FiltroDeMarcadores.mencionados`, o los que arma la red del #214 con `tope=None`) y deja la primera película de cada colección; las otras siguen nombradas en el texto (no se reescribe) pero sin tarjeta, y su lugar lo ocupa el título que sigue. Las series no tienen colección en TMDB: nunca se descartan. Corre al final del turno, por `en_hilo` (es bloqueante) y antes del `Resultado`; los detalles se piden en paralelo (un hilo por película) y solo de las candidatas: se miran tandas del tamaño de los lugares que faltan (normalmente una sola; con un descarte, otra con el reemplazo). Con menos de dos películas no se pregunta nada. **No rompe el turno**: si TMDB falla o se pasa del presupuesto de 2 s (`PRESUPUESTO_SAGAS`), esa película entra como hasta ahora. El log del turno suma `saga_descartadas=N`.
**Latencia medida (14/11/2026)**: 180-540 ms por detalle en frío, ~570 ms tres a la vez, 1,3 ms con caché. Los 2 s dan para dos rondas en frío y son menos que el `TMDB_TIMEOUT` de una llamada (5 s): esperar de más le cuesta al usuario más que mostrar una parte repetida.
**Opciones descartadas**: (1) solo el prompt: funcionó 1 de 2 veces. (2) Filtrar por el nombre antes de «:» (Duna / Duna: Parte dos): no detecta sagas con nombres distintos (Los juegos del hambre: Sinsajo, El Señor de los Anillos) y puede juntar títulos que no son de la misma saga.
Archivos (refuerzo): `backend/chatbot/marcadores.py`, `orquestador.py`, `tests_marcadores.py`, `tests_orquestador.py`, `backend/chatbot/README.md`, `openspec/specs/chat-api/spec.md`

### 14/11/2026 — Chatbot: duración solo si la piden y sin cierres con disculpas

Pidiendo «algo como Los juegos del hambre basado en libros», el chat cerró con «No tengo la duración de las dos series y en la búsqueda no apareció nada más ajustado». Nadie había pedido la duración: la búsqueda trajo la de la película, el modelo la puso, y la regla «si mencionás la duración, dala para todos» lo obligó a disculparse por las series. A Gonza no le cerró. Ahora la duración va **solo si el usuario la pidió** (y entonces para todos, con `detalle`), y una regla nueva prohíbe cerrar con aclaraciones sobre lo que no encontró o no sabe si no se las pidieron. Probado una vez en vivo: sin duraciones ni disculpas. Queda abierto que el modelo a veces marca 4 títulos con el tope de 3, y el cuarto sale sin tarjeta.
Archivos: `backend/chatbot/prompts.py`, `backend/chatbot/tests_orquestador.py`

### 15/11/2026 — Chatbot: el tope de 3 es de títulos recomendados, no de marcadores

Quedaba abierto del 14/11/2026: a veces el modelo marca 4 títulos con el tope de 3 tarjetas (`TOPE_TARJETAS`), y el cuarto sale como «**Título** (año)» sin tarjeta. Tres casos reales ese día, con el mismo patrón: tres títulos en lista y un cuarto en el cierre («Si querés algo más adulto… Duna»).
**Diagnóstico**: dos reglas del prompt competían. El tope estaba dicho como tope de _marcadores_ («Marcá como mucho 3 títulos por respuesta»), en media oración dentro de la regla que explica `[[ref]]`. La oración siguiente («Nunca escribas el nombre de un título que recomendás… sin marcador») y «Si recomendás, mostrá los títulos… con su marcador» obligan a marcar todo título recomendado. Ninguna limitaba cuántos títulos se _recomiendan_: si el modelo quería sumar un extra, la única forma permitida de nombrarlo era con marcador, y cumplía esa regla a costa del tope. Dos de los tres casos del 14/11 eran además dos partes de una saga, que ya resolvió `una_parte_por_saga` (#217).
**Decisión**: (1) regla nueva en «Al recomendar»: como mucho 3 títulos por respuesta contando el extra del cierre («si preferís algo más…», «otra opción es…», «también podés ver…»); si hay más, elegir los 3 mejores y no nombrar el resto. (2) La frase vieja pasa a explicar la consecuencia: «Solo hay 3 tarjetas por respuesta. Un cuarto título distinto se queda sin tarjeta, así que no lo marques ni lo nombres». El código no cambia: un cuarto marcador sigue saliendo en el texto, sin tarjeta.
**Medición con DeepSeek real** (15/11/2026, `chatear --usuario usuario001`, 5 pedidos de recomendación, una corrida de cada uno antes y después: «algo como Los juegos del hambre basado en libros», «sci fi basada en libros», «thrillers psicológicos», «algo como Breaking Bad» y «una comedia romántica para ver en pareja»). Antes (prompt de `develop`): 0 de 5 con más de 3 títulos. Después: 0 de 5. Las 10 corridas dieron 3 títulos, 3 tarjetas y `marcadores_validos=3`. **El defecto no se reprodujo**, así que la muestra no prueba que el cambio lo arregle: solo que no rompe nada (mismas tarjetas, 4,6 a 11,2 s frente a 6,6 a 11,1 s). Lo más probable es que las reglas del 14/11 (una parte por saga, no cerrar con aclaraciones) ya lo hayan vuelto raro: los cierres de hoy ofrecen afinar la búsqueda («Si querés algo más espacial, decime») sin nombrar otro título. El cambio se deja igual porque quita la contradicción y es barato; hay que seguir mirando `marcadores_validos` en los logs.
**Opciones descartadas o sin aplicar**: (a) que el cuarto marcador salga sin negrita: mientras se transmite no se sabe si va a tener tarjeta, porque `una_parte_por_saga` decide al final del turno y puede darle el lugar de una parte descartada. (b) Borrar la oración del cuarto título: el texto ya se transmitió y sería borrar algo que escribió el modelo; cambia lo que ve el usuario, lo decide Gonza. (c) Subir el tope a 4: es una decisión de interfaz. (d) Sumar `titulos_sin_tarjeta=N` a la línea `Turno:` para medir la frecuencia real: toca `orquestador.py`, que hoy está en refactor; queda propuesto.
Archivos: `backend/chatbot/prompts.py`, `backend/chatbot/tests_orquestador.py`, `backend/chatbot/golden.yaml`, `backend/chatbot/README.md`

### 15/11/2026 — Chatbot: `responder` partido en pasos (H5)

Pendiente de la revisión de arquitectura del 13/11/2026 (H5): partir `responder` antes de sumarle mecanismos (el siguiente es el deadline, H3). Era una sola función de unas 150 líneas con una docena de variables sueltas: el ciclo de vueltas, la retención del texto, la búsqueda forzada, la última llamada, la red de tarjetas, las sagas y el log. **Es un refactor puro: no cambia la conducta.** Los 446 tests del chatbot pasan sin modificar ninguno, y antes de mover código se sumaron 12 tests de caracterización (`tests_responder_caracterizacion.py`) que fijan lo que los otros no miraban: la secuencia exacta de eventos, en qué momento sale cada uno y la línea `Turno:` en los caminos menos comunes. Pasan igual antes y después.

Cómo quedó: `responder` solo ordena cinco pasos, cada uno una función de `orquestador.py`: `_abrir_turno` (base y mensajes), `_conversar` (el ciclo de vueltas, que por cada una llama a `_escuchar`, `_hay_que_forzar_la_busqueda`, `_cerrar_texto_de_la_vuelta` y `_buscar`), `_asegurar_respuesta` (la última llamada si no hubo texto), `_armar_tarjetas` (red sin marcadores y sagas) y `_registrar_turno`. El estado que antes eran variables locales vive en dos clases chicas: `_Turno` (lo que dura todo el turno) y `_Escucha` (lo de una llamada al modelo). El `for … else` del ciclo desapareció: al ser `_conversar` una función propia, salir con `return` cuando el modelo responde deja el caso «se acabaron las vueltas» como el código que sigue al `for`.

**Opciones descartadas**: (1) repartir los pasos en varios archivos: los tests reemplazan `chatbot.orquestador._ahora`, `_reloj`, `crear_proveedor` y `timezone`, así que mover esas funciones obligaba a tocar tests en un PR que promete no tocarlos. (2) Una clase `Turno` con los pasos como métodos: cambia más líneas y no se lee mejor que funciones que reciben el turno. No se tocó `marcadores.py` ni `prompts.py`, ni el contrato de `eventos.py`.
Archivos: `backend/chatbot/orquestador.py`, `backend/chatbot/tests_responder_caracterizacion.py`, `backend/chatbot/README.md`

### 15/11/2026 — Chatbot: el plazo de 25 s lo administra el orquestador (H3)

Pendiente de la revisión de arquitectura del 13/11/2026 (H3). Hasta ahora el único reloj del turno era el de la vista (`asyncio.timeout(LLM_TIMEOUT_SECONDS)` en `views.py`): a los 25 s cortaba lo que hubiera, el usuario veía `error` y no se guardaba nada, aunque el modelo ya tuviera resultados para responder. El orquestador no sabía cuánto tiempo le quedaba. **Decisión (Gonza)**: el orquestador conoce el plazo y lo reparte; la vista queda como red.

**Cómo se reparte** (`chatbot/plazo.py`, constantes en `orquestador.py`; son fracciones del plazo, entre paréntesis lo que valen con 25 s): (1) se guarda una **reserva para cerrar** del 30 % (7,5 s) para la llamada que escribe la respuesta; buscar puede usar el resto. (2) **Antes de otra vuelta con tools** tiene que quedar el 40 % (10 s: la reserva más una vuelta); si no, se hace la última llamada sin tools, la misma que ya existía para el tope de 4 vueltas. (3) Una **llamada al modelo que no escribió nada** se corta cuando queda solo la reserva (a los 17,5 s) y se pide el cierre; si **ya está escribiendo**, sigue hasta el final del plazo, porque cortarla para volver a pedirla sería peor. (4) Las **tools** tienen lo que queda menos la reserva; si no queda nada no corren, y si se pasan se dejan de esperar; en los dos casos el modelo las recibe como `tool_failed` y se pasa al cierre. (5) Las **sagas** esperan 2 s o lo que quede. (6) La **vista** corta un 20 % después (30 s): si se cumple, es un bug.

**Qué ve el usuario** (sin tocar el contrato SSE): si se acabó el tiempo para buscar, una respuesta normal con lo que se encontró (antes, `error`). Si se acabó con la respuesta a medio escribir, el texto termina en «…» y el turno cierra normal y se guarda. Si se acabó sin una sola palabra, `error` (`chat_unavailable`), igual que antes. El log suma `sin_tiempo=no|busqueda|respuesta`.

**Cliente TMDB corto para el chat**: dentro de las tools, TMDB espera 3 s y reintenta 1 vez (`CHAT_TMDB_TIMEOUT`, `CHAT_TMDB_REINTENTOS`) en vez de 5 s y 3 veces, y nunca más de lo que le queda al turno. Por qué 3 s: una llamada mide 180-540 ms en frío (14/11/2026), así que 3 s es más de 5 veces el peor caso. Por qué 1 reintento: con los valores generales una sola llamada a un TMDB caído puede tardar 27 s (4 intentos de 5 s y esperas de 1, 2 y 4 s), más que el turno entero; con estos, 7 s. No es otro cliente: `catalogo/plazo.py` guarda el plazo en una `ContextVar` (como el contador de `presupuesto.py`) que `_correr_tools` abre y `TMDBClient._request` consulta en cada pedido, así se conservan la caché, el respaldo y las conexiones compartidas. Fuera del chat la variable está vacía y nada cambia. Ollama usa el mismo plazo: la espera de carga del modelo (hasta 20 s) se recorta a lo que queda.

**Por qué el tiempo viaja hacia adentro de las tools**: las tools corren en un hilo (`sync_to_async`) y un hilo no se cancela. Probado con asgiref 3.13: un `asyncio.timeout` sobre `en_hilo` devuelve el control a los 0,5 s, pero el hilo sigue sus 2 s y la siguiente ida al hilo (el guardado) espera detrás. Sin el plazo de red, cortar las tools solo movía la espera al guardado.

**Cancelación**: `Corte` usa `asyncio.timeout_at` solo alrededor de cada espera (cada pedazo del modelo, la tanda de tools), nunca alrededor de un `yield`: si el límite abarcara los `yield`, podía cumplirse mientras la vista escribía en la conexión y cancelar el pedido entero. No crea tareas: se cancela la misma corrutina que esperaba, y `recorrer` cierra el stream del proveedor con `aclosing`.

**Medición en vivo (15/11/2026, DeepSeek real, Ollama apagado, mismo mensaje)**: antes, `segundos_total=8.9` (4 llamadas de 1,6 a 2,5 s y 6 tools); después, `segundos_total=8.4` (4 llamadas de 1,5 a 2,4 s y 6 tools, `sin_tiempo=no`). En las dos corridas `buscar_semantico` falló las 3 veces por Ollama apagado, como se esperaba. Un turno normal no cambia: el plazo solo actúa cuando el tiempo no alcanza.

**Opciones descartadas**: (1) Un `asyncio.timeout` por llamada con un valor fijo: no reparte, y cuatro vueltas lentas siguen pasándose. (2) Un segundo `TMDBClient` con su `httpx.Client` para el chat: duplica las conexiones y obliga a que las tools y `marcadores.py` elijan cliente; la `ContextVar` no toca a quien llama. (3) Un evento SSE nuevo para avisar que la respuesta quedó cortada: cambia el contrato y el front; queda como propuesta (hoy el «…» es la única señal). (4) Cortar el turno con error cuando la respuesta queda a medias: se pierde un texto que el usuario ya leyó. (5) Segundos fijos en vez de fracciones: los tests de la vista usan plazos de 0,3 s y una reserva fija de 7,5 s los dejaría sin tiempo.

**Tests**: `chatbot/tests_plazo.py` (reloj y corte simulados, sin dormir), `catalogo/tests_plazo.py` y un caso de punta a punta en `tests_sse.py`. Ningún test existente cambió. Specs: `openspec/specs/chat-api/spec.md` («Bounded turn») y `contracts/sse-chat.md` («Límites»).
Archivos: `backend/chatbot/plazo.py`, `orquestador.py`, `views.py`, `llm.py`, `backend/catalogo/plazo.py`, `client.py`, `services/semantica.py`, `backend/filmai/settings.py`, `.env.example`, `backend/chatbot/README.md`

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

DeepSeek respondía en español a mensajes en inglés aunque el prompt pidiera «el idioma del mensaje»: pesaba el perfil, con reseñas en español. Solo funcionó nombrar el idioma. `chatbot/idioma.py` detecta `es` o `en` contando palabras comunes, `ñ`, `¿`, `¡` y tildes, y el prompt cierra con «reply in English» o «respondé en español»; sin señal usa el idioma del turno. Heurística y no librería: determinista, testeable y sin dependencias. **El método de detección lo reemplazó la entrada del 22/11/2026**, más abajo: el criterio (el prompt nombra el idioma, sin señal vale el del turno) sigue igual.
Archivos: `backend/chatbot/idioma.py`

### 22/11/2026 — El detector de idioma del chatbot pasa a fast-langdetect (modelo lite)

Decidido por Marcos. Un mensaje en portugués («Na verdade, eu só gostei da aparência dos dragões…») se detectó como `es` y el bot respondió en español: la heurística de palabras comunes solo conoce dos idiomas y cuenta como español cualquier texto con `ñ`, tildes o palabras parecidas. Agregar listas por idioma queda descartado: inviable con alcance global.

- **Regla nueva.** `detectar_idioma()` identifica de forma positiva `es` o `en`: toma el idioma más probable (`k=1`) y lo devuelve solo si es `es` o `en` y su confianza es de 0,5 o más. Todo lo demás (portugués, italiano, francés, alemán, ruso, japonés, un título suelto) es `None`, y el chatbot responde en el idioma de la cuenta (el `or idioma` que ya tenía `orquestador._preparar()`). Las tools y las tarjetas siguen en el idioma del turno.
- **Librería.** `fast-langdetect>=1.2,<1.3` con el modelo `lite` (el `lid.176.ftz` de fastText, que viene dentro del paquete y nunca descarga nada). Se pasa `model="lite"` siempre: el valor por defecto (`auto`) bajaría el modelo completo de 126 MB. Se usa `max_input_length=None` (sin el recorte a 80 caracteres ni su log INFO por mensaje largo): dio los mismos aciertos y el mensaje ya tiene tope de 500 caracteres (`LARGO_MAXIMO_DEL_MENSAJE`). No se usa `fasttext-wheel` porque el backend tiene numpy 2.5.4 (por pgvector); `fast-langdetect` usa `fasttext-predict`, que no lo necesita.
- **Que no rompa un turno.** Texto vacío o solo espacios da `None` sin llamar a la librería. Si la librería lanza una excepción se loguea un WARNING (solo el tipo de error, nunca el texto del usuario) y da `None`. El detector es único por proceso y se crea en el primer uso (`functools.cache`).
- **Benchmark.** 80 mensajes etiquetados (78 evaluables): español rioplatense, inglés, mezclas con títulos, portugués, italiano, francés, alemán, ruso, japonés, ambiguos, mayúsculas, largos y el set dorado del chatbot. Regla común: top-1 `es` o `en` con confianza de 0,5 o más; si no, `None`. «Grave» es devolver `es` o `en` equivocado; «conservador» es esperar `es`/`en` y dar `None` (cae al idioma de la cuenta).

| Configuración                                    | Aciertos      | Graves                                                                | Conservadores                                                          | Carga  | RAM extra | Mediana      |
| ------------------------------------------------ | ------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------- | ------ | --------- | ------------ |
| Heurística anterior (palabras comunes)           | 62/78         | 13 (todo el portugués, italiano, francés y alemán dado por `es`/`en`) | 3                                                                      | 0 s    | 0 MB      | 0,003 ms     |
| **fast-langdetect `lite` (elegida)**             | **75/78**     | 1 («ok» → `en`)                                                       | 2 («Mostrame The Matrix» y un pedido largo lleno de títulos en inglés) | 0,18 s | 26 MB     | 0,014 ms     |
| fast-langdetect `full` (lid.176.bin, 126 MB)     | 70/78         | 1                                                                     | 7                                                                      | 0,36 s | 156 MB    | 0,012 ms     |
| fasttext-predict con el `.ftz`                   | 73/78         | 1                                                                     | 4                                                                      | 0,04 s | 5 MB      | 0,008 ms     |
| fasttext-predict con el `.bin`                   | 68/78         | 2                                                                     | 8                                                                      | 0,25 s | 135 MB    | 0,006 ms     |
| lingua (alta / baja precisión; set previo de 44) | 26/44 y 30/44 | 0                                                                     | 18 y 14                                                                | n/d    | ~48 MB    | 0,9 / 0,5 ms |

- **Por qué `lite`.** Gana en aciertos y es el más liviano de los que aciertan: el modelo completo no mejora y cuesta seis veces más memoria. Le gana a `fasttext-predict` con el mismo `.ftz` por el preprocesamiento de `fast-langdetect` (pasa a minúsculas el texto mayormente en mayúsculas y lo limpia). Lingua es demasiado conservador: manda a la cuenta casi la mitad de los mensajes.
- **Error aceptado.** «ok» se detecta como `en` (0,63). Es un error leve: una sola palabra, sin consecuencias prácticas. Subir el umbral para evitarlo costaría aciertos en mensajes cortos reales.
- **Costo.** Carga única de ~0,18 s en el primer mensaje de cada proceso, +26 MB de RAM y ~0,014 ms por detección (despreciable frente a la llamada al modelo).
- **Licencia.** El modelo lid.176 de fastText es de Facebook/Meta con licencia CC BY-SA 3.0; la atribución está en el README (sección «Créditos y licencias de terceros»).
- **Tests.** `chatbot/tests_idioma.py` (casos del benchmark con el modelo real, la excepción, el vacío, el umbral y `model="lite"` con mocks) y un test en `chatbot/tests_orquestador.py` que muestra que un mensaje en portugués arma el prompt en el idioma de la cuenta, `es` o `en`.

- **Revisión de PR-Agent (#242).** Aceptado: la versión se acota a `<1.3` (no `<2`), porque los tests usan el modelo real y una versión menor podría cambiar el preprocesamiento y poner el CI en rojo sin que cambie nuestro código. Descartado: «si el modelo no carga, se reintenta en cada mensaje y reaparece el bug del portugués». Con el detector caído el bot responde en el idioma de la cuenta (no en un idioma equivocado), y una firma incompatible de la librería la detectan antes del merge los tests que usan el modelo real.

Archivos: `backend/chatbot/idioma.py`, `backend/chatbot/tests_idioma.py`, `backend/chatbot/tests_orquestador.py`, `backend/requirements.txt`, `openspec/specs/chat-api/spec.md`, `README.md`

---

## Correos

### 24/08/2026 — Correos transaccionales con Resend

`EMAIL_BACKEND` propio sobre la API de Resend. Sin dominio propio Resend solo entrega al dueño de la cuenta: en desarrollo `RESEND_TEST_RECIPIENT` redirige todo ahí. Con `DEBUG=False`, esa variable o la falta de `RESEND_API_KEY` frenan el arranque en vez de fingir un envío. Riesgo vigente: hasta verificar un dominio, solo el dueño de la clave recibe correos reales.
Archivos: `backend/filmai/email_backends.py`

### 08/10–12/10/2026 — Servicio único, correos localizados y diseño del canvas

Los cuatro flujos pasan por `enviar_correo`, con plantillas por caso e idioma y una base HTML común. El idioma es el guardado del destinatario, si no el del pedido, si no inglés. Diseño del canvas sobre una tabla con estilos en línea, fuentes con alternativas del sistema (Gmail ignora las web), marca sin SVG (muchos clientes lo eliminan) y solo tema oscuro. Vigencias: 24 horas para confirmar el correo y 1 hora para restablecer la contraseña.
Archivos: `backend/filmai/correos/servicio.py`, `backend/templates/correos/base.html`

### 30/10–06/11/2026 — Pendientes: correos por Celery (Q-08) y Brevo como respaldo (#181)

`enviar_correo()` llama a Resend dentro del pedido HTTP; pasará a una tarea con reintentos con espera creciente, porque un correo fallido no tiene backfill que lo recupere. Resend gratis da 100 correos por día y los topes son por IP: una sola IP puede agotar el cupo y dejar sin confirmación ni reset a los usuarios legítimos. Se usará Brevo (300 por día) cuando Resend no pueda entregar, con un backend que recorra proveedores como `LLM_PROVEEDORES`: 429 (Too Many Requests), 5xx y timeout pasan al siguiente; un 400 (Bad Request) no. Descartados Amazon SES (dominio, DKIM y sandbox), Mailjet y Mailtrap (menos cupo). Plan en el change `brevo-respaldo` (archivado el 22/11/2026; ver las entradas de más abajo).
Archivos: `backend/filmai/email_backends.py`, `docs/05_Plan_de_Desarrollo.md`

### 18/11/2026 — Correos: Brevo primero y Celery (Q-08) después; `.eml` regenerados

**Brevo y Q-08 no se contradicen.** El plan decía que convenía hacerlos juntos y la propuesta de Brevo (el change `brevo-respaldo`, archivado el 22/11/2026) deja Q-08 afuera. Se resolvió así: son dos cambios separados, uno después del otro. Brevo cambia lo que pasa dentro de `enviar_correo()` (Resend y, si falla, Brevo, un intento por proveedor porque hoy el pedido espera); Q-08 cambia quién la llama (una tarea de Celery con reintentos) y deja la cadena de proveedores adentro sin tocarla. El requisito de `openspec/specs/emails/` («Do not silently route these synchronous account emails through Celery») no impide Q-08: pide que el paso a Celery sea un cambio deliberado que actualice la spec, no un efecto secundario. Q-08 además tiene que revisar los llamadores que usan lo que devuelve `send_mail` (`usuarios/adapter.py`, `passwords.py`, `serializers.py`).

**`.eml` de revisión regenerados.** Los ocho `.eml` y el `index.html` de `traducciones/revision-correos/` eran del 24/08 al 08/10/2026 y no se habían regenerado después del diseño del canvas (12/10/2026, `47687dd`) ni de quitar la franja dorada (06/11/2026, #175). Se generaron de nuevo con `enviar_correo()` y el backend de correo en memoria, sin envío externo. El enlace de muestra de `restablecer_contrasena` ahora es `/reset-password/…` (antes salía `/confirm-email/…` porque el contexto de muestra traía los dos enlaces).

Archivos: `docs/05_Plan_de_Desarrollo.md` (pendientes 3, 7 y 12, Q-08), `traducciones/revision-correos/`.

### 21/11/2026 — Correos: el logo es el ticket de la navbar

- **Qué estaba mal.** `correos/base.html` dibujaba la marca como un rectángulo amarillo con una estrella de texto (`&#9733;`), distinto del `TicketMark` de la navbar (ticket con muescas laterales y estrella de cinco puntas).
- **Qué se hizo.** La marca sale ahora como imagen `frontend/public/correos/ticket.png` (128×96 px, se muestra a 32×24 px), con el mismo trazado que `TicketMark` (`#f5c518` y estrella `#14110a`). Gmail y otros clientes no dibujan SVG en línea, por eso es PNG. La plantilla la pide a `{{ url_app }}/correos/ticket.png`; `enviar_correo()` pasa `url_app` desde `FRONTEND_URL` (sin barra final). El texto «FilmAI» no cambia.
- **Límite conocido.** En local `FRONTEND_URL` es `http://localhost:3000`: un cliente de correo real solo ve el logo si ese servidor está accesible; en producción lo sirve el dominio público. Los `.eml` de revisión llevan la imagen incrustada (`data:`) para que se vean sin servidor; Gmail no muestra `data:`, así que ese caso se comprueba con el envío real.
- **Tests.** `test_logo_es_el_ticket_de_la_navbar_servido_por_el_frontend` en `backend/filmai/test_servicio_correos.py`.

Archivos: `backend/templates/correos/base.html`, `backend/filmai/correos/servicio.py`, `backend/filmai/test_servicio_correos.py`, `frontend/public/correos/ticket.png`, `traducciones/revision-correos/` (ocho `.eml` e `index.html`), `openspec/specs/emails/spec.md`, `docs/05_Plan_de_Desarrollo.md`.

### 22/11/2026 — Brevo como respaldo de Resend y `email_unavailable` (#181)

Resend va primero; si no puede tomar un mensaje, ese mismo mensaje sale por Brevo (API transaccional v3, 300 correos por día gratis). Todo vive detrás de un único `EMAIL_BACKEND` (`filmai.email_backends.RespaldoBackend`): `enviar_correo()`, el adaptador de allauth y los flujos de contraseña no saben qué proveedor envió, igual que desde la decisión del 24/08/2026. Se hizo en dos PR apilados: el 1 (#243) trae los proveedores y el respaldo; el 2, los límites, el código `email_unavailable` y esta documentación.

**Decisiones D-1 a D-6, aceptadas por el usuario el 22/11/2026 tal como se proponían:**

| #   | Decisión                                                                                                                                                                                         |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D-1 | 401 (Unauthorized) y 403 (Forbidden) de Resend pasan a Brevo: una clave inválida o revocada es justo el caso «proveedor inutilizable». Cada paso al respaldo se loguea en `WARNING` con el motivo |
| D-2 | Un timeout de lectura de Resend también pasa a Brevo: un duplicado es inofensivo (los dos enlaces valen) y un correo que falta bloquea la cuenta. La `Idempotency-Key` de Resend no ayuda       |
| D-3 | Se mantienen los topes por correo y por IP, sin tope global; solo cambia el comentario de `settings.py`                                                                                          |
| D-4 | `email_unavailable` con 503 (Service Unavailable) en registro y reenvío; registro atómico; el reset sigue con el 200 (OK) genérico                                                               |
| D-5 | Variables propias `BREVO_FROM_EMAIL` y `BREVO_TEST_RECIPIENT` (Brevo no puede enviar como `onboarding@resend.dev`)                                                                               |
| D-6 | `httpx` como cliente de Brevo (un solo endpoint, ya es dependencia y tiene transporte de prueba); descartado `django-anymail`, que reemplazaría también el SDK de Resend                         |

**Qué errores pasan a Brevo.** Solo cuando el primer proveedor levantó error; un 2xx es definitivo y un mensaje aceptado nunca se reenvía. Un intento por proveedor, porque el pedido HTTP espera (los reintentos son de Q-08).

| Falla                                                                  | ¿Pasa a Brevo?                                              |
| ---------------------------------------------------------------------- | ----------------------------------------------------------- |
| Conexión, DNS, TLS o timeout                                           | Sí                                                          |
| 5xx                                                                    | Sí                                                          |
| 429 (Too Many Requests): límite, cuota diaria o mensual                | Sí                                                          |
| 402 (Payment Required)                                                 | Sí                                                          |
| 401 (Unauthorized) o 403 (Forbidden): clave, IP o remitente            | Sí (D-1)                                                    |
| 400 (Bad Request) o 422 (Unprocessable Entity): datos del mensaje, en el primer proveedor | No: los mismos datos fallarían igual; se levanta de inmediato |
| Cualquier error del respaldo después de un fallo transitorio del primero (p. ej. 400 (Bad Request) de Brevo por remitente no verificado) | Ya no hay a quién probar: `EnvioFallido`, que termina en `email_unavailable` |
| Falta la clave en la configuración                                     | El proveedor se saltea                                      |
| Cualquier otra excepción                                               | No: se trata como un bug                                    |

**Lo que se descubrió al inspeccionar el SDK de Resend (2.53.2).** Se clasifica por código HTTP y no por clase: el SDK levanta `ValidationError` también con 401 (Unauthorized) y 403 (Forbidden) (por ejemplo, enviar desde `onboarding@resend.dev` a quien no es el dueño de la cuenta), y todo error de transporte (conexión, DNS, TLS, timeout) llega como un `ResendError` genérico con código 500 (Internal Server Error), sin distinguir un timeout de una conexión caída. El timeout por defecto del SDK es de 30 s; se fijó en 10 s para ambos proveedores, porque dos proveedores lentos sostendrían el registro durante un minuto. `ErrorDeProveedor` guarda solo proveedor, estado y tipo de error y se levanta `from None`: el texto del proveedor puede repetir direcciones (el 403 (Forbidden) de prueba nombra al dueño de la cuenta) y ningún log o traza debe llevarlas.

**Cuando fallan los dos proveedores.** Si todos los activos fallan por algo transitorio, el backend levanta `EnvioFallido`; un error no transitorio (400 (Bad Request) o 422 (Unprocessable Entity)) del primer proveedor sale como `ErrorDeProveedor`, no como `EnvioFallido`, y no se informa como «correo no disponible». Si ya hubo un fallo transitorio, cualquier error del respaldo (aunque sea un 400 (Bad Request) de Brevo por un remitente no verificado) cuenta como «falló también» y termina en `EnvioFallido`, es decir, en `email_unavailable`.

> Q-08 lo cambió el mismo día (ver abajo): `email_unavailable` ya no significa «ningún proveedor pudo enviar» sino «la cola no aceptó el correo», y los proveedores caídos se reintentan en el worker. La tabla y el párrafo de `EnvioFallido` describen el estado del PR 2 antes de Q-08.

| Flujo                  | Antes                                    | Ahora                                                                                                                                              |
| ---------------------- | ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| Registro               | 500 (Internal Server Error), cuenta `PENDIENTE` | 503 (Service Unavailable) `email_unavailable`; `perform_create` corre en `transaction.atomic()`: no quedan `Usuario` ni `EmailAddress` y el visitante reintenta con el mismo correo |
| Reenvío de confirmación | 500 (Internal Server Error)             | 503 (Service Unavailable) `email_unavailable`                                                                                                      |
| Reset de contraseña    | 200 (OK) genérico, error en el log       | Igual (anti-enumeración)                                                                                                                           |
| Aviso de cambio de contraseña | Error en el log, contraseña guardada | Igual (corre tras el commit)                                                                                                                  |

`EnvioFallido` se convierte en `ExcepcionAPI("email_unavailable")` dentro de `UsuarioAccountAdapter.send_mail`, con contexto `registro` o `reenvio` según el caso: un solo punto cubre las dos vistas y no cambia la forma del esquema OpenAPI (solo suma el código al enum de `ErrorEnvelope`). El frontend ya traducía por código: `ApiError` toma el texto de `errors.codes.<código>`, nunca de `detail`, `debug` ni `codigo`. Textos aprobados por el usuario el 22/11/2026: «No pudimos enviar el correo. Intentá de nuevo en unos minutos.» y «We couldn’t send the email. Try again in a few minutes.».

**Capacidad combinada (planes gratuitos, noviembre de 2026; volver a verificar antes de desplegar).** Resend 100 por día y 3 000 por mes; Brevo 300 por día (~9 000 por mes); combinados ~400 por día y ~12 000 por mes. En un mes corrido el tope mensual de Resend se agota primero y Brevo cubre hasta 300 por día. Los topes por correo e IP (registro 5 y 10 por hora, reenvío 1 por minuto, 3 y 10 por hora, reset 5 por día y 10 por hora) no protegen la cuota global sino una bandeja y la reputación del remitente, así que no se tocaron; las siete tasas quedaron fijadas en `usuarios/test_seguridad_throttles.py`. Un tope global lo agotaría cualquiera a propósito y bloquearía todos los registros del día.

**Configuración en producción.** Con `BrevoBackend` o `RespaldoBackend` y `DEBUG=False`, el arranque falla si el remitente efectivo de Brevo (`BREVO_FROM_EMAIL` o, si falta, `DEFAULT_FROM_EMAIL`) no tiene una dirección con `@` o es `@resend.dev`: Brevo rechazaría cada correo con 400 (Bad Request). Las dos reglas (esta y la del error del respaldo) salieron de la revisión de PR-Agent del #243, que aceptó las dos observaciones.

**Para desplegar.** Sin dominio propio solo se puede enviar desde un remitente único verificado en Brevo, y un remitente de Gmail puede fallar DMARC al salir por Brevo: el correo llega a spam o se rechaza. Configurar SPF y DKIM de un dominio propio es parte del despliegue. Además, en Brevo hay que revisar «Authorised IPs» (Settings → Security): con una IP no autorizada cada llamada responde 401 (Unauthorized) aunque la clave sea correcta.

**Pendiente.** La prueba manual con cuentas reales (clave válida; `RESEND_API_KEY` inválida; ambas inválidas) la hace el usuario y su resultado se anotará acá. Q-08 lo cambió: ver «Correos de cuenta por Celery (Q-08)», abajo.

Archivos: `backend/filmai/email_backends.py`, `backend/filmai/email_validation.py`, `backend/filmai/settings.py`, `backend/filmai/errores/catalogo.py`, `backend/usuarios/adapter.py`, `backend/usuarios/views.py`, `backend/filmai/management/commands/send_test_email.py`, `backend/filmai/test_email_respaldo.py`, `backend/filmai/tests.py`, `backend/usuarios/test_errores_registro.py`, `backend/usuarios/test_seguridad_throttles.py`, `contracts/error-codes.json`, `contracts/openapi.yaml`, `traducciones/claves-extra.csv`, `frontend/messages/{en,es}/common.json`, `frontend/tests/access-screens.test.tsx`, `frontend/tests/i18n-shared.test.ts`, `.env.example`, `docs/05_Plan_de_Desarrollo.md`, `README.md`, `openspec/specs/emails/spec.md`.

### 22/11/2026 — Correos de cuenta por Celery (Q-08)

**Qué.** `enviar_correo()` sigue renderizando asunto, texto y HTML dentro del pedido, pero ya no llama al proveedor: encola la tarea `filmai.enviar_correo` (`filmai/tasks.py`) con esos tres textos y el destinatario. El worker de Celery la toma y llama a `send_mail` con el `EMAIL_BACKEND` configurado, así que la cadena Resend → Brevo queda igual. Cubre los cuatro correos de cuenta (confirmación de registro, reenvío, reset y aviso de cambio de contraseña).

**Por qué.** Con Resend y Brevo caídos el pedido esperaba hasta ~20 s (10 s por proveedor) con la transacción del registro abierta. La práctica estándar es encolar y reintentar en segundo plano. La revisión de PR-Agent del #243 y del #244 hizo dos observaciones, aceptadas: la de la transacción abierta se resuelve con este cambio; la del cupo del throttle, con la devolución de abajo.

**Por qué `apply_async` dentro de la transacción y no `on_commit` ni outbox.** La tarea recibe solo textos y no lee la base: el worker no necesita ver la cuenta, así que encolar antes del commit no tiene carrera. Y como el encolado ocurre dentro de `transaction.atomic()`, si la cola está caída la excepción deshace el `Usuario` y el `EmailAddress` (se mantiene D-4). Con `on_commit` la cuenta ya estaría guardada cuando falla el encolado, y habría que borrarla a mano o dejarla sin correo. Un outbox (tabla de correos pendientes más un proceso que la vacía) garantizaría la entrega aun con Redis caído, pero es más de lo que necesita el proyecto: con Redis caído el registro responde 503 (Service Unavailable) y el visitante reintenta.

**Reintentos.** Solo ante `EnvioFallido` (todos los proveedores con fallo transitorio): espera exponencial (60 s, 120 s, 240 s... con tope de 1800 s) con jitter (cada espera es un valor al azar entre 0 y ese tope, para que al volver Resend no salgan todos los correos juntos) y 8 reintentos como máximo. Peor caso ~2 h (60+120+240+480+960+1800+1800+1800 s), promedio ~1 h, muy por debajo de las 24 h de vigencia del enlace. Un `ErrorDeProveedor` no transitorio (400 (Bad Request) o 422 (Unprocessable Entity)) no se reintenta: log ERROR. Agotados los reintentos: log ERROR. `acks_late` y `reject_on_worker_lost`: si el worker muere a mitad de camino el mensaje se reentrega (un duplicado es inofensivo; un correo perdido deja la cuenta sin confirmar). `ignore_result`: el resultado no se guarda.

**Logs redactados.** Ningún log lleva direcciones ni enlaces. La tarea se encola con `argsrepr` redactado (el worker imprime eso al recibirla) y sus logs llevan solo el caso y el id de la tarea; el texto de `EnvioFallido` y `ErrorDeProveedor` ya llevaba solo proveedor y estado HTTP. Un correo encolado vive en Redis (DB 1) hasta que el worker lo toma, con el enlace dentro: Redis ya exige contraseña en producción.

**`email_unavailable` cambia de significado.** Ahora quiere decir «no se pudo encolar» (Redis caído): registro 503 (Service Unavailable) con la cuenta deshecha; reenvío 503 (Service Unavailable); reset, el mismo 200 (OK) genérico con log del pk; aviso de cambio de contraseña, log del pk (la contraseña ya quedó). Los proveedores caídos ya no llegan a las vistas: `EnvioFallido` vive dentro de la tarea y el adaptador de allauth ahora solo traduce `CorreoNoEncolado`. El mensaje al usuario no cambia. A cambio, un registro puede responder 201 (Created) y el correo no salir por una hora: el visitante puede pedir el reenvío (con su enfriamiento).

**Encolado que corta rápido.** Con el broker caído `apply_async` levanta `kombu.exceptions.OperationalError` (verificado contra un puerto cerrado y contra una IP que descarta paquetes), que `enviar_correo` convierte en `CorreoNoEncolado`. `retry=False` y `CELERY_BROKER_TRANSPORT_OPTIONS` (`socket_connect_timeout` y `connect_retries_timeout`, 2 s cada una) hacen que falle en ~2 s: sin ellas, con Redis que no responde esperaba ~124 s (medido en Celery 5.4 y kombu 5.7). Las opciones valen también para los `.delay()` del catálogo y del chat.

**Devolución del cupo.** Cuando registro o reenvío terminan en `email_unavailable`, ese intento no cuenta para sus límites: DRF anota cada intento en `allow_request`, antes de la vista, y `usuarios.throttles.devolver_cupo` recalcula la clave de cada throttle de la vista y quita la marca más reciente. Lo llama el manejador de excepciones (`filmai/exceptions.py`), que es el único punto que ve las dos vistas (el reenvío es la vista de dj-rest-auth, sin subclase por el esquema OpenAPI). Las tasas no cambian (D-3). Sin esto, 5 intentos con Redis caído agotaban el cupo por correo y el visitante recibía 429 (Too Many Requests) aunque no hubiera hecho nada mal.

**Pruebas y desarrollo.** La suite corre las tareas en el acto (`CELERY_TASK_ALWAYS_EAGER=True` cuando el subcomando es `test`): no depende de un broker. `send_test_email` no pasa por la cola: llama a `send_mail` directo y sigue enviando de forma sincrónica, porque es una herramienta de diagnóstico del proveedor. En desarrollo el worker de docker-compose ya corre; si se detiene, el registro responde 201 (Created) y el correo sale cuando vuelve.

**Revisión de PR-Agent (#244, segunda pasada).** Dos observaciones de severidad baja, aceptadas como compromiso y sin cambio de código. (1) *Correo encolado antes del commit*: si el COMMIT del registro fallara después de encolar, el worker enviaría un enlace de una cuenta deshecha. No hay `ATOMIC_REQUESTS`, así que después del encolado solo queda el COMMIT; es un caso rarísimo y su costo es un correo con un enlace que no funciona (el visitante se vuelve a registrar). Pasar a `on_commit` cambiaría ese riesgo por el de la cuenta guardada sin correo, que es peor. (2) *Devolución del cupo no atómica*: `devolver_cupo` lee y escribe la lista sin bloqueo, así que dos fallos simultáneos pueden devolver una sola marca. El `allow_request` de DRF tiene la misma carrera (también lee y escribe sin bloqueo), así que los throttles nunca fueron exactos con pedidos simultáneos; la devolución no empeora esa precisión.

**Pendiente: prueba manual con cuentas reales (la hace el usuario; anotar el resultado acá).** El change `brevo-respaldo` se archivó el 22/11/2026 (se borró la carpeta) con estas pruebas sin hacer; lo que sigue las deja descritas por completo.

1. *Cuenta de Brevo.* Crear una clave de API v3, verificar el remitente único de `BREVO_FROM_EMAIL` y revisar «Authorised IPs» (Settings → Security): permitir la IP de desarrollo o de producción, o quitar la restricción, porque con una IP no autorizada cada llamada responde 401 (Unauthorized).
2. *Prueba de punta a punta en Docker* (`-p filmai` y `RUN_MIGRATIONS=false` si se corre desde un worktree), con `EMAIL_BACKEND=filmai.email_backends.RespaldoBackend` y el worker de Celery levantado: (a) con clave válida de Resend llegan el registro, el reenvío y el reset, el log del worker dice «vía Resend» y Brevo no se llama; (b) con `RESEND_API_KEY=re_invalida` (reiniciando el backend y el worker) llegan los mismos tres correos, y el log muestra el `WARNING` con 401 (Unauthorized) o 403 (Forbidden) y «vía Brevo»; (c) con las dos claves inválidas, desde Q-08 el registro responde 201 (Created) y el worker reintenta y termina en un `ERROR` en su log (ya no hay 503 (Service Unavailable) por proveedores caídos); el reset responde el 200 (OK) genérico; (d) con Redis caído, el registro responde 503 (Service Unavailable) con el mensaje traducido y no deja cuenta.
3. *Q-08.* Con el worker detenido el registro responde 201 (Created) y el correo llega cuando el worker vuelve a arrancar.
4. *Revisar el correo recibido:* que el HTML se vea bien, que esté el texto plano, si Brevo agrega el pie «Sent with Brevo» y si cae en la bandeja o en spam.

**Resultado (22/11/2026, prueba manual de Marcos con el registro).**

- **(a) Clave de Resend válida.** Salió vía Resend en 0,7 s y Brevo no se llamó.
- **(b) Clave de Resend inválida.** Destapó un bug: Resend responde 400 (Bad Request) `validation_error`, no 401 (Unauthorized), y el respaldo no pasaba a Brevo. Se corrigió en el #245 (entrada «Resend responde 400 a una clave inválida»). Con el arreglo, el log muestra `invalid_api_key; se reintenta con Brevo` y el correo llegó vía Brevo.
- **(c) Las dos claves inválidas.** El registro respondió 201 (Created) y el worker reintentó a los 7 s y a los 53 s. Al restaurar las claves y recrear el worker, la tarea pendiente volvió a la cola y el correo salió vía Resend en el reintento siguiente, sin intervención.
- **Quedan sin probar** (d) Redis caído y el punto 3 (worker detenido): ya los cubren los tests de `test_correos_cola.py`.
- **Del correo recibido.** En Gmail el logo se ve roto en local porque `localhost` no es accesible (ver «Correos: el logo es el ticket de la navbar»). Los títulos se ven angostos porque Gmail no carga Big Shoulders y usa Arial Narrow; queda para un PR de interfaz.

Archivos: `backend/filmai/tasks.py`, `backend/filmai/correos/servicio.py`, `backend/filmai/settings.py`, `backend/filmai/exceptions.py`, `backend/usuarios/adapter.py`, `backend/usuarios/passwords.py`, `backend/usuarios/throttles.py`, `backend/filmai/errores/catalogo.py`, `backend/filmai/test_correos_cola.py`, `backend/usuarios/test_devolver_cupo.py`, `backend/usuarios/test_errores_registro.py`, `backend/filmai/test_servicio_correos.py`, `openspec/specs/emails/spec.md`

### 22/11/2026 — Resend responde 400 a una clave inválida

- **Qué pasó.** En la prueba manual del respaldo, con `RESEND_API_KEY` rota, el correo no salió por ningún lado. Resend respondió 400 (Bad Request) `validation_error` con el mensaje «API key is invalid», no 401 (Unauthorized) ni 403 (Forbidden) como dice su documentación. Como el respaldo trataba cualquier 400 como dato inválido, no pasó a Brevo ni reintentó.
- **Qué se hizo.** `ProveedorResend._traducir` reconoce ese 400 por el mensaje (contiene «api key») y lo marca como transitorio con código `invalid_api_key`. Del mensaje se guarda solo el código, no el texto. Cualquier otro 400 sigue sin pasar a Brevo.
- **De paso.** `ErrorDeProveedor` y `EnvioFallido` definen `__reduce__`. Celery guarda con `pickle` la excepción de una tarea fallida, y sin esto el log del worker mostraba un `UnpickleableExceptionWrapper` en lugar del error.
- **Tests.** `test_clave_invalida_con_400_es_transitoria` y `test_las_excepciones_sobreviven_a_pickle` en `backend/filmai/test_email_respaldo.py`.

Archivos: `backend/filmai/email_backends.py`, `backend/filmai/test_email_respaldo.py`, `openspec/specs/emails/spec.md`

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

Una revisión del código encontró dos efectos de la navbar fija en escritorio, y Gonza eligió arreglarlos junto con dos menores invisibles. (1) Next solo lleva arriba la página nueva si su comienzo quedó fuera de la pantalla (`topOfElementInViewport` en `layout-router.js`): con menos scroll que el alto de la barra (84 px), la barra tapaba el principio de la página nueva. `ScrollArribaAlNavegar`, en el layout, la lleva arriba en cada cambio de `pathname`, salvo al entrar, con atrás o adelante (`popstate`) y con un ancla. (2) El menú «…» de las tarjetas de Lists estaba en una caja con `z-10`, que encerraba su capa de cierre (z-40) debajo de la barra (z-30): tocar la barra no lo cerraba y quedaban dos menús abiertos. Se sacó el `z-10`; `relative` alcanza para quedar encima del enlace de la tarjeta. (3) `scroll-padding-top` solo en páginas con navbar (`html:has(header[data-navbar])`), no en login ni registro. (4) `useFondo` usa un `IntersectionObserver` sobre la imagen grande y solo en escritorio: el scroll ya no mide la página en cada evento, y el fondo se actualiza aunque la imagen cambie de alto sin scroll. Quedó sin tocar, por decisión de Gonza, el margen de los títulos de Terms al saltar desde el índice.
Archivos: `frontend/components/ScrollArribaAlNavegar.tsx`, `frontend/app/layout.tsx`, `frontend/components/Navbar.tsx`, `frontend/components/features/lists/ListCard.tsx`, `frontend/app/globals.css`, `frontend/e2e/navbar-fija.spec.ts`, `frontend/e2e/listas.spec.ts`

### 13/11/2026 — Calidad del chatbot: botón, cursor de mano y foco (Q-01, Q-03, Q-04)

El botón flotante no parecía clickeable: no tenía cursor de mano ni hover. El efecto se diseñó primero en el canvas (mesa «Chat button · states») y se aprobó: `bg-primary/80` como los botones primarios, 2 px de elevación con sombra más profunda, 1 px hacia abajo al pulsar, y con `motion-reduce` solo cambia el color. El texto se mantiene sobre 4,5:1 (7,4:1 en el peor caso, sobre negro). Tailwind 4 mueve con la propiedad `translate`, no `transform`: la transición nombra `translate`, si no la elevación saltaría sin animar. El hover solo aplica con el botón habilitado.

El problema del cursor no era solo del chat: Tailwind 4 dejó la flecha en los `<button>` y `globals.css` no tenía ninguna regla. Hay una sola regla en `@layer base` que da la mano a botones, `role="button|switch|menuitem|radio|tab"`, `summary`, `select` y a las casillas con su etiqueta, salvo los deshabilitados y los `aria-disabled`. Está en la capa base para que `cursor-not-allowed`, `cursor-wait` o `cursor-grab` la pisen. Un recorrido de 8 pantallas con la sesión simulada no encontró mano en elementos no interactivos ni botones activos sin ella; los textos, las tarjetas y las capas invisibles de cierre (`div`) no la tienen.

Q-01: axe-core WCAG 2.1 AA sin infracciones en el botón, el panel, una respuesta con tarjetas y el error, a 375, 768 y 1440 px. La app es solo de tema oscuro, no hay variante clara. Se encontró un hueco de foco: al cancelar, el botón «Cancel» se desmonta y el foco caía al `body` dentro de un diálogo modal, y lo mismo al elegir una sugerencia (desaparece la lista). Ahora el foco pasa al campo. Foco al abrir y cerrar, `Escape`, el orden de Tab y la región de anuncios (vacía mientras llega la respuesta, completa al final) quedaron cubiertos con tests. La prueba con lector de pantalla real sigue en el pendiente 7.

Q-03: sin red, 500 (Internal Server Error) con y sin cuerpo JSON (502, Bad Gateway), error dentro del stream, 429 (Too Many Requests) con la espera, respuesta lenta, cancelación e historial sin red: todos muestran su mensaje traducido y una salida; no hubo huecos de mensaje. Q-04: sin desbordes y con objetivos de 44 px en el botón y el panel a 375, 768 y 1440 px. El teclado del celular se simuló reduciendo el área visible a 380 px; no se probó con un teclado real de Android ni de iOS.
Archivos: `frontend/app/globals.css`, `frontend/components/features/chat/ChatFab.tsx`, `frontend/components/features/chat/ChatInput.tsx`, `frontend/components/features/chat/ChatPanel.tsx`, `frontend/e2e/chat-calidad.spec.ts`, `frontend/e2e/chat-simulado.ts`, `docs/05_Plan_de_Desarrollo.md`

### 13/11/2026 — Menos padding vertical en la navbar de escritorio

Marcos sintió que la navbar de escritorio tenía demasiado aire arriba y abajo: el padding vertical baja de `md:py-5` (1,25 rem) a `md:py-3` (0,75 rem). En celular no cambia nada (la altura fija `h-[3.75rem]` sigue igual). La barra pasa de 84 a 68 px, así que `scroll-padding-top` (el espacio que se reserva arriba al enfocar un control o saltar a un ancla) baja de `6rem` a `5rem`: el mismo margen de 12 px sobre la barra. Con `6rem`, el e2e del modal del avatar (`hotfix-perfil.spec.ts`) fallaba porque el botón quedaba dentro de esa franja y Playwright movía la página antes del clic.
Archivos: `frontend/components/Navbar.tsx`, `frontend/app/globals.css`

### 13/11/2026 — Pendientes en el Inicio, Recomendado sin Pendientes y flechas al estilo Netflix

Tres cambios del Inicio. (1) Fila «Pendientes» después de Tendencias: solo con sesión y con títulos de la lista (y del tipo del selector), lo último agregado primero, hasta 20, con «Ver todo» a `/lists/{id}` y `?from=list-{id}` en las tarjetas; usa `GET /api/lists/` (id y cantidad de la predeterminada) y `GET /api/lists/{id}/items/?clase=`, sin cambios en el backend; sin skeleton, así que no reserva lugar y empuja Novedades solo cuando aparece; si las listas fallan, la fila se oculta en silencio y no cuenta para el aviso ni para «fallaron todas» (que siguen siendo solo del catálogo). (2) «Recomendado» excluye también lo que está en Pendientes (antes solo Vistas): ya lo tiene anotado; Favoritos sigue sin excluir (`catalogo/services/recomendado.py`). (3) En `MediaRow` las flechas dejaron el encabezado (quedaban sobre el último póster) y son dos bandas a los costados, a la altura de los pósters (alto calculado con `cqw` desde el ancho de la fila), con degradé desde `--background`; aparecen con hover o foco de teclado, sin izquierda al principio ni derecha al final (según `scrollLeft`/`scrollWidth`, se recalcula al scrollear y al cambiar el tamaño) y solo desde `md`. El canvas de Claude Design queda por ajustar al código.
Archivos: `backend/catalogo/services/recomendado.py`, `frontend/components/features/HomeView.tsx`, `frontend/components/features/MediaRow.tsx`, `traducciones/claves-extra.csv`, `docs/04`

### 13/11/2026 — Pendientes, última fila del Inicio

Marcos pidió que la fila «Pendientes» vaya al final, después de Novedades, y no después de Tendencias: las filas de arriba son de descubrimiento y Pendientes es la lista propia. De paso, como es la última fila que llega (primero se piden las listas y después sus ítems), al aparecer ya no empuja hacia abajo a Novedades.
Archivos: `frontend/components/features/HomeView.tsx`, `frontend/tests/home-page.test.tsx`, `frontend/e2e/home.spec.ts`, `docs/04_Lineamientos_UI.md`

### 13/11/2026 — El botón «Ask FilmAI» ya no se desvanece en el hover

Marcos pidió quitar el desvanecimiento del botón flotante del chat: el hover bajaba el fondo a `bg-primary/80` (el diseño aprobado en la mesa «Chat button · states», ver la entrada de calidad del chatbot) y el amarillo se veía lavado. Ahora el fondo queda igual y el hover es solo la elevación de 2 px con la sombra más profunda; con `motion-reduce`, solo la sombra. El contraste del texto no cambia (el fondo es el amarillo opaco). El e2e pasa a exigir que el fondo se mantenga y que cambie la sombra.
Archivos: `frontend/components/features/chat/ChatFab.tsx`, `frontend/e2e/chat-calidad.spec.ts`

### 15/11/2026 — Interfaz decidida en el canvas para las secciones 13 a 17

Marcos y Gonza eligieron entre las alternativas del canvas de Claude Design (14 y 15/11/2026), cada una dibujada dentro de la pantalla real donde se usa. El canvas quedó limpio: en cada sección hay solo la opción elegida, con un bloque «Behaviour» que describe cada acción, y los artboards interactivos se pueden recorrer con Play. Es la fuente de verdad para el frontend que empieza el 16/11/2026.

- **13 · Lupa de la navbar**: el campo ya construido (#216) mide hoy 20rem fijos y pasa a `clamp(12rem, 24vw, 20rem)` (15,4rem a 1024 px y 12rem a 768 px). El desplegable pasa a la variante «rica»: filas de 84 px, póster de 48 × 72, nota con ★ y fotos de persona de 48 px. Se descartó la compacta (póster de 32 × 48), que es la que está hoy en el código: a Gonza le resultaba muy chica.
- **14 · Títulos parecidos**: en la ficha, la fila «More like {title}» igual a las filas del Inicio (opción A). En las listas, una banda abierta sin caja al final («no una card dentro de otra card»), con filas compactas en 3 columnas y «+ Add» en relleno suave (`--raised-2`, `--line` al pasar el mouse) en lugar de amarillo. En escritorio las filas son un 15 % más grandes que en el celular (póster de 74 × 111 contra 64 × 96; «+ Add» de 34 contra 30 px de alto, con área táctil de 44 px). «Show more suggestions» pide la página siguiente (`?pagina=N`) en lugar de recalcular.
- **15 · «Watching»**: en la ficha, un solo botón de estado con menú (Watchlist, Watching, Watched y «Remove status»). Cada cambio se guarda al instante y muestra un toast con Undo por 6 s: arriba al centro en escritorio y abajo, sobre la barra de pestañas, en el celular (en el celular, todos los toasts van abajo). Undo vuelve un solo paso; si llegan dos cambios seguidos, el segundo reemplaza al toast. Calificar mueve el título a Watched, y Undo devuelve el estado pero conserva la nota. Si el pedido falla, el estado vuelve atrás con un toast de error. La lista Watching usa la página genérica de listas (sin ícono ni texto arriba del buscador, con el conteo en la línea del título) y un menú «⋯» en cada tarjeta: Mark as finished, Rate it… y Remove from Watching, con el mismo toast. Su estado vacío es «Nothing in progress» con «Open Watchlist». Las listas quedan en 4 predeterminadas (4, 2 y 1 columnas). Se descartaron la fila «Continue watching» del Inicio (al tocar la tarjeta no se ve nada, como en una plataforma), las acciones sobre el póster y las filas en lugar de tarjetas.
- **16 · Registro en 3 pasos**: una sola barra de progreso continua de 4 px debajo del logo (33, 67 y 100 %, transición de 0,4 s y sin ella con `prefers-reduced-motion`, `role="progressbar"`). Se pintan solo las barras: sin títulos por paso ni nombres de paso, y el alto del formulario no cambia entre pasos. «Continue» ocupa todo el ancho («Create account» en el paso 3) y «‹ Back» es un enlace discreto debajo, oculto en el paso 1 sin correr nada. El avatar se elige en un modal en el paso 3, en lugar de la grilla dentro del formulario del 13/11/2026.
- **17 · «Stream or rent»**: la línea de proveedores de una fila termina en un chevron dentro de un círculo y toda la línea abre un diálogo (Stream, Rent y Buy, logos de 40 px y atribución a TMDB y JustWatch). En el celular se abre como hoja inferior. Se cierra con Esc o la ✕ y el foco vuelve a la línea. Se descartaron el desplegable que está hoy en el código y la versión colapsable.

Archivos: `docs/decisiones.md`, `docs/05_Plan_de_Desarrollo.md`; canvas «FilmAI — Sistema y catálogo», secciones 13 a 17.

### 15/11/2026 — «Dónde ver» en un diálogo (canvas, sección 17)

La línea «Stream or rent · N options in Argentina» del hero de la ficha termina en un chevrón dentro de un círculo y es un único botón (`aria-expanded`, 44 px). Abre un diálogo modal en escritorio y una hoja inferior en el celular, con el mismo contenido: grupos separados por líneas finas, logos de 40 px sin nombre, «See all options on TMDB» y el crédito de JustWatch. Se cierra con Esc o con el botón de 44 px, y el foco vuelve a la línea. Reemplaza al panel desplegable anterior. Se monta sobre `DialogShell`, que suma una prop opcional `relleno`; los demás diálogos no cambian.
El grupo «Free» que Marcos pidió el 15/11/2026 (después de Stream y solo con datos) ya existía: el backend arma `gratis` uniendo `free` y `ads` de TMDB, así que no se tocó (Marcos confirmó que se queda así el 16/11/2026, ver esa fecha). «N options» sigue contando plataformas únicas (una que está en Stream y en Buy cuenta una vez), como en el canvas: 5 opciones con 6 logos. El scrim y la sombra de la hoja quedan los del `DialogShell` compartido (negro al 60 %; el canvas dibuja 72 %) para no cambiar los otros diálogos.
Archivos: `frontend/components/features/title/WatchProviders.tsx`, `frontend/components/features/title/DialogShell.tsx`, `frontend/tests/watch-providers.test.tsx`, `frontend/e2e/ficha.spec.ts`, `openspec/specs/title-page-ui/spec.md`.

### 16/11/2026 — «Free» de «Dónde ver» incluye las plataformas con publicidad

TMDB separa lo que se ve sin pagar en `free` (gratis) y `ads` (gratis con publicidad). El backend los une en `gratis` desde el 18/10/2026 (`backend/catalogo/services/plataformas.py`); al implementar la sección 17 apareció la duda de si eso era intencional. Marcos decidió dejarlo así: para quien busca dónde ver un título, lo que importa es si tiene que pagar, y separar las plataformas con publicidad dejaría opciones reales afuera o sumaría un grupo más al diálogo.

Para que no se lea como «sin publicidad», el encabezado del grupo pasa a decir «Free (with or without ads)» / «Gratis (con o sin publicidad)». Se eligió esa frase porque es cierta siempre, haya o no plataformas con publicidad en el grupo; «algunas con publicidad» fallaría cuando no hay ninguna. El conteo «N options» no cambia.
Archivos: `docs/decisiones.md`, `traducciones/claves-extra.csv` (clave `title.providers.groups.free`), `frontend/messages/{en,es}/common.json` (regenerados), `frontend/tests/watch-providers.test.tsx` y `openspec/specs/title-page-ui/spec.md`.

### 17/11/2026 — Canvas reorganizado con los 4 PRs del canvas como mergeados (versión 488)

Pedido de Marcos. El canvas «FilmAI — Sistema y catálogo» muestra la app con #223, #224, #225 y #226 ya mergeados, sin paneles «Behaviour» ni notas.

- **Ficha** (sección 3), escritorio y celular:
  - botón de estado con su menú en lugar de Watched y Watchlist;
  - «Stream or rent» que abre el diálogo (hoja inferior en celular);
  - fila «More like Interstellar»;
  - nombres de dirección y reparto con enlace a Search.
  - Se suman a la sección los artboards «status menu, toast and undo» y «where to watch dialog».
- **Search** (sección 4): se suman «Navbar search · states» y «Navbar search · dropdown in Home».
- **Access** (sección 6): Sign up pasa al registro en 3 pasos con el modal de avatar paginado. Se suma «Sign up with Google · steps 2 and 3».
- **Lists** (sección 7):
  - Lists con 4 predeterminadas en 4, 2 y 1 columnas;
  - List detail con el conteo al lado del título y la banda de sugerencias;
  - se suma «Watching · list page and empty state».
- **Borrados**: los títulos de las secciones 13 a 17 y los artboards de propuesta ya absorbidos (`Prop-Similares-Ficha`, `Prop-Viendo-Listas*`, `Prop-Sugerencias-Lista*`, `Prop-Registro-L2*` y `Prop-Registro-Avatares*`). Las menciones a «sección 13 a 17 del canvas» en este archivo y en `docs/05` quedan como referencia histórica: hoy esos diseños viven en las secciones 3, 4, 6 y 7.

### 19/11/2026 — Arreglos de la revisión del #223 (lupa de la navbar y diálogo de «Dónde ver»)

Se aplicaron los puntos de baja severidad de la revisión del #223. **Lupa**: la ✕ del campo pasa de 40 a 44 px (`size-11`) y la píldora pierde relleno (`pl-3`, sin `pr`) para que a 768 px, con 12rem, el texto conserve unos 80 px. El desplegable rico se acota con `max-h-[calc(100dvh-5rem)] overflow-y-auto` y la opción activa se acerca con `scrollIntoView({ block: "nearest" })` (suave, o sin animación con `prefers-reduced-motion`). El póster rico se pide con tope `w154` y tamaño intrínseco de 96 × 144 (el doble de lo que se ve); con 48 × 72 el cargador de `next/image` nunca habría salido de `w92`. `inicialesDe` queda solo en el modo `rica`: la lista compacta de Buscar vuelve a la primera letra. **Créditos**: el nombre con enlace lleva un subrayado tenue fijo (`decoration-fg-3/40`), porque en celular no hay hover. **`DialogShell`**: cierra al tocar el fondo, con la misma comprobación de caja que `ListsMenu` (el relleno del propio `<dialog>` también es «el `<dialog>`»), salvo con `busy` o en un `alertdialog`; y suma `returnFocus` (ref) para devolver el foco al botón que abrió el diálogo, que en Safari no queda enfocado tras un clic. `WatchProviders` lo usa. Se corrigió además la cita al change borrado en `docs/05_Plan_de_Desarrollo.md`.

**Cerrar al tocar el fondo es opcional** (`cerrarConFondo`, apagado por defecto) y por ahora solo lo usa «Dónde ver». En calificar, reseñar, renombrar listas o confirmar, un toque sin querer fuera de la caja borraría lo escrito, así que esos diálogos se siguen cerrando solo con Esc o ✕. Hay un test en `tests/dialog-shell.test.tsx`.

Archivos: `frontend/components/NavbarSearch.tsx`, `SugerenciasLista.tsx`, `features/title/CreditsSection.tsx`, `DialogShell.tsx`, `WatchProviders.tsx`, `frontend/lib/catalog.ts` (`w154`), `frontend/tests/` (`sugerencias-lista`, `navbar-search`, `credits-section`, `watch-providers`, `setup`), `frontend/e2e/navbar-lupa.spec.ts`, `openspec/specs/navbar-search/spec.md`, `openspec/specs/title-page-ui/spec.md`, `docs/05_Plan_de_Desarrollo.md`.

### 19/11/2026 — Canvas al día con el bloqueo al guardar

- **Canvas.** En el artboard «Watching · tap while saving» se borró la opción A y quedó la B (bloqueo + toast «Saving…»). Se sumaron tres artboards con la misma simulación de servidor lento (2,5 s): «Title page · tap while saving» (escritorio, en la sección 3), «Title page · tap while saving · mobile» (sección 3) y «Watching · tap while saving · mobile» (sección 7). En el celular el menú de estado y el de cada tarjeta se abren como hoja inferior. Se renderizaron y probaron los tres estados (menú, guardando, toast con Undo), sin errores de consola.
- **Plan 05.** Se quitó la nota «Canvas pendiente (Watching)».

Archivos: `docs/05_Plan_de_Desarrollo.md` y este archivo.

### 21/11/2026 — Separación entre la lupa y el avatar en la navbar

- **Cambio.** El contenedor de la derecha de la navbar (lupa de búsqueda, avatar o «Log in»/«Sign up») pasa de `gap-2` (0,5 rem) a `gap-5` (1,25 rem, `calc(var(--spacing) * 5)`, 20 px). Lo probó Marcos en las herramientas del navegador y lo dejó como valor definitivo.
- **Alcance.** El gap es del contenedor, así que en escritorio también separa más «Log in» de «Sign up» cuando no hay sesión. La lupa y el avatar no se ven por debajo de 768 px (en celular la lupa está oculta), por lo que ahí no cambia nada. La lupa desplegada crece hacia la izquierda sobre su propio lugar, así que el cambio no la afecta.

Archivos: `frontend/components/Navbar.tsx`, `docs/04_Lineamientos_UI.md` y este archivo.

### 21/11/2026 — «Explorar» en la navbar y campo de Buscar con el estilo de la lupa

Decidido por Marcos. Desde el 14/11/2026 en escritorio `/search` solo se alcanzaba escribiendo en la lupa, aunque sin texto ya muestra todo por popularidad con filtros.

- **Enlace «Explorar».** La navbar de escritorio suma «Explorar» («Browse», clave `nav.main.browse`) entre Inicio y Listas. Lleva a `/search` sin texto, se ve con o sin sesión (Listas sigue solo con sesión) y marca `aria-current="page"` en `/search`. Convive con la lupa, que sigue oculta en `/search`.
- **Celular.** La pestaña inferior que ya llevaba a `/search` pasa a usar la misma clave `nav.main.browse`, así el enlace y la pestaña dicen lo mismo. `nav.main.search` queda para el título de la página, el pie y las migas.
- **Campo de Buscar.** Copia el estilo del campo de la lupa (píldora de 2,75 rem, `bg-raised`, borde `--field-border`, foco con `--fg-3` y anillo, lupa, placeholder y ✕) en escritorio y celular. Las clases se extrajeron a `frontend/components/campo-busqueda.ts`, usado por `NavbarSearch` y `SearchView`. No cambia la lógica: Escape y «/» siguen igual. Antes era un campo grande (3,25 a 3,625 rem, tipografía de pantalla en escritorio).
- **Textos.** Clave nueva `nav.main.browse` en `traducciones/claves-extra.csv` (es «Explorar», en «Browse»); catálogos regenerados.

Archivos: `frontend/components/Navbar.tsx`, `MobileTabs.tsx`, `NavbarSearch.tsx`, `campo-busqueda.ts`, `features/SearchView.tsx`, `frontend/messages/*/common.json` y `common.d.json.ts`, `traducciones/claves-extra.csv`, `frontend/tests/errors-and-account-menu.test.tsx`, `search-view.test.tsx`, `frontend/e2e/*`, `docs/04_Lineamientos_UI.md` y este archivo.

- **Título de la página (21/11/2026).** El h1, el título de la pestaña, la miga de la ficha, el enlace del pie y el de la pantalla 404 (Not Found) dicen «Browse» / «Explorar», igual que la navbar y la pestaña del celular. La clave `nav.main.search` queda sin uso en pantalla. Archivos: `frontend/app/search/page.tsx`, `SearchView.tsx`, `TitleView.tsx`, `Footer.tsx`, `ErrorScreens.tsx` y sus tests.

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

### 16/11/2026 — Q-07: flujo de calificar y scroll infinito extraídos

Primera unidad del PR 4 del canvas («Watching»), antes de tocar el flujo de calificar y de sumar la lista Watching. Es un refactor puro: ningún test existente cambió.

- **`frontend/lib/review-actions.ts`:** `crearCalificacion`, `editarCalificacion` (usa `planEdicion`), `borrarTextoDeResena` y `quitarCalificacion`. Cada una devuelve el resultado y la clave del aviso (`title.feedback.*`). Cada pantalla arma su toast y su estado: la ficha reemplaza la calificación y Mis reseñas la mezcla con el ítem. Las usan `TitleView` y `MyReviewsView`.
- **`frontend/lib/use-cursor-list.ts`:** cursor, «cargar más», reintento y descarte de respuestas viejas. Lo usan Mis reseñas y el detalle de lista; la página Watching lo va a reutilizar.
- **`frontend/lib/use-sentinel.ts`:** `IntersectionObserver` con anticipo de 600 px, usado en Search, Mis reseñas y el detalle de lista. El centinela del chatbot y el de la barra no siguen ese patrón y quedaron como estaban.
- En Search, el callback del centinela ahora lee el estado del último render en vez del que había cuando se creó el observador. No cambia nada visible.

Archivos: `frontend/lib/review-actions.ts`, `frontend/lib/use-cursor-list.ts`, `frontend/lib/use-sentinel.ts`, `frontend/components/features/title/TitleView.tsx`, `frontend/components/features/reviews/MyReviewsView.tsx`, `frontend/components/features/lists/ListDetailView.tsx`, `frontend/components/features/SearchView.tsx`, tests nuevos en `frontend/tests/` y `docs/05_Plan_de_Desarrollo.md` (Q-07).

### 18/11/2026 — Tiempo de los tests: diagnóstico y plan (pendiente 13)

Se planteó reequilibrar la pirámide de pruebas o correr la suite por secciones, porque el CI tarda cada vez más. **Lo que hay**: Playwright con `--shard` en dos jobs y `fullyParallel`, y Vitest con sus workers por defecto. El backend corre en serie (sin `--parallel`) y no hay Test Impact Analysis: cada PR corre todo, incluso los que solo tocan docs.

**Diagnóstico**: el paso «Correr tests (Django)» en `develop` tardó 1m31s en `829f890` y 7m29s en `18d0f5b` (13/11/2026, merge de #203, `perf/ficha-primer-clic`), y desde entonces se mantiene en ~8 min. En la corrida verde del 17/11/2026 (`Ran 1959 tests in 485 s`), 21 tests de `chatbot` tardan ~19,3 s cada uno (406 s en total): `_precalentar_tarjetas` encola una tarea de Celery al guardar un turno con tarjetas, el CI no tiene Redis y la llamada espera al broker hasta rendirse; el `except` la registra («No se pudo precalentar las tarjetas del chat») y el test pasa igual. Otros 7 tests de `catalogo` esperan el backoff real de los reintentos (7 s cada uno, 49 s en total). Los 1931 restantes corren en ~30 s.

**Decisión (Marcos)**: no se reequilibra la pirámide ni se adopta TIA test por test; el problema son unos pocos tests lentos, no la forma de la suite. Se dejan como pendientes, sin implementar todavía, los puntos 1 a 5 del pendiente 13 del plan: aislar los tests del broker, mockear el backoff, `--durations` en el CI, filtros por ruta en los PR y correr solo lo afectado en local. `--parallel` en Django y el sharding del backend quedan como posibilidad, no por ahora.

Archivos: `docs/05_Plan_de_Desarrollo.md` (pendiente 13).

### 19/11/2026 — El CI del #226 tras unir con `develop`

Dos fallas que aparecieron al unir `feat/viendo` con `develop` (que traía el #223, el #224 y el #225).

- **e2e de sugerencias en celular.** El test del #224 buscaba «4 items · 4 movies · 0 TV shows», pero en este PR el conteo pasó a la línea del título y en celular solo dice «4 items» (el desglose es `hidden md:inline`). Se cambió el test por un texto que empieza con «4 items» y solo cuenta el visible, para que valga en ambos viewports. El componente sigue lo que dice el canvas.
- **Undo y conteo inestables.** `datosAhora` (la ref que usa `meterEnLaGrilla` para saber si la tarjeta ya está) se actualizaba en un `useEffect`, un instante después de pintar. Un Undo justo después veía datos viejos, volvía a insertar la tarjeta y sumaba uno de más. Con `useLayoutEffect` la ref se pone al día en el mismo commit del render.

Archivos: `frontend/components/features/lists/ListDetailView.tsx`, `frontend/e2e/listas-sugerencias.spec.ts`

### 19/11/2026 — Base local de desarrollo al día y última llamada del chatbot contra DeepSeek real

- **Migraciones.** Se hizo un respaldo con `pg_dump` y se levantó el backend, que migra al arrancar. Antes estaban aplicadas `catalogo.0008` y `listas.0008`; faltaba `listas.0009_lista_viendo`, que se aplicó sin errores. Antes: 5 usuarios, 7 listas propias, 0 listas «Viendo»/«Watching», 119 ítems. Después: 5 listas Viendo (una por usuario), 7 listas propias intactas, 119 ítems, `showmigrations` sin pendientes y `makemigrations --check` sin cambios. Al desplegar se aplican con el `migrate` normal.
- **Última llamada sin tools, vista por fin contra DeepSeek real.** Con el tope bajado a 1 vuelta solo en el proceso de la prueba (script fuera del repo, sin tocar el orquestador), dos preguntas encadenadas («la más reciente de Villeneuve y después parecidas» y «parecida a Breaking Bad y su precuela») llegaron al tope: `ultima_sin_tools=si`, terminaron con texto y salieron las tarjetas (5 y 2 marcadores válidos, 0 inválidos). Dos preguntas que se resolvían en una vuelta cerraron sin llegar al tope. 10 llamadas al proveedor en total. La línea de log no se vio en la terminal (Django la redirige); la métrica del turno lo confirma.
- **Limpieza.** El comentario de `Tarjeta.poster` en `backend/chatbot/eventos.py` citaba la tool retirada `mostrar_tarjetas`; ahora dice dónde se arma el póster hoy.

Archivos: `backend/chatbot/eventos.py`, `docs/05_Plan_de_Desarrollo.md` y este archivo.

### 21/11/2026 — Suite del backend: de ~9 min a ~2 min (tests aislados del broker y del backoff)

Se implementaron los puntos 1, 2, 3 y 5 del pendiente 13 (diagnóstico del 18/11/2026, esta misma sección). No se tocó el código de producción: los tests dejan de llegar al broker y de dormir, nada más.

- **Precalentado sin broker.** `guardar_turno()` llama a `_precalentar_tarjetas()`, que encola la materialización con `materializar_produccion.delay()`. Cuando el broker no responde, `.delay()` no falla rápido: medido en un compose sin Redis, tarda **19,6 s** en lanzar `OperationalError` (`Name or service not known`). El `except` de `_precalentar_tarjetas` lo registra y el turno se guarda igual, así que cada test con tarjetas pagaba esa espera. Se anula el encolado con `patch("chatbot.servicio.materializar_listado_en_segundo_plano")` en `BaseSSE` y `CorteDeConexionTests` (`chatbot/tests_sse.py`), `GuardarTurnoTests` (`chatbot/tests_servicio.py`) y `FechaDeRecomendadosTests` (`chatbot/tests_recorte.py`); el encolado en sí lo sigue probando `PrecalentarTarjetasTests`, que ya lo mockeaba. En local, con el Redis de Docker levantado, esos tests sí encolaban tareas reales (el broker de desarrollo responde en 0,16 s); ahora tampoco.
- **Backoff sin dormir.** `catalogo.tests.EndpointIntegrationTest` anula `catalogo.client.time.sleep` en `setUp`: los casos de 429 (Too Many Requests), 502 (Bad Gateway) y 503 (Service Unavailable) ya no esperan el backoff real (1 + 2 + 4 s) y el reintento se sigue probando. Queda un test de otra clase (`TMDBClientTest.test_http_errors_map_to_domain_exceptions`) que todavía duerme 7 s; no estaba en el alcance de este cambio.
- **`--durations 15` en el CI.** El paso «Correr tests (Django)» de `.github/workflows/ci.yml` lista los 15 tests más lentos en cada corrida. La regresión del #203 pasó 5 días sin que nadie la viera; con esto aparece en el PR que la trae.
- **En local, solo lo que se toca.** El README documenta `python manage.py test <app>` y `npx vitest --changed` mientras se trabaja, y la suite completa antes del PR (sección 5 de `AGENTS.md`).

**Medición** (`python manage.py test --durations 15` dentro de Docker, proyecto de compose propio y `RUN_MIGRATIONS=false`, sin Redis en la red, que es lo que hace lento al broker):

| Corrida              | Tests | Total   | 15 más lentos |
| -------------------- | ----- | ------- | ------------- |
| Antes (21/11, 17:13) | 2039  | 549,7 s | 287,9 s       |
| Después (21/11)      | 2039  | 126,1 s | 22,1 s        |

La suma de los 15 más lentos pasa de 287,9 s a 22,1 s; el test más lento ya no es un turno con tarjetas (19,1 s) sino los 7 s del caso de `TMDBClientTest` que queda. Los 21 tests de `chatbot` que costaban ~19 s corren ahora en menos de 0,7 s. Queda pendiente el punto 4 (filtros por ruta en los PR) y el e2e `access-screens`, fuera de este cambio.

Archivos: `backend/chatbot/{tests_sse,tests_servicio,tests_recorte}.py`, `backend/catalogo/tests.py`, `.github/workflows/ci.yml`, `README.md`, `docs/05_Plan_de_Desarrollo.md` y este archivo.

### 21/11/2026 — Cierre del pendiente 13: filtros por ruta en el CI y `access-screens` estable

- **Filtros por ruta.** Un job `cambios` en `.github/workflows/ci.yml` compara el PR con su base (`git diff --name-only base...head`). Solo documentación no corre ningún job pesado; solo `frontend/` no corre el backend; solo `backend/` no corre el frontend ni Playwright. Cualquier otro archivo (contratos, traducciones, scripts, el propio workflow) corre los dos: ante la duda, todo. Los push a `main` y `develop` corren todo, porque el CI es la única puerta. Los jobs saltados cuentan como aprobados (la rama no tiene protección con checks obligatorios, y aunque la tuviera un job saltado no bloquea).
- **`access-screens`.** La inestabilidad era de tiempo: cada test renderiza la página de registro con los 3 pasos montados y la lista de países (~1 s solo), y con todos los archivos de Vitest en paralelo superaba el plazo de 5 s (falló en la corrida completa de local, también en `main`). Se probó `userEvent.setup({ delay: null })` y casi no ayudó (35 s a 31 s), así que el archivo sube su plazo a 20 s con `vi.setConfig`. La suite completa de frontend pasa: 83 archivos, 861 tests.
- **Último test dormilón.** `TMDBClientTest.test_http_errors_map_to_domain_exceptions` anula `catalogo.client.time.sleep` y deja de esperar 7 s.

Archivos: `.github/workflows/ci.yml`, `frontend/tests/access-screens.test.tsx`, `backend/catalogo/tests.py`, `docs/05_Plan_de_Desarrollo.md` y este archivo.
