# Generated manually for L-01 on 2026-09-19.

from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):
    dependencies = [
        ("listas", "0002_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="lista",
            name="uq_lista_usuario_nombre",
        ),
        migrations.AddConstraint(
            model_name="lista",
            constraint=models.UniqueConstraint(
                Lower("nombre"),
                "usuario",
                name="uq_lista_usuario_nombre",
            ),
        ),
    ]
