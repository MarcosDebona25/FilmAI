from django.db import migrations


def normalizar_nombres(apps, schema_editor):
    Usuario = apps.get_model("usuarios", "Usuario")
    for usuario in Usuario.objects.all().iterator():
        nombre = " ".join(usuario.nombre.split())
        apellido = " ".join(usuario.apellido.split())
        if nombre != usuario.nombre or apellido != usuario.apellido:
            Usuario.objects.filter(pk=usuario.pk).update(nombre=nombre, apellido=apellido)


class Migration(migrations.Migration):
    dependencies = [("usuarios", "0005_usuario_nombre_ci_unique")]

    operations = [migrations.RunPython(normalizar_nombres, migrations.RunPython.noop)]
