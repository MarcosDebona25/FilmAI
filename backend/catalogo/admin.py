"""Configuración del admin de Django para el catálogo.

Por ahora solo se registra `ProduccionEmbedding`, para poder auditar en
desarrollo en qué estado quedó cada embedding (C-04a). El registro de
`Usuario` y `Reseña` con sus filtros es parte de AD-01' (Módulo 6).
"""

from django.contrib import admin

from catalogo.models import ProduccionEmbedding


@admin.register(ProduccionEmbedding)
class ProduccionEmbeddingAdmin(admin.ModelAdmin):
    list_display = (
        "produccion",
        "estado",
        "model_version",
        "fecha_actualizacion",
    )
    list_filter = ("estado", "model_version")
    search_fields = ("produccion__titulo", "produccion__id_tmdb")
    # El vector son 1024 números: legible por API, ilegible en un formulario.
    # Se excluye del form y se muestran solo los metadatos que sirven para
    # diagnosticar (estado, hash, versión del modelo).
    exclude = ("vector",)
    readonly_fields = ("source_hash", "model_version", "fecha_actualizacion")
