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
