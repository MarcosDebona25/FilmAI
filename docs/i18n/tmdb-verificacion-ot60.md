# Verificación real de TMDB — OT-60

Fecha: 08/10/2026. Consultas HTTP de lectura usando la configuración del
backend; sin escrituras en la base de desarrollo. La clave API no se registra.
Son observaciones del proveedor en esta fecha, no fixtures inmutables.

## Inglés explícito

Se comparó `GET /movie/550`, `/movie/10778` y `/tv/1396` sin `language`
contra `language=en-US`. Título (`title`/`name`), `overview`, `poster_path`
y `genres` fueron iguales en los tres casos. Esto verifica la muestra del
paso 1; no supone igualdad para toda la base de TMDB.

## Idiomas y géneros

`GET /configuration/primary_translations` contiene `en-US` y `es-MX`,
variantes usadas por el mapa del backend. El endpoint documenta etiquetas
IETF: [primary translations](https://developer.themoviedb.org/reference/configuration-primary-translations).

`GET /genre/tv/list` con cada variante devolvió 16 géneros y los mismos IDs.
`16` fue “Animation” / “Animación”; `10759` fue “Action & Adventure” en ambas
respuestas. El backend conserva lo que entrega el proveedor.
El parámetro está documentado en [TV genres](https://developer.themoviedb.org/reference/genre-tv-list).

## Ausencia de traducción

Se compararon detalles EN/ES y traducciones de películas japonesas:

| ID | Traducción es-MX | Título ES | Título EN | Sinopsis ES |
| --- | --- | --- | --- | --- |
| 36095 | Presente | Cure | Cure | No vacía |
| 1559362 | Ausente | 荒木又右衛門 | Araki Mataemon | Vacía |

El segundo caso demuestra que una traducción ausente puede devolver un título
original no vacío. OT-61 completará por campo vacío, conservando cualquier
valor no vacío; no deducirá ausencia de traducción a partir del idioma del
título ni consultará traducciones para cada resultado de listado.

## Idioma de imágenes

`GET /movie/550/images?language=es-MX&include_image_language=es,en,null`
devolvió 61 pósters con etiquetas `es`, `en` y nulas. La selección de imágenes
usa códigos de idioma sin región; `include_image_language` permite varios
idiomas y recursos sin idioma, según [image languages](https://developer.themoviedb.org/docs/image-languages)
y [movie images](https://developer.themoviedb.org/reference/movie-images).
No se añade un endpoint de imágenes ni se modifica la política de pósters
en esta orden.

## Pruebas automatizadas

Las pruebas nuevas usan `httpx.MockTransport` para inspeccionar la solicitud
HTTP y fakeredis para verificar aciertos separados. No necesitan API externa
ni datos variables. Las seis vistas localizables resuelven el encabezado con
el analizador de Django; keywords mantiene su contrato global.
