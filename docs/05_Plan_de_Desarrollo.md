# FilmAI — Plan de desarrollo

Estado verificado contra el código de `main` el **26/09/2026**. Responsables: **Marcos** (autenticación, listas, chatbot y administración), **Gonza** (catálogo, perfil y calidad); Fundación y Q-05 son tareas conjuntas.

**Leyenda:** ✅ implementada; 🟡 implementada en parte; ⬜ pendiente. El check verde indica que existe la funcionalidad prevista en el repositorio, no que se haya probado una instalación nueva ni una integración con servicios externos en esta revisión. Cuando una tarea incluye API y pantalla, ambas deben existir para marcarla ✅.

| Módulo                   | Estado | Qué falta                                                                                              |
| ------------------------ | ------ | ------------------------------------------------------------------------------------------------------ |
| 0. Fundación             | 🟡     | Completar el conjunto de 20 avatares previsto en F-05.                                                 |
| 1. Autenticación         | ✅     | —                                                                                                      |
| 2. Catálogo y búsqueda   | 🟡     | Home, búsqueda, ficha de detalle y calificaciones/reseñas de usuarios.                                 |
| 3. Listas                | 🟡     | Pantallas y acciones desde la ficha.                                                                   |
| 4. Perfil y preferencias | 🟡     | Pantallas y navegación del menú de usuario.                                                            |
| 5. Chatbot               | 🟡     | Proveedor de embeddings, búsqueda semántica, LLM, API y panel.                                         |
| 6. Administración        | ✅     | —                                                                                                      |
| 7. Calidad               | 🟡     | Accesibilidad y estados de todas las pantallas, errores, pruebas responsive y cierre de documentación. |

## 0. Fundación — ambos

| ID   | Tarea                                                                                                 | Estado y evidencia                                                                                                                                                                    |
| ---- | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| F-01 | Docker Compose: Django, Next.js, PostgreSQL y Redis.                                                  | ✅ `docker-compose.yml` define esos servicios, Celery worker y Beat.                                                                                                                  |
| F-02 | Proyecto Django, DRF y apps de dominio.                                                               | ✅ `backend/filmai/`, `backend/usuarios/`, `backend/catalogo/`, `backend/listas/` y `backend/chatbot/`.                                                                               |
| F-03 | Proyecto Next.js con Tailwind y componentes Shadcn.                                                   | ✅ `frontend/app/`, `frontend/components/ui/`, `frontend/components.json` y `frontend/app/globals.css`.                                                                               |
| F-04 | Modelos y migraciones: usuario, producción, calificación, reseña, lista, pertenencia, chat y mensaje. | ✅ Modelos y migraciones de las cuatro apps; `Usuario` es `AUTH_USER_MODEL`.                                                                                                          |
| F-05 | Datos de desarrollo: usuarios, producciones, calificaciones, reseñas y avatares.                      | 🟡 `python manage.py seed` crea 3 usuarios y 50 producciones con datos relacionados; `backend/usuarios/avatares.py` solo habilita **10** IDs de avatar frente a los **20** previstos. |
| F-06 | Lint y formato en ambos proyectos; hook local.                                                        | ✅ Ruff, ESLint, Prettier y `.husky/pre-commit` configurados.                                                                                                                         |

## 1. Autenticación — Marcos

| ID   | Tarea                                                                                         | Estado y evidencia                                                                                                          |
| ---- | --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| A-01 | Registro con validaciones, cuenta pendiente, correo de confirmación y listas predeterminadas. | ✅ `backend/usuarios/serializers.py`, `views.py` y `signals.py`.                                                            |
| A-02 | Confirmación de correo y pantallas de resultado.                                              | ✅ Vista de confirmación y `frontend/app/confirmar-correo/[key]/page.tsx`.                                                  |
| A-03 | Login por correo o usuario, JWT en cookies y rechazo de cuentas inactivas.                    | ✅ `backend/usuarios/serializers.py`, `views.py`, `authentication.py` y ajustes de sesión.                                  |
| A-04 | Pantalla de login con Google, recuperación de contraseña y estados de formulario.             | ✅ `frontend/app/(public)/login/page.tsx`.                                                                                  |
| A-05 | Pantalla de registro, validaciones y disponibilidad de usuario con debounce.                  | ✅ `frontend/app/(public)/register/page.tsx` y endpoint de disponibilidad.                                                  |
| A-06 | Google OAuth y completado de datos del primer ingreso.                                        | ✅ Backend social y `frontend/app/completar-google/page.tsx`; el ingreso real requiere credenciales Google configuradas.    |
| A-07 | Recuperación de contraseña por correo, límite de solicitudes y pantalla para crear una nueva. | ✅ Endpoints de `usuarios` y `frontend/app/restablecer-contrasena/[uid]/[token]/page.tsx`.                                  |
| A-08 | Cierre de sesión desde el avatar con confirmación.                                            | ✅ `frontend/components/Navbar.tsx` y `/api/auth/logout/`.                                                                  |
| A-09 | Redirección de rutas protegidas y validación de JWT en el backend.                            | ✅ `frontend/middleware.ts` y autenticación del backend; varias pantallas protegidas aún están pendientes en otros módulos. |

## 2. Catálogo y búsqueda — Gonza

El descubrimiento usa TMDB con caché Redis; PostgreSQL guarda el catálogo materializado y los datos locales. C-04a crea la infraestructura de embeddings, pero el proveedor real y la consulta vectorial pertenecen a B-06. Ver [decisiones](decisiones.md) y los specs canónicos de `openspec/specs/`.

| ID    | Tarea                                                                              | Estado y evidencia                                                                                                                                                                               |
| ----- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| C-01  | Cliente TMDB: tendencias, estrenos, descubrimiento, búsqueda, detalle y metadatos. | ✅ `backend/catalogo/client.py` incluye reintentos, timeout, géneros, créditos y cambios.                                                                                                        |
| C-02  | Caché Redis para las consultas TMDB.                                               | ✅ `backend/catalogo/cache.py` define claves, TTL por endpoint y degradación si Redis falla.                                                                                                     |
| C-03  | API pública de catálogo y búsqueda con filtros, paginación y errores controlados.  | ✅ Siete rutas bajo `/api/catalogo/` en `backend/catalogo/urls.py` y vistas correspondientes.                                                                                                    |
| C-04a | Materialización por `(id_tmdb, tipo)` y encolado asíncrono del embedding.          | ✅ `backend/catalogo/services/materialization.py`, modelo `ProduccionEmbedding` y `generar_embedding` en Celery. El proveedor sigue pendiente en B-06.                                           |
| C-04b | Sincronización diaria, refresco de cambios TMDB y backfill de embeddings.          | ✅ `backend/catalogo/tasks.py` y `backend/filmai/settings.py` programan la sync y el backfill. El backfill solo podrá producir vectores útiles tras B-06.                                        |
| C-04c | Seed inicial y retomable del catálogo por género, década y tipo.                   | ✅ `python manage.py seed_catalogo` en `backend/catalogo/management/commands/seed_catalogo.py`. El comando existe y fue probado; el tamaño final del corpus sigue siendo una decisión operativa. |
| C-05  | Home de descubrimiento: destacada, recomendaciones, tendencias y novedades.        | ⬜ Solo existe la landing pública; falta la Home de catálogo.                                                                                                                                    |
| C-06  | Panel de búsqueda con texto, filtros, paginación y estados.                        | ⬜ Existe la API de búsqueda; falta el panel frontend.                                                                                                                                           |
| C-07  | Ficha de película/serie con metadatos, reseñas y acciones.                         | ⬜ Existen los endpoints de detalle; falta la pantalla.                                                                                                                                          |
| C-08  | API y modal para calificar de 1 a 10 y crear, editar o eliminar reseñas propias.   | ⬜ Existen los modelos y la moderación en Admin; faltan la API y la interfaz de usuario.                                                                                                         |

## 3. Listas — Marcos

Las altas de ítems reciben `(id_tmdb, tipo)` y pasan por `materializar()` antes de crear `Tiene`. Las listas predeterminadas se crean con el usuario.

| ID   | Tarea                                                                             | Estado y evidencia                                                                                                                           |
| ---- | --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| L-01 | API para consultar, crear, renombrar y eliminar listas; agregar y quitar ítems.   | ✅ `backend/listas/urls.py`, `views.py` y pruebas. Incluye resúmenes, preview de pósters, paginación y protección de listas predeterminadas. |
| L-02 | Vista general, creación/edición, orden persistido de listas personales y estados. | ⬜ Falta la pantalla y el mecanismo de reordenamiento.                                                                                       |
| L-03 | Detalle de lista con ítems, paginación visual y eliminación.                      | ⬜ Falta la pantalla.                                                                                                                        |
| L-04 | Acciones de listas desde la ficha de detalle.                                     | ⬜ Falta la ficha; la API ya impide quitar de Vistas una producción calificada.                                                              |

## 4. Perfil y preferencias — Gonza

La API usa nombres `snake_case`. La baja conserva los datos y revoca las sesiones; una cuenta Google puede establecer contraseña local sin perder su vínculo social. Ver [reporte del módulo](reportes_dev/modulo-4-api.md).

| ID   | Tarea                                                                    | Estado y evidencia                                                                                                                                    |
| ---- | ------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| P-01 | Consulta y edición de perfil; cambio de contraseña en endpoint separado. | ✅ `/api/profile/` y `/api/profile/change-password/`, serializers y pruebas en `backend/usuarios/`.                                                   |
| P-02 | Pantalla de perfil con edición inline, avatar y cambio de contraseña.    | ⬜ Falta la pantalla.                                                                                                                                 |
| P-03 | Consulta y edición parcial de tema, privacidad y notificaciones.         | ✅ `/api/preferences/` en `backend/usuarios/cuenta.py`.                                                                                               |
| P-04 | Pantalla de preferencias y acceso a la baja de cuenta.                   | ⬜ Falta la pantalla.                                                                                                                                 |
| P-05 | Baja lógica de cuenta y cierre de sesiones.                              | ✅ `/api/account/deactivate/` en `backend/usuarios/cuenta.py`, con pruebas.                                                                           |
| P-06 | Pantalla «Mis reseñas», edición y eliminación de las propias.            | ⬜ Depende también de C-08.                                                                                                                           |
| P-07 | Avatar y menú de navegación de usuario.                                  | 🟡 `frontend/components/Navbar.tsx` muestra iniciales, menú y logout; Perfil, Mis reseñas y Preferencias aún muestran «Todavía no está implementado». |

## 5. Chatbot — Marcos

El retrieval acordado combina herramientas TMDB y búsqueda vectorial global; el contexto privado se consulta por SQL y se anonimiza antes de enviarlo al LLM. Ver [decisiones](decisiones.md).

| ID   | Tarea                                                                                           | Estado y evidencia                                                                                                                                       |
| ---- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| B-01 | Chat único del MVP, mensaje con autor y contexto JSON.                                          | ✅ `backend/chatbot/models.py`, migración de unicidad y creación del chat por señal.                                                                     |
| B-02 | Servicio LLM con tool calling, datos anonimizados y respuestas ancladas en producciones reales. | ⬜ No hay servicio LLM.                                                                                                                                  |
| B-03 | API autenticada para enviar mensajes, consultar historial y cancelar.                           | ⬜ `backend/chatbot/views.py` aún no implementa endpoints.                                                                                               |
| B-04 | Botón flotante y panel responsive de conversación.                                              | ⬜ Falta la interfaz.                                                                                                                                    |
| B-05 | Contexto con historial, calificaciones, géneros y favoritos del usuario.                        | ⬜ El campo JSON existe; falta construir y actualizar ese contexto.                                                                                      |
| B-06 | Ollama/BGE-M3 y `buscar_semantico` sobre embeddings listos, con filtros SQL.                    | 🟡 pgvector, modelo, texto canónico y tarea Celery existen; `generar_vector()` sigue siendo un stub y faltan el servicio Ollama y la consulta semántica. |

## 6. Administración — Marcos

| ID     | Tarea                                                              | Estado y evidencia                                                                    |
| ------ | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------- |
| AD-01' | Gestión de usuarios y moderación de reseñas mediante Django Admin. | ✅ `backend/usuarios/admin.py`, `backend/catalogo/admin.py` y pruebas HTTP del Admin. |

## 7. Calidad y cierre — Gonza (Q-05 conjunta)

| ID   | Tarea                                                                          | Estado y evidencia                                                                                                                                                                 |
| ---- | ------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Q-01 | Accesibilidad WCAG 2.1 AA en todos los flujos.                                 | 🟡 Hay foco, etiquetas y manejo de Escape en pantallas existentes; falta evaluar y completar los módulos de UI pendientes.                                                         |
| Q-02 | Pantallas 404, error general y errores de API con reintento.                   | ⬜ No hay pantallas de error dedicadas.                                                                                                                                            |
| Q-03 | Carga, vacío, error y feedback coherentes en todas las pantallas.              | 🟡 Hay estados y toasts en autenticación; faltan las demás pantallas.                                                                                                              |
| Q-04 | Verificación responsive de Home, catálogo, listas, detalle, navbar y modales.  | 🟡 La UI actual usa breakpoints; faltan las pantallas principales y su verificación en móvil, tablet y escritorio.                                                                 |
| Q-05 | Variables de entorno e instrucciones completas de instalación, seed y pruebas. | 🟡 `.env.example` y `README.md` documentan el arranque y el seed; `frontend/README.md` conserva el texto inicial de Next.js y falta validar el recorrido de una instalación nueva. |
| Q-06 | CI para lint y formato de frontend y backend.                                  | ✅ `.github/workflows/ci.yml` ejecuta ESLint, Prettier, Ruff y tests Django en PRs y pushes a `main`.                                                                              |

## Próximo trabajo

1. Completar la UI de catálogo (C-05 a C-08) y listas (L-02 a L-04), junto con las pantallas de perfil (P-02, P-04, P-06 y P-07).
2. Conectar Ollama y la búsqueda semántica (B-06), luego construir el servicio, la API, el contexto y el panel del chatbot (B-02 a B-05).
3. Cerrar F-05 y Q-01 a Q-05 sobre los flujos ya implementados. Q-06 ya está implementada.
