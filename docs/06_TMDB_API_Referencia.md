# FilmAI — Referencia de Endpoints TMDB API v3

> Referencia rápida de lo que expone la API externa integrada (RNF #14).
> Se usa para implementar `TMDBClient` (C-01), la caché (C-02), la
> sincronización diaria (C-04) y las herramientas de tool calling del chatbot
> (B-02). Decisiones asociadas: `docs/decisiones.md`.

## Uso general

- **Base URL**: `https://api.themoviedb.org/3`
- **Autenticación**: header `Authorization: Bearer <token>` (read-only v4) o
  parámetro `api_key` (v3). La API key vive en las variables de entorno del
  backend (`.env`).
- **Caché (C-02)**: TTL por endpoint — trending 6h, discover 6h, detalle 24h,
  search 1h. Key pattern `tmdb:{endpoint}:{params_hash}`.
- **Rate limiting**: respetar límites, reintentos con backoff, timeout 5s
  (C-01). Consultas de detalle cacheadas para no duplicar llamadas (RNF #8).
- **Referencia oficial**: https://developer.themoviedb.org/reference

---

## Índice de secciones

- [Autenticación](#autenticacion)
- [Account](#account)
- [Certifications](#certifications)
- [Changes](#changes)
- [Collections](#collections)
- [Companies](#companies)
- [Configuration](#configuration)
- [Credits](#credits)
- [Discover](#discover)
- [Find](#find)
- [Genres](#genres)
- [Guest Sessions](#guest-sessions)
- [Keywords](#keywords)
- [Lists](#lists)
- [Movies](#movies)
- [Networks](#networks)
- [People](#people)
- [Reviews](#reviews)
- [Search](#search)
- [Trending](#trending)
- [TV](#tv)
- [TV Seasons](#tv-seasons)
- [TV Episodes](#tv-episodes)
- [TV Episode Groups](#tv-episode-groups)
- [Watch Providers](#watch-providers)
- [Uso en FilmAI (tool calling)](#uso-en-filmai-tool-calling)

---

## Autenticacion

| Método | Endpoint          | Detalle                              |
| :----- | :---------------- | :----------------------------------- |
| GET    | `/authentication` | Estado del sistema de autenticación. |

## Account

| Método | Endpoint                                  | Detalle                         |
| :----- | :---------------------------------------- | :------------------------------ |
| GET    | `/account/{account_id}`                   | Datos de la cuenta autenticada. |
| POST   | `/account/{account_id}/favorite`          | Marcar/desmarcar favorito.      |
| POST   | `/account/{account_id}/watchlist`         | Agregar/quitar de watchlist.    |
| GET    | `/account/{account_id}/favorite/movies`   | Películas favoritas.            |
| GET    | `/account/{account_id}/favorite/tv`       | Series favoritas.               |
| GET    | `/account/{account_id}/rated/movies`      | Películas calificadas.          |
| GET    | `/account/{account_id}/rated/tv`          | Series calificadas.             |
| GET    | `/account/{account_id}/rated/tv/episodes` | Episodios calificados.          |
| GET    | `/account/{account_id}/watchlist/movies`  | Películas en watchlist.         |
| GET    | `/account/{account_id}/watchlist/tv`      | Series en watchlist.            |
| GET    | `/account/{account_id}/lists`             | Listas de la cuenta.            |

> Nota: la cuenta de FilmAI es propia; estos endpoints no se usan como fuente de
> datos del usuario (eso vive en nuestra BD).

## Certifications

| Método | Endpoint                                       | Detalle                               |
| :----- | :--------------------------------------------- | :------------------------------------ |
| GET    | `/certification/movie/list`                    | Clasificaciones de películas.         |
| GET    | `/certification/tv/list`                       | Clasificaciones de series.            |
| GET    | `/certification/tv/{certification_country}`    | Clasificaciones por país (TV).        |
| GET    | `/certification/movie/{certification_country}` | Clasificaciones por país (películas). |

## Changes

| Método | Endpoint          | Detalle                         |
| :----- | :---------------- | :------------------------------ |
| GET    | `/movie/changes`  | Cambios recientes en películas. |
| GET    | `/person/changes` | Cambios recientes en personas.  |
| GET    | `/tv/changes`     | Cambios recientes en series.    |

## Collections

| Método | Endpoint                                   | Detalle                       |
| :----- | :----------------------------------------- | :---------------------------- |
| GET    | `/collection/{collection_id}`              | Detalle de colección.         |
| GET    | `/collection/{collection_id}/images`       | Imágenes de la colección.     |
| GET    | `/collection/{collection_id}/translations` | Traducciones de la colección. |

## Companies

| Método | Endpoint                                  | Detalle                         |
| :----- | :---------------------------------------- | :------------------------------ |
| GET    | `/company/{company_id}`                   | Detalle de compañía/productora. |
| GET    | `/company/{company_id}/alternative_names` | Nombres alternativos.           |
| GET    | `/company/{company_id}/images`            | Imágenes de la compañía.        |

## Configuration

| Método | Endpoint                              | Detalle                                 |
| :----- | :------------------------------------ | :-------------------------------------- |
| GET    | `/configuration`                      | Configuración base (imágenes, tamaños). |
| GET    | `/configuration/countries`            | Países disponibles.                     |
| GET    | `/configuration/jobs`                 | Trabajos del equipo.                    |
| GET    | `/configuration/languages`            | Idiomas disponibles.                    |
| GET    | `/configuration/primary_translations` | Traducciones primarias.                 |
| GET    | `/configuration/timezones`            | Zonas horarias.                         |

## Credits

| Método | Endpoint              | Detalle                           |
| :----- | :-------------------- | :-------------------------------- |
| GET    | `/credit/{credit_id}` | Detalle de un crédito individual. |

## Discover

| Método | Endpoint          | Detalle                                                      |
| :----- | :---------------- | :----------------------------------------------------------- |
| GET    | `/discover/movie` | Descubrir películas por filtros (género, año, rating, etc.). |
| GET    | `/discover/tv`    | Descubrir series por filtros.                                |

> **Uso en FilmAI**: base de la herramienta `top_por_genero` y del
> "Recomendado para ti" (Home, doc 04 sección 3.3).

## Find

| Método | Endpoint              | Detalle                                   |
| :----- | :-------------------- | :---------------------------------------- |
| GET    | `/find/{external_id}` | Buscar por ID externo (IMDB, TVDB, etc.). |

## Genres

| Método | Endpoint            | Detalle                        |
| :----- | :------------------ | :----------------------------- |
| GET    | `/genre/movie/list` | Lista de géneros de películas. |
| GET    | `/genre/tv/list`    | Lista de géneros de series.    |

## Guest Sessions

| Método | Endpoint                                              | Detalle                                      |
| :----- | :---------------------------------------------------- | :------------------------------------------- |
| GET    | `/guest_session/{guest_session_id}/rated/movies`      | Películas calificadas en sesión de invitado. |
| GET    | `/guest_session/{guest_session_id}/rated/tv`          | Series calificadas en sesión de invitado.    |
| GET    | `/guest_session/{guest_session_id}/rated/tv/episodes` | Episodios calificados en sesión de invitado. |

## Keywords

| Método | Endpoint                       | Detalle                           |
| :----- | :----------------------------- | :-------------------------------- |
| GET    | `/keyword/{keyword_id}`        | Detalle de un keyword.            |
| GET    | `/keyword/{keyword_id}/movies` | Películas asociadas a un keyword. |

> **Uso en FilmAI**: los keywords de cada producción se sincronizan en C-04 vía
> `/movie/{id}/keywords` y `/tv/{id}/keywords` (sección Movies/TV) y alimentan el
> texto a embebear del retrieval semántico (B-06).

## Lists

| Método | Endpoint                      | Detalle                   |
| :----- | :---------------------------- | :------------------------ |
| GET    | `/list/{list_id}`             | Detalle de lista de TMDB. |
| POST   | `/list`                       | Crear lista.              |
| POST   | `/list/{list_id}/add_item`    | Agregar ítem.             |
| POST   | `/list/{list_id}/remove_item` | Quitar ítem.              |
| DELETE | `/list/{list_id}`             | Eliminar lista.           |

## Movies

| Método | Endpoint                               | Detalle                                                       |
| :----- | :------------------------------------- | :------------------------------------------------------------ |
| GET    | `/movie/{movie_id}`                    | Detalle de película (título, sinopsis, géneros, duración...). |
| GET    | `/movie/{movie_id}/account_states`     | Estados de la cuenta sobre la película.                       |
| GET    | `/movie/{movie_id}/alternative_titles` | Títulos alternativos.                                         |
| GET    | `/movie/{movie_id}/changes`            | Cambios en la película.                                       |
| GET    | `/movie/{movie_id}/credits`            | Reparto y equipo (actores/directores).                        |
| GET    | `/movie/{movie_id}/external_ids`       | IDs externos (IMDB, etc.).                                    |
| GET    | `/movie/{movie_id}/images`             | Imágenes.                                                     |
| GET    | `/movie/{movie_id}/keywords`           | **Keywords temáticos** (B-06).                                |
| GET    | `/movie/{movie_id}/lists`              | Listas que contienen la película.                             |
| GET    | `/movie/{movie_id}/recommendations`    | Recomendaciones de TMDB.                                      |
| GET    | `/movie/{movie_id}/release_dates`      | Fechas de estreno por país.                                   |
| GET    | `/movie/{movie_id}/reviews`            | Reseñas de TMDB.                                              |
| GET    | `/movie/{movie_id}/similar`            | **Películas similares** (herramienta `similares_a`).          |
| GET    | `/movie/{movie_id}/translations`       | Traducciones.                                                 |
| GET    | `/movie/{movie_id}/videos`             | Videos (trailers).                                            |
| GET    | `/movie/{movie_id}/watch/providers`    | Proveedores de streaming.                                     |
| POST   | `/movie/{movie_id}/rating`             | Calificar (vía TMDB).                                         |
| DELETE | `/movie/{movie_id}/rating`             | Quitar calificación.                                          |
| GET    | `/movie/now_playing`                   | En cartelera.                                                 |
| GET    | `/movie/popular`                       | Populares.                                                    |
| GET    | `/movie/top_rated`                     | Mejor calificadas.                                            |
| GET    | `/movie/upcoming`                      | Próximos estrenos.                                            |

## Networks

| Método | Endpoint                                  | Detalle                |
| :----- | :---------------------------------------- | :--------------------- |
| GET    | `/network/{network_id}`                   | Detalle de red/cadena. |
| GET    | `/network/{network_id}/alternative_names` | Nombres alternativos.  |
| GET    | `/network/{network_id}/images`            | Imágenes.              |

## People

| Método | Endpoint                               | Detalle                |
| :----- | :------------------------------------- | :--------------------- |
| GET    | `/person/{person_id}`                  | Detalle de persona.    |
| GET    | `/person/{person_id}/changes`          | Cambios.               |
| GET    | `/person/{person_id}/combined_credits` | Créditos combinados.   |
| GET    | `/person/{person_id}/external_ids`     | IDs externos.          |
| GET    | `/person/{person_id}/images`           | Imágenes.              |
| GET    | `/person/{person_id}/movie_credits`    | Créditos en películas. |
| GET    | `/person/{person_id}/tagged_images`    | Imágenes etiquetadas.  |
| GET    | `/person/{person_id}/tv_credits`       | Créditos en series.    |
| GET    | `/person/{person_id}/translations`     | Traducciones.          |
| GET    | `/person/popular`                      | Personas populares.    |

## Reviews

| Método | Endpoint              | Detalle                    |
| :----- | :-------------------- | :------------------------- |
| GET    | `/review/{review_id}` | Detalle de reseña de TMDB. |

## Search

| Método | Endpoint             | Detalle                                                            |
| :----- | :------------------- | :----------------------------------------------------------------- |
| GET    | `/search/collection` | Buscar colecciones.                                                |
| GET    | `/search/company`    | Buscar compañías.                                                  |
| GET    | `/search/keyword`    | Buscar keywords.                                                   |
| GET    | `/search/movie`      | **Buscar películas por título** (herramienta `buscar_por_titulo`). |
| GET    | `/search/multi`      | Búsqueda múltiple (películas, series y personas).                  |
| GET    | `/search/person`     | Buscar personas.                                                   |
| GET    | `/search/tv`         | **Buscar series por título** (herramienta `buscar_por_titulo`).    |

## Trending

| Método | Endpoint                         | Detalle                         |
| :----- | :------------------------------- | :------------------------------ |
| GET    | `/trending/all/{time_window}`    | Tendencias globales (day/week). |
| GET    | `/trending/movie/{time_window}`  | Películas en tendencia.         |
| GET    | `/trending/person/{time_window}` | Personas en tendencia.          |
| GET    | `/trending/tv/{time_window}`     | Series en tendencia.            |

> **Uso en FilmAI**: fuente de las filas "Tendencias de la semana" (Home, C-05) y
> de la sync diaria (C-04).

## TV

| Método | Endpoint                                | Detalle                                                      |
| :----- | :-------------------------------------- | :----------------------------------------------------------- |
| GET    | `/tv/{series_id}`                       | Detalle de serie (título, sinopsis, géneros, temporadas...). |
| GET    | `/tv/{series_id}/account_states`        | Estados de la cuenta sobre la serie.                         |
| GET    | `/tv/{series_id}/aggregate_credits`     | Créditos agregados.                                          |
| GET    | `/tv/{series_id}/alternative_titles`    | Títulos alternativos.                                        |
| GET    | `/tv/{series_id}/changes`               | Cambios.                                                     |
| GET    | `/tv/{series_id}/content_ratings`       | Clasificaciones de contenido.                                |
| GET    | `/tv/{series_id}/credits`               | Reparto y equipo.                                            |
| GET    | `/tv/{series_id}/episode_groups`        | Grupos de episodios.                                         |
| GET    | `/tv/{series_id}/external_ids`          | IDs externos.                                                |
| GET    | `/tv/{series_id}/images`                | Imágenes.                                                    |
| GET    | `/tv/{series_id}/keywords`              | **Keywords temáticos** (B-06).                               |
| GET    | `/tv/{series_id}/recommendations`       | Recomendaciones de TMDB.                                     |
| GET    | `/tv/{series_id}/reviews`               | Reseñas de TMDB.                                             |
| GET    | `/tv/{series_id}/screened_theatrically` | Estrenadas en cines.                                         |
| GET    | `/tv/{series_id}/similar`               | **Series similares** (herramienta `similares_a`).            |
| GET    | `/tv/{series_id}/translations`          | Traducciones.                                                |
| GET    | `/tv/{series_id}/videos`                | Videos.                                                      |
| GET    | `/tv/{series_id}/watch/providers`       | Proveedores de streaming.                                    |
| POST   | `/tv/{series_id}/rating`                | Calificar (vía TMDB).                                        |
| DELETE | `/tv/{series_id}/rating`                | Quitar calificación.                                         |
| GET    | `/tv/airing_today`                      | Al aire hoy.                                                 |
| GET    | `/tv/on_the_air`                        | Al aire.                                                     |
| GET    | `/tv/popular`                           | Series populares.                                            |
| GET    | `/tv/top_rated`                         | Series mejor calificadas.                                    |

## TV Seasons

| Método | Endpoint                                                   | Detalle               |
| :----- | :--------------------------------------------------------- | :-------------------- |
| GET    | `/tv/{series_id}/season/{season_number}`                   | Detalle de temporada. |
| GET    | `/tv/{series_id}/season/{season_number}/account_states`    | Estados de la cuenta. |
| GET    | `/tv/{series_id}/season/{season_number}/aggregate_credits` | Créditos agregados.   |
| GET    | `/tv/{series_id}/season/{season_number}/credits`           | Reparto y equipo.     |
| GET    | `/tv/{series_id}/season/{season_number}/external_ids`      | IDs externos.         |
| GET    | `/tv/{series_id}/season/{season_number}/images`            | Imágenes.             |
| GET    | `/tv/{series_id}/season/{season_number}/translations`      | Traducciones.         |
| GET    | `/tv/{series_id}/season/{season_number}/videos`            | Videos.               |

## TV Episodes

| Método | Endpoint                                                                         | Detalle               |
| :----- | :------------------------------------------------------------------------------- | :-------------------- |
| GET    | `/tv/{series_id}/season/{season_number}/episode/{episode_number}`                | Detalle de episodio.  |
| GET    | `/tv/{series_id}/season/{season_number}/episode/{episode_number}/account_states` | Estados de la cuenta. |
| GET    | `/tv/{series_id}/season/{season_number}/episode/{episode_number}/changes`        | Cambios.              |
| GET    | `/tv/{series_id}/season/{season_number}/episode/{episode_number}/credits`        | Reparto y equipo.     |
| GET    | `/tv/{series_id}/season/{season_number}/episode/{episode_number}/external_ids`   | IDs externos.         |
| GET    | `/tv/{series_id}/season/{season_number}/episode/{episode_number}/images`         | Imágenes.             |
| GET    | `/tv/{series_id}/season/{season_number}/episode/{episode_number}/translations`   | Traducciones.         |
| GET    | `/tv/{series_id}/season/{season_number}/episode/{episode_number}/videos`         | Videos.               |

## TV Episode Groups

| Método | Endpoint                                  | Detalle                        |
| :----- | :---------------------------------------- | :----------------------------- |
| GET    | `/tv/episode_group/{tv_episode_group_id}` | Detalle de grupo de episodios. |

## Watch Providers

| Método | Endpoint                   | Detalle                               |
| :----- | :------------------------- | :------------------------------------ |
| GET    | `/watch/providers/regions` | Regiones disponibles.                 |
| GET    | `/watch/providers/movie`   | Proveedores de streaming (películas). |
| GET    | `/watch/providers/tv`      | Proveedores de streaming (series).    |

---

## Uso en FilmAI (tool calling)

| Herramienta del LLM (B-02)           | Endpoint(s) de TMDB                                   |
| :----------------------------------- | :---------------------------------------------------- |
| `buscar_por_titulo(titulo, tipo)`    | `GET /search/movie`, `GET /search/tv`                 |
| `top_por_genero(genero, tipo, page)` | `GET /discover/movie`, `GET /discover/tv`             |
| `similares_a(id_tmdb, tipo)`         | `GET /movie/{id}/similar`, `GET /tv/{id}/similar`     |
| `buscar_semantico(query)`            | No usa TMDB: pgvector sobre embeddings locales (B-06) |
| Detalle on-demand                    | `GET /movie/{id}`, `GET /tv/{id}`                     |
| Keywords para embeddings (C-04)      | `GET /movie/{id}/keywords`, `GET /tv/{id}/keywords`   |

---

## Materialización y embeddings (C-04 / B-06)

> Flujo acordado (08/09/2026, ver `docs/decisiones.md`). Los endpoints de esta
> referencia alimentan el catálogo materializado global y su corpus semántico.

1. **Exposición**: los listados (`/trending`, `/movie/now_playing`,
   `/discover`, `/search`) se sirven en vivo con caché Redis (C-02) y no
   requieren sincronización previa.
2. **Materialización**: cada producción expuesta por el catálogo o abierta en
   detalle se materializa en `ProduccionAudiovisual` por `(id_tmdb, tipo)`
   usando `GET /movie/{id}` / `GET /tv/{id}` (enriquecimiento) y
   `GET /movie/{id}/keywords` / `GET /tv/{id}/keywords` (keywords).
3. **Encolado**: tras persistir, se crea `ProduccionEmbedding` en estado
   `pending` y se encola la tarea Celery que genera el vector con BGE-M3 vía
   Ollama. La generación es asíncrona: ningún endpoint de catálogo o detalle
   espera a Ollama.
4. **Búsqueda semántica**: `buscar_semantico` consulta solo embeddings en
   estado `ready` (pgvector). Las producciones sin embedding `ready` siguen
   siendo recuperables por las herramientas TMDB de la tabla anterior; si un
   resultado de TMDB es relevante, se materializa y encola (el corpus crece
   progresivamente con el uso).
5. **Sync diaria (C-04b)**: el beat de Celery a las 3 AM sincroniza populares,
   tendencias y novedades (mantenimiento/seed del corpus), nunca reemplaza al
   discovery en vivo ni pisa datos locales.

## Idioma explícito del cliente y las vistas (OT-60)

El cliente y su caché admiten `en-US` y `es-MX`. Listados, búsqueda, detalles
y géneros envían `language`, incluido en los parámetros que forman la clave
Redis. Los TTL no cambian. Keywords, créditos y cambios conservan el contrato
global. La fábrica sin argumentos devuelve el cliente inglés compartido por
materialización; cada cliente mantiene un idioma fijo. Las seis vistas públicas
localizables seleccionan ese cliente por el encabezado Accept-Language, con
pesos y regiones, o inglés por defecto. Su autenticación permanece vacía;
keywords conserva el servicio global. 

Comportamiento del proveedor verificado contra la API real el 08/10/2026
(observaciones de esa fecha, no garantías):

- Omitir `language` equivale a `en-US` en título, sinopsis, póster y géneros
  (`/movie/550`, `/movie/10778`, `/tv/1396`).
- `en-US` y `es-MX` figuran en `/configuration/primary_translations`. Los
  géneros conservan sus IDs entre idiomas; algunos nombres llegan sin traducir
  (`10759` es “Action & Adventure” en ambos).
- TMDB no rellena con otro idioma: sin traducción, la sinopsis llega vacía y el
  título puede ser el original (`1559362` devuelve «荒木又右衛門»). Por eso el
  respaldo completa campo por campo solo lo vacío y no deduce la ausencia de
  traducción a partir del título.
- Las imágenes se filtran con códigos sin región
  (`include_image_language=es,en,null`). No hay endpoint de imágenes propio ni
  cambio en la política de pósters.


## Respaldo, persistencia y consumo frontend (OT-61–63, OT-72–76)

Los listados y detalles en español completan únicamente los campos vacíos con su versión inglesa, por identidad TMDB. `campos_en_ingles` identifica cuáles se completaron; el frontend marca el campo presentado con `lang="en"`. Los datos ya traducidos no se reemplazan. Pósters y backdrops también se resuelven por idioma.

`ProduccionAudiovisual` mantiene el contenido canónico inglés y `generos_ids`; `ProduccionTraduccion` guarda título, sinopsis y póster por producción/idioma. Listas y mis reseñas seleccionan título y póster por `idioma_efectivo(request)`, sin modificar el texto escrito por el usuario. El prefetch evita una consulta SQL por cada tarjeta. `GET /api/catalogo/genres/?tipo=movie|tv` entrega nombres localizados para los filtros futuros; sus IDs son estables.

`python manage.py rellenar_traducciones` procesa producciones enriquecidas, por lotes e idempotentemente. Los registros sin `fecha_enriquecimiento` se completan al materializarse. La sincronización diaria reintenta traducciones pendientes; no altera el texto canónico ni el hash de embeddings. En la base revisada el 08/10/2026 no quedan producciones enriquecidas pendientes; las 39 filas sin enriquecer quedan fuera del relleno.

El cliente frontend envía `Accept-Language` en cada solicitud. La localización de TMDB usa `es-MX`, mientras fechas y números de interfaz usan `es-AR`. El chatbot utilizará tools localizadas y responderá en el idioma efectivo; su corpus BGE-M3 conserva el inglés (decisión del 08/10/2026). Su comportamiento durante SSE se revisará en el pair programming del 09/10/2026.
