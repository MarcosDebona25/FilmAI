"""Plataformas donde ver una producción en un país (watch providers de TMDB).

TMDB entrega una sola respuesta con todos los países (`results.AR`, `results.US`…)
y los datos vienen de JustWatch. No hay enlaces directos a cada plataforma: solo
un `link` a la página de TMDB que los lista. Se devuelve un país ya agrupado en
las cuatro categorías de la ficha; `gratis` une `free` y `ads`.
"""

CATEGORIAS = {
    "suscripcion": ("flatrate",),
    "gratis": ("free", "ads"),
    "alquiler": ("rent",),
    "compra": ("buy",),
}


def plataformas(servicio, tipo, id_tmdb, pais):
    datos = servicio.get_watch_providers(id_tmdb, tipo)
    del_pais = (datos.get("results") or {}).get(pais) or {}
    respuesta = {"pais": pais, "enlace": None}
    hay_datos = False
    for categoria, claves in CATEGORIAS.items():
        items = _agrupar(del_pais, claves)
        hay_datos = hay_datos or bool(items)
        respuesta[categoria] = items
    # Sin ninguna plataforma el enlace no lleva a nada útil.
    if hay_datos:
        respuesta["enlace"] = del_pais.get("link") or None
    return respuesta


def _agrupar(del_pais, claves):
    """Ordena por `display_priority` y descarta repetidos (una plataforma puede estar en free y ads)."""
    candidatos = [
        proveedor
        for clave in claves
        for proveedor in del_pais.get(clave) or []
        if proveedor.get("provider_id") is not None and proveedor.get("provider_name")
    ]
    # `sorted` es estable: a igual prioridad se conserva el orden de TMDB.
    candidatos.sort(key=lambda p: p.get("display_priority", 9999))
    vistos = set()
    items = []
    for proveedor in candidatos:
        if proveedor["provider_id"] in vistos:
            continue
        vistos.add(proveedor["provider_id"])
        items.append(
            {
                "id": proveedor["provider_id"],
                "nombre": proveedor["provider_name"],
                "logo": proveedor.get("logo_path"),
            }
        )
    return items
