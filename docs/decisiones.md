# Decisiones y Cambios — FilmAI

Registro de decisiones de diseño y cambios relevantes del proyecto.
Formato: fecha (DD/MM/AAAA), título y descripción (qué, por qué, archivos afectados).

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

| Decisión | Regla acordada |
| --- | --- |
| D1: idiomas e infraestructura | Inglés y español; inglés nativo de los diseños y por defecto. Frontend con next-intl 4.x, mensajes ICU y sin prefijos de idioma en las rutas. |
| D2: resolución y persistencia | La cuenta es la fuente de verdad con sesión; la cookie `filmai_locale` es su espejo para renderizar. Selector autenticado guarda preferencias y cookie; sin sesión solo cookie. Login sincroniza el idioma guardado. Backend resuelve cuenta, `Accept-Language`, `en`, en ese orden. Registro local y Google guardan el idioma del encabezado. |
| D3: responsabilidad del backend | El backend emite códigos, no traducciones de respuestas. `LANGUAGE_CODE` sigue en `es-ar`, sin LocaleMiddleware. Solo correos y TMDB consumen el idioma efectivo. El chatbot queda fuera de la implementación. |
| D4 y D5: contrato de errores | Sobre `code`, `params`, `errors`; cada error tiene `field` o nulo, `code` y `params`. Códigos ingleses snake_case; campos y enumeraciones actuales siguen en español. `debug` solo con DEBUG=True y nunca se muestra en frontend. Catálogo único y exportación versionada. |
| D6: enumeraciones | `Lista.clave` identifica `favoritos`, `pendientes`, `vistas`; nulo para personalizadas. Nombres almacenados en español; etiquetas traducidas en frontend. Se reservan nombres predeterminados en ambos idiomas y se unifica género por valor estable. |
| D7: texto de interfaz y baja | Se preservan los textos y comportamiento de baja de cuenta. La migración actual es intermedia: capas compartidas y tres pilotos; las pantallas restantes conservan español fijo hasta su rediseño. |
| D8: contenido de TMDB | Idioma por request, caché por idioma y fallback campo por campo a inglés. Persistencia canónica y embeddings en inglés; traducciones en `ProduccionTraduccion`, géneros identificados por ID. Pósters por idioma, con respaldo al original. |
| D9: formatos | Intl con `en-US` y `es-AR`; fecha medium/long en ambos idiomas. Se acepta «28 sept 2026» y se corrigen los diseños. Duración con NumberFormat: narrow en inglés y short en español («2 h 49 min»). Toda lógica de formato se centraliza. |
| D10: rutas | Rutas visibles en inglés, incluida `/complete-signup`; constantes compartidas. Backend, frontend y tests cambian juntos. No se necesitan redirecciones: no hay producción ni enlaces permanentes emitidos. |
| D11: vocabulario y alcance | Glosario en `docs/i18n/glosario.md`; copia española con voseo. No se incorporan instrucciones del sistema de diseño, nombres de mesas de trabajo ni datos de muestra como textos de interfaz. |
| D12: correos | Cuatro casos en texto y HTML, plantillas por idioma con base y servicio compartidos. Idioma del destinatario; vigencias por contexto (24 horas de confirmación, 1 hora de restablecimiento). |
| D13: catálogos | `equivalencias.json` queda inmutable (634 entradas, 41 pantallas). CSV por fila con clave, namespace y estado. Fragmentos se recomponen con ICU; se excluyen muestras/diseño/chatbot. Errores y selector nuevos requieren aprobación de copia antes de sembrar. |

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
aprobados; cuatro recorridos de idioma pasan en el servidor propio del puerto
3117. El puerto habitual 3100 respondía desde otro servidor; la configuración
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
- **Archivos afectados**: `frontend/components/{Navbar,AccountMenu,MobileTabs}.tsx`, `frontend/components/errors/ErrorScreens.tsx`, `frontend/app/{not-found,error,layout}.tsx`, `frontend/app/(public)/page.tsx`, `frontend/lib/routes.ts`, `frontend/scripts/i18n/rules.mjs`, `docs/i18n/copia-propuesta.csv`, catálogos generados, tests `tests/errors-and-account-menu.test.tsx`, `e2e/errores-menu.spec.ts` y ajustes en `e2e/cuenta.spec.ts` y `e2e/perfil.spec.ts`.

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
- **Archivos afectados**: `frontend/components/errors/ErrorScreens.tsx`, `frontend/components/Navbar.tsx`, `docs/i18n/copia-propuesta.csv` (4 claves `errors.pages.*`), catálogos generados, `tests/errors-and-account-menu.test.tsx` y `e2e/errores-menu.spec.ts`.

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
