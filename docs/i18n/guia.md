# Usar multiidioma en FilmAI

La aplicación admite `en` y `es` sin prefijos de idioma en las rutas. Las pantallas piloto son Preferencias (`/settings`), confirmación (`/confirm-email/[key]`) y restablecimiento (`/reset-password/[uid]/[token]`). Login, registro, perfil y reseñas conservan su copia heredada hasta integrar sus diseños; sus validaciones, formatos y errores ya usan el idioma activo.

## Agregar texto

Usá una clave que describa la función y una frase completa. La copia aprobada vive en `claves.csv` y `copia-propuesta.csv`. `npm run i18n:generate` produce `messages/{en,es}/common.json`, `legal.json` y la copia de `contracts/enums.json` dentro del frontend. `legacy.*` conserva la copia de las pantallas existentes, con voseo en confirmación y el `*` de la ayuda de contraseña corregidos. El generador parte de los CSV, nunca de los catálogos existentes. Después, ejecutá `npm run format`.

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

## Chatbot

Esta entrega no implementa B-02–B-06. La decisión vigente pide respuestas en `idioma_efectivo()`, español con voseo y tools TMDB localizadas. BGE-M3 consulta el corpus canónico inglés; no se duplican embeddings. En el pair programming del 09/10/2026 hay que acordar cómo fijar el idioma de una respuesta SSE en curso, qué pasa al cambiar Preferencias durante esa solicitud y cómo localizar tarjetas y errores.

El botón de Google recibe `locale` y la carga inicial del SDK usa `hl`, según la [documentación oficial de GIS](https://developers.google.com/identity/gsi/web/guides/display-button). La librería mantiene un solo script y elimina las escuchas de carga cuando cambia el idioma o se desmonta el componente.
