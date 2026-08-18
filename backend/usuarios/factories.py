"""
Factories de factory_boy para la app `usuarios`.

Se usan únicamente para sembrar datos de desarrollo (`python manage.py seed`).
"""

import factory

from .models import EstadoCuenta, Tema, TipoGenero, Usuario


class UsuarioFactory(factory.django.DjangoModelFactory):
    """Crea un `Usuario` con estado Activa y una contraseña por defecto.

    La contraseña se aplica a través de `UsuarioManager.create_user` para que
    quede correctamente hasheada: el campo `password` (heredado de
    `AbstractBaseUser`) no se hashea con un `create` directo.
    """

    class Meta:
        model = Usuario

    nombre_usuario = factory.Sequence(lambda n: f"usuario{n:03d}")
    correo = factory.LazyAttribute(lambda o: f"{o.nombre_usuario}@filmia.com")
    nombre = factory.Faker("first_name", locale="es")
    apellido = factory.Faker("last_name", locale="es")
    fecha_nacimiento = factory.Faker("date_of_birth", minimum_age=18, maximum_age=60)
    genero = factory.Iterator(TipoGenero.values)
    estado = EstadoCuenta.ACTIVA
    avatar_id = factory.Faker("random_int", min=1, max=20)
    tema = Tema.OSCURO

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "Password123!")
        return model_class.objects.create_user(password=password, **kwargs)
