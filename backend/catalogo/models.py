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
from pgvector.django import HnswIndex, VectorField


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
    generos_ids = ArrayField(
        models.IntegerField(),
        blank=True,
        default=list,
        verbose_name="ids de géneros (TMDB)",
        help_text="Ids de TMDB de los géneros. La etiqueta se resuelve por "
        "idioma con la lista de géneros; `generos` conserva los nombres en "
        "inglés que usa el texto canónico de los embeddings.",
    )
    keywords = ArrayField(
        models.CharField(max_length=50),
        blank=True,
        default=list,
        verbose_name="keywords",
        help_text="Keywords temáticos de TMDB sincronizados en C-04 "
        "(/movie/{id}/keywords, /tv/{id}/keywords). Forman parte del texto a "
        "embeber para la búsqueda semántica (B-06, doc 03).",
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
    fecha_enriquecimiento = models.DateTimeField(
        "fecha de enriquecimiento",
        null=True,
        blank=True,
        help_text="Cuándo se trajo por última vez el detalle completo de TMDB "
        "(detalle + créditos + keywords). Nulo significa que la fila nunca se "
        "enriqueció: puede haber nacido de un listado, que trae título pero no "
        "géneros, reparto ni keywords. La sync diaria (C-04b) refresca lo que "
        "TMDB reporta como cambiado; esta fecha es además la red de seguridad "
        "si esa lista se pierde.",
    )

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


class ProduccionTraduccion(models.Model):
    """Textos de una producción en un idioma distinto del canónico (inglés).

    `ProduccionAudiovisual` sigue en inglés porque de ahí sale el corpus de
    embeddings. Acá va lo que la interfaz muestra en otro idioma. Un campo
    vacío significa "TMDB no tiene esa traducción": quien lee cae al canónico.
    """

    produccion = models.ForeignKey(
        ProduccionAudiovisual,
        on_delete=models.CASCADE,
        related_name="traducciones",
        verbose_name="producción audiovisual",
    )
    idioma = models.CharField("idioma", max_length=5)
    titulo = models.CharField("título", max_length=100, blank=True, default="")
    sinopsis = models.CharField("sinopsis", max_length=2000, blank=True, default="")
    poster = models.CharField("póster", max_length=250, blank=True, default="")

    class Meta:
        db_table = "produccion_traduccion"
        verbose_name = "traducción de producción"
        verbose_name_plural = "traducciones de producciones"
        constraints = [
            models.UniqueConstraint(
                fields=["produccion", "idioma"],
                name="uq_traduccion_produccion_idioma",
            ),
        ]

    def __str__(self):
        return f"{self.produccion_id} [{self.idioma}] {self.titulo}"


class EstadoEmbedding(models.TextChoices):
    """Ciclo de vida del embedding (decisión 08/09/2026).

    `pending` → `processing` → `ready` | `failed`. La búsqueda semántica solo
    consulta los `ready`; el resto no existe para el usuario final.
    """

    PENDING = "pending", "Pendiente"
    PROCESSING = "processing", "Procesando"
    READY = "ready", "Listo"
    FAILED = "failed", "Falló"


class ProduccionEmbedding(models.Model):
    """Representación semántica de una producción para búsqueda por similitud.

    Se crea junto con la producción (materialización, C-04a) en estado
    `pending`; un worker de Celery la completa después. Que el vector tarde o
    falle nunca debe impedir que la producción se vea en el catálogo, por eso
    vive en una tabla aparte y no como columnas de `ProduccionAudiovisual`.
    """

    produccion = models.OneToOneField(
        ProduccionAudiovisual,
        on_delete=models.CASCADE,
        related_name="embedding",
        verbose_name="producción audiovisual",
    )
    vector = VectorField(
        "vector semántico",
        dimensions=1024,
        null=True,
        blank=True,
        help_text="Generado por el proveedor de embeddings (bge-m3, 1024 "
        "dimensiones). Nulo mientras el estado no sea 'ready'.",
    )
    estado = models.CharField(
        "estado",
        max_length=20,
        choices=EstadoEmbedding.choices,
        default=EstadoEmbedding.PENDING,
    )
    source_hash = models.CharField(
        "hash del texto fuente",
        max_length=64,
        blank=True,
        default="",
        help_text="SHA-256 del texto canónico embebido. Si cambia, el vector "
        "quedó viejo y hay que regenerarlo.",
    )
    model_version = models.CharField(
        "versión del modelo",
        max_length=50,
        blank=True,
        default="",
        help_text="Modelo que generó el vector: vectores de modelos distintos "
        "no son comparables entre sí.",
    )
    fecha_creacion = models.DateTimeField("fecha de creación", auto_now_add=True)
    fecha_actualizacion = models.DateTimeField("fecha de actualización", auto_now=True)

    class Meta:
        db_table = "produccion_embedding"
        verbose_name = "embedding de producción"
        verbose_name_plural = "embeddings de producción"
        indexes = [
            # Búsquedas del worker/backfill: "dame los pendientes o fallidos".
            models.Index(fields=["estado"], name="idx_embedding_estado"),
            # HNSW resuelve "los N vectores más parecidos a este" sin comparar
            # contra toda la tabla. `vector_cosine_ops` = distancia coseno, que
            # es la métrica con la que se entrenó bge-m3.
            HnswIndex(
                name="idx_embedding_vector_hnsw",
                fields=["vector"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]
        constraints = [
            # Un embedding `ready` sin vector sería invisible para la búsqueda
            # pero contaría como "listo": se prohíbe en la base, no solo en
            # Python, para que ningún camino de escritura pueda saltearlo.
            models.CheckConstraint(
                condition=~models.Q(estado=EstadoEmbedding.READY)
                | models.Q(vector__isnull=False),
                name="ck_embedding_ready_requiere_vector",
            ),
        ]

    def __str__(self):
        return f"Embedding de {self.produccion} ({self.get_estado_display()})"


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
