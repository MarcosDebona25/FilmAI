from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):
    dependencies = [("usuarios", "0004_alter_usuario_avatar_id_alter_usuario_correo_and_more")]

    operations = [
        migrations.AddConstraint(
            model_name="usuario",
            constraint=models.UniqueConstraint(Lower("nombre_usuario"), name="usuario_nombre_ci_unique"),
        ),
    ]
