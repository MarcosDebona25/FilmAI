"""
Modelos de la app `chatbot`.

Implementa la conversación del chatbot (doc 03):

    Chat  ──<  Mensaje
     │
     └── Usuario (FK a usuarios.Usuario)

Un `Chat` pertenece a un único usuario. El modelo contempla múltiples chats por
usuario, aunque el MVP implementa uno solo (doc 03, B-01). El campo `contexto`
se almacena como JSONB para alojar datos de estructura variable (resumen del
historial, géneros preferidos, última recomendación y parámetros activos).
"""

from django.db import models


class TipoAutor(models.TextChoices):
    """Autor de un mensaje dentro del chat (doc 03: 'Usuario' | 'Chatbot')."""

    USUARIO = "usuario", "Usuario"
    CHATBOT = "chatbot", "Chatbot"


class Chat(models.Model):
    """Conversación entre un usuario y el chatbot de recomendaciones."""

    titulo = models.CharField("título", max_length=25)
    contexto = models.JSONField(
        "contexto",
        default=dict,
        help_text=(
            "JSONB con estado variable de la conversación: resumen del historial, "
            "géneros preferidos, última recomendación y parámetros activos (B-01)."
        ),
    )
    fecha = models.DateField("fecha", auto_now_add=True)
    activo = models.BooleanField("activo", default=True)
    usuario = models.ForeignKey(
        "usuarios.Usuario",
        on_delete=models.CASCADE,
        related_name="chats",
        verbose_name="usuario",
    )

    class Meta:
        db_table = "chat"
        verbose_name = "chat"
        verbose_name_plural = "chats"
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"{self.titulo} ({self.usuario})"


class Mensaje(models.Model):
    """Mensaje individual dentro de un chat.

    El atributo `autor` distingue si el mensaje proviene del usuario o del
    chatbot, sin necesidad de una segunda entidad para los roles (doc 03).
    """

    texto = models.TextField(
        "texto",
        help_text=(
            "El diagrama de tablas indica VARCHAR(250), pero una respuesta del LLM "
            "puede superar ese límite; se usa TextField para no truncar contenido."
        ),
    )
    autor = models.CharField("autor", max_length=25, choices=TipoAutor.choices)
    fecha_hora = models.DateTimeField("fecha y hora", auto_now_add=True)
    chat = models.ForeignKey(
        Chat,
        on_delete=models.CASCADE,
        related_name="mensajes",
        verbose_name="chat",
    )

    class Meta:
        db_table = "mensaje"
        verbose_name = "mensaje"
        verbose_name_plural = "mensajes"
        ordering = ["fecha_hora", "id"]

    def __str__(self):
        return f"[{self.get_autor_display()}] {self.texto[:50]}"
