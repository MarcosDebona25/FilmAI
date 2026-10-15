"""Créditos de la ficha (C-07): directores y reparto con personaje.

En películas los directores salen del equipo (`job == "Director"`). En series
ese rol no existe a nivel serie —los directores son por episodio— y se usan los
creadores (`created_by`) del detalle, como ya hace la materialización de C-04a.
Verificado contra TMDB el 13/10/2026 con Breaking Bad.
"""

MAX_REPARTO = 50


def creditos(servicio, tipo, id_tmdb):
    datos = servicio.get_credits(id_tmdb, tipo)
    if tipo == "movie":
        directores = [
            persona["name"]
            for persona in datos.get("crew") or []
            if persona.get("job") == "Director" and persona.get("name")
        ]
    else:
        detalle = servicio.get_tv_detail(id_tmdb)
        directores = [
            persona["name"]
            for persona in detalle.get("created_by") or []
            if persona.get("name")
        ]
    reparto = [
        {"nombre": persona["name"], "personaje": persona.get("character") or ""}
        for persona in (datos.get("cast") or [])[:MAX_REPARTO]
        if persona.get("name")
    ]
    return {"directores": directores, "reparto": reparto}
