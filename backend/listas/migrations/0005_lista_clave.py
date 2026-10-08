"""Identifica las listas existentes sin cambiar nombres ni relaciones."""

from django.db import migrations, models
from django.db.models.functions import Lower


CLAVES = ("favoritos", "pendientes", "vistas")


def completar_claves(apps, schema_editor):
    Lista = apps.get_model("listas", "Lista")
    predeterminadas = (
        Lista.objects.using(schema_editor.connection.alias)
        .filter(tipo="predeterminada")
        .annotate(nombre_normalizado=Lower("nombre"))
    )
    desconocidas = list(
        predeterminadas.exclude(nombre_normalizado__in=CLAVES)
        .order_by("pk")
        .values_list("pk", "nombre")
    )
    if desconocidas:
        raise RuntimeError(
            "No se pueden asignar claves a listas predeterminadas con nombres "
            f"desconocidos (id, nombre): {desconocidas!r}. "
            "Corregí los nombres antes de repetir la migración."
        )
    for clave in CLAVES:
        predeterminadas.filter(nombre_normalizado=clave).update(clave=clave)


def vaciar_claves(apps, schema_editor):
    Lista = apps.get_model("listas", "Lista")
    Lista.objects.using(schema_editor.connection.alias).update(clave=None)


class Migration(migrations.Migration):
    dependencies = [("listas", "0004_calificadas_en_vistas")]

    operations = [
        migrations.AddField(
            model_name="lista",
            name="clave",
            field=models.CharField(
                "clave",
                max_length=25,
                choices=[
                    ("favoritos", "Favoritos"),
                    ("pendientes", "Pendientes"),
                    ("vistas", "Vistas"),
                ],
                null=True,
                blank=True,
            ),
        ),
        migrations.RunPython(completar_claves, vaciar_claves),
    ]
