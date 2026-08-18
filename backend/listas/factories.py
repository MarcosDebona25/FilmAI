"""
Factories de factory_boy para la app `listas`.

Se usan únicamente para sembrar datos de desarrollo (`python manage.py seed`).
"""

import factory

from usuarios.factories import UsuarioFactory

from .models import Lista, TipoLista


class ListaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Lista

    nombre = factory.Sequence(lambda n: f"Mi lista {n:02d}")
    tipo = TipoLista.PERSONALIZADA
    activa = True
    usuario = factory.SubFactory(UsuarioFactory)
