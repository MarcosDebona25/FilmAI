"""Sugerencias de la navbar (13/11/2026): títulos y personas con una sola llamada.

`GET /api/catalogo/suggest/?q=` usa `search/multi` de TMDB, que busca
películas, series y personas a la vez. El diseño está en
`openspec/changes/busqueda-navbar/design.md` (§1).

Se conserva el orden de TMDB (la relevancia por nombre ya pone a «Christopher
Nolan» primero con «nolan» y a «Dune» primero con «dune»), pero se limpia:

- Títulos: solo los que pasan el corte de relevancia de Buscar (`es_relevante`).
  Si ninguno pasa, los títulos como vienen, igual que en la grilla.
- Personas: solo de `Acting` o `Directing` y con popularidad 1 o más (saca a
  «Nolan Yee», 0,1). Como mucho 2, para que no tapen a los títulos.
- Como mucho 5 en total. Con `tipo="person"` (el campo «Persona» de los
  filtros), solo personas y hasta 5.
"""

from catalogo.services.browse import es_relevante

MAX_SUGERENCIAS = 5
MAX_PERSONAS = 2
# Popularidad mínima de una persona (medido el 13/11/2026: «Nolan Yee» 0,1 y
# «Chihiro Yoshioka» 0,4 quedan afuera; «Nolan North», 2,2, entra).
MIN_POPULARIDAD_PERSONA = 1
# `known_for_department` de TMDB → el rol que se muestra y se manda a Buscar.
# Guion, producción y demás quedan afuera de la v1 (pregunta Q-3 de la propuesta).
ROLES = {"Acting": "actor", "Directing": "director"}

# Los campos de cada título que usa el frontend (`normalizeTitles`).
CAMPOS_PELICULA = ("title", "release_date")
CAMPOS_SERIE = ("name", "first_air_date")


def sugerir(servicio, q, tipo="all"):
    """Hasta 5 sugerencias para el texto `q`, en el orden de TMDB."""
    datos = servicio.search_multi(q, 1)
    resultados = datos.get("results") or []

    personas = [p for p in map(_persona, resultados) if p is not None]
    if tipo == "person":
        return {"results": personas[:MAX_SUGERENCIAS]}

    personas = personas[:MAX_PERSONAS]
    titulos = [item for item in resultados if item.get("media_type") in ("movie", "tv")]
    pasan = [item for item in titulos if es_relevante(item, q)]
    elegidos = _combinar(resultados, pasan or titulos, personas)[:MAX_SUGERENCIAS]
    # El español completa los títulos vacíos con el inglés, solo de los que se
    # muestran (los servicios de inglés no tienen este método: no hace falta).
    completar = getattr(servicio, "completar_titulos", None)
    titulos_elegidos = [item for item in elegidos if item["media_type"] != "person"]
    if completar is not None:
        completar(titulos_elegidos, "search_multi", q, 1)
    return {
        "results": [
            item if item["media_type"] == "person" else _titulo(item)
            for item in elegidos
        ]
    }


def _persona(item):
    """La persona como la usa el frontend, o `None` si no se sugiere."""
    if item.get("media_type") != "person":
        return None
    rol = ROLES.get(item.get("known_for_department"))
    if rol is None or (item.get("popularity") or 0) < MIN_POPULARIDAD_PERSONA:
        return None
    return {
        "media_type": "person",
        "id": item["id"],
        "name": item.get("name") or "",
        "rol": rol,
        "gender": item.get("gender"),
        "profile_path": item.get("profile_path"),
    }


def _combinar(originales, titulos, personas):
    """Títulos y personas elegidos, en el orden en que TMDB los devolvió."""
    claves = {("person", p["id"]): p for p in personas}
    claves.update({(t["media_type"], t["id"]): t for t in titulos})
    orden = [(i.get("media_type"), i.get("id")) for i in originales]
    return [claves[clave] for clave in orden if clave in claves]


def _titulo(item):
    """Solo los campos de TMDB que el frontend usa para dibujar la sugerencia."""
    fecha = CAMPOS_PELICULA if item["media_type"] == "movie" else CAMPOS_SERIE
    campos = ("media_type", "id", *fecha, "poster_path", "vote_average")
    salida = {campo: item.get(campo) for campo in campos}
    if item.get("campos_en_ingles"):
        salida["campos_en_ingles"] = item["campos_en_ingles"]
    return salida
