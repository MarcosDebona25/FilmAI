"""Factories de usuarios para desarrollo y pruebas."""

import factory
from django.utils import timezone

from .avatares import AVATAR_IDS_VALIDOS
from .models import EstadoCuenta, TipoGenero, Usuario
from .paises import pais_por_indice


class UsuarioFactory(factory.django.DjangoModelFactory):
    """Crea usuarios activos con contraseña hasheada."""

    class Meta:
        model = Usuario

    nombre_usuario = factory.Sequence(lambda n: f"usuario{n:03d}")
    correo = factory.LazyAttribute(lambda o: f"{o.nombre_usuario}@filmai.com")
    nombre = factory.Faker("first_name", locale="es")
    apellido = factory.Faker("last_name", locale="es")
    fecha_nacimiento = factory.Faker("date_of_birth", minimum_age=18, maximum_age=60)
    genero = factory.Iterator(TipoGenero.values)
    estado = EstadoCuenta.ACTIVA
    avatar_id = factory.Faker(
        "random_element", elements=tuple(sorted(AVATAR_IDS_VALIDOS))
    )
    # Misma rotación que la migración y el seed: determinista y variada.
    pais = factory.Sequence(pais_por_indice)
    # Toda cuenta nueva acepta los términos al registrarse; el seed hereda esto.
    fecha_aceptacion_terminos = factory.LazyFunction(timezone.now)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop("password", "Password123!")
        return model_class.objects.create_user(password=password, **kwargs)
