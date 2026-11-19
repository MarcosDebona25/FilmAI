"""Créditos de la ficha (C-07): directores y reparto con personaje.

En películas los directores salen del equipo (`job == "Director"`). En series
ese rol no existe a nivel serie —los directores son por episodio— y se usan los
creadores (`created_by`) del detalle, como ya hace la materialización de C-04a.
Verificado contra TMDB el 13/10/2026 con Breaking Bad.

Cada persona lleva su `id` de TMDB (15/11/2026): con él la ficha enlaza el
nombre a Buscar filtrado por esa persona. Si falta, va `None` y el nombre queda
como texto.
"""

MAX_REPARTO = 50


def id_de_persona(persona):
    """El `id` de TMDB de la persona, o `None` si no vino o no es un entero."""
    valor = persona.get("id")
    # `bool` es subclase de `int` en Python: un `True` no es un id.
    return valor if isinstance(valor, int) and not isinstance(valor, bool) else None


def creditos(servicio, tipo, id_tmdb):
    datos = servicio.get_credits(id_tmdb, tipo)
    if tipo == "movie":
        personas = [
            persona
            for persona in datos.get("crew") or []
            if persona.get("job") == "Director"
        ]
    else:
        personas = servicio.get_tv_detail(id_tmdb).get("created_by") or []
    directores = [
        {"id": id_de_persona(persona), "nombre": persona["name"]}
        for persona in personas
        if persona.get("name")
    ]
    reparto = [
        {
            "id": id_de_persona(persona),
            "nombre": persona["name"],
            "personaje": persona.get("character") or "",
        }
        for persona in (datos.get("cast") or [])[:MAX_REPARTO]
        if persona.get("name")
    ]
    return {"directores": directores, "reparto": reparto}
