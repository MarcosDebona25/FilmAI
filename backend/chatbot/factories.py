"""
Factories de factory_boy para la app `chatbot`.

Se usan únicamente para sembrar datos de desarrollo (`python manage.py seed`).
"""

import factory

from usuarios.factories import UsuarioFactory

from .models import Chat, Mensaje, TipoAutor


class ChatFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Chat

    titulo = "Recomendaciones"
    contexto = factory.LazyFunction(dict)
    activo = True
    usuario = factory.SubFactory(UsuarioFactory)


class MensajeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Mensaje

    texto = factory.Faker("sentence", nb_words=12)
    autor = factory.Iterator(TipoAutor.values)
    chat = factory.SubFactory(ChatFactory)
