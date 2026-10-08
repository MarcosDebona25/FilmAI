# OT-13: revisión editorial aprobada

Estado: copia nueva y seis resoluciones de curaduría **aprobadas por el usuario
el 08/10/2026**. El cierre de validaciones y publicación se registra en el plan. No se crearon
catálogos, código ni tests. OT-11 y OT-12 están integradas en `feat/i18n-multiidioma`, con CI en verde.
Al retomar se comprobaron las 91 filas y los 74 códigos contra el contrato integrado.

La propuesta está en `copia-propuesta.csv`: 65 errores públicos del borrador
OT-11, 9 respuestas exitosas, un respaldo desconocido, una variante de espera,
8 textos del selector, 6 mensajes específicos de campo y el asunto de reenvío.
Las 91 filas quedan `aprobado`: el usuario confirmó ambos idiomas, los
argumentos y el significado del borrador actualizado. Las seis decisiones de
curaduría se aplicaron conservando todos los textos y pantallas originales.

## Reglas de la propuesta

- ES usa voseo y EN usa las equivalencias del glosario de OT-10.
- Los nombres de idioma se muestran como `English` y `Español` en ambos locales.
- Parámetros numéricos obligatorios usan los nombres de OT-11. No se imprimen
  IDs de avatar, opciones internas, atributos del modelo ni nombres de campos.
- `errors.codes.throttled` no promete una espera desconocida;
  `throttledWithWait` es una variante editorial, no un código de backend.
  El helper convierte `retry_after_seconds` a `retryAfterSeconds` solo cuando existe.
- `unknown` es respaldo del frontend. Los textos de éxito usan la misma búsqueda
  por clave, sin obligar a que un éxito lleve el sobre de errores.
- `csrf_ready` tiene traducción por paridad; no se propone mostrar un toast de CSRF.
- `already_confirmed` evita afirmar que una cuenta dada de baja está activa:
  el código actual también incluye enlaces que no pueden reactivarla.
- El éxito de baja conserva exactamente el texto actual del backend. Las filas
  de baja 487–491 y 568 del CSV original no se modifican.
- El asunto de reenvío conserva el de registro; la tabla no aporta otro asunto.
  Correos: 24 horas para confirmar, 1 hora para restablecer; el contacto ya
  aprobado es `contacto@filmai.com`.

## Ajustes del borrador al retomar

- Credenciales inválidas: el mensaje sirve para contraseña y Google, sin asumir
  que el fallo sea una combinación de correo y contraseña.
- Límite de solicitudes: las variantes con y sin espera evitan atribuir el exceso
  al usuario, porque también pueden representar un límite de TMDB.
- Reenvío de confirmación: el mensaje es condicional, porque el endpoint devuelve
  éxito también para correos desconocidos o cuentas ya confirmadas, sin enviar.
- El usuario aprobó las 91 filas del borrador actualizado el 08/10/2026.

## Seis decisiones aplicadas a la curaduría

Los diseños Claude nuevos no están versionados. El usuario resolvió explícitamente
el uso de las seis entradas; las columnas originales siguen inmutables.

| ID  | Resolución aprobada                                                                          | Destino                                                          |
| --- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| 214 | Reutilizar la confirmación completa de eliminar calificación y reseña, y quitar de Vistas.   | `title.rating.removeBothDescription`; mismo mensaje que 209/211. |
| 215 | Reutilizar la confirmación completa de eliminar calificación sin reseña, y quitar de Vistas. | `title.rating.removeOnlyDescription`; mismo mensaje que 210/212. |
| 320 | Filtro de nota exacta: «Calificación {rating}/10» / “Rating {rating}/10”.                    | `reviews.filters.ratingValueLabel`; argumento `rating`.          |
| 355 | Etiqueta del campo: «Contraseña» / “Password”.                                               | Reutiliza `auth.password.label`.                                 |
| 448 | Metadato de locale `es`/`en`, excluido del catálogo.                                         | Estado `diseño`, sin clave ni texto curado.                      |
| 535 | Encabezado autónomo «Incluye» / “Includes”.                                                  | `auth.adminAccess.includedResources`.                            |

La confirmación de eliminación coincide con el comportamiento de
`frontend/components/ReviewModal.tsx:169` y el invariante del doc 03:51.
El formato X/10 está definido en doc 04:1055. La decisión sobre el filtro
es exacta, no un mínimo ni un rango.

## Checklist de continuación

- [x] Confirmar integración y versión final de OT-11/OT-12.
- [x] Aprobar las 91 filas de copia nueva ES/EN.
- [x] Revisar y aprobar la curaduría completa.
- [x] Resolver las seis filas con contexto del diseño o decisión explícita.
- [x] Actualizar el CSV de curaduría conservando columnas originales inmutables.
- [x] Validar sintaxis ICU con el analizador usado en OT-12 y paridad de argumentos.
- [x] Revisar specs `i18n-core` y `emails`; quitar su estado de borrador solo al aprobar.
- [ ] Root registra decisión/traspaso, actualiza graphify y coordina formato/CI.

Se mantienen dos unidades de revisión menores de 400 líneas: specs juntas;
y copia CSV más esta revisión. La aprobación editorial habilita el cierre de
OT-13 una vez verificadas las suites y publicada la entrega hacia integración.

## Estado de validación y publicación

Validación editorial y de datos aprobada: 91 mensajes nuevos, 451 filas ICU
utilizables y 425 claves sin colisiones; originales y baja intactos.
Ruff, ESLint, Prettier, TypeScript, los 43 tests unitarios del frontend y el
build pasan en la sesión retomada. Se repite la suite backend con el contrato
OpenAPI copiado a `/contracts` dentro del contenedor: el montaje de desarrollo
solo incluye `backend/`. Playwright corre con `CI=1` para arrancar su servidor.
Los resultados finales se registrarán antes de integrar.

Specs y decisión: PR #53 hacia `feat/i18n-multiidioma`. Copia, curaduría y
registro: segunda entrega apilada sobre la primera. El PR #52 se sustituye
por estas dos entregas; su CI del borrador no se usa para aprobarlas.
El respaldo del checkout inicial queda en `/tmp/filmai-retoma-08oct/` y en
el stash `respaldo ot13 aprobado antes de dividir entrega`. Main queda fuera.
