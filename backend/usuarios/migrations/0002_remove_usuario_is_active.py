from django.db import migrations


class Migration(migrations.Migration):
    """Elimina la columna huérfana `is_active` (docs/decisiones.md, 22/08/2026).

    `is_active` dejó de ser un campo de BD: ahora es una propiedad derivada de
    `estado` (Opción A1). La columna creada en 0001_initial quedó sin
    correspondencia con el modelo, por lo que se elimina.
    """

    dependencies = [
        ("usuarios", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="usuario",
            name="is_active",
        ),
    ]
