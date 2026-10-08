"""Contrae el diseño de `clave`: unicidad por usuario y coherencia con `tipo`."""

from django.db import migrations, models
from django.db.models import Count, Q


def verificar_datos(apps, schema_editor):
    """Falla con un mensaje claro en vez de con un error opaco de la base."""
    Lista = apps.get_model("listas", "Lista")
    consulta = Lista.objects.using(schema_editor.connection.alias)
    sin_clave = list(
        consulta.filter(tipo="predeterminada", clave__isnull=True).values_list(
            "pk", "usuario_id"
        )
    )
    con_clave = list(
        consulta.filter(tipo="personalizada", clave__isnull=False).values_list(
            "pk", "usuario_id"
        )
    )
    repetidas = list(
        consulta.filter(clave__isnull=False)
        .values("usuario_id", "clave")
        .annotate(total=Count("pk"))
        .filter(total__gt=1)
        .values_list("usuario_id", "clave", "total")
    )
    problemas = []
    if sin_clave:
        problemas.append(f"predeterminadas sin clave (id, usuario): {sin_clave!r}")
    if con_clave:
        problemas.append(f"personalizadas con clave (id, usuario): {con_clave!r}")
    if repetidas:
        problemas.append(f"claves repetidas (usuario, clave, total): {repetidas!r}")
    if problemas:
        raise RuntimeError(
            "No se pueden agregar las restricciones de clave: "
            + "; ".join(problemas)
            + ". Corregí los datos antes de repetir la migración."
        )


class Migration(migrations.Migration):
    dependencies = [("listas", "0005_lista_clave")]

    operations = [
        migrations.RunPython(verificar_datos, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="lista",
            constraint=models.UniqueConstraint(
                fields=("usuario", "clave"),
                condition=Q(clave__isnull=False),
                name="uq_lista_usuario_clave",
            ),
        ),
        migrations.AddConstraint(
            model_name="lista",
            constraint=models.CheckConstraint(
                condition=(
                    Q(tipo="predeterminada", clave__isnull=False)
                    | Q(tipo="personalizada", clave__isnull=True)
                ),
                name="ck_lista_tipo_clave",
            ),
        ),
    ]
