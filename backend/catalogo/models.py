"""
Modelos de la app `catalogo`.

Implementa las entidades del dominio de contenidos audiovisuales (doc 03):

    ProduccionAudiovisual  ──<  Calificacion  ──<  Reseña
                                 │
                                 └── Usuario (FK a usuarios.Usuario)

`ProduccionAudiovisual` unifica películas y series en una única entidad con un
atributo `tipo`, tal como lo justifica el doc 03 (los IDs de TMDB no garantizan
unicidad entre películas y series, por lo que no se modelan subclases).

`Reseña` se modela como composición 1:1 con `Calificacion`: una calificación
puede existir sin reseña, pero una reseña no puede existir sin su calificación.
"""

from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class TipoProduccion(models.TextChoices):
    """Tipo de producción audiovisual (doc 03: 'Pelicula' | 'Serie')."""

    PELICULA = "pelicula", "Película"
    SERIE = "serie", "Serie"


class ProduccionAudiovisual(models.Model):
    """Catálogo unificado de películas y series sincronizado desde TMDB (CU-021).

    Los campos `reparto`, `directores` y `generos` se almacenan como arreglos
    nativos de PostgreSQL (VARCHAR[] en el diagrama de tablas).
    """

    id_tmdb = models.IntegerField(
        "id TMDB",
        help_text="Identificador de la producción en la API de TMDB.",
    )
    tipo = models.CharField("tipo", max_length=25, choices=TipoProduccion.choices)
    titulo = models.CharField("título", max_length=100)
    poster = models.CharField("póster", max_length=250, blank=True, default="")
    sinopsis = models.CharField("sinopsis", max_length=2000, blank=True, default="")
    fecha_lanzamiento = models.DateField("fecha de lanzamiento", null=True, blank=True)
    reparto = ArrayField(
        models.CharField(max_length=100),
        blank=True,
        default=list,
        verbose_name="reparto",
    )
    directores = ArrayField(
        models.CharField(max_length=100),
        blank=True,
        default=list,
        verbose_name="directores",
    )
    estatus = models.CharField("estatus", max_length=25, blank=True, default="")
    generos = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        default=list,
        verbose_name="géneros",
    )
    calificacion_promedio = models.FloatField(
        "calificación promedio (TMDB)", null=True, blank=True
    )
    cantidad_temporadas = models.IntegerField(
        "cantidad de temporadas", null=True, blank=True
    )
    cantidad_episodios = models.IntegerField(
        "cantidad de episodios", null=True, blank=True
    )
    duracion = models.IntegerField("duración (minutos)", null=True, blank=True)

    class Meta:
        db_table = "produccion_audiovisual"
        verbose_name = "producción audiovisual"
        verbose_name_plural = "producciones audiovisuales"
        ordering = ["titulo"]
        constraints = [
            # Los IDs de TMDB no son únicos entre películas y series (doc 03),
            # por lo que la unicidad es por par (id_tmdb, tipo).
            models.UniqueConstraint(
                fields=["id_tmdb", "tipo"],
                name="uq_produccion_tmdb_tipo",
            ),
        ]

    def __str__(self):
        return f"{self.titulo} ({self.get_tipo_display()})"


class Calificacion(models.Model):
    """Calificación numérica (1-10) que un usuario asigna a una producción (CU-015)."""

    valor = models.IntegerField(
        "valor",
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Rango permitido: 1 a 10 (CU-015).",
    )
    fecha = models.DateField("fecha", auto_now_add=True)
    activa = models.BooleanField("activa", default=True)
    usuario = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.CASCADE,
        related_name="calificaciones",
        verbose_name="usuario",
    )
    produccion = models.ForeignKey(
        ProduccionAudiovisual,
        on_delete=models.CASCADE,
        related_name="calificaciones",
        verbose_name="producción audiovisual",
    )

    class Meta:
        db_table = "calificacion"
        verbose_name = "calificación"
        verbose_name_plural = "calificaciones"
        ordering = ["-fecha", "-id"]
        constraints = [
            # Un usuario califica una misma producción una única vez (CU-015).
            models.UniqueConstraint(
                fields=["usuario", "produccion"],
                name="uq_calificacion_usuario_produccion",
            ),
            models.CheckConstraint(
                check=models.Q(valor__gte=1, valor__lte=10),
                name="ck_calificacion_valor_rango",
            ),
        ]

    def __str__(self):
        return f"{self.usuario} → {self.produccion} ({self.valor}/10)"


class Resena(models.Model):
    """Texto opcional asociado a una calificación (composición 1:1, CU-015)."""

    texto = models.CharField("texto", max_length=1000)
    fecha = models.DateField("fecha", auto_now_add=True)
    activa = models.BooleanField("activa", default=True)
    calificacion = models.OneToOneField(
        Calificacion,
        on_delete=models.CASCADE,
        related_name="resena",
        verbose_name="calificación",
    )

    class Meta:
        db_table = "resena"
        verbose_name = "reseña"
        verbose_name_plural = "reseñas"
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"Reseña de {self.calificacion.usuario} sobre {self.calificacion.produccion}"
