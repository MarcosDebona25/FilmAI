# Curaduría de textos para multiidioma

`equivalencias.json` conserva la tabla original. `claves.csv` agrega destinos
semánticos y textos completos para revisión; no crea catálogos de producción.
La siembra corresponde a OT-77, después de la revisión editorial de OT-13.

Cada `origen_id` es la posición original, empezando en 1. Hay una fila por
entrada y se conservan exactamente `es_original`, `en_original` y `pantallas`.
Los textos curados pueden cambiar sin perder esa referencia.

| Columna                   | Qué contiene                                                         |
| ------------------------- | -------------------------------------------------------------------- |
| `clave` / `namespace`     | Destino que describe una función, por ejemplo `search.results.count` |
| `estado`                  | Clasificación que decide si se puede revisar para siembra            |
| `es_curado` / `en_curado` | Mensaje completo, con argumentos y plurales cuando corresponde       |
| `grupo`                   | IDs de los fragmentos que forman una sola frase                      |
| `observaciones`           | Motivo del cambio, datos variables y revisiones pendientes           |

| Estado        | Filas | Tratamiento                                                   |
| ------------- | ----: | ------------------------------------------------------------- |
| `ok`          |   408 | Mensajes aprobados en OT-13                                   |
| `fragmento`   |    43 | Frase completa recompuesta y aprobada en OT-13                |
| `muestra`     |    61 | Datos de ejemplo excluidos                                    |
| `diseño`      |   101 | Mesas, documentación de diseño y previsualizaciones excluidas |
| `chatbot`     |    21 | Módulo fuera de alcance, incluido su lanzador compartido      |
| `incoherente` |     0 | Sin pendientes; las exclusiones no se siembran                |

Las 451 filas utilizables apuntan a 425 claves distintas. Una clave repetida
solo es válida si ambos mensajes curados son idénticos. Así varias filas de
un grupo conservan su trazabilidad sin crear traducciones duplicadas.
Los 41 nombres de pantalla del original se conservan; no se perdió ninguna
pantalla ni se incorporaron textos de otra persona o fuente.

## Frases y datos variables

ICU expresa cantidades y plurales en una sola frase. `lists.count.items`
usa `{count, plural, one {# ítem} other {# ítems}}`; la variante inglesa usa
`item` y `items`. No se unen prefijos, números y sufijos por separado.
Los grupos 239–240, 352–353, 376–378 y 541–542 recomponen, respectivamente,
la creación de listas, el envío neutro de recuperación, la aceptación de
los términos y la explicación de acceso de administrador.

Los nombres de personas, listas y producciones se interpolan como `{name}`,
`{listName}` y `{title}`. Fechas, notas decimales y listas de géneros se
formatean por locale antes de interpolarse como `{date}`, `{rating}` y
`{genres}`. Las cantidades de votos usan `#` en un plural ICU: en inglés
41,355 votos; en español 41.355. El original incorrecto `41.355 votes`
permanece visible en las columnas de origen de las filas 162 y 163.

Las frases con enlaces usan tags: `auth.signUp.termsAcceptance` contiene
`<terms>…</terms>` y `title.rating.editSummary` contiene `<edit>…</edit>`.
`t.rich` recibe una función que convierte cada tag en el enlace o control
correspondiente; no se concatenan piezas de la frase.

## Revisión editorial

Se aplicaron las correcciones menores acordadas en el plan 3.9:
«Recomendado para vos» (24), «no sabés» (593) y «Reenviar enlace» (610).
La vigencia de los correos es `{expiryHours}`, tomada de configuración,
y las muestras de saludo y copyright usan nombre y año variables.

Genre y Gender tienen claves distintas: `search.filters.genreLabel`
y `auth.signUp.genderLabel`. Las listas predeterminadas usan `Favorites`,
`Watchlist`, `Watched`; `no_especifica` usa «No especificar» y
`Prefer not to say`. Los identificadores de API conservan el español.
La copia de baja de cuenta de 487–491 y 568 se conserva exactamente en
ambos idiomas, conforme a la decisión del usuario.

Las seis dudas fueron resueltas por el usuario en OT-13 el 08/10/2026:
214/215 reutilizan las confirmaciones completas de eliminación; 320 expresa
una nota exacta X/10; 355 reutiliza la etiqueta de contraseña; 448 es metadato
de locale excluido y 535 es el encabezado autónomo de recursos.
`revision-ot13.md` registra los destinos y `copia-propuesta.csv` contiene los
91 textos nuevos aprobados. No quedan filas incoherentes pendientes.
Las filas 584/585 incorporan `contacto@filmai.com`, confirmado por el usuario;
las columnas originales conservan el marcador de contacto.

Las claves de pantallas futuras son propuestas de función; se confirman al
implementar cada diseño. Los grupos 245–247, 260–262, 319 y los nombres
accesibles de filtros (292 y 325) conservan observaciones específicas para
revisar su ubicación y concordancia. Los mensajes nuevos de errores y del
selector faltan en el original: fueron redactados y aprobados en OT-13.
`emails.*` es referencia para las plantillas de backend de F5, no un namespace
que se envíe al proveedor de cliente. `legal.*` se carga solo en términos.

## Verificación y partición

La comprobación de datos verificó 634 IDs únicos, el original inmutable,
los 41 nombres de pantalla, claves sin colisiones y el texto de baja intacto.
Un analizador de FormatJS validó sintaxis ICU y paridad ES/EN de argumentos
y tags en las 451 filas utilizables: 28 filas con plurales y 3 con tags.
Estas comprobaciones validan estructura; OT-13 registra la aprobación editorial. No se modificó código, tests ni dependencias del repo.

Se propone integrar el CSV por bloques acumulativos, conservando los IDs:

1. 1–270: navegación compartida, diseño, Home y ficha; 270 filas.
2. 271–499: búsqueda, reseñas, autenticación, listas, perfil y preferencias;
   229 filas nuevas, total acumulado 499.
3. 500–634: exclusiones del chatbot, errores, acceso, términos, footer y
   correos; 135 filas nuevas, total acumulado 634.

Los cortes no separan un grupo de fragmentos. El grupo reutilizado de ítems
(241–242 y 414–415) se completa en el segundo bloque con los mismos valores.
Durante la integración parcial, una referencia de grupo a un ID futuro indica
trazabilidad prevista; el CSV completo resuelve todas las referencias.

## Reserva de nombres (OT-41)

OT-41 agrega una fila nueva aprobada a `copia-propuesta.csv` para
`list_name_reserved` (HTTP 409, sin parámetros). Las 91 filas originales
aprobadas en OT-13 permanecen intactas. El mensaje distingue un nombre del
sistema de un nombre personalizado duplicado. `contracts/enums.json` publica
las identidades, valores de género y nombres reservados ES/EN; se reproduce
con `python manage.py exportar_enums`.
