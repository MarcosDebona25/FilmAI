"""Configuración del admin de Django para el catálogo y las reseñas."""

from django.contrib import admin

from catalogo.models import ProduccionEmbedding, Resena


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


@admin.register(Resena)
class ResenaAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "produccion", "tipo", "valor", "activa", "fecha")
    list_filter = ("activa", "calificacion__produccion__tipo")
    search_fields = (
        "texto",
        "calificacion__usuario__correo",
        "calificacion__usuario__nombre_usuario",
        "calificacion__produccion__titulo",
    )
    fields = ("calificacion", "texto", "activa", "fecha")
    readonly_fields = ("calificacion", "fecha")
    actions = ("desactivar_resenas",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("calificacion__usuario", "calificacion__produccion")
        )

    @admin.display(
        description="Usuario", ordering="calificacion__usuario__nombre_usuario"
    )
    def usuario(self, obj):
        return obj.calificacion.usuario

    @admin.display(
        description="Producción", ordering="calificacion__produccion__titulo"
    )
    def produccion(self, obj):
        return obj.calificacion.produccion

    @admin.display(description="Tipo", ordering="calificacion__produccion__tipo")
    def tipo(self, obj):
        return obj.calificacion.produccion.get_tipo_display()

    @admin.display(description="Calificación", ordering="calificacion__valor")
    def valor(self, obj):
        return obj.calificacion.valor

    @admin.action(description="Desactivar reseñas", permissions=["change"])
    def desactivar_resenas(self, request, queryset):
        cantidad = queryset.update(activa=False)
        self.message_user(request, f"{cantidad} reseña(s) desactivada(s).")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
