"""
Factories de factory_boy para la app `catalogo`.

Se usan únicamente para sembrar datos de desarrollo (`python manage.py seed`).
"""

import random

import factory
from faker import Faker

from usuarios.factories import UsuarioFactory

from .models import Calificacion, ProduccionAudiovisual, Resena, TipoProduccion

fake = Faker("es")

GENEROS = [
    "Acción",
    "Aventura",
    "Animación",
    "Comedia",
    "Crimen",
    "Documental",
    "Drama",
    "Fantasía",
    "Terror",
    "Romance",
    "Ciencia ficción",
    "Suspenso",
]


def _lista_nombres(cantidad_min=3, cantidad_max=8):
    return [fake.name() for _ in range(random.randint(cantidad_min, cantidad_max))]


class ProduccionAudiovisualFactory(factory.django.DjangoModelFactory):
    """Crea una producción audiovisual simulando un registro de TMDB.

    Los campos de serie (`cantidad_temporadas`, `cantidad_episodios`) y de
    película (`duracion`) se rellenan según `tipo` para mantener los datos
    consistentes con el dominio.
    """

    class Meta:
        model = ProduccionAudiovisual

    id_tmdb = factory.Sequence(lambda n: n + 1)
    tipo = factory.Iterator(TipoProduccion.values)
    titulo = factory.LazyFunction(lambda: fake.sentence(nb_words=3).rstrip(".").title())
    poster = factory.Faker("image_url", width=300, height=450)
    sinopsis = factory.Faker("paragraph", nb_sentences=3)
    fecha_lanzamiento = factory.Faker(
        "date_between", start_date="-25y", end_date="today"
    )
    reparto = factory.LazyFunction(_lista_nombres)
    directores = factory.LazyFunction(
        lambda: [fake.name() for _ in range(random.randint(1, 2))]
    )
    estatus = "Released"
    generos = factory.LazyFunction(lambda: random.sample(GENEROS, random.randint(1, 3)))
    calificacion_promedio = factory.Faker(
        "pyfloat",
        left_digits=1,
        right_digits=1,
        positive=True,
        min_value=1,
        max_value=10,
    )
    cantidad_temporadas = factory.LazyAttribute(
        lambda o: random.randint(1, 8) if o.tipo == TipoProduccion.SERIE else None
    )
    cantidad_episodios = factory.LazyAttribute(
        lambda o: random.randint(6, 24) if o.tipo == TipoProduccion.SERIE else None
    )
    duracion = factory.LazyAttribute(
        lambda o: random.randint(80, 180) if o.tipo == TipoProduccion.PELICULA else None
    )


class CalificacionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Calificacion

    valor = factory.Faker("random_int", min=1, max=10)
    activa = True
    usuario = factory.SubFactory(UsuarioFactory)
    produccion = factory.SubFactory(ProduccionAudiovisualFactory)


class ResenaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Resena

    texto = factory.Faker("paragraph", nb_sentences=2)
    activa = True
    calificacion = factory.SubFactory(CalificacionFactory)
