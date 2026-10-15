"""Agrega `Lista.orden` para reordenar las listas personalizadas (L-02).

Las existentes conservan el orden que ya mostraban (por id) dentro de cada
usuario; las predeterminadas quedan en 0 porque su lugar es fijo.
"""

from django.db import migrations, models


def numerar_personalizadas(apps, schema_editor):
    Lista = apps.get_model("listas", "Lista")
    consulta = Lista.objects.using(schema_editor.connection.alias)
    cambios = []
    posicion_por_usuario = {}
    for lista in consulta.filter(tipo="personalizada").order_by("usuario_id", "id"):
        posicion = posicion_por_usuario.get(lista.usuario_id, 0) + 1
        posicion_por_usuario[lista.usuario_id] = posicion
        lista.orden = posicion
        cambios.append(lista)
    consulta.bulk_update(cambios, ["orden"], batch_size=500)


class Migration(migrations.Migration):
    dependencies = [
        ("listas", "0006_lista_restricciones_clave"),
    ]

    operations = [
        migrations.AddField(
            model_name="lista",
            name="orden",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Posición de una lista personalizada en «Lists» (L-02). "
                "Las predeterminadas van siempre primero en orden fijo y no lo "
                "usan; las nuevas entran al final. Empates (datos viejos) se "
                "desempatan por id.",
                verbose_name="orden",
            ),
        ),
        migrations.RunPython(numerar_personalizadas, migrations.RunPython.noop),
    ]
