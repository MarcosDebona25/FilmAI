# Usar multiidioma en FilmAI

La aplicación admite `en` y `es` sin prefijos de idioma en las rutas. Las pantallas piloto son Preferencias (`/settings`), confirmación (`/confirm-email/[key]`) y restablecimiento (`/reset-password/[uid]/[token]`). Login, registro, perfil y reseñas conservan su copia heredada hasta integrar sus diseños; sus validaciones, formatos y errores ya usan el idioma activo.

## Agregar texto

Usá una clave que describa la función y una frase completa. La copia aprobada vive en `claves.csv` y `copia-propuesta.csv` (ver «Fuentes de la copia»). `npm run i18n:generate` produce `messages/{en,es}/common.json`, `legal.json` y la copia de `contracts/enums.json` dentro del frontend. `legacy.*` conserva la copia de las pantallas existentes, con voseo en confirmación y el `*` de la ayuda de contraseña corregidos. El generador parte de los CSV, nunca de los catálogos existentes. Después, ejecutá `npm run format`.

En un componente cliente, `useTranslations("settings.language")` entrega una función `t` para pedir claves del namespace. En componentes de servidor usá `getTranslations` de `next-intl/server`. Para cantidades usá una frase ICU con `plural`; para enlaces dentro de una frase, `t.rich`. Los argumentos son valores del dominio, no fragmentos de texto. Los catálogos de correos no llegan al navegador y `legal.json` queda separado para cargarlo únicamente cuando exista la página de términos. Sus claves y argumentos ya están tipados. Esa página importará el catálogo de su locale y lo pasará a su propio proveedor; en servidor puede usar `createTranslator` con ese catálogo. El proveedor global sigue enviando solo `common.json`.

No escribas literales visibles en JSX, atributos o toasts fuera de las excepciones de `frontend/scripts/i18n/rules.mjs`. La lista tiene un máximo de 13 archivos y debe reducirse cuando cada diseño se integre. Los componentes de Shadcn son primitivas sin copia de producto; no integran esa lista. `npm run i18n:check` detecta residuos de español fuera de esas excepciones.

## Errores y validaciones

Django responde `{code, params, errors}`; `debug` aparece solo en desarrollo. `ApiError` conserva estado HTTP, código, parámetros y hojas, sin leer textos anteriores ni diagnósticos. `translateError` busca primero una clave de campo, después una de código y finalmente `errors.codes.unknown`. `fieldErrors` traduce la primera hoja de cada campo. La espera `retry_after_seconds` se convierte en `retryAfterSeconds` en un solo lugar.

Un código nuevo se agrega en `backend/filmai/errores/catalogo.py`, se exporta con `python manage.py exportar_contrato` y recibe copia en ambos idiomas. Los parámetros salen de la regla que falló. No incluyas contraseñas, tokens ni textos de excepciones. Los validadores puros devuelven códigos; `useValidation` los traduce para los formularios heredados. Un formulario bilingüe debe guardar el código y traducir al renderizar, para que los errores también cambien al elegir otro idioma.

## Formatos y datos de catálogo

`lib/format.ts` concentra fechas medias y largas, enteros, notas decimales y duración. Las funciones puras reciben el locale; `useFormats` lo toma del proveedor. Inglés usa `en-US`; español usa `es-AR`. Una fecha sin hora se interpreta en UTC para no cambiar de día entre dispositivos. No construyas `Intl.*` ni uses `toLocale*` en otros módulos.

`apiFetch` y la petición CSRF mandan `Accept-Language`. Las consultas de disponibilidad de username también lo incluyen. TMDB usa `en-US`/`es-MX` en el backend; eso es independiente de los formatos argentinos. `campos_en_ingles` señala cada respaldo: el campo visible correspondiente lleva `lang="en"`. ReviewCard ya lo aplica al título. Los futuros filtros consumirán `GET /api/catalogo/genres/`; los géneros traducidos no deben fijarse en el frontend. Género de usuario, tema y listas predeterminadas usan valores estables y etiquetas de `enums.*`.

## Idioma de cuenta y del dispositivo

Sin sesión, el selector escribe solo `filmai_locale`. Con sesión, Preferencias guarda primero por `PUT /api/preferences/` y actualiza cuenta, cookie y render después de la confirmación. Un error deja el idioma anterior. Al iniciar sesión o cargar una cuenta, el idioma guardado prevalece; si es nulo, se conserva la resolución del dispositivo. Google recibe el locale vigente al renderizar su botón.

Con sesión solo se cambia el idioma en Preferencias. El footer enlaza a `/settings#t-idioma`. Sin sesión, Landing, login y registro muestran `EN | ES`; el footer de escritorio ofrece nombres completos. No hay banderas ni controles de idioma en navbar o avatar.

Los enlaces de los correos usan rutas inglesas sin parámetro de idioma. El usuario confirmó el 08/10/2026 que al abrirlos se respeta cookie → navegador → inglés del dispositivo receptor, aunque el correo esté escrito en otro idioma.

## Verificar

| Prueba                  | Comportamiento protegido                                                                          |
| ----------------------- | ------------------------------------------------------------------------------------------------- |
| `i18n-catalogs.test.ts` | Paridad de claves, argumentos, tags, plurales, códigos y nombres reservados                       |
| `i18n-shared.test.ts`   | Formatos contra Intl, resolución de errores, espera y encabezados HTTP/CSRF                       |
| `i18n-account.test.tsx` | Cuenta prevalece, idioma nulo, guardado pendiente y fallo sin cambiar cookie                      |
| `i18n-google.test.tsx`  | Locale del botón y carga tardía del SDK sin escuchas obsoletas                                    |
| `i18n-guards.test.ts`   | Reglas que rechazan literales/debug/formatos, límite de excepciones y generación reproducible     |
| `i18n-flows.spec.ts`    | Registro, confirmación, login, cambio y reset en ambos idiomas; footer móvil/escritorio y teclado |
| Suite Django            | Contrato sin claves anteriores en todos los 4xx/5xx, seguridad y regresión de los módulos         |

Ejecutá Vitest, Playwright, TypeScript, build, ESLint, Prettier, Ruff y Django. CI ahora incluye `develop` y el control de residuos. No marques una ejecución remota como aprobada sin verla.

## Revisar correos

`revision-correos/index.html` reúne ocho variantes renderizadas con los enlaces nuevos; los EML vecinos se pueden abrir en un cliente de correo. Son ejemplos sin tokens reales y no se enviaron al exterior. Comprobá asunto, texto, HTML, tamaños móvil/escritorio, enlaces y ausencia de texto del otro idioma. La revisión en un cliente real sigue siendo una aceptación humana, distinta de las pruebas de render.

El botón de Google recibe `locale` y la carga inicial del SDK usa `hl`, según la [documentación oficial de GIS](https://developers.google.com/identity/gsi/web/guides/display-button). La librería mantiene un solo script y elimina las escuchas de carga cuando cambia el idioma o se desmonta el componente.

## Fuentes de la copia

`claves.csv` tiene una fila por texto del diseño (634) y es la fuente de los catálogos. `copia-propuesta.csv` suma los textos que el diseño no traía (errores, selector, nombres reservados). `ot70-catalogo-transitorio.csv` guarda la copia `legacy.*` de las pantallas heredadas y se reduce al integrar cada diseño.

| Columna                       | Qué contiene                                                         |
| ----------------------------- | -------------------------------------------------------------------- |
| `origen_id`                   | Posición en la tabla de equivalencias original; no cambia            |
| `es_original` / `en_original` | Texto tal como estaba en el diseño; no se edita                      |
| `clave` / `namespace`         | Destino que describe una función, por ejemplo `search.results.count` |
| `estado`                      | Decide si la fila se siembra                                         |
| `es_curado` / `en_curado`     | Mensaje completo, con argumentos y plurales cuando corresponde       |
| `grupo`                       | IDs de los fragmentos que forman una sola frase                      |
| `observaciones`               | Motivo del cambio y datos variables                                  |

Se siembran las filas `ok` (408) y `fragmento` (43). Quedan fuera `muestra` (61, datos de ejemplo), `diseño` (101, mesas y documentación del canvas) y `chatbot` (21, módulo todavía sin implementar). Una clave repetida solo es válida si sus dos mensajes curados son idénticos. Las claves de pantallas todavía no construidas son propuestas: se confirman al implementar cada diseño.

## Glosario

| Concepto             | Inglés            | Español                | Uso                                    |
| -------------------- | ----------------- | ---------------------- | -------------------------------------- |
| Cuenta               | Account           | Cuenta                 | Cuenta del usuario, distinta de perfil |
| Perfil               | Profile           | Perfil                 | Datos personales                       |
| Preferencias         | Settings          | Preferencias           | Configuración y selector de idioma     |
| Inicio de sesión     | Log in            | Iniciar sesión         | Acción de autenticarse                 |
| Registro             | Sign up           | Crear cuenta           | Alta de cuenta                         |
| Calificación         | Rating            | Calificación           | Nota entera de 1 a 10                  |
| Reseña               | Review            | Reseña                 | Texto asociado a una calificación      |
| Favoritos            | Favorites         | Favoritos              | Lista con `clave=favoritos`            |
| Pendientes           | Watchlist         | Pendientes             | Lista con `clave=pendientes`           |
| Vistas               | Watched           | Vistas                 | Lista con `clave=vistas`               |
| Género de producción | Genre             | Género                 | Filtro del catálogo                    |
| Género de persona    | Gender            | Género                 | Campo del perfil                       |
| Género no declarado  | Prefer not to say | No especificar         | Valor `no_especifica`                  |
| Tema oscuro          | Dark              | Oscuro                 | Valor `oscuro`                         |
| Tema claro           | Light             | Claro                  | Valor `claro`                          |
| Película             | Movie             | Película               | API `movie`, dominio `pelicula`        |
| Serie                | TV show           | Serie                  | API `tv`, dominio `serie`              |
| Confirmación         | Confirm account   | Confirmar cuenta       | Activación mediante enlace             |
| Restablecimiento     | Reset password    | Restablecer contraseña | Recuperación mediante enlace           |
| Reenvío de enlace    | Resend link       | Reenviar enlace        | Acción de las pantallas de correo      |

Genre y Gender usan claves distintas aunque coincidan en español. Rating y Review nunca son intercambiables. El español usa voseo («elegí», «guardá», «podés»). No se traducen nombres de usuario, de personas, de listas personalizadas ni reseñas de la comunidad; los títulos de las producciones los da TMDB por idioma.

## Al implementar una pantalla nueva

- Pedí el catálogo con `apiFetch`. Las vistas públicas de catálogo no autentican: su idioma sale solo de `Accept-Language`, nunca de la cuenta.
- `campos_en_ingles` no viaja en las respuestas en inglés; tratalo como opcional.
- Las producciones del `seed` son datos inventados sin traducción: sus títulos salen en inglés con `lang="en"` aunque la interfaz esté en español. Es el respaldo previsto.
- Las cuentas del `seed` tienen idioma guardado (`usuario001` y `003` en `es`, `usuario002` en `en`), así que al iniciar sesión manda la cuenta y no el navegador.
- El `.env` de desarrollo usa Resend: registrarse o pedir un restablecimiento envía correos reales.
- Retirá el archivo de `legacyFiles` en `frontend/scripts/i18n/rules.mjs` y su copia `legacy.*` al integrar el diseño.

## Pendiente

Falta abrir los ocho EML de `revision-correos/` en un cliente de correo real y registrar cliente, versión y resultado. No bloquea las interfaces.

El chatbot (B-02–B-06) no está implementado. Sus reglas de idioma quedaron resueltas en `docs/decisiones.md`, entrada «Chatbot: idioma, tarjetas, errores y límites» del 09/10/2026. Sigue pendiente curar y aprobar las 21 filas `chatbot` de `claves.csv` y agregar las de cancelación y errores.
