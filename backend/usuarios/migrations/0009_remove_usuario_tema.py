from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0008_fecha_aceptacion_terminos'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='usuario',
            name='tema',
        ),
    ]
