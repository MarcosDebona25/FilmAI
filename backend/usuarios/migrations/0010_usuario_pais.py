from django.db import migrations, models

# Misma rotación que `usuarios.paises.ROTACION`, copiada: una migración no debe
# depender de código que puede cambiar después.
ROTACION = ["AR", "BR", "US", "ES", "GB", "PT", "CN", "MX"]


def asignar_paises(apps, schema_editor):
    Usuario = apps.get_model("usuarios", "Usuario")
    for usuario in Usuario.objects.all().iterator():
        usuario.pais = ROTACION[usuario.pk % len(ROTACION)]
        usuario.save(update_fields=["pais"])


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0009_remove_usuario_tema'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='pais',
            field=models.CharField(
                max_length=2,
                null=True,
                verbose_name='país',
                help_text='Código ISO 3166-1 alfa-2 (lista en contracts/enums.json)',
            ),
        ),
        migrations.RunPython(asignar_paises, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='usuario',
            name='pais',
            field=models.CharField(
                max_length=2,
                verbose_name='país',
                help_text='Código ISO 3166-1 alfa-2 (lista en contracts/enums.json)',
            ),
        ),
    ]
