# Plan de implementación por fases: multiidioma (inglés y español) en FilmAI

> Alcance de este documento: es un plan, no una implementación. La sesión de planificación solo entrega este archivo en `docs/plan-multiidioma.md`, sin tocar código, dependencias ni migraciones. La implementación se ejecuta con Codex, por órdenes de trabajo (sección 10). El documento es autosuficiente: quien lo ejecute no tiene acceso a la conversación en la que se elaboró.

Fecha de elaboración: 07/10/2026. Estado del repositorio analizado: rama `main`, commit `a7dabaf`, árbol limpio.

## Contexto

FilmAI tiene el backend completo (salvo el chatbot) y una base de frontend de 9 páginas, todo en español. Las interfaces definitivas se diseñaron en Claude Design, son nativas en inglés y se implementarán después. Antes hace falta que el idioma deje de ser un supuesto repartido por el código: textos por clave, errores por código, formatos por locale, datos de TMDB y correos según el idioma del usuario, y un selector operativo. El resultado buscado es que una pantalla nueva se construya sin tocar infraestructura de idioma.

---

## 1. Resumen ejecutivo y supuestos

### Resumen

- El trabajo es viable con las decisiones D1 a D13, con **cinco correcciones** que se argumentan en la sección 3: el orden de prioridad de D2 necesita una regla de sincronización, D9 no puede reproducir los formatos en español de los diseños usando solo Intl, la discrepancia de enlaces de D10 no existe, la tabla de equivalencias no puede sembrarse tal cual (D13) y los textos de baja de cuenta contradicen el comportamiento real (D7).
- La aplicación **no está en producción**, lo que elimina la necesidad de redirecciones y reduce el riesgo de las migraciones de datos.
- El backend no necesita traducir errores: basta con emitir códigos. Solo dos piezas del backend dependen del idioma: los correos y TMDB.
- Para las pantallas actuales se adoptó la opción (c), intermedia: migrar las capas compartidas y tres pantallas piloto, y dejar el resto en una lista de excepciones que se vacía al implementar cada interfaz nueva.
- Las 14 preguntas que dejó abiertas la planificación fueron respondidas por el usuario el 07/10/2026 y sus decisiones ya están incorporadas (sección 9).
- Son 10 fases. Las fases 3, 4, 5 y 6 son independientes entre sí después de la fase 2.

### Verificado

- Stack de backend: Django 5.x, DRF 3.15, dj-rest-auth con JWT en cookies httpOnly, allauth 65.19.1, simplejwt, Celery y Redis, PostgreSQL 16 con pgvector, drf-spectacular (`backend/requirements.txt:6-37`, `backend/filmai/settings.py:48-55,156-176,347-376`).
- Stack de frontend: Next.js 15.5.23 con App Router, React 19.1, TypeScript estricto, Tailwind v4, sonner, Vitest y Playwright (`frontend/package.json:5-44`).
- Estado de i18n: `LANGUAGE_CODE = "es-ar"`, `USE_I18N = True`, sin `LocaleMiddleware`, sin `LANGUAGES`, sin `LOCALE_PATHS`, sin archivos `.po` (`backend/filmai/settings.py:65-75,141-144`). El único gettext está en `backend/usuarios/validators.py:11`. En el frontend no hay librería de i18n y `<html lang="es">` está fijo (`frontend/app/layout.tsx:34`).
- Línea base medida el 07/10/2026, con todo en verde: backend 410 tests (141 segundos, `docker compose exec backend python manage.py test`), Vitest 43 tests en 5 archivos y Playwright 24 tests (2,8 minutos).
- La aplicación no está desplegada: sin artefactos de despliegue, `runserver` en el Dockerfile (`backend/Dockerfile:54`), correo en modo sandbox de Resend (`.env.example:42-52`), `docs/decisiones.md:1359-1360`.
- El frontend no compara contra el texto de los mensajes del backend. Todas las bifurcaciones usan `codigo`, estado HTTP o claves de campo (`frontend/app/confirmar-correo/[key]/page.tsx:38-44`, `frontend/app/(public)/login/page.tsx:118`).
- next-intl 4.14.9 declara compatibilidad con Next 15 y React 19 (consulta a npm) y documenta un modo sin enrutamiento por idioma, con el locale leído de una cookie en `i18n/request.ts`.
- Salidas reales de Intl en Node 22 (ICU 78), ejecutadas en esta sesión: ver sección 3.5.
- La tabla de equivalencias tiene 634 entradas y 41 pantallas (recuento sobre `docs/i18n/equivalencias.json`).

### Refutado

- "Los enlaces de los correos usan `confirm-email` y `reset-password` y no coinciden con el frontend": **falso**. Ambos lados usan rutas en español y coinciden (`backend/usuarios/adapter.py:52`, `backend/usuarios/serializers.py:313`, `frontend/app/confirmar-correo/[key]/page.tsx`, `frontend/app/restablecer-contrasena/[uid]/[token]/page.tsx`). La cadena `account-confirm-email` solo aparece como ruta interna de allauth (`backend/filmai/urls.py:135-139`).
- "Unos 80 mensajes en 15 archivos": son 61 apariciones (50 textos distintos) en español en 14 archivos, más 10 en inglés.
- "4 casos de correo con 10 plantillas": son 4 casos con 9 archivos de plantilla; el cuarto caso no tiene plantilla.
- "Rutas `/listas` visibles": `/listas` no tiene página; solo figura en listas de protección (`frontend/middleware.ts:4,27`). `/login` y `/register` ya están en inglés.
- "No existe un campo de tipo en las listas": existe `tipo` (`predeterminada` o `personalizada`, `backend/listas/models.py:37-42`), pero no distingue entre las tres listas por defecto.
- La tabla de equivalencias **no estaba en el repositorio** (búsqueda por contenido, por nombre de archivo y en el historial de git, sin resultados). Se guardó durante la planificación en `docs/i18n/equivalencias.json`.

### Sin verificar (supuestos)

- El texto exacto de los mensajes por defecto de DRF, allauth y simplejwt en español no se observó en ejecución.
- La inalcanzabilidad de los mensajes de cuenta inactiva en el inicio de sesión (sección 2.6) se infiere de la lectura del código.
- El comportamiento de TMDB cuando falta una traducción no está en la documentación oficial; proviene de respuestas del personal de TMDB en su foro y de la medición propia registrada en `docs/decisiones.md:2350-2352`.
- No existe medición de cobertura en ninguno de los dos proyectos.

---

## 2. Hallazgos del repositorio

### 2.1 Cifras estimadas frente a cifras reales

| Concepto | Estimado | Real | Evidencia |
|---|---|---|---|
| Textos de interfaz en el frontend | 270 en 25 archivos | 302 apariciones en 27 archivos (236 textos únicos) | Recorrido con el compilador de TypeScript sobre `app`, `components`, `lib` |
| Archivos de test del frontend | 10 | 10 (5 Vitest, 5 Playwright) | `frontend/tests/`, `frontend/e2e/` |
| Selectores por texto en español | 243 | 220 selectores más 24 aserciones de texto (244) | Mismo recorrido |
| Tests del frontend | sin dato | 43 unitarios y 24 e2e, en verde | Ejecución del 07/10/2026 |
| Usos de `data-testid` | sin dato | 0 | Búsqueda en fuente y tests |
| Mensajes visibles del backend | 80 en 15 archivos | 61 en español (50 distintos) en 14 archivos, más 10 en inglés en 2 | Sección 2.4 |
| Tests del backend que comparan texto en español | sin dato | 20 aserciones (más 2 sobre salida de comandos) | `backend/filmai/tests.py:180-274`, `backend/usuarios/tests.py:88-240,652,1079-1152` |
| Tests del backend | sin dato | 410, en verde | Ejecución del 07/10/2026 |
| Casos de correo | 4 | 4 (más un correo de prueba de desarrollo) | Sección 2.8 |
| Plantillas de correo | 10 | 9 archivos | `backend/templates/account/email/`, `backend/templates/registration/` |
| Rutas visibles en español | 6 | 5 con página (`/perfil`, `/preferencias`, `/mis-resenas`, `/confirmar-correo`, `/restablecer-contrasena`) más `/completar-google` | `frontend/app/` |
| Formatos fijos en es-AR | varios | 2 puntos de uso | `frontend/app/perfil/page.tsx:28-35`, `frontend/components/ReviewCard.tsx:68-70` |
| Literales de ruta en español en e2e | sin dato | 33 llamadas a `goto` o `toHaveURL` | `frontend/e2e/*.spec.ts` |

### 2.2 Stack, estructura, CI y comandos

- Backend: un único módulo de configuración (`backend/filmai/settings.py`), apps `usuarios`, `catalogo`, `listas`, `chatbot` y el paquete `filmai`. Plantillas en `backend/templates/`.
- Frontend: `app/` en la raíz de `frontend/`, 11 componentes, 7 módulos en `lib/`. Todas las páginas con contenido son componentes de cliente; no hay obtención de datos en el servidor. El layout raíz no conoce al usuario (`frontend/app/layout.tsx`).
- Autenticación: cookies httpOnly `access` y `refresh` puestas por el backend; el frontend no guarda tokens (`frontend/lib/api.ts:10-19`).
- CI (`.github/workflows/ci.yml`): job `frontend` (eslint, prettier, `npm run test:unit`, `tsc --noEmit`), job `e2e` (Playwright con API simulada) y job `backend` (ruff y `python manage.py test`). No hay `next build` ni job de despliegue.
- Comandos: `docker compose exec backend python manage.py test`; en `frontend/`, `npm run test:unit` y `npm run test:e2e`.
- Convenciones: ramas `feat/<slug>`, `fix/<slug>`, `chore/<slug>`; commits convencionales en español con ámbito (`perfil`, `usuarios`, `catalogo`, `api`, `decisiones`); merge commit sin squash; sin revisión de PR; sin atribución de IA en los commits (`.agents/skills/conventional-commits/SKILL.md`).

### 2.3 Textos del frontend

- Distribución de las 302 apariciones: 181 textos JSX, 25 de validación, 25 en mapas de etiquetas, 20 `aria-label`, 20 toasts, 19 estados de error, 4 metadatos, 3 `alt`, 2 `placeholder`, 2 títulos de modal y 1 `window.confirm` (`frontend/app/perfil/page.tsx:193-195`).
- No existen `error.tsx`, `not-found.tsx` ni `loading.tsx`.
- Los módulos puros devuelven texto en español: `frontend/lib/validation.ts` (19 textos) y `frontend/lib/reviews.ts:26-29` (lanza `Error` con texto que la interfaz muestra).
- Concatenación y concordancia manual: `frontend/components/ReviewModal.tsx:168-169` (tres condicionales anidados y el nombre "Vistas" incrustado) y `frontend/components/MisResenas.tsx:160-172` (seis variantes de toast por ternario).
- Registros mezclados: voseo en casi todo, "usted" en `frontend/app/confirmar-correo/[key]/page.tsx:57-87` y en `frontend/components/Navbar.tsx:225`.
- Defecto de copia existente: la ayuda de contraseña omite `*` en `frontend/app/restablecer-contrasena/[uid]/[token]/page.tsx:174-175`.

### 2.4 Mensajes del backend y su consumo

- Manejador global en `backend/filmai/exceptions.py:23-70`: reescribe el cuerpo de 401, 403, 404, 405, 429 y 500 con texto en español y descarta los segundos de espera del 429.
- Formas de respuesta vigentes: `{"detail": "..."}`, `{"campo": ["..."]}`, `{"non_field_errors": ["..."]}`, `{"campo": "texto"}` (cadena, no lista, en `backend/catalogo/views.py` y `backend/usuarios/exceptions.py:6-11`), `{"codigo": "...", "detail": "..."}` con 409 (`backend/listas/exceptions.py:8-44`, `backend/catalogo/exceptions.py:49-64`) y `{"codigo": "..."}` con 400 (`backend/usuarios/views.py:202-224,276`).
- Códigos existentes: 8 valores de `codigo` en español y los `code=` de los validadores de contraseña (`backend/usuarios/validators.py:43-63`).
- Textos en inglés que llegan al cliente: validación de parámetros en `backend/catalogo/views.py:22-46` y errores de TMDB en `backend/catalogo/client.py:55-91` vía `backend/catalogo/exceptions.py:41-46`.
- También viaja texto para mostrar en respuestas exitosas: `backend/usuarios/perfil.py:114`, `backend/usuarios/views.py:249-252,280`, `backend/usuarios/cuenta.py:66`.
- Consumo en el frontend: `frontend/lib/api.ts:61-96`. Cinco flujos muestran el texto del backend tal cual (registro, Google, restablecimiento, perfil y cambio de contraseña) y `extractError` puede exponer el nombre interno del campo (`frontend/lib/api.ts:69-70`).

### 2.5 Listas por defecto y género

- `Lista` tiene `nombre`, `tipo`, `activa` y unicidad por `Lower(nombre)` y usuario (`backend/listas/models.py:28-73`). **No hay un identificador estable por lista predeterminada**: se distinguen por el nombre en español.
- Creación por señal `post_save` con `LISTAS_PREDETERMINADAS = ("Favoritos", "Pendientes", "Vistas")` (`backend/usuarios/provisioning.py:6,22-32`, `backend/usuarios/signals.py:19-25`).
- Lógica que depende de la etiqueta: `backend/listas/services.py:17,27-29,52-57`, `backend/listas/views.py:46-52,271`, `backend/listas/migrations/0004_calificadas_en_vistas.py:25`, `backend/usuarios/management/commands/seed.py:50,299,311-313`, `backend/usuarios/management/commands/reparar_recursos_usuarios.py:32` y el texto de `backend/listas/exceptions.py:43`.
- La API devuelve `nombre` y `tipo` crudos (`backend/listas/serializers.py:55-62`).
- Un nombre personalizado se valida contra los nombres del propio usuario, incluidas las predeterminadas (`backend/listas/serializers.py:34-40`); una etiqueta traducida como "Watchlist" no queda reservada.
- Género: `CharField` con valores `masculino`, `femenino`, `no_especifica` (`backend/usuarios/models.py:20-22,94`). Los valores ya son estables. Hay tres etiquetas distintas para `no_especifica`: "No especificar" (`frontend/app/(public)/register/page.tsx:24-28`), "No especificado" (`frontend/app/perfil/page.tsx:37-46`) y "No especifica" en el backend.
- La API nunca expone etiquetas de `choices`; solo valores.

### 2.6 Usuario, flujos y baja de cuenta

- `Usuario` no tiene campo de idioma. Las preferencias existentes son `tema`, `perfil_publico` y tres `notif_*`, servidas por `GET/PUT /api/preferences/` (`backend/usuarios/cuenta.py:18-49`, `backend/usuarios/models.py:107-116`).
- Registro: cuenta en estado `pendiente` y envío sincrónico de la confirmación (`backend/usuarios/views.py:93-116`). Google crea la cuenta `activa` sin correo (`backend/usuarios/adapter.py:88`).
- Ningún correo de usuario pasa por Celery.
- Baja (`POST /api/account/deactivate/`, `backend/usuarios/cuenta.py:52-67`): pone `estado = baja`, invalida todos los tokens de refresco y borra las cookies. No pide contraseña y no elimina datos.
- Efectos comprobados en código: inicio de sesión bloqueado con 403 (`backend/usuarios/serializers.py:55-60`), Google bloqueado (`:208-209,265-266`), el restablecimiento ignora la cuenta en silencio (`:304-309,362-365`), un enlace de confirmación vigente no reactiva (`backend/usuarios/adapter.py:44-45`), correo y nombre de usuario no se pueden reutilizar (`backend/usuarios/serializers.py:88-98`).
- No hay endpoint de reactivación. Solo el Admin de Django puede cambiar `estado` (`backend/usuarios/admin.py:53`).
- Las reseñas y calificaciones de una cuenta dada de baja **siguen visibles** en el listado de la comunidad: no hay filtro por estado del autor (`backend/catalogo/reviews.py:90-101`).
- Los mensajes "Tu cuenta fue dada de baja." y "Tu cuenta aún no está activa." se lanzan como `PermissionDenied` y el manejador los reemplaza por el mensaje genérico de permisos (`backend/filmai/exceptions.py:50-51`); los tests solo verifican el 403 (`backend/usuarios/tests.py:916-936`).

### 2.7 TMDB

- Cliente en `backend/catalogo/client.py:32-164`. **No se envía `language`, `region` ni `include_image_language`** en ninguna llamada. Es una decisión registrada: `docs/decisiones.md:2341-2358`.
- Caché propia sobre Redis (`backend/catalogo/cache.py:32-35,163-169`), clave `tmdb:{endpoint}:{sha256(params)[:16]}`, TTL de 1 hora a 30 días. El idioma entraría en la clave con solo pasarlo como parámetro.
- Persistencia en `ProduccionAudiovisual` (`backend/catalogo/models.py:38-108`): `titulo`, `sinopsis`, `generos` (nombres, por ejemplo "Action"), `keywords` y `estatus` dependen del idioma. Una fila por `(id_tmdb, tipo)`, sin variantes por idioma.
- Los títulos persistidos se sirven en `backend/listas/serializers.py:77-78` y `backend/catalogo/serializers_reviews.py:126-127`.
- No hay tabla de géneros; `get_genres` solo lo usa la semilla (`backend/catalogo/management/commands/seed_catalogo.py:210`).
- Las vistas de catálogo son públicas y sin autenticación (`backend/catalogo/views.py:68-72`): no hay usuario del que leer el idioma.
- El texto canónico de los embeddings usa rótulos en inglés y el corpus en inglés (`backend/catalogo/services/embeddings.py:17-55`, `openspec/specs/embedding-infrastructure/spec.md:40`).
- El frontend no llama a TMDB; solo arma URLs de imagen (`frontend/lib/reviews.ts:35-45`).

### 2.8 Correos

| Caso | Asunto actual | Texto plano | HTML | Origen |
|---|---|---|---|---|
| Confirmación al registrarse | "[FilmAI] Confirmación de cuenta" | Sí | Sí | allauth, `backend/usuarios/views.py:113-115` |
| Reenvío de confirmación | El mismo | Sí | Sí | dj-rest-auth, `backend/filmai/urls.py:130-133` |
| Restablecimiento | "[FilmAI] Restablecimiento de contraseña" | Sí | Sí | `backend/usuarios/serializers.py:316-333` |
| Contraseña actualizada | "[FilmAI] Contraseña actualizada" (literal en código) | Sí | **No** | `backend/usuarios/passwords.py:12-31` |

- No hay plantilla base compartida; cada HTML declara `lang="es"`.
- Las vigencias (24 horas y 1 hora) están escritas dentro del texto y también en la configuración (`backend/filmai/settings.py:137,323`).
- Los correos usan "usted"; la tabla de equivalencias los pasa a voseo.
- `FRONTEND_URL` falta en `.env.example`.

### 2.9 Tests

- Backend: runner por defecto de Django, sin pytest. La mayoría de las aserciones son sobre estado HTTP y claves de campo; ya hay 13 aserciones por `codigo`.
- Seis aserciones del backend buscan por expresión regular las rutas en español de los correos (`backend/usuarios/tests.py:90,221,267,321,346`, `backend/usuarios/test_perfil.py:523`).
- Ningún test verifica la variante HTML de los correos ni el asunto del correo de contraseña actualizada.
- Frontend: los tests unitarios simulan `@/lib/api`, `sonner`, `next/navigation` y `AccountProvider`; Playwright no fija `locale` (`frontend/playwright.config.ts`).
- `frontend/tests/components.test.tsx:55` verifica el literal "3/10/2026", que depende del locale.

### 2.10 Documentación

- `docs/decisiones.md` no tiene ninguna entrada sobre idioma, formatos numéricos o idioma de las rutas. La única relacionada es "El contenido de TMDB sigue en inglés, por ahora" (`docs/decisiones.md:2341-2358`), que este trabajo reemplaza.
- `docs/04_Lineamientos_UI.md` contiene copia literal en español en las secciones 5 a 5j y no define idioma ni formatos. No menciona Claude Design.
- Specs que fijan texto o códigos en español: `openspec/specs/profile-ui/spec.md:19,35`, `openspec/specs/list-endpoints/spec.md:53-54`, `openspec/specs/reviews-api/spec.md:27,195`. `openspec/specs/tmdb-client` no menciona `language`. No hay spec de correos ni de preferencias.
- Desactualizaciones detectadas: `openspec/config.yaml` afirma que el frontend no tiene tests; `docs/03_Modelos de Datos y de Diseño.md:43` dice "Vistos" en lugar de "Vistas".

### 2.11 ¿Qué hacer con las pantallas actuales?

Todas las pantallas existentes (inicio de sesión, registro, confirmación, perfil, preferencias, calificaciones y reseñas) tienen una versión nueva en Claude Design, de modo que su JSX será reescrito.

| Opción | Costo descartable | Riesgo de regresión | Problema principal |
|---|---|---|---|
| (a) Migrar todo | Alto: 302 textos y 244 selectores sobre pantallas que se reescriben | Medio, repartido en 27 archivos | Las claves no se reutilizan: la copia de los diseños es distinta de la actual |
| (b) Solo infraestructura | Nulo | Bajo | **No es viable tal cual**: la fase 3 quita el texto de las respuestas de error y cinco flujos actuales lo muestran |
| (c) Intermedio | Bajo | Bajo y concentrado | Convive interfaz mixta hasta implementar los diseños |

**Decisión: opción (c)**, recomendada por el plan y aceptada por el usuario el 07/10/2026, con este alcance:

- Se migran las capas que sobreviven al rediseño: cliente de API, traducción de errores por código, `lib/validation.ts`, `lib/reviews.ts`, mapas de etiquetas (género, tema, tipo), formatos, metadatos y rutas.
- Se migran tres pantallas piloto completas: Preferencias (aloja el selector, 31 textos) y las dos pantallas de destino de los correos (confirmación y restablecimiento, 29 textos), porque un correo en inglés no debe aterrizar en una página en español.
- El resto (inicio de sesión, registro, completar Google, perfil, calificaciones y reseñas, barra de navegación y modales, unos 200 textos) queda en español fijo, registrado en una lista de excepciones del lint. Cada archivo sale de la lista cuando se implementa su interfaz nueva.
- Los tests de las pantallas no migradas no se tocan y corren con el idioma forzado a español.

Consecuencia aceptada: hasta implementar los diseños, un usuario con idioma inglés verá esas pantallas en español. Es admisible porque la aplicación no está en producción.

---

## 3. Decisiones técnicas

### 3.1 Librería de i18n del frontend

| Alternativa | A favor | En contra |
|---|---|---|
| **next-intl 4.x** | Modo documentado sin prefijo de idioma (locale por cookie en `i18n/request.ts`), sintaxis ICU con plurales y `select`, `t.rich` para frases con enlaces, tipado de claves, `useFormatter` sobre Intl, funciona en componentes de servidor y de cliente | Leer la cookie en el layout vuelve dinámicas todas las rutas |
| react-i18next | Muy difundida | Más configuración manual para App Router; ICU requiere un complemento |
| Lingui | Extracción automática | Usa el texto fuente como identificador, contrario a D13 |
| Solución propia | Sin dependencias | Reimplementa plurales, texto enriquecido y tipado |

**Recomendación: next-intl sin enrutamiento por idioma.**

- El locale se resuelve en `frontend/i18n/request.ts`: cookie `filmai_locale`, luego `Accept-Language`, luego `en`.
- No se necesita el middleware de next-intl; `frontend/middleware.ts` conserva solo la protección de rutas.
- El render dinámico es aceptable: hoy no hay contenido estático que proteger.
- Las claves no pueden contener puntos y los nombres de argumentos solo admiten letras, números y guion bajo (documentación de next-intl), lo que condiciona la convención de la sección 4.
- A verificar en el primer paso de la fase 7: opción experimental `createMessagesDeclaration` para tipar argumentos.

### 3.2 Resolución del idioma (D2)

**Problema de D2 tal como está escrita.** Con la prioridad "idioma guardado, luego selección manual", un usuario autenticado que usa el selector no vería ningún cambio salvo que el selector también escriba en la cuenta. Además, el layout raíz no conoce al usuario, de modo que el primer render solo puede basarse en la cookie.

**Regla propuesta** (respeta la intención de D2):

- La cookie `filmai_locale` es lo que el frontend usa para renderizar. La cuenta es la fuente de verdad para usuarios autenticados y la cookie es su espejo.
- El frontend envía el idioma activo en cada request con el encabezado estándar `Accept-Language` (un solo valor, `en` o `es`), fijado en `apiFetch`.
- El backend calcula el idioma efectivo con una función explícita, `idioma_efectivo(request, usuario=None)`: idioma guardado del usuario, luego encabezado, luego `en`.
- Selector con sesión: `PUT /api/preferences/` con `idioma`, actualiza la cookie y refresca.
- Selector sin sesión: solo cookie.
- Registro (incluido Google): el backend guarda en `idioma` el idioma del encabezado.
- Inicio de sesión: gana el guardado. Si difiere de la cookie, el frontend actualiza la cookie y refresca.
- Cuentas existentes: no se migran. Las bases de desarrollo se regeneran con la semilla, que asigna `es` o `en` a cada cuenta para poder probar ambos idiomas.
- `idioma` admite nulo solo para cuentas creadas fuera del registro (superusuario del arranque, altas desde el Admin). En ese caso se usa el encabezado hasta que el usuario elija.

**Por qué no `LocaleMiddleware`.** La autenticación por JWT ocurre dentro de DRF, después de los middlewares de Django, así que un middleware no ve al usuario. Y por D3 el backend no traduce respuestas: solo correos y TMDB necesitan el idioma, y ambos pueden pedirlo de forma explícita.

### 3.3 Contrato de errores (D4 y D5)

El punto de partida es correcto en su idea y se **mejora** en cuatro aspectos: no cubre errores sin campo, no admite parámetros en errores generales, no define el campo de depuración y deja sin tratar las respuestas exitosas que hoy llevan texto.

Formato único para toda respuesta 4xx y 5xx:

```json
{
  "code": "validation_error",
  "params": {},
  "errors": [
    { "field": "correo", "code": "email_already_used", "params": {} },
    { "field": null, "code": "passwords_do_not_match", "params": {} }
  ],
  "debug": { "message": "El correo ya está registrado." }
}
```

- `code`: código general. Para validación es siempre `validation_error`. Para el resto es el código específico: `not_authenticated`, `invalid_credentials`, `permission_denied`, `not_found`, `method_not_allowed`, `throttled`, `list_name_duplicated`, `upstream_unavailable`, `server_error`.
- `params`: solo valores de máquina. Ejemplo: `throttled` lleva `{"retry_after_seconds": 42}` y la respuesta incluye el encabezado `Retry-After`.
- `errors`: lista, vacía cuando no es un error de validación. `field` es el nombre del campo del request (identificador, no texto) o `null` para errores sin campo. Los campos anidados usan ruta con puntos.
- `debug`: **se incluye solo con `DEBUG=True`**, con el mensaje interno en español. Se recomienda incluirlo porque abarata el diagnóstico, con dos resguardos: un test del backend con `DEBUG=False` que verifica su ausencia y una regla de lint del frontend que prohíbe leer `.debug`.
- Respuestas exitosas: dejan de llevar texto. Pasan a `{"code": "password_updated"}` o equivalente.

Decisiones asociadas:

- **Los códigos van en inglés y `snake_case`**, como en el ejemplo de D4. Es la única parte del contrato que se nombra en inglés; los nombres de campos y los valores de enumeraciones existentes (`masculino`, `oscuro`) no se renombran. El usuario aceptó esa asimetría.
- Los 8 valores actuales de `codigo` se migran: `expirado` a `link_expired`, `invalido` a `link_invalid`, `ya_confirmada` a `already_confirmed`, `nombre_lista_duplicado` a `list_name_duplicated`, `item_duplicado` a `list_item_duplicated`, `lista_predeterminada_protegida` a `default_list_protected`, `calificacion_impide_quitar_de_vistas` a `rating_blocks_removal_from_watched`, `calificacion_duplicada` a `rating_duplicated`.
- **Mecanismo**: DRF ya transporta un código en cada `ErrorDetail`. Basta con agregar `code=` a cada `ValidationError` y construir el sobre en el manejador a partir de `exc.get_full_details()`. Los códigos por defecto de DRF (`required`, `blank`, `invalid`, `max_length`, `unique`, `invalid_choice`) entran al catálogo como genéricos.
- **Catálogo como fuente única**: `backend/filmai/errores/catalogo.py` registra cada código con su estado HTTP y su mensaje interno. El manejador rechaza en tests cualquier código no registrado y normaliza los de terceros (simplejwt, allauth, dj-rest-auth).
- **Exportación**: el comando `exportar_contrato` escribe `contracts/error-codes.json` (versionado). Un test del backend falla si el archivo está desactualizado. Un test del frontend falla si algún código no tiene traducción en `en` y en `es`.
- Búsqueda de la traducción en el frontend: `errors.fields.<campo>.<código>`, luego `errors.codes.<código>`, luego `errors.codes.unknown`. Permite un mensaje específico por campo sin multiplicar códigos.
- **Ventana de compatibilidad**: durante las fases 3 a 7 el backend emite el sobre nuevo y además las claves anteriores (`detail`, `codigo`, claves de campo). Se eliminan cuando el frontend ya consume códigos.

Estados de cuenta en el inicio de sesión: por decisión del usuario, **el inicio de sesión debe distinguir** una cuenta dada de baja (`account_deactivated`) de una sin confirmar (`account_pending_confirmation`). Para no revelar el estado de una cuenta a quien no la controla, esos códigos se emiten solo después de validar la contraseña o el token de Google; con credenciales incorrectas la respuesta es siempre `invalid_credentials`.

### 3.4 Listas por defecto y género (D6)

**¿Dónde se traduce la etiqueta?**

| Alternativa | A favor | En contra |
|---|---|---|
| **Frontend por código** | Coherente con D3 y D4 (el backend no envía texto para mostrar), cambia de idioma sin volver a pedir datos, una sola fuente (los catálogos) | El backend necesita una lista de nombres reservados |
| Backend según idioma | El cliente no conoce los códigos | Dos fuentes de texto, obliga a activar traducción en el backend y a invalidar datos al cambiar de idioma |

**Recomendación: frontend por código**, con claves `enums.defaultList.<clave>` y `enums.gender.<valor>`.

Modelo:

- Se agrega `Lista.clave` (`favoritos`, `pendientes`, `vistas`, nulo para personalizadas), con unicidad por usuario y una restricción que exige `clave` si y solo si `tipo = predeterminada`.
- La API expone `clave`. Para una lista con `clave`, el frontend ignora `nombre`.
- `nombre` se conserva en español, como pide D6.
- Nombres reservados: una lista personalizada no puede llamarse como una predeterminada en ningún idioma soportado. El backend mantiene el conjunto y el contrato exportado lo publica; el test de paridad verifica que coincide con las etiquetas de los catálogos.
- Género: no requiere migración. Se unifican las tres etiquetas en una sola clave por valor.

### 3.5 Formatos por locale (D9)

Salidas reales de Intl en Node 22 (ICU 78), obtenidas durante la planificación:

| Formato | Opciones de Intl | en-US | es-AR |
|---|---|---|---|
| Fecha corta | `dateStyle: "medium"` | Sep 28, 2026 | 28 sept 2026 |
| Fecha larga | `dateStyle: "long"` | September 28, 2026 | 28 de septiembre de 2026 |
| Decimal | `minimumFractionDigits: 1`, `maximumFractionDigits: 1` | 8.5 | 8,5 |
| Entero con miles | por defecto | 41,355 | 41.355 |
| Duración, unidad angosta | `style: "unit"`, `unitDisplay: "narrow"` | 2h 49m | 2h 49min |
| Duración, unidad corta | `style: "unit"`, `unitDisplay: "short"` | 2 hr 49 min | 2 h 49 min |

Otras comprobaciones hechas:

- Con es-AR los números de cuatro cifras también se agrupan ("4.135"); con es-ES no ("4135").
- Con es-MX el decimal lleva punto ("8.5") y los miles coma, por lo que se descarta para formatos.
- Pedir día, mes abreviado y año como opciones sueltas da "28 de sept de 2026" en es-AR. Por eso se usa el formato predefinido (`dateStyle`).

**Corrección a D9.** El inglés coincide exactamente con lo pedido. En español, la fecha corta de los diseños ("28 sep 2026") no la produce Intl con es-AR: la abreviatura de CLDR es "sept". Además, `Intl.DurationFormat` no existe en Node 22, la versión de CI.

**Decisión** (el usuario pidió la opción más simple para el multiidioma):

- Español con **es-AR**: el proyecto es argentino, el backend usa `es-ar` y da coma decimal y punto de miles.
- Fechas: el formato predefinido de Intl, con las mismas opciones en ambos idiomas (`dateStyle: "medium"` para la corta y `dateStyle: "long"` para la larga). No hay composición manual ni código distinto por idioma. En español resulta "28 sept 2026" y **se corrigen los diseños**, no el código.
- Duración: `Intl.NumberFormat` con `style: "unit"`, una llamada para las horas y otra para los minutos, unidas por un espacio. No se usa `DurationFormat`. La única diferencia por idioma es `unitDisplay`: `narrow` en inglés ("2h 49m") y `short` en español ("2 h 49 min").
- El mapa de `en` a `en-US` y de `es` a `es-AR`, junto con el `unitDisplay` de cada uno, vive en un único lugar (`frontend/i18n/config.ts`).
- Una sola utilidad, `frontend/lib/format.ts`, con funciones puras que reciben el locale, y un hook que lo toma del contexto.
- Los tests de formato comparan contra la salida de Intl del entorno, no contra literales.
- Se reemplaza la convención anterior: el inglés usa coma de miles. La tabla de equivalencias tiene "41.355 votes" en inglés y se corrige en la curaduría.

### 3.6 Correos (D12)

| Alternativa | A favor | En contra |
|---|---|---|
| gettext con msgid en español | Estándar de Django | Requiere binarios de gettext y compilación en Docker y CI; los msgid serían párrafos enteros; la copia en inglés no es traducción literal |
| **Plantillas por idioma con base compartida** | Cada correo se revisa entero, sin herramientas nuevas, estructura común en un solo layout | Duplica el cuerpo por idioma |
| Catálogo en diccionarios de Python | Simple | Mezcla copia larga con código |

**Recomendación: plantillas por idioma con un layout HTML común** y un único servicio de envío, `enviar_correo(caso, destinatario, contexto, idioma)`, usado por los cuatro casos (el adaptador de allauth delega en él).

- Idioma del correo: idioma guardado del destinatario; si es nulo, el del request; si no, inglés. En el registro el idioma ya quedó guardado en la misma operación.
- Las vigencias pasan como parámetros desde la configuración.
- "Contraseña actualizada" gana plantilla y versión HTML.
- Un test verifica que cada caso tenga asunto, texto y HTML en ambos idiomas.

### 3.7 TMDB (D8)

Hechos de la documentación oficial vigente:

- `language` usa el formato `xx-YY` (ISO 639-1 más ISO 3166-1).
- Los nombres de personas y personajes no se traducen.
- Géneros: `genre/movie/list` acepta `language` (por defecto `en`). El equivalente de series debe confirmarse en la fase 6.
- Imágenes: `poster_path` prueba el idioma pedido, luego el original y luego la mejor valorada; las variantes regionales no aplican a imágenes; `include_image_language` (por ejemplo `es,en,null`) amplía el filtro.
- Fallback: **la documentación oficial no describe ninguno**. Según el personal de TMDB en su foro, la API no rellena con otro idioma y devuelve la sinopsis vacía. Coincide con la medición propia: 7 de 80 sinopsis vacías con `es-MX` y 5 de 80 con `es-ES` (`docs/decisiones.md:2350-2352`).

Decisiones:

- **Variante de español: `es-MX`** (decisión del usuario, que debe registrarse en `docs/decisiones.md` como decisión relevante). Se elige por los títulos de distribución latinoamericana y por ser lo más simple: una sola variante fija por idioma, sin selección regional por usuario ni por país. El mapa (`en` a `en-US`, `es` a `es-MX`) vive en la configuración y se valida contra `configuration/primary_translations` en la fase 6.
- Costo conocido de esa decisión: con `es-MX` hay algo más de sinopsis vacías que con `es-ES` (7 de 80 frente a 5 de 80 en la medición propia). Lo cubre el fallback a inglés.
- Pósters: cambian con el idioma, con respaldo al original (decisión del usuario).
- El idioma se pasa como parámetro canónico del cliente, por lo que **entra en la clave de caché sin cambiar su formato**. No hace falta vaciar Redis: las claves viejas dejan de coincidir y vencen solas.
- Fallback a inglés, en el backend y campo por campo: si en español `overview` o el título llegan vacíos, se pide la versión en inglés (también cacheada) y se completa. En listados se pide la misma página en inglés y se combina por id. La respuesta indica qué campos quedaron en inglés para que la interfaz marque `lang="en"`.
- Datos persistidos: `ProduccionAudiovisual` sigue siendo canónica en inglés (lo exige el corpus de embeddings). Se agrega `ProduccionTraduccion` (producción, idioma, título, sinopsis, póster), que se completa al materializar y en la sincronización nocturna. Los serializadores eligen por idioma efectivo con fallback al canónico.
- Géneros: se agrega `generos_ids` y la etiqueta se resuelve con la lista de géneros cacheada por idioma. `generos` (nombres en inglés) se conserva para los embeddings.
- `estatus` se trata como código y lo traduce el frontend.
- Limitación conocida: el orden por título usa el título canónico.

### 3.8 Rutas (D10)

| Actual | Nueva |
|---|---|
| `/perfil` | `/profile` |
| `/preferencias` | `/settings` |
| `/mis-resenas` | `/my-reviews` |
| `/listas` (solo protegida) | `/lists` |
| `/confirmar-correo/[key]` | `/confirm-email/[key]` |
| `/restablecer-contrasena/[uid]/[token]` | `/reset-password/[uid]/[token]` |
| `/completar-google` (no listada en D10) | `/complete-signup` (aceptada por el usuario) |
| `/login`, `/register` | Sin cambio |

- **No hacen falta redirecciones**: la aplicación no está en producción y los únicos enlaces emitidos son correos de desarrollo que vencen en 24 horas y 1 hora.
- El cambio debe ser simultáneo en backend y frontend: `backend/usuarios/adapter.py:52`, `backend/usuarios/serializers.py:313`, las 6 expresiones regulares de los tests del backend, los directorios de `frontend/app/`, las tres listas de rutas (`frontend/middleware.ts:4,27`, `frontend/components/AccountProvider.tsx:85,98`, `frontend/components/Navbar.tsx:16`) y los 33 literales de e2e.
- Las tres listas se unifican en `frontend/lib/routes.ts`.
- La referencia rota a `/inicio` (`frontend/app/(public)/page.tsx:57`) se deja para la interfaz de Home; solo se registra.

### 3.9 Siembra de catálogos (D13)

La tabla **no puede sembrarse tal cual**. Problemas detectados al leerla:

- Fragmentos pensados para concatenar: "Creaste «", "» y agregaste Interstellar.", " ítem", " ítems", "Mostrar ", " más", " de ", "Si", "En ". Contradicen D13 y deben recomponerse como mensajes ICU con parámetros y plurales.
- Datos de muestra que no son textos de interfaz: reseñas de ejemplo, "Juan Pérez", "Película · 2014", "12 ítems", fechas, "Pelicula24".
- Documentación del sistema de diseño y nombres de mesas de trabajo ("Opción A · Cartel", "Inicio · escritorio", toda la pantalla "System"), excluidos por D11.
- Textos del chatbot, fuera de alcance: no entran a los catálogos (confirmado por el usuario).
- Marcadores con nombres internos en español (`{{p.titulo}}`, `{{r.nota}}`, `Filtros{{badgeAria}}`), que deben pasar a argumentos ICU.
- Incoherencias: "41.355 votes" en inglés (contra D9); "Recomendado para ti" y "si no sabes qué ver" en tuteo frente al voseo del resto; "Ver detalle" y "Ver ficha" con la misma traducción; el correo dice «Reenviar correo» y el botón "Reenviar enlace"; "[EMAIL DE CONTACTO]" sin completar.
- Homónimos que confirman la necesidad de claves propias: "Todo", "Todos" y "Todas" son "All"; "Género" es "Genre" y "Gender".
- Faltantes: etiquetas del selector de idioma y la mayoría de los mensajes de los códigos de error.

Procedimiento:

- La tabla ya está en `docs/i18n/equivalencias.json` (634 entradas). Ese archivo no se edita: queda como registro del original.
- Construir `docs/i18n/claves.csv`: una fila por entrada con clave, namespace y estado (`ok`, `fragmento`, `muestra`, `diseño`, `chatbot`, `incoherente`). Es trabajo de curaduría con revisión humana.
- Un script genera los catálogos desde las filas `ok` y las recompuestas. A partir de ahí los catálogos son la fuente de verdad y la tabla queda como referencia histórica.
- La copia nueva que falte (errores, selector) requiere aprobación del usuario antes de entrar a los catálogos.
- **Voseo en todo el español** (decisión del usuario): se corrigen los casos en tuteo de la tabla y el "usted" de las pantallas y correos actuales.
- Las correcciones menores señaladas arriba se aplican en la curaduría y los catálogos usan el texto corregido.

---

## 4. Estructura de proyecto propuesta

```
contracts/                              # contrato versionado entre backend y frontend
  error-codes.json                      # generado por el backend
  enums.json                            # claves de listas, géneros, nombres reservados
  openapi.yaml                          # esquema capturado
docs/i18n/
  equivalencias.json                    # tabla original
  claves.csv                            # curaduría: clave, namespace, estado
  glosario.md                           # D11

backend/
  filmai/
    idioma.py                           # IDIOMAS, idioma_efectivo(), mapa a TMDB
    errores/
      catalogo.py                       # fuente única de códigos
      excepciones.py                    # ErrorFilmAI(codigo, params)
      manejador.py                      # arma el sobre (reemplaza exceptions.py)
    correos/
      servicio.py                       # enviar_correo(caso, destinatario, contexto, idioma)
    management/commands/exportar_contrato.py
    tests_golden/                       # respuestas, correos y esquema de referencia
  templates/correos/
    base.html
    confirmacion_registro/{es,en}/{asunto.txt,cuerpo.txt,cuerpo.html}
    confirmacion_correo/{es,en}/...
    restablecer_contrasena/{es,en}/...
    contrasena_actualizada/{es,en}/...
  catalogo/
    models.py                           # + ProduccionTraduccion, generos_ids
    services/idioma_tmdb.py             # fallback a inglés campo por campo
  listas/models.py                      # + Lista.clave
  usuarios/models.py                    # + Usuario.idioma

frontend/
  i18n/
    config.ts                           # locales, defaultLocale, mapa a locale de Intl
    request.ts                          # cookie, Accept-Language, en
    locale-cookie.ts                    # leer y escribir filmai_locale
  messages/
    en/{common,nav,auth,profile,settings,reviews,lists,title,search,home,
        errors,validation,enums,footer,legal}.json
    es/...                              # mismos archivos
  lib/
    api.ts                              # envía Accept-Language; ApiError con códigos
    errors.ts                           # código a clave de catálogo
    format.ts                           # fechas, números, duración
    routes.ts                           # rutas y listas de protección
  components/LanguageSwitcher.tsx       # selector mínimo, reemplazable
  tests/
    i18n-parity.test.ts                 # claves en vs es; códigos del backend
    helpers/render.tsx                  # render con proveedor y locale
  scripts/i18n/
    sembrar-catalogos.mjs
    buscar-residuos.mjs
```

Convenciones de claves:

- Forma `namespace.sección.elemento`, en inglés y `camelCase`. Ejemplo: `auth.login.submit`, `lists.detail.emptyTitle`.
- La clave describe la función del texto, nunca su contenido.
- Sin puntos dentro de un segmento. Argumentos en `camelCase` y en inglés: `{title}`, `{count}`.
- Plurales con ICU: `{count, plural, one {# item} other {# items}}`.
- Frases con enlaces o énfasis con `t.rich`, nunca partidas en fragmentos.
- Enumeraciones del backend: `enums.<enumeración>.<valor>` con el valor tal como viaja en la API (`enums.gender.no_especifica`).
- Errores: `errors.codes.<código>` y `errors.fields.<campo>.<código>`.
- `legal` se carga solo en la página de términos y no se envía al proveedor de cliente.
- Atributos accesibles con sufijo: `...Label` para `aria-label`, `...Alt` para `alt`.

---

## 5. Fases

Reglas comunes a todas las fases:

- Una rama por fase (`feat/i18n-fN-<slug>`), merge commit a `main` con CI en verde, resumen en markdown para el otro integrante.
- Antes de cerrar: `ruff format . && ruff check .`, `npx prettier --check .`, suites completas, entrada en `docs/decisiones.md`, spec canónica actualizada y `graphify update .`.
- Commits convencionales en español, sin atribución de IA.
- **Ningún test existente se modifica** salvo en los puntos señalados como "Tests existentes que cambian", cada uno con su justificación.
- Reestructurar y traducir van en commits separados; se indica en cada fase.

Dependencias: F0, luego F1, luego F2. Después de F2, las fases F3, F4, F5 y F6 son independientes entre sí. F7 requiere F2, F3 y F4. F8 requiere F7. F9 cierra.

### Fase 0: línea base y red de seguridad (tamaño M)

- **Objetivo**: fijar el comportamiento actual antes de tocar nada.
- **Alcance**: solo tests, archivos de referencia y CI.
- **Archivos**: `backend/filmai/tests_golden/` (nuevo), `backend/filmai/tests_contrato.py` (nuevo), `contracts/openapi.yaml` (nuevo), `.github/workflows/ci.yml`.
- **Pasos**:
  1. Correr `docker compose exec backend python manage.py test` y comparar con la referencia del 07/10/2026: 410 tests en verde.
  2. Correr `npm run test:unit` y `npm run test:e2e`. Referencia de esta sesión: 43 y 24 en verde.
  3. Escribir pruebas de caracterización: una por cada mensaje del inventario 2.4, guardando estado HTTP y cuerpo como JSON de referencia. Ejecutarlas con `DEBUG=False` forzado, porque el manejador cambia con `DEBUG`.
  4. Caracterizar los 4 correos: asunto, texto y HTML renderizados.
  5. Capturar el esquema con `python manage.py spectacular --file contracts/openapi.yaml` y agregar un test que detecte divergencias.
  6. Comprobar por ejecución los dos supuestos de 2.6: mensajes de cuenta inactiva y visibilidad de reseñas tras la baja.
  7. Agregar `next build` al job de frontend.
  8. Fijar `locale: "es-AR"` en `frontend/playwright.config.ts` para que la suite no dependa del navegador.
- **Criterios de aceptación**: las tres suites en verde con los conteos registrados; los archivos de referencia se regeneran solo con una variable de entorno explícita; CI ejecuta el build.
- **Pruebas nuevas**: caracterización de API, correos y esquema.
- **Riesgos**: referencias frágiles por datos variables (fechas, tokens). Mitigación: normalizarlos antes de comparar.
- **Reversión**: revertir el merge; no hay cambios de comportamiento.
- **Commits**: `test(api): caracteriza las respuestas de error actuales`; `test(usuarios): caracteriza los correos renderizados`; `chore(api): captura el esquema openapi`; `ci: agrega el build del frontend`; `test(e2e): fija el locale de playwright`.
- **Dependencias**: ninguna. **Ninguna otra fase comienza sin esta.**

### Fase 1: diseño del contrato y de la estructura (tamaño M)

- **Objetivo**: cerrar por escrito todo lo que las fases siguientes implementan.
- **Alcance**: documentación y datos de referencia; sin código de producción.
- **Archivos**: `docs/decisiones.md`, `docs/i18n/equivalencias.json`, `docs/i18n/claves.csv`, `docs/i18n/glosario.md`, specs nuevas `openspec/specs/i18n-core`, `error-contract` y `emails`.
- **Pasos**:
  1. Verificar que `docs/i18n/equivalencias.json` existe y tiene 634 entradas (ya guardada durante la planificación).
  2. Registrar en `docs/decisiones.md` las decisiones D1 a D13 con las correcciones de la sección 3, y marcar como reemplazada la entrada de `docs/decisiones.md:2341-2358`. La elección de `es-MX` para TMDB va como entrada propia, por ser una decisión relevante.
  3. Listar el catálogo completo de códigos: los 60 mensajes del inventario más los genéricos de DRF y los de terceros, con su correspondencia.
  4. Curar la tabla en `claves.csv` según 3.9.
  5. Registrar en `docs/decisiones.md` las respuestas del usuario de la sección 9, incluida la cuestión a considerar sobre la baja de cuenta (9.1).
  6. Redactar y aprobar la copia faltante.
- **Criterios de aceptación**: cada mensaje del inventario tiene un código asignado; cada fila de la tabla tiene estado; ninguna pregunta de impacto alto sigue abierta.
- **Pruebas**: ninguna.
- **Riesgos**: que la curaduría se subestime. Mitigación: acotarla a las filas `ok` y dejar las de pantallas futuras con clave provisional marcada.
- **Reversión**: revertir el merge.
- **Commits**: `docs(i18n): agrega la tabla de equivalencias`; `docs(decisiones): registra las decisiones de multiidioma`; `docs(i18n): asigna claves y namespaces`; `docs(api): especifica el contrato de errores`.
- **Dependencias**: F0.

### Fase 2: backend, núcleo de idioma (tamaño S)

- **Objetivo**: que el backend conozca el idioma efectivo de cada operación.
- **Archivos**: `backend/usuarios/models.py`, migración nueva, `backend/filmai/idioma.py` (nuevo), `backend/filmai/settings.py`, `backend/usuarios/cuenta.py:18-49`, `backend/usuarios/serializers.py` (registro, Google, detalles de usuario), `backend/usuarios/adapter.py`, `backend/usuarios/management/commands/seed.py`, `README.md`.
- **Pasos**:
  1. Definir `IDIOMAS_SOPORTADOS = ("en", "es")` e `IDIOMA_POR_DEFECTO = "en"` en la configuración. `LANGUAGE_CODE` no cambia (D3).
  2. Agregar `Usuario.idioma` (nulo permitido, con opciones). Migración sin relleno de datos.
  3. Implementar `idioma_efectivo(request, usuario=None)` con el analizador de `Accept-Language` de Django.
  4. Exponer `idioma` en `PreferenciasSerializer` (lectura y escritura) y en los serializadores de usuario (lectura).
  5. Guardar el idioma del request al crear la cuenta, también con Google.
  6. Permitir el encabezado en la configuración de CORS si hiciera falta.
  7. Hacer que la semilla asigne `idioma` a las cuentas que crea, repartidas entre `es` y `en`, con al menos una cuenta conocida de cada idioma documentada en el README. Después de aplicar la migración, cada integrante regenera su base de desarrollo con la semilla. No se escribe ningún relleno para las cuentas previas.
- **Criterios de aceptación**: `PUT /api/preferences/` con `{"idioma": "es"}` persiste y un valor no soportado devuelve 400; un registro con `Accept-Language: es` deja `idioma = "es"`; sin encabezado el resultado es `en`; después de correr la semilla hay cuentas en ambos idiomas.
- **Pruebas nuevas**: tabla de casos de `idioma_efectivo` (guardado, encabezado con varios valores y pesos, encabezado inválido, ausente), preferencias, registro y Google. La semilla asigna ambos idiomas.
- **Tests existentes que cambian**: los que comparan la lista exacta de campos de preferencias o de usuario, si existen; se amplían por el campo nuevo.
- **Riesgos**: que el idioma por defecto en inglés afecte flujos existentes. No ocurre: nada lo consume todavía.
- **Reversión**: revertir el merge y la migración (columna nula, sin pérdida).
- **Commits**: `feat(usuarios): agrega el idioma del usuario`; `feat(api): resuelve el idioma efectivo del request`; `feat(usuarios): expone el idioma en preferencias`; `feat(usuarios): guarda el idioma activo al registrarse`; `feat(usuarios): asigna idioma a las cuentas de la semilla`.
- **Dependencias**: F1.
- **Punto de extensión para el chatbot**: `idioma_efectivo` es todo lo que el módulo futuro necesita. No se agrega nada más.

### Fase 3: backend, errores con códigos estables (tamaño L)

- **Objetivo**: que toda respuesta de error lleve códigos del catálogo.
- **Archivos**: `backend/filmai/errores/` (nuevo), `backend/filmai/exceptions.py`, `backend/filmai/views.py:9,17`, `backend/filmai/documentation.py:40`, `backend/usuarios/{serializers,validators,perfil,views,cuenta,exceptions,avatares}.py`, `backend/listas/{serializers,exceptions}.py`, `backend/catalogo/{exceptions,serializers_reviews,views,client}.py`, `contracts/error-codes.json`.
- **Pasos**:
  1. Crear el catálogo y la excepción base.
  2. **Reestructurar**: agregar `code=` a cada error, sin cambiar textos ni formas. Las pruebas de caracterización de F0 deben seguir en verde sin tocarlas.
  3. Hacer que el manejador agregue el sobre nuevo (`code`, `params`, `errors`, `debug`) **junto a** las claves anteriores.
  4. Normalizar los casos irregulares: `{"campo": "texto"}`, errores de TMDB, parámetros de catálogo en inglés, códigos de simplejwt y allauth.
  5. Agregar `retry_after_seconds` y el encabezado `Retry-After` al 429.
  6. Agregar `code` a las respuestas exitosas que hoy llevan texto.
  7. Dar código propio a los estados de cuenta en el inicio de sesión, con el resguardo de 3.3.
  8. Implementar `exportar_contrato` y el test de archivo desactualizado.
  9. Publicar el sobre en el esquema OpenAPI.
- **Criterios de aceptación**: toda respuesta 4xx y 5xx de la suite cumple el sobre; ningún código emitido falta en el catálogo; con `DEBUG=False` no hay `debug`; `contracts/error-codes.json` coincide con el catálogo.
- **Pruebas nuevas**: una por código del catálogo; un cliente de test que valida el sobre en cada respuesta de error de toda la suite; ausencia de `debug`.
- **Tests existentes que cambian**: ninguno en esta fase, gracias a la emisión doble. Las referencias de F0 se regeneran una vez para incorporar las claves nuevas; se justifica porque es una adición y el diff debe mostrar solo claves agregadas.
- **Riesgos**: regresión en el backend terminado; colisión entre claves nuevas y nombres de campo. Mitigación: la caracterización de F0 y una verificación de que ningún serializador tiene campos llamados `code`, `params`, `errors` o `debug`.
- **Reversión**: revertir el merge; el frontend sigue leyendo las claves anteriores, que nunca dejaron de emitirse.
- **Commits**: `feat(api): agrega el catálogo de códigos de error`; `refactor(usuarios): asigna códigos a los errores de validación`; `refactor(listas): ...`; `refactor(catalogo): ...`; `feat(api): emite el sobre de errores junto al formato anterior`; `feat(api): informa la espera en el límite de uso`; `feat(api): exporta el contrato de errores`; `docs(decisiones): ...`.
- **Dependencias**: F1.
- **Cierre diferido**: la eliminación de las claves anteriores ocurre en F8.

### Fase 4: backend, listas por defecto y género (tamaño M)

- **Objetivo**: identificar las listas predeterminadas por clave, nunca por nombre.
- **Archivos**: `backend/listas/models.py`, dos migraciones, `backend/usuarios/provisioning.py:6,22-32`, `backend/listas/services.py:17-57`, `backend/listas/views.py:46-52,271`, `backend/listas/serializers.py:34-40,55-62`, `backend/usuarios/management/commands/{seed,reparar_recursos_usuarios}.py`, `contracts/enums.json`.
- **Pasos (expandir, migrar, contraer)**:
  1. **Expandir**: agregar `clave` nula y una migración de datos que la complete para `tipo = predeterminada` según `Lower(nombre)`. La migración falla de forma explícita si encuentra una predeterminada con nombre desconocido.
  2. **Migrar el código**: reemplazar cada comparación por nombre de 2.5 por `clave`. El orden de presentación pasa a depender de `clave`.
  3. Exponer `clave` en la API.
  4. Agregar los nombres reservados en ambos idiomas a la validación de nombres personalizados y exportarlos.
  5. **Contraer**: restricción de unicidad por usuario y restricción de coherencia entre `tipo` y `clave`, en una migración separada.
  6. `nombre` no se elimina (D6).
- **Prueba sobre copia de datos reales**: no hay producción. Se usa un volcado de la base de desarrollo con la semilla completa, restaurado en una base temporal. Se verifica: tres claves por usuario, cero predeterminadas sin clave, cero personalizadas con clave, mismo total de filas en `Lista` y `Tiene`.
- **Criterios de aceptación**: una búsqueda de `"Vistas"`, `"Favoritos"` y `"Pendientes"` en el código de producción solo encuentra la constante de provisión; renombrar en la base una predeterminada no rompe "calificada implica vista".
- **Pruebas nuevas**: test de migración hacia adelante y hacia atrás; test que cambia el `nombre` de la lista de vistas y verifica que calificar sigue funcionando; nombres reservados; `clave` en la respuesta.
- **Tests existentes que cambian**: ninguno; siguen creando y buscando por nombre, que se conserva.
- **Género**: sin cambios de modelo. Se exportan los valores a `contracts/enums.json`.
- **Riesgos**: datos de desarrollo con una predeterminada renombrada a mano. Mitigación: la migración se detiene y lo informa.
- **Reversión**: la migración de datos es reversible (vacía `clave`); el código anterior sigue funcionando porque `nombre` no cambió.
- **Commits**: `feat(listas): agrega la clave de lista predeterminada`; `refactor(listas): identifica las predeterminadas por clave`; `feat(listas): expone la clave y reserva los nombres del sistema`; `feat(listas): agrega las restricciones de clave`; `docs(decisiones): ...`.
- **Dependencias**: F1. Independiente de F3.

### Fase 5: backend, correos localizados (tamaño M)

- **Objetivo**: los cuatro correos salen en el idioma del destinatario, en texto y HTML.
- **Archivos**: `backend/filmai/correos/servicio.py` (nuevo), `backend/templates/correos/` (nuevo), `backend/usuarios/adapter.py`, `backend/usuarios/serializers.py:316-333`, `backend/usuarios/passwords.py:12-31`, `backend/usuarios/templatetags/nombres.py:8-19`; se retiran las plantillas de `backend/templates/account/email/` y `backend/templates/registration/`.
- **Pasos**:
  1. **Reestructurar**: crear el servicio y el layout base y mover las plantillas actuales a `correos/<caso>/es/`, sin cambiar texto. Las referencias de F0 deben coincidir sin regenerarse.
  2. Pasar las vigencias como contexto.
  3. Agregar plantilla y HTML para "contraseña actualizada", en español.
  4. **Traducir**: agregar las plantillas `en` desde la tabla y elegir el idioma según 3.6.
  5. **Actualizar la copia en español** a la de la tabla (voseo). Commit separado.
  6. Localizar el saludo de reserva ("usuario").
  7. Agregar `FRONTEND_URL` a `.env.example`.
- **Criterios de aceptación**: cada caso produce asunto, texto y HTML en `en` y `es`; un usuario con `idioma = "en"` recibe "[FilmAI] Reset your password" aunque el request llegue en español; `lang` del HTML coincide con el idioma.
- **Pruebas nuevas**: matriz caso por idioma por formato; completitud de plantillas; idioma tomado del destinatario; referencias en ambos idiomas.
- **Tests existentes que cambian**: las aserciones de asunto y cuerpo de `backend/usuarios/tests.py:88,116,217-240` y las referencias de F0 cambian solo en el paso 5, porque la copia se reemplaza a propósito. Se actualizan en ese mismo commit.
- **Riesgos**: depender de la búsqueda de plantillas de allauth. Mitigación: sobrescribir el envío en el adaptador propio, que ya existe.
- **Reversión**: revertir el merge.
- **Commits**: `refactor(usuarios): unifica el envío de correos en un servicio`; `feat(usuarios): agrega la versión html del aviso de contraseña actualizada`; `feat(usuarios): envía los correos en el idioma del destinatario`; `feat(usuarios): actualiza la copia de los correos en español`; `docs(decisiones): ...`.
- **Dependencias**: F2. Las rutas de los enlaces no cambian aquí.

### Fase 6: backend, TMDB según idioma (tamaño L)

- **Objetivo**: datos de TMDB en el idioma efectivo, con inglés como respaldo.
- **Archivos**: `backend/catalogo/client.py:47,102-161`, `backend/catalogo/cache.py`, `backend/catalogo/views.py:78-140`, `backend/catalogo/services/idioma_tmdb.py` (nuevo), `backend/catalogo/models.py`, migraciones, `backend/catalogo/services/materialization.py:151-221`, `backend/catalogo/tasks.py`, `backend/listas/serializers.py:77-78`, `backend/catalogo/serializers_reviews.py:126-127`.
- **Pasos**:
  1. **Reestructurar**: agregar el parámetro de idioma al cliente con `en-US` explícito por defecto. Verificar con una muestra que la respuesta no cambia respecto de no enviarlo.
  2. Confirmar contra la API real: `configuration/primary_translations`, lista de géneros de series, comportamiento del título cuando falta traducción, `include_image_language`.
  3. Resolver el idioma del request en las vistas públicas a partir del encabezado.
  4. Implementar el fallback campo por campo para detalle y listados.
  5. Agregar `ProduccionTraduccion` y `generos_ids` (expandir) y completarlos al materializar.
  6. Rellenar los datos existentes con un comando idempotente, reutilizando la caché.
  7. Hacer que los serializadores elijan por idioma.
  8. Extender la sincronización nocturna.
  9. Exponer la lista de géneros por idioma.
- **Criterios de aceptación**: la misma consulta con `Accept-Language: es` y `en` produce claves de caché distintas; una producción sin sinopsis en español devuelve la inglesa y la marca; títulos de listas y reseñas respetan el idioma; el texto canónico de embeddings y su `source_hash` no cambian.
- **Pruebas nuevas**: cliente (parámetro e idioma en la clave), fallback con respuestas simuladas (sinopsis vacía, título vacío, ambos presentes), combinación de páginas por id, serializadores por idioma, invariancia del hash de embeddings.
- **Tests existentes que cambian**: los que verifican los parámetros exactos enviados a TMDB reciben el parámetro nuevo; es una adición.
- **Riesgos**: duplicar llamadas a TMDB y tocar el límite de uso; pósters distintos por idioma. Mitigación: el fallback solo se dispara con campos vacíos y siempre pasa por caché; el relleno se ejecuta por lotes.
- **Reversión**: cambiar el mapa de idiomas para que `es` apunte a `en-US` restaura el comportamiento actual sin revertir código.
- **Commits**: `refactor(catalogo): pasa el idioma como parámetro del cliente de tmdb`; `feat(catalogo): resuelve el idioma en las vistas públicas`; `feat(catalogo): completa con inglés los campos sin traducción`; `feat(catalogo): guarda las traducciones de las producciones`; `feat(catalogo): sirve títulos y géneros según el idioma`; `feat(catalogo): sincroniza las traducciones`; `docs(decisiones): ...`.
- **Dependencias**: F2. Independiente de F3, F4 y F5.

### Fase 7: frontend, infraestructura (tamaño L)

- **Objetivo**: textos por clave, errores por código, formatos por locale y selector operativo.
- **Archivos**: `frontend/package.json`, `frontend/next.config.ts`, `frontend/i18n/` (nuevo), `frontend/messages/` (nuevo), `frontend/app/layout.tsx`, `frontend/lib/{api,errors,format,routes,validation,reviews}.ts`, `frontend/components/{AccountProvider,LanguageSwitcher}.tsx`, `frontend/middleware.ts`, páginas piloto, `frontend/e2e/cuenta.ts`, `backend/usuarios/adapter.py:52`, `backend/usuarios/serializers.py:313`.
- **Pasos**, en cuatro bloques:
  - **7a. Infraestructura sin cambio visible (reestructurar)**:
    1. Instalar next-intl y configurar el plugin, `request.ts` y el proveedor.
    2. `<html lang>` dinámico y `generateMetadata` en los cuatro puntos con metadatos.
    3. Catálogo `es` con los textos actuales de las piezas a migrar; catálogo `en` con las mismas claves.
    4. Envoltorio de render para los tests con el proveedor en español. Los tests existentes siguen en verde sin cambiar sus selectores.
  - **7b. Capas compartidas**:
    5. `lib/format.ts` y reemplazo de los dos usos de `es-AR`.
    6. `apiFetch` envía `Accept-Language`.
    7. `ApiError` expone `code` y `errors`; `lib/errors.ts` traduce. Los cinco flujos que mostraban texto del backend pasan a traducir por código.
    8. `lib/validation.ts` y `lib/reviews.ts` devuelven códigos.
    9. Etiquetas de género, tema y tipo desde `enums`.
    10. Actualizar la API simulada de e2e al sobre nuevo.
  - **7c. Selector y sincronización**:
    11. `Preferencias` gana `idioma`; `AccountProvider` aplica la regla de 3.2.
    12. `LanguageSwitcher` mínimo en Preferencias y en las páginas públicas.
    13. Pasar el locale al botón de Google (`frontend/components/GoogleButton.tsx:46-51`).
  - **7d. Rutas y pantallas piloto (traducir)**:
    14. Renombrar rutas según 3.8, con `lib/routes.ts`, en el mismo PR que los dos enlaces del backend.
    15. Migrar las tres pantallas piloto. El español usa voseo, en reemplazo del "usted" actual de la pantalla de confirmación.
    16. Sembrar los catálogos completos desde `claves.csv`.
- **Criterios de aceptación**: cambiar el selector cambia `lang`, las pantallas piloto, los errores y los formatos sin recargar manualmente; el idioma persiste entre sesiones y dispositivos; ningún flujo muestra texto del backend; un correo en inglés lleva a una página en inglés.
- **Pruebas nuevas**: resolución del locale (cookie, encabezado, defecto), formatos por locale contra Intl, traducción de errores con sus tres niveles de búsqueda, sincronización al iniciar sesión y al registrarse, selector.
- **Tests existentes que cambian**:
  - `frontend/tests/reviews.test.ts:28-33`: comparaban subcadenas en español; el módulo ahora devuelve códigos.
  - `frontend/tests/components.test.tsx:55`: compara contra la salida de la utilidad de formato en lugar del literal "3/10/2026".
  - Los 33 literales de ruta de e2e y las 6 expresiones regulares del backend, por el renombre. Cambio mecánico, en el mismo commit que el renombre.
  - Los tests de las tres pantallas piloto pasan a selectores independientes del idioma (se completa en F8).
- **Riesgos**: salto de idioma en el primer render de usuarios autenticados cuya cookie difiere de la cuenta; render dinámico de todas las rutas. Mitigación: la cookie se escribe al iniciar sesión y al usar el selector, de modo que el salto solo ocurre en un dispositivo nuevo.
- **Reversión**: los cuatro bloques son PR separados. 7a no altera nada visible. El renombre de rutas es un commit aislado y reversible.
- **Commits** (resumen): `build(frontend): agrega next-intl sin enrutamiento por idioma`; `feat(i18n): resuelve el locale por cookie y encabezado`; `feat(i18n): centraliza los formatos por locale`; `feat(api): envía el idioma y traduce los errores por código`; `refactor(i18n): devuelve códigos desde las validaciones`; `feat(preferencias): agrega el selector de idioma`; `refactor(frontend): pasa las rutas visibles a inglés`; `feat(i18n): migra preferencias y las pantallas de los correos`; `feat(i18n): siembra los catálogos desde la tabla`.
- **Dependencias**: F2, F3 y F4. F5 y F6 no bloquean.

### Fase 8: frontend, pruebas y cierre del contrato (tamaño M)

- **Objetivo**: que el idioma no pueda degradarse sin que un control falle.
- **Archivos**: `frontend/tests/`, `frontend/e2e/`, `frontend/eslint.config.mjs`, `frontend/scripts/i18n/`, `.github/workflows/ci.yml`, y en el backend `filmai/errores/manejador.py`.
- **Pasos**:
  1. Test de paridad: mismas claves y mismos argumentos ICU en `en` y `es`; todo código de `contracts/error-codes.json` traducido en ambos; todo valor de `contracts/enums.json` con etiqueta; nombres reservados coherentes.
  2. Regla de lint contra literales en JSX y en atributos visibles (`react/jsx-no-literals`, ya disponible con la configuración de Next; se evalúa `eslint-plugin-i18next` si no cubre atributos), más una regla para literales en `toast.*`. La lista de excepciones enumera los archivos heredados de 2.11.
  3. Regla que prohíbe leer `.debug` y construir locales de Intl fuera de `lib/format.ts`.
  4. Selectores de las pantallas piloto: por rol con nombre tomado del catálogo, y `data-testid` donde no haya rol estable.
  5. Recorrido e2e en ambos idiomas: registro, confirmación, inicio de sesión, cambio de idioma, restablecimiento.
  6. Script de residuos de español y, opcional, pseudo-localización (sección 6).
  7. **Contraer el contrato de errores**: migrar los tests del backend que leen la forma anterior para que lean el sobre, con ambas formas todavía emitidas (verde antes y después). En un commit posterior, eliminar las claves anteriores.
- **Criterios de aceptación**: quitar una clave de `es` rompe CI; agregar un código sin traducción rompe CI; un literal nuevo en JSX fuera de la lista de excepciones rompe el lint; el recorrido pasa en `en` y `es`; el backend ya no emite `detail`, `codigo` ni claves de campo en errores.
- **Tests existentes que cambian**: los del backend que afirman la forma anterior de los errores, incluidas las 20 aserciones de texto de 2.9. Justificación: el cambio de contrato es el objetivo, y el oráculo se preserva al migrar los tests mientras ambas formas coexisten, en un commit sin cambios de lógica.
- **Riesgos**: que la lista de excepciones se vuelva permanente. Mitigación: un test fija su tamaño máximo y solo puede bajar.
- **Reversión**: la eliminación de las claves anteriores es un commit aislado.
- **Commits**: `test(i18n): verifica la paridad de catálogos y códigos`; `chore(eslint): prohíbe literales de texto en la interfaz`; `test(e2e): recorre los flujos de cuenta en ambos idiomas`; `test(api): afirma los errores por código`; `refactor(api): elimina el formato anterior de errores`.
- **Dependencias**: F7.

### Fase 9: documentación y cierre (tamaño S)

- **Objetivo**: dejar la documentación coherente con el código y una guía de uso.
- **Archivos**: `docs/decisiones.md`, `docs/04_Lineamientos_UI.md`, `docs/03_Modelos de Datos y de Diseño.md`, `docs/06_TMDB_API_Referencia.md`, `openspec/specs/{profile-ui,list-endpoints,reviews-api,tmdb-client,tmdb-cache}/spec.md`, `openspec/config.yaml`, `README.md`, `AGENTS.md`, `docs/i18n/guia.md` (nuevo).
- **Pasos**:
  1. Doc 04: declarar inglés como idioma nativo, formatos por locale, rutas y el selector en Preferencias.
  2. Doc 03: `idioma`, `clave`, `ProduccionTraduccion`; corregir "Vistos".
  3. Specs: reemplazar texto literal por claves y códigos nuevos.
  4. `docs/i18n/guia.md`: cómo agregar un texto, un código de error, un correo y un formato.
  5. AGENTS.md: regla de no introducir literales y de mantener la paridad.
  6. Documentar el punto de extensión del chatbot: `idioma_efectivo` y nada más.
  7. Ejecutar la lista de la sección 8.
- **Criterios de aceptación**: la sección 8 completa; ninguna spec cita mensajes en español como requisito.
- **Commits**: `docs: alinea doc 03, doc 04 y doc 06 con multiidioma`; `docs(specs): actualiza las specs al contrato por códigos`; `docs(i18n): agrega la guía de uso`.
- **Dependencias**: F8.

---

## 6. Matriz de verificación

| Qué se comprueba | Cómo | Dónde | Fase |
|---|---|---|---|
| Ninguna respuesta lleva texto para mostrar | Cliente de test que valida el sobre en toda respuesta de error; test con `DEBUG=False` | Backend, CI | F3, F8 |
| Todo código tiene traducción | Test de paridad contra `contracts/error-codes.json` | Frontend, CI | F8 |
| El contrato exportado está al día | Test que regenera y compara | Backend, CI | F3 |
| Catálogos equivalentes | Mismas claves y argumentos ICU en `en` y `es` | Frontend, CI | F8 |
| Sin literales nuevos en la interfaz | Regla de lint con lista de excepciones decreciente | Frontend, CI | F8 |
| Sin residuos de español | Script con el compilador de TypeScript que busca literales con tildes, eñes o palabras frecuentes fuera de `messages/es` y de la lista de excepciones | Frontend, CI | F8 |
| Sin locale fijo en componentes | Regla que restringe `Intl.*` y `toLocale*` a `lib/format.ts` | Frontend, CI | F8 |
| Sin lógica por etiqueta | Búsqueda de los nombres de listas en código de producción; test que renombra la lista de vistas | Backend | F4 |
| Correos completos | Matriz caso por idioma por formato; referencias en ambos idiomas | Backend, CI | F5 |
| Recorrido de correos | Con `RESEND_TEST_RECIPIENT`, enviar los 4 casos en `en` y `es` y revisar en un cliente real | Manual | F5, F9 |
| TMDB por idioma | Clave de caché distinta por idioma; fallback con respuestas simuladas | Backend, CI | F6 |
| Flujos en ambos idiomas | Recorrido e2e parametrizado por locale | Frontend, CI | F8 |
| Formatos | Tests por locale contra la salida de Intl | Frontend, CI | F7 |
| Texto fijo oculto o que no entra | Pseudo-localización: locale de desarrollo generado desde `en` con caracteres acentuados y 30 % más de largo | Manual, opcional | F8 |
| Esquema de la API | Comparación con `contracts/openapi.yaml` | Backend, CI | F0 |

La pseudo-localización se considera útil pero opcional: es barata y conviene sobre todo al implementar las interfaces nuevas.

---

## 7. Riesgos principales y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Regresión en el backend terminado al reestructurar errores | Media | Alto | Caracterización de F0; reestructurar sin cambiar textos; emisión doble; un commit por app |
| La línea base cambia entre la planificación y el inicio del trabajo | Baja | Medio | OT-00 vuelve a correr las tres suites y las compara con los conteos de 10.5 |
| Migración de datos de listas | Baja | Medio | Sin producción; expandir y contraer; la migración se detiene ante nombres desconocidos; prueba sobre volcado de desarrollo |
| Relleno de traducciones de TMDB excede el límite de uso | Media | Medio | Por lotes, idempotente, reutiliza la caché |
| Enlaces ya emitidos | Muy baja | Bajo | Sin producción; vencen en 24 horas y 1 hora; backend y frontend cambian en el mismo PR |
| Desfase entre catálogos y códigos | Media | Alto | Contrato exportado y versionado; dos tests de paridad en CI; el manejador rechaza códigos no registrados |
| Trabajo descartable en pantallas que se reemplazan | Alta con la opción (a) | Medio | Opción (c): solo capas compartidas y tres pantallas piloto |
| La lista de excepciones del lint se vuelve permanente | Media | Medio | Tamaño máximo fijado por test; cada interfaz nueva la reduce |
| Interfaz mixta hasta implementar los diseños | Cierta | Bajo | Aceptada de forma explícita; no hay usuarios reales |
| La tabla se siembra con fragmentos o datos de muestra | Alta sin curaduría | Alto | Curaduría con estados en `claves.csv` antes de generar |
| Los formatos en español no coinciden con los diseños | Cierta | Bajo | Decidido: manda Intl y se corrigen los diseños ("28 sept 2026"); tests contra Intl |
| Salto de idioma en el primer render | Media | Bajo | Cookie como espejo de la cuenta |
| Divergencia entre cookie y cuenta | Media | Medio | Una sola regla de sincronización, con tests |
| `debug` filtra texto a la interfaz | Baja | Medio | Solo con `DEBUG=True`; test de ausencia; regla de lint |
| Códigos de estado de cuenta permiten enumerar usuarios | Media | Medio | Se emiten solo tras validar la contraseña o el token de Google; con credenciales incorrectas, siempre `invalid_credentials` |
| Los textos de baja de cuenta no describen todo el comportamiento real | Cierta | Bajo | Aceptado por el usuario; se registra como cuestión a considerar (9.1) |

---

## 8. Definition of Ready

Se puede empezar a implementar las interfaces de Claude Design cuando todo lo siguiente es verificable:

- [ ] Las tres suites están en verde en CI, con `next build` incluido.
- [ ] `useTranslations` funciona en componentes de servidor y de cliente, y `docs/i18n/guia.md` explica cómo agregar un texto.
- [ ] `frontend/messages/en` y `frontend/messages/es` contienen las claves de todas las pantallas diseñadas, con plurales y parámetros, sin fragmentos concatenables.
- [ ] El test de paridad de catálogos pasa y falla al quitar una clave.
- [ ] El backend responde errores solo con el sobre de códigos y no emite las claves anteriores.
- [ ] `contracts/error-codes.json` está al día y cada código tiene traducción en ambos idiomas.
- [ ] `frontend/lib/errors.ts` convierte cualquier `ApiError` en un mensaje localizado, por campo y general.
- [ ] `frontend/lib/format.ts` cubre fecha corta, fecha larga, decimal, entero con miles y duración, y es el único lugar con locales de Intl.
- [ ] El selector cambia el idioma con y sin sesión, y la elección persiste en la cuenta y en la cookie.
- [ ] La semilla crea cuentas en `es` y en `en`, documentadas en el README.
- [ ] `<html lang>` y los metadatos siguen el idioma activo.
- [ ] `GET /api/lists/` devuelve `clave` y las etiquetas de listas y género salen de `enums`.
- [ ] Los endpoints de catálogo devuelven datos en el idioma del request, con inglés como respaldo, e indican los campos en respaldo.
- [ ] Los cuatro correos existen en ambos idiomas, en texto y HTML, y sus enlaces usan `/confirm-email` y `/reset-password`.
- [ ] Las rutas visibles están en inglés y definidas en `frontend/lib/routes.ts`.
- [ ] La regla de lint contra literales está activa y la lista de excepciones contiene solo las pantallas heredadas.
- [ ] El recorrido e2e pasa en `en` y en `es`.
- [ ] `docs/decisiones.md`, doc 03, doc 04 y las specs reflejan el estado real.
- [ ] `idioma_efectivo` está documentado como punto de extensión para el chatbot.

---

## 9. Preguntas al usuario y decisiones tomadas

Las 14 preguntas que dejó abiertas la planificación fueron respondidas por el usuario el 07/10/2026. **No queda ninguna pendiente.** Cada respuesta ya está incorporada en la sección indicada y debe registrarse en `docs/decisiones.md` durante OT-10.

| N.º | Pregunta | Decisión del usuario | Dónde se aplica |
|---|---|---|---|
| 1 | ¿Qué hacer con las pantallas actuales? | Opción (c), intermedia. Se acepta la interfaz mixta hasta implementar los diseños | 2.11, F7, F8 |
| 2 | ¿Dónde está la tabla de equivalencias? | Resuelto: `docs/i18n/equivalencias.json`, 634 entradas | 3.9, F1 |
| 3 | Baja de cuenta: el texto no describe todo el comportamiento | Se deja como está: no cambian ni el texto ni el comportamiento. Se documenta como cuestión a considerar | 9.1, F1 |
| 4 | ¿Códigos de error en inglés con campos y enumeraciones en español? | Sí | 3.3 |
| 5 | ¿El inicio de sesión distingue cuenta dada de baja y cuenta sin confirmar? | Sí, debe poder distinguirlas | 3.3, F3 |
| 6 | Formato de fecha corta en español | El más simple para el multiidioma: el formato predefinido de Intl, igual en ambos idiomas. Resulta "28 sept 2026" y se corrigen los diseños | 3.5, F7 |
| 7 | Variante de español para TMDB | `es-MX`, con la implementación más simple. Debe registrarse como decisión relevante | 3.7, F1, F6 |
| 8 | ¿Qué idioma tienen las cuentas existentes? | No se migran: se regeneran con la semilla, que asigna `es` o `en` para poder probar ambos idiomas | 3.2, F2 |
| 9 | Registro del español | Voseo en todo: interfaz, correos y catálogos | 3.9, F5, F7 |
| 10 | ¿Los pósters cambian con el idioma? | Sí, con respaldo al original | 3.7, F6 |
| 11 | Ruta para completar el registro con Google | `/complete-signup` | 3.8, F7 |
| 12 | ¿Los textos del chatbot entran a los catálogos? | No. Quedan en la tabla hasta que se aborde ese módulo | 3.9, F1 |
| 13 | Correcciones menores de la tabla | Se corrigen en la curaduría y los catálogos usan el texto corregido | 3.9, F1 |
| 14 | Duración en español | "2 h 49 min", que Intl produce con la unidad corta | 3.5, F7 |

### 9.1 Cuestión a considerar: baja de cuenta

Por decisión del usuario, este trabajo **no cambia** ni los textos ni el comportamiento de la baja de cuenta. Queda documentado lo siguiente para una revisión futura:

- La baja es lógica: la cuenta pasa a estado `baja` y no se elimina ningún dato.
- Un administrador puede reactivar la cuenta desde el Admin de Django. El usuario no puede hacerlo por su cuenta.
- Las calificaciones y reseñas de la cuenta dada de baja se conservan y siguen visibles para el resto de los usuarios, con el nombre de usuario.
- El correo y el nombre de usuario de la cuenta no pueden volver a usarse en un registro nuevo.
- Los textos de la interfaz dicen que la baja es "irreversible" y que la cuenta no se podrá reactivar. Es cierto para el usuario, no para un administrador.
- Los términos y condiciones dicen que la baja es "definitiva" y ofrecen la supresión de datos a pedido, un circuito que hoy no existe.
- Los textos no avisan que las reseñas siguen públicas después de la baja.

Acción dentro de este plan: registrar la cuestión en `docs/decisiones.md` durante OT-10, con el comportamiento actual descrito. Los catálogos usan los textos de la tabla sin modificarlos.

---

## 10. Ejecución con Codex

El plan se ejecuta en sesiones cortas e independientes. Cada sesión toma **una sola orden de trabajo (OT)**, la termina con todo en verde y deja constancia en este mismo documento, porque la sesión siguiente no recuerda nada de la anterior.

### 10.1 Lo que debe aportar el usuario

- La tabla de equivalencias ya está en `docs/i18n/equivalencias.json` (634 entradas, 41 pantallas). No requiere ninguna acción.
- Las preguntas de la sección 9 ya están respondidas (07/10/2026). No requiere ninguna acción.
- Aprobar la copia nueva que se redacte en OT-13 (mensajes de error y etiquetas del selector).
- El entorno con Docker ya funciona (confirmado el 07/10/2026). No requiere ninguna acción.
- Revisar a mano los correos en un cliente real al cerrar OT-52 y OT-90.

### 10.2 Requisitos de entorno

- Backend con Docker: `docker compose up -d` y `docker compose exec backend python manage.py test`.
- Backend sin Docker: Python 3.12, `pip install -r backend/requirements.txt`, PostgreSQL 16 con pgvector y las variables que usa CI (`.github/workflows/ci.yml:110-167`).
- Frontend: Node 22, el de CI. En la máquina de desarrollo está en `~/.nvm/versions/node/`, fuera del PATH por defecto.
- e2e: `npx playwright install --with-deps chromium` la primera vez.
- Lint y formato: `ruff format . && ruff check .` en `backend/`; `npx eslint . --max-warnings=0`, `npx prettier --check .` y `npx tsc --noEmit` en `frontend/`.

### 10.3 Reglas de cada sesión

- Leer `AGENTS.md`, las secciones 1 a 4 de este plan, la fase correspondiente de la sección 5 y esta sección completa.
- Revisar las skills de `.agents/skills/` que apliquen (`explicar-al-implementar` está siempre activa).
- Ejecutar solo la orden indicada. No adelantar trabajo de otra orden.
- Comprobar que las citas de archivo y línea siguen vigentes antes de editar; el repositorio pudo avanzar desde `a7dabaf`.
- Ante una ambigüedad o una contradicción entre el plan y el repositorio, detenerse y preguntar (AGENTS.md, sección 3).
- No modificar tests existentes, salvo los que la fase lista en "Tests existentes que cambian".
- Mantener en commits separados los cambios de estructura y los de texto.
- Rama `feat/i18n-otNN-<slug>` (o `chore/`, `docs/` según corresponda), commits convencionales en español, sin atribución de IA, merge commit a `main` con CI en verde.
- Al cerrar: lint y formato en ambos proyectos, suites completas, entrada en `docs/decisiones.md` si hubo una decisión, spec afectada actualizada, `graphify update .`, y actualización de la fila de la orden (10.4) y de las notas de traspaso (10.5).

### 10.4 Órdenes de trabajo

Se recomienda el orden numérico, que respeta todas las dependencias. Las fases 4, 5 y 6 pueden intercambiarse entre sí si alguna queda bloqueada. "Pasos" remite a los pasos numerados de la fase en la sección 5.

| OT | Fase y pasos | Entrega | Depende de | Tamaño | Estado |
|---|---|---|---|---|---|
| OT-00 | F0, pasos 1 y 2 | Suites corridas en el entorno de ejecución y comparadas con la línea base de 10.5 (410, 43 y 24) | Ninguna | S | Completada: 07/10/2026; 410, 43 y 24 en verde (ver 10.5) |
| OT-01 | F0, paso 3 | Caracterización de las respuestas de error de la API | OT-00 | M | Completada: 07/10/2026; F0 integrada, 508/43/24 y CI en verde (ver 10.5) |
| OT-02 | F0, pasos 4, 5 y 6 | Caracterización de correos, esquema OpenAPI capturado y supuestos de 2.6 comprobados | OT-00 | S | Completada: 07/10/2026; F0 integrada, 508/43/24 y CI en verde (ver 10.5) |
| OT-03 | F0, pasos 7 y 8 | `next build` en CI y locale fijo en Playwright | OT-00 | S | Completada: 07/10/2026; F0 integrada, 508/43/24 y CI en verde (ver 10.5) |
| OT-10 | F1, pasos 1, 2 y 5 | Decisiones D1 a D13 y respuestas de la sección 9 registradas en `docs/decisiones.md`; glosario | F0 | S | Completada: 08/10/2026; PR #47 integrado fuera de main; CI en verde |
| OT-11 | F1, paso 3 | Spec `error-contract` con cada mensaje del inventario asignado a un código | OT-10 | M | Completada: 08/10/2026; correspondencia completa de F0 y HTTP/429 definidos; integrada fuera de main con CI en verde |
| OT-12 | F1, paso 4 | `docs/i18n/claves.csv` con clave, namespace y estado por fila. Puede partirse por grupos de pantallas | OT-10 | L | Completada: 08/10/2026; 634 filas en los PRs #48, #49 y #50, integrados fuera de main; revisión editorial OT-13 pendiente |
| OT-13 | F1, paso 6 | Copia faltante redactada y specs `i18n-core` y `emails` | OT-11, OT-12 | S | Completada: 08/10/2026; copia y curaduría aprobadas; entregas #53/#54 hacia integración; suites 508/43/24 y build aprobados; integrada fuera de main con CI verde de ambas cabezas (ver 10.5) |
| OT-20 | F2, todos | Campo `idioma`, `idioma_efectivo`, preferencias, registro y semilla con cuentas en ambos idiomas | F1 | S | Completada: 08/10/2026; PRs #55/#56/#57 integrados con CI verde; 520 backend, merge final 51bcb2b (ver 10.5) |
| OT-30 | F3, pasos 1 y 3 | Catálogo, excepción base y sobre nuevo emitido junto al formato anterior | OT-11 | M | Completada: 08/10/2026; PRs #58/#59/#60/#61 integrados fuera de main con CI 3/3 verde; 543 backend; merge final 10fe49f (ver 10.5) |
| OT-31 | F3, paso 2 | Códigos en `usuarios` y `filmai` | OT-30 | M | Parcial: 08/10/2026; cinco unidades integradas en `develop` y verificadas con la suite local completa; faltan las respuestas directas de F3 (OT-33) y la publicación/CI (ver 10.5) |
| OT-32 | F3, pasos 2 y 4 | Códigos en `listas` y `catalogo`; casos irregulares normalizados | OT-30, primer bloque de OT-31 | M | Completada: 08/10/2026 en `develop`; 611 backend OK; falta publicar/CI (ver 10.5) |
| OT-33 | F3, pasos 5, 6 y 7 | Espera en el 429, códigos en respuestas exitosas, estados de cuenta en el inicio de sesión | OT-31 | S | Completada: 08/10/2026 en `develop`; 622 backend OK; falta publicar/CI (ver 10.5) |
| OT-34 | F3, pasos 8 y 9 | Contrato exportado, sobre en OpenAPI, validación del sobre en toda la suite y rechazo de códigos no registrados | OT-31, OT-32, OT-33 | S | Completada: 08/10/2026 en `develop`; 634 backend OK; cierra F3; falta publicar/CI (ver 10.5) |
| OT-40 | F4, paso 1 | Campo `clave` con migración de datos y su test | F1 | S | Completada: 08/10/2026; PR #62 con CI 3/3 verde sobre 6dee3b5; 546 backend; merge 65b7e7b solo a integración (ver 10.5) |
| OT-41 | F4, pasos 2, 3 y 4 | Código por `clave`, `clave` en la API, nombres reservados, `contracts/enums.json` | OT-40 | M | En validación: 08/10/2026; OT-41A y OT-41B integradas en `develop` (identidad por clave, `list_name_reserved`, `contracts/enums.json`); falta publicación/CI (ver 10.5) |
| OT-42 | F4, paso 5 | Restricciones y prueba sobre un volcado de desarrollo | OT-41 | S | Completada: 08/10/2026 en `develop`; 644 backend OK; cierra F4; falta publicar/CI (ver 10.5) |
| OT-50 | F5, pasos 1 y 7 | Servicio único y layout base, con las plantillas actuales sin cambios de texto | OT-20, OT-02 | M | En validación: 08/10/2026; servicio y layout integrados en `develop` y verificados con la suite local completa; falta publicación/CI y OT-51…53 (ver 10.5) |
| OT-51 | F5, pasos 2 y 3 | Vigencias por contexto y HTML de "contraseña actualizada" | OT-50 | S | Completada: 08/10/2026 en `develop` (206725e); falta revisión manual en cliente real y CI |
| OT-52 | F5, pasos 4 y 6 | Plantillas en inglés y elección del idioma del destinatario | OT-51 | M | Completada: 08/10/2026 en `develop` (81fa8ee); falta revisión manual en cliente real y CI |
| OT-53 | F5, paso 5 | Copia en español pasada a la de la tabla | OT-52 | S | Completada: 08/10/2026 en `develop` (a89ef6e); falta revisión manual en cliente real y CI |
| OT-60 | F6, pasos 1, 2 y 3 | Idioma como parámetro del cliente, idioma en vistas públicas, comprobaciones contra la API real | OT-20 | M | Completada: 08/10/2026 en `develop`; suite backend completa OK; verificada contra la API real; falta CI |
| OT-61 | F6, paso 4 | Fallback a inglés en detalle y listados | OT-60 | M | Completada: 08/10/2026 en `develop`; suite backend completa OK; verificada contra la API real; falta CI |
| OT-62 | F6, pasos 5 y 6 | `ProduccionTraduccion`, `generos_ids`, materialización y relleno | OT-60 | M | Completada: 08/10/2026 en `develop`; suite backend completa OK; verificada contra la API real; falta CI |
| OT-63 | F6, pasos 7, 8 y 9 | Serializadores por idioma, géneros por idioma, sincronización nocturna | OT-61, OT-62 | M | Completada: 08/10/2026 en `develop`; suite backend completa OK; verificada contra la API real; falta CI |
| OT-70 | F7, pasos 1 a 4 | next-intl configurado, sin cambio visible | F1 | M | Completada: 08/10/2026; PRs #63/#64/#65 integrados solo en integración con CI 3/3 verde; 546 backend, 73 unitarios y 30 e2e; merge final 600aaee (ver 10.5) |
| OT-71 | F7, paso 5 | `lib/format.ts` y reemplazo de los usos de `es-AR` | OT-70 | S | Pendiente |
| OT-72 | F7, pasos 6, 7 y 10 | `Accept-Language`, `ApiError` con códigos, `lib/errors.ts`, API simulada de e2e | OT-70, OT-34 | M | Pendiente |
| OT-73 | F7, pasos 8 y 9 | Validaciones por código y etiquetas desde `enums` | OT-72 | S | Pendiente |
| OT-74 | F7, pasos 11, 12 y 13 | Selector, sincronización entre cookie y cuenta, locale del botón de Google | OT-70, OT-20 | M | Pendiente |
| OT-75 | F7, paso 14 | Rutas en inglés en frontend, backend y tests, en un solo PR | OT-70 | M | Pendiente |
| OT-76 | F7, paso 15 | Tres pantallas piloto migradas | OT-73, OT-74, OT-75 | M | Pendiente |
| OT-77 | F7, paso 16 | Catálogos completos sembrados desde `claves.csv` | OT-70, OT-12, OT-13 | M | Pendiente |
| OT-80 | F8, pasos 1, 2, 3 y 6 | Paridad, reglas de lint, script de residuos | OT-77, OT-34, OT-41 | M | Pendiente |
| OT-81 | F8, pasos 4 y 5 | Selectores independientes del idioma en las pantallas piloto y recorrido e2e en ambos idiomas | OT-76, OT-52 | M | Pendiente |
| OT-82 | F8, paso 7, primera parte | Tests del backend afirmando por código, con ambas formas emitidas | OT-72 | M | Pendiente |
| OT-83 | F8, paso 7, segunda parte | Formato anterior de errores eliminado | OT-82 | S | Pendiente |
| OT-90 | F9, todos | Documentación alineada, guía de uso y lista de la sección 8 completa | Todas | M | Pendiente |

### 10.5 Notas de traspaso

Cada sesión agrega aquí, al cerrar, una entrada breve: fecha, orden, rama o PR, resultado de las suites, desvíos respecto del plan y dudas pendientes. Las respuestas del usuario a las preguntas de la planificación están en la sección 9.

- 07/10/2026, planificación: línea base medida con todo en verde. Backend 410 tests (141 segundos), Vitest 43, Playwright 24.
- 07/10/2026, planificación: la tabla de equivalencias se guardó en `docs/i18n/equivalencias.json` (634 entradas, 41 pantallas, JSON validado).
- 07/10/2026, planificación: el usuario respondió las 14 preguntas de la sección 9. Las decisiones quedaron incorporadas en las secciones 2.11, 3.2, 3.3, 3.5, 3.7, 3.8 y 3.9, y en las fases 1, 2 y 7.
- 07/10/2026, OT-00: rama `docs/i18n-ot00-linea-base`, creada desde `main` actualizado (`7985200`). Verificadas las citas de ejecución: `backend/requirements.txt:6-37`, `frontend/package.json:5-44` y `.github/workflows/ci.yml:110-167`; backend, frontend y CI siguen idénticos a `a7dabaf`.
  - Backend: `docker compose exec -T backend python manage.py test`, **410 tests en verde**, 145,261 segundos (referencia: 410, 141 segundos).
  - Frontend con Node 22.23.3: `npm run test:unit`, **43 tests en verde en 5 archivos**, 6,58 segundos; `npm run test:e2e`, **24 tests en verde**, 2,8 minutos. Los tres conteos coinciden con la línea base.
  - Calidad: `ruff format . && ruff check .` en el contenedor backend (85 archivos sin cambios); `npx eslint . --max-warnings=0`, `npx prettier --check .` y `npx tsc --noEmit` en frontend, todos en verde.
  - Incidencia de entorno: la comprobación inicial del puerto 3100 demoró el arranque de Playwright. Se levantó manualmente `npm run dev -- -p 3100` con `NEXT_PUBLIC_API_URL=http://127.0.0.1:3100` y `NEXT_DIST_DIR=.next-e2e`, como indica su configuración; el intento automático concurrente informó puerto ocupado, pero los 24 casos pasaron. Sin cambios de configuración ni de tests.
  - Alcance: solo F0, pasos 1 y 2, más este registro y la actualización de graphify. Sin decisiones de diseño ni cambios de comportamiento; no corresponde modificar `docs/decisiones.md` ni specs canónicas. F0 sigue pendiente de OT-01, OT-02 y OT-03. Sin dudas pendientes ni desvíos de alcance.

- 07/10/2026, OT-03: rama `chore/i18n-ot03-build-locale`; se agrega `npm run build` al job de frontend y `locale: "es-AR"` a Playwright. Las referencias de CI, `frontend/package.json` y `frontend/playwright.config.ts` se verificaron antes de editar.
  - Frontend con Node 22.23.3: build real de producción en verde; ESLint sin warnings, Prettier y TypeScript en verde; Vitest **43 tests en 5 archivos** (4,99 segundos), Playwright **24 tests** (1,2 minutos). Catálogo de avatares sincronizado y su test unitario en verde. Ningún test existente cambió.
  - Incidencias de entorno resueltas: Turbopack rechaza `node_modules` enlazado fuera del worktree; se copiaron las dependencias localmente, sin cambios versionados. Se arrancó manualmente el servidor e2e con las variables de su configuración debido a la demora inicial en detectar el puerto 3100; se detuvo al terminar.
  - Backend sin modificaciones: la última referencia es OT-00, **410 tests** en verde; su suite y lint completos se reejecutan al integrar F0. Esta nota no afirma una nueva ejecución del backend.
  - Decisión registrada en `docs/decisiones.md`; no se afecta una spec de dominio. `graphify update .` ejecutado: sin cambios de topología, manifiesto actualizado. Sin dudas pendientes ni desvíos de alcance. Los cambios permanecen fuera de `main`, conforme a la instrucción del usuario.

- 07/10/2026, OT-02: rama `feat/i18n-ot02-correos-openapi`. Nuevos tests autónomos en `filmai/tests_correos_contrato.py`, `filmai/tests_esquema.py` y `filmai/tests_estado_cuenta.py`, sin modificar tests existentes. Cuatro referencias de correo guardan asunto, texto y HTML; la contraseña actualizada caracteriza la ausencia de HTML. Solo se normalizan los segmentos variables de los enlaces.
  - Siete tests enfocados en verde en una base aislada `test_filmai_ot02`, con backend de correo en memoria: ningún correo externo. Las referencias se regeneran únicamente con `FILMAI_ACTUALIZAR_REFERENCIAS=1`. Grafo actualizado con `graphify update .`; falta el cierre integrado de las suites completas, coordinado por la rama de integración.
  - Capturado `contracts/openapi.yaml` mediante `spectacular`; comparación semántica del YAML para detectar divergencias. El generador existente informa 14 advertencias (11 únicas) y 100 errores de introspección (21 únicos), por vistas sin serializer declarado, autenticadores sin extensión y otros límites actuales. No se corrigen dentro de esta orden.
  - Comprobado: el serializer lanza mensajes de baja o pendiente antes de validar contraseña, para correo y username, con contraseña correcta e incorrecta; HTTP oculta ambos con el 403 genérico. La reseña, nota y nombre del autor siguen visibles después de ejecutar la baja real. No cambia ese comportamiento; F3 validará las credenciales antes de revelar el estado.
  - Citas comprobadas: `usuarios/serializers.py:55-60,304-333`, `usuarios/passwords.py:12-31`, `usuarios/cuenta.py:52-67`, `catalogo/reviews.py:90-101` y `filmai/exceptions.py:50-51`, sin desvíos. El plan nombraba un único `tests_contrato.py`; los tres módulos nuevos separan esta orden de OT-01 para permitir trabajo paralelo. Sin dudas de alcance pendientes.

- 07/10/2026, OT-01: rama `feat/i18n-ot01-caracterizacion-api`, 91 escenarios de API, serializers, validadores y manejadores reales, con `DEBUG=False`; JSON de estado y cuerpo regenerables solo con `REGENERAR_REFERENCIAS_API=1`. Citas de 2.4 verificadas en los archivos reales; sin cambios de comportamiento ni tests existentes. Prueba enfocada: 91 en verde; grafo actualizado; suites completas, CI y PR coordinados en la rama de integración. Las ramas defensivas y los textos que no salen por API se distinguen en `backend/filmai/tests_golden/README.md`. Autorización del usuario para OT-30: ajustar exclusivamente estas pruebas nuevas para comparar los campos heredados durante la emisión doble, con pruebas separadas del sobre nuevo. En OT-01 se conserva la comparación estricta del cuerpo completo actual. El usuario también autorizó actualizar únicamente las nuevas pruebas y referencias de F0 cuando el plan cambie deliberadamente el comportamiento; los tests anteriores al plan conservan sus excepciones originales. Excepción de tamaño `size:exception` aprobada por el usuario solo para el PR de OT-01. La ejecución combinada detectó que los escenarios de catálogo dejaban poblada la caché del servicio y afectaban un test anterior del singleton; se corrigió exclusivamente el aislamiento de los nuevos tests con limpieza al iniciar y mediante `addCleanup`. Verificación enfocada de la corrección: 92 tests en verde; nueva ejecución completa pendiente de coordinación.

- 07/10/2026, cierre integrado de F0 (OT-01, OT-02 y OT-03): PRs #46, #45 y #44 integrados con merge commit únicamente en `feat/i18n-multiidioma`, con los tres jobs de CI en verde. El PR de seguimiento #43 sigue en draft hacia main; no hay merge a main ni auto-merge.
  - Backend combinado: **508 tests en verde**, 157,767 segundos (410 anteriores + 91 de API + 7 de correos/esquema/estado). Ruff: 90 archivos sin cambios y lint aprobado. Frontend: **43 unitarios y 24 e2e en verde**, ESLint, Prettier, TypeScript y build real aprobados; CI ejecuta build y Playwright fija es-AR.
  - La primera suite completa detectó caché singleton de TMDB dejada por pruebas nuevas. Se corrigió su aislamiento con limpieza antes y después; 92 casos enfocados y la nueva suite completa pasan. No se modificó ningún test anterior al plan ni sus oráculos.
  - El usuario autorizó adaptar solo las nuevas pruebas/referencias de F0 en cambios deliberados del plan, y excepción de tamaño solo para OT-01. Confirmó 24 horas de confirmación y corrección posterior del doc 02. Sin bloqueos pendientes para comenzar F1.

- 08/10/2026, OT-10: rama `docs/i18n-ot10-decisiones-glosario`. Verificadas 634 entradas y 41 pantallas sin modificar `equivalencias.json`; decisiones del plan y las 14 respuestas de la sección 9 registradas. `es-MX` tiene entrada propia; la decisión de TMDB solo inglés del 30/09 queda reemplazada como alcance, conservando el comportamiento vigente hasta F6. Glosario por concepto y registro de la cuestión de baja conservada para otro alcance.
  - Sin código, tests ni datos modificados. Baseline vigente de F0: backend 508, Vitest 43, Playwright 24 y build en verde; no se agregan pruebas para una entrega documental. Las specs nuevas de contrato, núcleo y correos corresponden a OT-11/OT-13.
  - Registradas las instrucciones posteriores: rama de integración, PRs por orden y prohibición de merge a main; excepciones acotadas para nuevas pruebas de F0 y tamaño de OT-01. El doc 02 se corregirá al cierre para reflejar 24 horas de confirmación, según respuesta del usuario. Sin decisiones pendientes de OT-10; copia nueva y curaduría se revisan en OT-13.

- 08/10/2026, OT-12, bloque A: rama `docs/i18n-ot12-claves-descubrimiento`.
  Curadas las filas 1–270, con originales y pantallas preservados, destinos
  semánticos y mensajes completos ICU. La entrega se divide por grupos en tres
  PRs de documentación: descubrimiento, cuenta/listas y administración/correos.
  No se crean catálogos ni se modifican tests; las dudas y la aprobación editorial
  se resuelven en OT-13. La tabla original sigue intacta. Backend/frontend son
  idénticos a OT-10: referencia 508/43/24 y build, con CI verde en PR #47.
  Se verifica trazabilidad del bloque y se actualiza graphify antes del commit.

- 08/10/2026, OT-12, bloque B: rama `docs/i18n-ot12-claves-cuenta-listas`.
  Se agregan las filas 271–499 de búsqueda, reseñas, autenticación, listas,
  perfil y preferencias; total acumulado 499. Originales y pantallas exactos;
  copia de baja preservada, sin catálogos ni modificaciones de código/tests.
  La guía amplía el uso de ICU y las reglas de curaduría. Pendientes bloque C y
  revisión editorial OT-13. Verificación y suites completas mediante CI por PR;
  referencia de aplicación sin cambios: 508 backend, 43 unitarios y 24 e2e.

- 08/10/2026, OT-12, bloque C: rama `docs/i18n-ot12-claves-legal-correos`.
  Se agregan 135 filas de exclusiones del chatbot, errores, administración,
  términos, footer y correos. CSV completo: 634 IDs y 41 pantallas exactos;
  406 ok, 40 fragmentos recompuestos, 61 muestras, 100 diseño, 21 chatbot y
  6 incoherentes pendientes de OT-13. Las 446 filas utilizables apuntan a
  423 claves sin colisiones. Parser ICU: sintaxis y paridad de argumentos/tags
  verificadas; 28 filas con plurales y 3 con tags. Contacto confirmado por el
  usuario: contacto@filmai.com en textos curados, originales conservados.
  Sin código, tests ni dependencias modificados; referencia de suites completas
  508/43/24 y build verde. CI por PR y graphify antes del commit; no merge a main.

- 08/10/2026, OT-11: rama `docs/i18n-ot11-contrato-errores`, apilada sobre el bloque C de OT-12. Spec `error-contract` y correspondencia en `docs/i18n/errores.csv` (88 filas). Auditoría documental: 91/91 referencias de API de F0 citadas (las cuatro de correos pertenecen a OT-13/F5) y todas sus cadenas de mensaje presentes en el CSV (recomprobado al cerrar). Se documentan normalizaciones de librerías instaladas, respuestas exitosas, ramas defensivas y textos fuera de API. Sin cambios de producción ni tests. El usuario aprobó propagar la espera real de TMDB cuando esté informada y omitir parámetro/encabezado si se desconoce; también confirmó códigos por significado y estados permitidos por contexto, conservando el HTTP actual durante multiidioma. Sin dudas pendientes de contrato; copia nueva reservada para aprobación en OT-13.

- 08/10/2026, corte de la sesión (cierre hecho con Claude Code sobre el trabajo que Codex dejó sin commitear). Estado para retomar:
  - Integrado en `feat/i18n-multiidioma`: F0 completa, OT-10, OT-11 y OT-12. Nada llegó a `main`; el PR de seguimiento #43 sigue en draft.
  - OT-13 es lo único abierto de F1. Su borrador está en la rama `docs/i18n-ot13-copia-specs` (PR en draft hacia la rama de integración): `docs/i18n/copia-propuesta.csv` con 91 filas en `pendiente_aprobacion`, `docs/i18n/revision-ot13.md` con las seis dudas de curaduría (IDs 214, 215, 320, 355, 448 y 535) y su checklist, y las specs `i18n-core` y `emails` marcadas como borrador. Nada de eso está aprobado ni habilita la siembra de catálogos.
  - Para retomar: el usuario aprueba o corrige la copia y resuelve las seis dudas; después se cierra OT-13 siguiendo el checklist de `revision-ot13.md` y recién entonces empieza F2 (OT-20). OT-30 y OT-40 dependen solo de OT-11 y de F1 respectivamente, pero no se adelantaron.
  - No se tocó código de producción ni tests desde F0: la referencia de suites sigue siendo 508 backend, 43 unitarios y 24 e2e, verificada por CI en cada PR.
  - Los PRs con base `docs/**` no disparan CI (el workflow filtra por rama destino `main` o `feat/**`); hay que reapuntarlos a la rama de integración y cerrarlos y reabrirlos para que corra.
  - Quedan worktrees de Codex en `/tmp/filmai-i18n-*`. Su contenido ya está commiteado en las ramas correspondientes; se pueden quitar con `git worktree remove`.

- 08/10/2026, continuación de OT-13 en `docs/i18n-ot13-copia-specs`:
  el usuario aprobó los 91 textos nuevos ES/EN y las seis resoluciones de
  curaduría. Se corrigieron mensajes de credenciales compartidos con Google,
  límites de solicitudes compartidos con TMDB y reenvío condicional de correo.
  214/215 reutilizan confirmaciones completas, 355 la etiqueta de contraseña,
  448 se excluye como metadato de locale, 535 es encabezado y 320 es nota exacta
  «Calificación {rating}/10». Los originales y la copia de baja se conservan.
  - Curaduría: 634 IDs y 41 pantallas exactos; 451 filas utilizables, 425 claves
    sin colisiones y ninguna fila incoherente. ICU/paridad de argumentos y tags
    aprobados en 451 filas y en los 91 mensajes nuevos; 28 plurales y 3 tags.
    Las specs de núcleo y correos reflejan la aprobación y el saludo de respaldo
    localizado. Ningún archivo de producción o test fue modificado.
  - Verificación local: Ruff, ESLint, Prettier y TypeScript aprobados;
    Vitest **43 tests en 5 archivos**, 6,66 segundos. La nueva suite backend
    quedó bloqueada por acceso denegado al socket de Docker. Playwright no pudo
    abrir el servidor (listen EPERM); build de Turbopack falla por su operación
    interna de abrir un puerto, también prohibida. No son suites completas en
    verde; la última referencia íntegra continúa siendo CI anterior 508/43/24.
  - Publicación pendiente: GitHub no es accesible y `.git` es de solo lectura
    para las operaciones de cierre; `git stash` falla al crear index.lock.
    Los cambios aprobados permanecen en el checkout, con respaldo adicional
    en `/tmp/filmai-ot13-aprobada-snapshot`. No hubo nuevo commit, push ni merge.
    Graphify se actualiza antes de detener la sesión.
  - Próximo paso: cerrar OT-13 con permisos de entorno suficientes, dividir la
    entrega en dos unidades (specs; copia/curaduría/registro) según chained-pr,
    publicar y comprobar CI hacia `feat/i18n-multiidioma`. El PR #52 remoto sigue
    conteniendo el borrador anterior; no representa todavía la copia aprobada.
    Después puede empezar OT-20. Main sigue fuera de alcance.

- 08/10/2026, nueva comprobación de cierre de OT-13:
  - Se creó `docs/i18n-ot13-specs-aprobadas` desde el checkout de OT-13,
    conservando los cambios aprobados. Todavía no contiene un commit nuevo.
  - GitHub permite consultar el PR #52: sigue abierto en draft hacia
    `feat/i18n-multiidioma`, con CI verde del borrador anterior. Ese CI no
    verifica los cambios locales aprobados.
  - Las escrituras necesarias siguen bloqueadas: `git add` no puede crear
    `.git/index.lock` y `git fetch` no puede escribir `.git/FETCH_HEAD`.
    Docker permite listar servicios, pero ejecutar la suite backend falla por
    acceso denegado al socket. No se hizo push ni merge.
  - ESLint, Prettier y TypeScript pasan; Vitest: 43 tests en 5 archivos,
    4,91 segundos. Playwright no pudo iniciar su servidor; build falla al
    abrir un puerto interno de Turbopack con EPERM. El cierre completo sigue
    pendiente. Código de producción y tests permanecen sin cambios.
  - Siguiente orden funcional: OT-20, después de cerrar F1. Incluye el campo
    nullable de idioma sin relleno, resolución cuenta/Accept-Language/default,
    preferencias y registro normal/Google, y cuentas de semilla ES/EN.
    No se inició su implementación ni se avanzó hacia las interfaces.

- 08/10/2026, retoma con permisos efectivos: Git, Docker y puertos funcionan.
  Se respaldó el checkout aprobado y se dividió OT-13 desde la integración:
  PR #53 contiene specs y decisión; la segunda entrega contiene copia,
  curaduría y registro. PR #52 será sustituido, sin perder su historial.
  ESLint, Prettier, TypeScript, 43 unitarios y build pasan. Se repite backend
  tras copiar el contrato OpenAPI al contenedor (ausente del montaje local);
  Playwright corre con `CI=1`. Se mantiene la prohibición de merge a main.

- 08/10/2026, verificación final OT-13: backend 508 tests en 162,455 s;
  Vitest 43 en 5,35 s; Playwright 24 en 41,9 s; Ruff, ESLint, Prettier,
  TypeScript y build aprobados. ICU válido en 91 mensajes y 451 filas;
  634 originales y baja intactos, 425 claves sin colisiones. La primera
  corrida backend falló por el contrato OpenAPI ausente del montaje; se copió
  `/contracts` al contenedor y pasó la repetición completa, sin modificar tests.
  PR #53 integrado con merge commit en `feat/i18n-multiidioma`, con CI verde.
  PR #54 reapuntado a integración; solo se integra cuando pase el CI de su
  cabeza final. PR #52 cerrado y sustituido por #53/#54. Ningún merge a main.

- 08/10/2026, cierre de F1: PR #54 integrado con CI verde de su cabeza
  `7c34285`, merge `8d97762`, únicamente en `feat/i18n-multiidioma`.
  OT-13 está cerrada. Empieza OT-20 desde esa integración, en tres unidades:
  núcleo; preferencias/registros; semilla. La primera tiene cuatro pruebas
  enfocadas verdes (1,013 s), incluida migración real sin relleno. No se
  modifica la base de desarrollo ni se ejecuta la semilla automáticamente.
  - Autorización nueva OT-31/32: adaptar solo igualdades exactas pre-plan de
    confirmación/reset/documentación/TMDB para verificar campos heredados,
    conservando HTTP, con sobre nuevo probado por separado. Afecta
    `filmai/tests.py` (TMDB y documentación) y `usuarios/tests.py`
    (confirmación y reset); no es permiso general para cambiar otras pruebas.
  - OT-42: reparar recursos faltantes SOLO en la copia temporal del volcado,
    antes del baseline; nunca en la base de desarrollo original.
  - OT-70: título transitorio «Mis reseñas» / “My reviews” aprobado.

- 08/10/2026, OT-20 segunda unidad: lectura de idioma en preferencias/usuario/
  perfil y escritura soportada en preferencias; registro tradicional y Google
  guardan el idioma activo y cuentas Google existentes lo conservan. Once tests
  enfocados pasan en 4,071 s; se regenera OpenAPI con la autorización de F0.
  Se distingue lectura nullable de escritura restringida en el esquema.
  El usuario también aprobó las 53 traducciones EN transitorias propuestas
  para OT-70 en `/tmp/filmai-ot70-copia-faltante.csv`; el agente de esa orden
  las versionará con trazabilidad propia, conservando ES hasta OT-76.

- 08/10/2026, OT-20 tercera unidad: seed completo asigna `es` a usuario001/
  usuario003 y `en` a usuario002; README documentado. Dos tests nuevos pasan
  en 3,663 s: recreación repetida y modo de reseñas conservando idiomas. No se
  ejecuta seed ni migración en la base de desarrollo. Regresión completa
  backend en curso. El árbol frontend coincide exactamente con el validado
  en OT-13 (43 unitarios, 24 e2e y build); CI comprobará cada nueva cabeza.

- 08/10/2026, verificación OT-20: PR #55 y #56 integrados con CI completo
  verde, solo en `feat/i18n-multiidioma` (merges `54d31b1` y `fee46bb`).
  La suite local con semilla corrió 520 tests en 184,491 s: cinco fallos de
  autenticación 401 dentro del test preexistente de preferencias. No se toca
  su comportamiento ni se da por cerrado OT-20; se instrumenta JWT en un
  runner temporal para determinar la causa. Los dos tests de semilla pasan.
  El usuario aprobó para OT-41 `list_name_reserved`, HTTP 409, sin parámetros:
  «Ese nombre está reservado para una lista predeterminada.» / “This name is
  reserved for a default list.”. Esa copia nueva se registra al implementarla.

- 08/10/2026, OT-20 verificada: repetición normal completa **520 tests**
  en 190,527 s, resultado OK. Ruff y formato/frontend limpios. Se conserva el
  fallo intermitente anterior sin atribuir una causa ni cambiar tests previos.
  Frontend exacto `88f94c0`: evidencia vigente de OT-13 43 unitarios/24 e2e/build;
  no se presenta como corrida nueva. Semilla PR #57 hacia integración; solo
  se integra con CI verde de su cabeza final. Núcleo/API #55/#56 ya integrados.

- 08/10/2026, cierre OT-20 e inicio de publicación OT-30: los PRs #55,
  #56 y #57 quedaron integrados con CI verde únicamente en
  `feat/i18n-multiidioma`, merge final `51bcb2b`. Se conserva la evidencia
  local de 520 tests y la incidencia intermitente documentada, sin atribuirle
  una causa no demostrada. OT-30 parte de esa base en cuatro unidades:
  catálogo/excepción, hojas/metadatos, composición del sobre y manejador/F0.
  Se conservan decisiones de ambas órdenes y se regenera el grafo por unidad.
  Las autorizaciones vigentes permiten adaptar los tests nuevos de F0 OT-01
  y OT-02 para comparar campos heredados; permanecen la matriz completa de
  credenciales/estados y los goldens originales. Los tests nuevos comprueban
  el sobre por separado y la regresión de PermissionDenied de Django en ambos
  modos DEBUG. La última cabeza requiere su suite completa nueva y CI verde;
  no se integra ningún PR de esta cadena hasta coordinar su cabeza exacta.
  El tracker #43 continúa draft y main permanece fuera de los merges.

- 08/10/2026, primera verificación OT-30 sobre OT-20 final: **543 tests**
  en 189,235 s; dos subcasos del nuevo test de preferencias de idioma devolvieron
  401 en vez de 400. La clase aislada pasó sus tres tests en 1,683 s. Se conserva
  el resultado fallido sin atribuirle causa ni cambiar el código/tests de OT-20;
  la repetición completa está en curso. Las cuatro unidades pasan sus pruebas
  propias (4, 9 y 16 acumuladas; 7 del manejador) y el formato/lint. Los PRs
  #58 y #59 tienen los tres jobs CI verdes para sus cabezas exactas; #60 y la
  última entrega requieren completar su verificación antes de integrar.

- 08/10/2026, cierre de OT-30: las cuatro unidades de los PRs #58–#61
  quedaron integradas con merge commit únicamente en `feat/i18n-multiidioma`.
  Cada cabeza exacta pasó los tres jobs CI; el merge final es `10fe49f`.
  La suite backend base contiene 543 tests. Se conserva la primera corrida
  fallida y su repetición en el registro anterior; main permanece intacta.

- 08/10/2026, preparación de OT-40 sobre OT-30 cerrada: campo `Lista.clave`
  nullable y migración reversible `0005`; tres pruebas recorren el esquema
  real, conservan filas y el idioma de las cuentas y prueban rollback completo
  ante una predeterminada desconocida. Se conserva un respaldo de la cabeza
  anterior antes del rebase. No se aplica la migración a la base de desarrollo.
  El cierre requiere las suites de esta base y el CI de la cabeza publicada;
  todavía no se implementan consumidores de OT-41 ni restricciones de OT-42.

  Verificación final local: 546 backend en 196,439 s; tres tests de migración
  en 3,769 s; Ruff, Prettier y consistencia de migraciones aprobados. Frontend
  coincide con el árbol validado en OT-13 (43 unitarios, 24 e2e y build),
  evidencia reutilizada y no una ejecución nueva. Se requiere CI sobre la
  cabeza publicada antes de integrar OT-40; main permanece sin merges.

- 08/10/2026, cierre de OT-40: PR #62 integrado con merge commit
  `65b7e7b3d9f821e06e104db6164fc7b414dae96c` únicamente en
  `feat/i18n-multiidioma`; los tres jobs CI pasaron sobre la cabeza exacta
  `6dee3b55bfe714769bd427c1699c7cc96b99b5a4`. Backend: 546 tests.

- 08/10/2026, OT-70 preparado sobre la cabeza final de OT-40 mediante un
  único rebase, con respaldos de las tres unidades y grafo actualizado en
  cada una. Núcleo next-intl sin prefijos, 77 textos transitorios aprobados,
  cuatro metadatos localizados y proveedor de render español. Las páginas
  mantienen sus textos actuales y los tests heredados sus selectores.
  - Nueva verificación de esta base: backend **546 tests en 199,264 s** en
    contenedor aislado con `TEST.NAME=test_filmai_ot70`; unitarios **73 en
    10,93 s**, build, TypeScript, ESLint, Prettier y Ruff aprobados.
  - Los **30 e2e en 41,0 s** verificados previamente en `28b7862` siguen
    siendo evidencia vigente, no una ejecución nueva: el árbol frontend
    `267f94944eecbb1347b5ff60bce1b2da3241073b` coincide exactamente tras el
    rebase. Ahora el puerto 3100 pertenece a otra aplicación y no se detuvo;
    el intento aislado no pudo iniciar SWC sin su caché/red. El CI de las
    cabezas publicadas debe repetir la suite completa antes de integrar.
  - La lectura directa de `.env` por Docker no interpreta comentarios
    inline: el primer intento backend se detuvo en configuración sin ejecutar
    tests. Docker Compose interpreta ese archivo y la repetición completa
    pasó, sin cambiar `.env`, producción ni tests. No se aplicaron migraciones
    a la base de desarrollo. Publicación y CI de tres PRs quedan pendientes;
    main permanece fuera de alcance.

- 08/10/2026, cierre OT-20: #57 integrado con CI verde de su cabeza final
  `c4cad5b` mediante merge `51bcb2b`, únicamente en `feat/i18n-multiidioma`.
- 08/10/2026, OT-60 primera unidad: cliente fijo EN/ES, fábrica independiente
  y separación de caché verificados con 29 tests (7,159 s). El usuario aprobó
  añadir solo `language: en-US` a los cuatro fixtures previos de caché; se
  mantienen sus comprobaciones de hit, almacenamiento y TTL. Las vistas se
  entregan por separado. OT-60 todavía no está cerrada.

- 08/10/2026, OT-60 segunda unidad: seis vistas públicas seleccionan idioma
  por encabezado/default sin cambiar autenticación. Tres tests nuevos y 29
  enfocados verdes (21,276 s). Evidencia real en
  `docs/i18n/tmdb-verificacion-ot60.md`; variantes, muestra inglesa, géneros
  TV, falta de traducción e imágenes comprobados. Pendiente integrar ambas
  unidades con CI verde. Suite completa local: 528 tests en 189,141 s, OK;
  Ruff y Prettier limpios. Frontend exacto `88f94c0` conserva la evidencia
  vigente 43/24/build de OT-13; no se presenta como nueva ejecución.

- 08/10/2026, cierre de OT-70: PRs #63/#64/#65 integrados únicamente en
  `feat/i18n-multiidioma` con CI 3/3 verde de cada cabeza exacta. Merge final
  `600aaee`; CI final de `6614fb8`: 546 backend (167,496 s), 73 unitarios
  y 30 e2e (1,1 min), ejecuciones nuevas. Main permanece sin merges.

- 08/10/2026, OT-60 tras rebase sobre OT-70: 554 backend en 269,277 s,
  Ruff (108 archivos) y Prettier aprobados. Frontend conserva el árbol
  `267f94944eecbb1347b5ff60bce1b2da3241073b`, con evidencia nueva de CI
  OT-70: 73 unitarios, 30 e2e y build; no se presenta como otra ejecución
  local. Se preservó el respaldo anterior antes del rebase y se regeneró
  el grafo en ambas unidades. Pendiente CI e integración de OT-60.
- 08/10/2026, cierre OT-30: #58/#59/#60/#61 integrados exclusivamente a
  `feat/i18n-multiidioma`, con CI verde en las cuatro cabezas verificadas;
  merges bb4ce4e, 58373f1, 0e2bd31 y 10fe49f. La repetición completa pasó
  **543 tests** en 191,397 s; se conserva también el primer resultado fallido,
  sin atribuirle causa. Formato/lint y Prettier aprobados.
- 08/10/2026, primer bloque OT-31: frontera compartida final de DRF, con
  límites/choices/configuración de contraseña y rutas anidadas; **19 tests**
  enfocados en verde. Ningún serializer productivo la adopta todavía.
  Segunda unidad: perfil y preferencias adoptan la frontera; cinco tests HTTP
  del sobre y 29 regresiones enfocadas pasan (34 en total). Mensajes y HTTP
  heredados se conservan, incluidos errores múltiples del RegexField.
  Tercera unidad: solicitudes, cambios y restablecimientos de contraseña
  adoptan la frontera; seis pruebas HTTP nuevas y **53 tests** enfocados
  pasan. No se modifica envío ni persistencia. Se conserva también el primer
  fallo 401 de subcasos pre-plan; la repetición pasó sin cambiar esos tests.
  Cuarta unidad: códigos de registro y frontera en su segunda validación
  durante save; cinco pruebas nuevas y **15 tests** enfocados pasan.
  Proveedores y estados de cuenta quedan en OT-32/OT-33 respectivamente.
  Quinta unidad: Google y validadores restantes; **108 tests** enfocados
  pasan, incluidos F0 y regresiones Google. Token requerido conserva legacy
  y explicita id_token en el sobre; credenciales de proveedor quedan para OT-32.
  OT-32 depende técnicamente de este bloque y lo reutiliza; se entrega después
  de OT-31. Publicación coordinada tras OT-40 → OT-70 → OT-60; sin merges a main.

- 08/10/2026, pausa de entregas OT-31 por instrucción del usuario: trabajo
  local en `/tmp/filmai-i18n-ot31-retoma`, rama `feat/i18n-ot31-frontera`,
  desde integración 10fe49f. Unidades anteriores: e194fee (351 líneas authored),
  54b6d94 (205), 7adee17 (261), 76b7911 (244); la última unidad Google cierra
  sobre esas cuatro. Cada commit incluye código/tests, decisión/spec y grafo.
  No hay push, PR ni merge de OT-31; main permanece fuera del trabajo.
  Pendientes para completar OT-31: sobre en documentación JSON, handlers
  Django 404/500 y errores directos de enlaces de confirmación/restablecimiento;
  aplicar únicamente las igualdades pre-plan autorizadas (confirmación/reset/
  documentación), preservando HTTP y campos legacy; tests nuevos del sobre
  separados. Después: suite completa backend, verificaciones restantes y base
  actualizada con la cola coordinada. OT-31 no se declara completada.
  OT-32 no tiene implementación: worktree limpio
  `/tmp/filmai-i18n-ot32-retoma`, rama `feat/i18n-ot32-normalizacion`, base
  10fe49f. Reutilizar la frontera compartida de OT-31; conservar el manejador
  TMDB especializado y su test directo legacy, normalizando solo el global.
  Logs OT-31 en `/tmp/filmai-ot31-{perfil,contrasena,registro,google}-test.log`;
  primer resultado contraseña conservado en
  `/tmp/filmai-ot31-contrasena-primer-intento.log`; Prettier aprobado en
  `/tmp/filmai-ot31-prettier.log`. Los grafos tienen logs por unidad en `/tmp`.
- 08/10/2026, OT-50 unidad 1: servicio único y plantillas ES trasladadas sin
  cambiar textos; las cuatro referencias F0 coinciden sin regeneración. Tres
  tests nuevos y 34 enfocados verdes (25,339 s). El usuario autorizó solo
  cambiar el destino del mock de fallo de notificación a
  `filmai.correos.servicio.send_mail`, preservando HTTP y contraseña. Contenedor
  de pruebas con entrypoint explícito y DB `test_filmai_ot50`, sin aplicar
  migraciones a desarrollo. Layout y publicación pendientes.

- 08/10/2026, OT-50 unidad 2: registro hereda el layout compartible sin
  cambios en sus referencias F0. Siete tests verdes (1,964 s). Recuperación
  y reenvío se incorporan al layout en las siguientes unidades; sin cambiar
  copia ni idioma. La división previa de ambas confirmaciones medía 411 líneas
  escritas: se conserva en backup y se separa por flujo, sin recortar código.

- 08/10/2026, OT-50 unidad 3: reenvío usa el layout común con su introducción
  anterior. Siete tests de correos verificaron este resultado junto al registro
  (1,964 s); unidad intermedia de registro verificada de nuevo (1,972 s).
  Se mantienen las cuatro referencias originales sin regenerarlas.

- 08/10/2026, OT-50 unidad 4: recuperación hereda la base compartida y
  conserva sus bloques y color previos. 34 tests verdes (25,469 s), incluidas
  las cuatro referencias F0 intactas y la caída de correo posterior al commit.
  Tres correos comparten HTML; notificación conserva solo texto hasta OT-51.
  Suite completa de las cuatro unidades: 523 tests verdes (189,454 s); Ruff y
  Prettier limpios. Frontend exacto `88f94c0` conserva 43/24/build de OT-13,
  sin presentarlos como nueva ejecución. Publicación pendiente después OT-60.
- 08/10/2026, cierre de OT-40: PR #62 integrado en `feat/i18n-multiidioma`
  mediante merge `65b7e7b`, cabeza exacta `6dee3b5` con los tres jobs CI verdes.
  La suite local normal pasó 546 tests en 196,439 s; main permanece intacta.

- 08/10/2026, OT-41A: consumidores y API por clave, con siete tests nuevos
  aprobados junto a doce regresiones de contraseña (19 en 16,229 s). Provisión y semilla conservan los nombres; auditoría
  cuenta por clave. La segunda entrega agrega nombres reservados, el código
  `list_name_reserved` HTTP 409 sin parámetros y su copia bilingüe aprobada
  como fila nueva, sin alterar las 91 aprobadas de OT-13. No se ejecutan
  semilla ni reparación sobre desarrollo; OT-42 repara solo copia temporal.
  Primera suite: 552 en 198,548 s, un 401 inesperado en una regresión previa
  de rollback de contraseña. La clase y los siete nuevos pasaron juntos (19);
  repetición normal completa: 553 aprobados en 201,893 s. Ruff, Prettier y
  consistencia de migraciones aprobados. Publicación espera la cola OT-70/60
  y una verificación de la base final, sin declarar integrada esta entrega.

- 08/10/2026, OT-41B local: reserva ES/EN al crear y renombrar, código
  `list_name_reserved` 409 sin parámetros y fila editorial nueva aprobada;
  las 91 de OT-13 y los originales de errores permanecen intactos.
  `contracts/enums.json` y su exportador publican identidades y reservas;
  seis nuevos más la regresión nueva F0 duplicada pasan (7 en 2,019 s).
  El F0 usa ahora una personalizada duplicada, preservando su golden; el
  caso reservado se comprueba separado. Primera suite normal: 559 en
  200,128 s, un 401 en la regresión anterior de baja; su clase pasó aislada
  (6 en 3,087 s). Repetición y CI pendientes, sin alterar sus oráculos.

- 08/10/2026, **cierre parcial — rama única `develop`**. Se integraron en una
  sola rama las tres entregas que estaban fuera de la línea principal:
  OT-31 (`ec509d2`), OT-50 (`b14785c`) y OT-41A (`ed85794`), más el trabajo de
  OT-41B que estaba **sin commitear** en el worktree `/tmp/filmai-i18n-ot41b-retoma`
  (rescatado y commiteado como `7eb7584`). Únicos conflictos: `docs/decisiones.md`,
  `docs/plan-multiidioma.md`, `graphify-out/` (regenerable) y los imports de
  `backend/usuarios/serializers.py` (OT-31 vs OT-50; se conservaron ambos
  lados y se quitó `render_to_string`, que ya no se usaba).
  `contracts/openapi.yaml` regenerado con `FILMAI_ACTUALIZAR_REFERENCIAS=1`:
  el docstring de `FronteraErroresMixin` aporta una `description` a los
  esquemas `CambiarContrasena` y `Preferencias` (valorar si conviene ocultarlo
  en OT-34/OT-72). Verificación final: **598 tests backend OK**, **73/73
  Vitest**, `ruff format/check` limpios (124 archivos), Prettier de frontend
  limpio, `makemigrations --check` sin cambios, y **login real contra la base
  de desarrollo** (200 + cookies `access`/`refresh`; password inválida → 400
  con el contrato vigente). Entorno: imagen de frontend reconstruida con
  `next-intl@4.14.9` y contenedor **recreado** (el volumen anónimo de
  `node_modules` solo se siembra al crear el contenedor); migraciones
  `usuarios.0007_usuario_idioma` y `listas.0005_lista_clave` aplicadas en
  desarrollo. Limpieza: 49→2 ramas locales, 36→2 remotas, 16 worktrees de
  `/tmp` eliminados, stash de OT-13 descartado y PRs #42/#43/#66/#67 cerrados
  con explicación. Contexto y SHAs de recuperación (archivo retirado, ver `git show 05a53a2:`): `docs/cierre-parcial-2026-10-08.md`.
  Corrida previa de 598 con un `401 != 200` intermitente (misma incidencia ya
  documentada en OT-41A/OT-41B); su repetición salió en verde sin tocar tests.

- 08/10/2026, OT-32 en `develop` (sin merge a main): códigos en `listas` y `catalogo`, parámetros de catálogo normalizados con cuerpo irregular intacto, TMDB con sobre en el manejador global (429 de TMDB como `throttled` sin espera). Dos tests del manejador global ajustados (autorizado). 611 backend OK, Ruff limpio. Siguiente: OT-33.

- 08/10/2026, OT-33 en `develop` (sin merge a main): `retry_after_seconds` en el 429, `code` en respuestas exitosas (decorador `con_codigo_exito` para vistas de dj-rest-auth, OpenAPI intacto) y estados de cuenta en el login solo tras validar contraseña/token. Desvío deliberado: baja/pendiente con contraseña incorrecta pasa de 403 a 400 `invalid_credentials`; test de OT-02 ajustado. 622 backend OK. Siguiente: OT-34.

- 08/10/2026, OT-34 en `develop` (sin merge a main): `exportar_contrato` + `contracts/error-codes.json`, ejecutor de pruebas que valida el sobre en toda respuesta 4xx/5xx de la suite (corrigió enlaces, simplejwt, documentación y handlers 404/500), modo estricto para códigos no registrados, `ErrorEnvelope` en OpenAPI y campo `code` de Google eliminado por colisión. `filmai` pasa a `INSTALLED_APPS` solo por el comando. 634 backend OK. F3 cerrada. Siguiente: OT-42.

- 08/10/2026, OT-42 en `develop` (sin merge a main): migración `listas.0006` (verificación previa + unicidad por usuario/clave + coherencia tipo/clave), probada con un volcado de desarrollo en base temporal (reparación de `admin` solo en la copia; conteos idénticos en avance, retroceso y reavance). El entrypoint del backend migra la base de desarrollo en cada arranque: `0006` ya está aplicada allí. Un test de OT-41A ajustado. 644 backend OK. F4 cerrada. Siguiente: OT-51 (F5).

- 08/10/2026, OT-51/52/53 en `develop` (sin merge a main): vigencias desde configuración, HTML de contraseña actualizada, plantillas `en`, idioma del destinatario y copia final en español (voseo) con encabezado, motivo y pie. Saludo sin nombre («Hola usuario,» / “Hi there,”) aprobado por el usuario el 08/10/2026. Referencias de correo regeneradas (4 `es`, 4 `.en`). F5 cerrada salvo la revisión manual en un cliente real. Siguiente: F6 (OT-60 a OT-63).

- 08/10/2026, OT-60 a OT-63 en `develop` (sin merge a main): respaldo en inglés campo por campo con marca `campos_en_ingles`, `ProduccionTraduccion` + `generos_ids` (migración `catalogo.0006`), comando `rellenar_traducciones`, serializers por idioma, `GET /api/catalogo/genres/` y pasada de traducciones en la sync nocturna. Verificado contra la API real. **Backend del plan terminado (F2 a F6).** Estado y pasos que faltan: `docs/siguientes-pasos-multiidioma.md`. Siguiente: F7 (OT-71).

### 10.6 Instrucción para iniciar una sesión

```text
Contexto: repositorio FilmAI. Leer primero AGENTS.md y después docs/plan-multiidioma.md:
secciones 1 a 4, la fase de la sección 5 que corresponde a la orden y la sección 10 completa.

Tarea: ejecutar únicamente la orden de trabajo OT-NN de la sección 10.4.

Reglas: las de la sección 10.3. En particular:
- No avanzar a otra orden ni ampliar el alcance.
- Verificar que las citas de archivo y línea del plan siguen vigentes antes de editar.
- Ante una ambigüedad o una contradicción entre el plan y el repositorio, detenerse y preguntar.
- No modificar tests existentes salvo los que la fase lista en "Tests existentes que cambian".
- Al terminar: lint, formato y suites completas de ambos proyectos; decisión en
  docs/decisiones.md si corresponde; spec afectada; graphify update .; fila de la orden
  y notas de traspaso actualizadas en la sección 10.

Entrega: resumen de lo hecho, resultado de las suites y lista de dudas o desvíos.
```

---

## Verificación del propio plan

- Comprobar que cada cita de archivo y línea sigue vigente al iniciar cada fase; el repositorio puede haber avanzado desde `a7dabaf`.
- Al cerrar cada fase: suites completas, lint y formato en ambos proyectos, entrada en `docs/decisiones.md`, `graphify update .`.
- Al cerrar F9: recorrer la lista de la sección 8 punto por punto.
