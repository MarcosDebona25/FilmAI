"""Agrega la lista predeterminada «Viendo» y deja a cada título en un solo estado.

PR 4 (15/11/2026): «Pendientes», «Viendo» y «Vistas» pasan a ser estados
excluyentes de un título (`listas/services.py::poner_estado`). Los datos
anteriores no lo cumplen, así que esta migración los lleva a la regla, en este
orden:

1. Crea la lista «Viendo» en toda cuenta que no la tenga. Si la cuenta ya tenía
   una lista personalizada con ese nombre (`uq_lista_usuario_nombre` no distingue
   mayúsculas), la renombra a «Viendo 2» (o el primer número libre): conserva sus
   ítems y evita que la migración choque.
2. Toda calificación activa cuyo título no está en ningún estado pasa a «Vistas»
   (calificar mueve a Watched). Favoritos no cuenta como estado.
3. Si un título está en «Pendientes» y en «Vistas» a la vez, queda solo en la
   lista donde se agregó último (`fecha_agregado`); con fechas iguales gana
   «Vistas».

Es de datos más un `AlterField` de `choices` (no cambia ninguna columna). Usa los
modelos históricos (`apps.get_model`), no los de `models.py`.

La reversa no hace nada: los pasos 2 y 3 no se pueden deshacer (no hay forma de
distinguir lo que movió la migración de lo que movió el usuario) y la lista
«Viendo» que quede es inocua para el código anterior. Si hay que sacarla, se
borra a mano.
"""

from django.db import migrations, models

NOMBRE = "Viendo"
ESTADOS = ("pendientes", "viendo", "vistas")


def _nombre_libre(nombres_en_uso):
    """«Viendo 2», «Viendo 3»… el primero que el usuario no use (sin distinguir mayúsculas)."""
    numero = 2
    while f"{NOMBRE} {numero}".lower() in nombres_en_uso:
        numero += 1
    return f"{NOMBRE} {numero}"


def crear_listas_viendo(apps, schema_editor):
    Lista = apps.get_model("listas", "Lista")
    Usuario = apps.get_model("usuarios", "Usuario")

    con_viendo = set(
        Lista.objects.filter(clave="viendo", tipo="predeterminada").values_list(
            "usuario_id", flat=True
        )
    )
    for usuario_id in Usuario.objects.exclude(pk__in=con_viendo).values_list(
        "pk", flat=True
    ):
        nombres = {
            nombre.lower()
            for nombre in Lista.objects.filter(usuario_id=usuario_id).values_list(
                "nombre", flat=True
            )
        }
        if NOMBRE.lower() in nombres:
            chocan = Lista.objects.filter(
                usuario_id=usuario_id, nombre__iexact=NOMBRE
            ).first()
            chocan.nombre = _nombre_libre(nombres)
            chocan.save(update_fields=["nombre"])
        Lista.objects.create(
            usuario_id=usuario_id, nombre=NOMBRE, tipo="predeterminada", clave="viendo"
        )


def _listas_de_estado(apps):
    """`{usuario_id: {clave: lista_id}}` de las listas de estado."""
    Lista = apps.get_model("listas", "Lista")
    por_usuario = {}
    for usuario_id, clave, lista_id in Lista.objects.filter(
        tipo="predeterminada", clave__in=ESTADOS
    ).values_list("usuario_id", "clave", "pk"):
        por_usuario.setdefault(usuario_id, {})[clave] = lista_id
    return por_usuario


def calificadas_a_vistas(apps, schema_editor):
    Calificacion = apps.get_model("catalogo", "Calificacion")
    Tiene = apps.get_model("listas", "Tiene")

    listas = _listas_de_estado(apps)
    con_estado = set(
        Tiene.objects.filter(
            lista__tipo="predeterminada", lista__clave__in=ESTADOS
        ).values_list("lista__usuario_id", "produccion_id")
    )
    nuevos = []
    for usuario_id, produccion_id in Calificacion.objects.filter(
        activa=True
    ).values_list("usuario_id", "produccion_id"):
        vistas = listas.get(usuario_id, {}).get("vistas")
        # Sin «Vistas» el estado de la cuenta está roto (lo repara
        # `reparar_recursos_usuarios`): se la saltea en vez de abortar.
        if vistas is not None and (usuario_id, produccion_id) not in con_estado:
            nuevos.append(Tiene(lista_id=vistas, produccion_id=produccion_id))
    # `ignore_conflicts`: correrla dos veces no duplica (`uq_tiene_lista_produccion`).
    Tiene.objects.bulk_create(nuevos, ignore_conflicts=True, batch_size=1000)


def una_sola_lista_de_estado(apps, schema_editor):
    Tiene = apps.get_model("listas", "Tiene")

    # Todos los ítems de estado, de a dos por título como mucho (Viendo es nueva).
    # Se agrupan por (usuario, título) y se conserva el más reciente.
    elegidos = {}
    a_borrar = []
    filas = Tiene.objects.filter(
        lista__tipo="predeterminada", lista__clave__in=ESTADOS
    ).values_list("pk", "lista__usuario_id", "produccion_id", "lista__clave", "fecha_agregado")
    for pk, usuario_id, produccion_id, clave, fecha in filas:
        llave = (usuario_id, produccion_id)
        # La tupla ordena por fecha y, a igual fecha, «vistas» le gana a las demás.
        candidato = (fecha, clave == "vistas", pk)
        previo = elegidos.get(llave)
        if previo is None:
            elegidos[llave] = candidato
        elif candidato > previo:
            a_borrar.append(previo[2])
            elegidos[llave] = candidato
        else:
            a_borrar.append(pk)
    for inicio in range(0, len(a_borrar), 1000):
        Tiene.objects.filter(pk__in=a_borrar[inicio : inicio + 1000]).delete()


def aplicar(apps, schema_editor):
    crear_listas_viendo(apps, schema_editor)
    calificadas_a_vistas(apps, schema_editor)
    una_sola_lista_de_estado(apps, schema_editor)


def revertir(apps, schema_editor):
    """No deshace nada: ver el docstring del módulo."""


class Migration(migrations.Migration):
    dependencies = [
        ("catalogo", "0008_lapida_tmdb"),
        ("listas", "0008_lapida_tmdb"),
        ("usuarios", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="lista",
            name="clave",
            field=models.CharField(
                blank=True,
                choices=[
                    ("favoritos", "Favoritos"),
                    ("pendientes", "Pendientes"),
                    ("viendo", "Viendo"),
                    ("vistas", "Vistas"),
                ],
                max_length=25,
                null=True,
                verbose_name="clave",
            ),
        ),
        migrations.RunPython(aplicar, revertir),
    ]
