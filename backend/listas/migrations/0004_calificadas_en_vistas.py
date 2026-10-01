"""Pone en «Vistas» toda producción ya calificada (regla del 30/09/2026).

Desde el 30/09 calificar agrega a «Vistas» y borrar la calificación la saca
(`listas/services.py`). Las calificaciones creadas antes —por la API de C-08 o
por `seed --solo-resenas`— no tienen su ítem: esta migración las repara una
sola vez en cada base, al correr `migrate`.

Es de datos, no de esquema: no cambia ninguna tabla. Usa los modelos
históricos (`apps.get_model`) y no los de `models.py`, porque una migración
tiene que seguir funcionando aunque esos modelos cambien después.

El reverse no hace nada: al revertir no hay forma de distinguir los ítems que
agregó esta migración de los que el usuario marcó a mano.
"""

from django.db import migrations


def poner_calificadas_en_vistas(apps, schema_editor):
    Calificacion = apps.get_model("catalogo", "Calificacion")
    Lista = apps.get_model("listas", "Lista")
    Tiene = apps.get_model("listas", "Tiene")

    vistas_por_usuario = dict(
        Lista.objects.filter(nombre="Vistas", tipo="predeterminada").values_list(
            "usuario_id", "id"
        )
    )
    # Un usuario sin «Vistas» tiene el estado roto de antes (lo repara
    # `reparar_recursos_usuarios`); se lo saltea en vez de abortar la migración.
    items = [
        Tiene(lista_id=vistas_por_usuario[usuario_id], produccion_id=produccion_id)
        for usuario_id, produccion_id in Calificacion.objects.values_list(
            "usuario_id", "produccion_id"
        )
        if usuario_id in vistas_por_usuario
    ]
    # `ignore_conflicts`: lo que ya estaba en «Vistas» choca con
    # `uq_tiene_lista_produccion` y se saltea, en vez de abortar la migración.
    Tiene.objects.bulk_create(items, ignore_conflicts=True, batch_size=1000)


class Migration(migrations.Migration):
    dependencies = [
        ("catalogo", "0005_produccionaudiovisual_fecha_enriquecimiento"),
        ("listas", "0003_lista_nombre_case_insensitive"),
    ]

    operations = [
        migrations.RunPython(poner_calificadas_en_vistas, migrations.RunPython.noop),
    ]
