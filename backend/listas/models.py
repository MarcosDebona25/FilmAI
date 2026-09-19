"""
Modelos de la app `listas`.

Implementa las listas de contenidos del usuario y la tabla intermedia `Tiene`
que materializa la relación N:N entre `Lista` y `ProduccionAudiovisual`
(doc 03, Modelo 2):

    Lista  ──<  Tiene  >──  ProduccionAudiovisual
     │
     └── Usuario (FK a usuarios.Usuario)

`Tiene` registra `fechaAgregado` (TIMESTAMP) y su PK compuesta (idLista,
idProduccion) se modela en Django como una restricción de unicidad compuesta,
lo que impide que una misma producción se repita dentro de una lista.
"""

from django.db import models
from django.db.models.functions import Lower


class TipoLista(models.TextChoices):
    """Tipo de lista (doc 03: 'Predeterminada' | 'Personalizada')."""

    PREDETERMINADA = "predeterminada", "Predeterminada"
    PERSONALIZADA = "personalizada", "Personalizada"


class Lista(models.Model):
    """Lista de producciones de un usuario.

    Cada usuario tiene por defecto las listas predeterminadas (Favoritos,
    Pendientes, Vistas), que no pueden eliminarse, y puede crear listas
    personalizadas adicionales (doc 03, CU-009/CU-012).
    """

    nombre = models.CharField("nombre", max_length=80)
    tipo = models.CharField(
        "tipo",
        max_length=25,
        choices=TipoLista.choices,
        default=TipoLista.PERSONALIZADA,
    )
    activa = models.BooleanField("activa", default=True)
    usuario = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.CASCADE,
        related_name="listas",
        verbose_name="usuario",
    )
    producciones = models.ManyToManyField(
        "catalogo.ProduccionAudiovisual",
        through="Tiene",
        related_name="listas",
        verbose_name="producciones",
    )

    class Meta:
        db_table = "lista"
        verbose_name = "lista"
        verbose_name_plural = "listas"
        ordering = ["id"]
        constraints = [
            # El nombre de lista es único por usuario sin distinguir
            # mayúsculas/minúsculas (CU-012).
            models.UniqueConstraint(
                Lower("nombre"),
                "usuario",
                name="uq_lista_usuario_nombre",
            ),
        ]

    def __str__(self):
        return self.nombre


class Tiene(models.Model):
    """Tabla intermedia N:N entre `Lista` y `ProduccionAudiovisual`.

    Registra el momento (`fecha_agregado`) en que una producción fue añadida a
    una lista. La unicidad (lista, produccion) garantiza que una producción no
    se repita dentro de la misma lista (doc 03, PK compuesta idLista+idProduccion).
    """

    lista = models.ForeignKey(
        Lista,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="lista",
    )
    produccion = models.ForeignKey(
        "catalogo.ProduccionAudiovisual",
        on_delete=models.CASCADE,
        related_name="+",
        verbose_name="producción audiovisual",
    )
    fecha_agregado = models.DateTimeField("fecha de agregado", auto_now_add=True)

    class Meta:
        db_table = "tiene"
        verbose_name = "ítem de lista"
        verbose_name_plural = "ítems de lista"
        ordering = ["fecha_agregado"]
        constraints = [
            models.UniqueConstraint(
                fields=["lista", "produccion"],
                name="uq_tiene_lista_produccion",
            ),
        ]

    def __str__(self):
        return f"{self.lista} → {self.produccion}"
