"""Activa la extensión `unaccent` de Postgres (15/10/2026).

«Mis reseñas» busca por título sin distinguir acentos: «amelie» encuentra
«Amélie». La comparación la hace la base (`titulo__unaccent__icontains`),
porque con paginación por cursor no se puede filtrar del lado de Python.
"""

from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("catalogo", "0006_traducciones_y_generos_ids")]

    operations = [UnaccentExtension()]
