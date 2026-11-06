"""
Modelos de la app `chatbot`.

Implementa la conversación del chatbot (doc 03):

    Chat  ──<  Mensaje
     │
     └── Usuario (FK a usuarios.Usuario)

Un `Chat` pertenece a un único usuario. El modelo contempla múltiples chats por
usuario, aunque el MVP implementa uno solo (doc 03, B-01). El campo `contexto`
es JSONB y guarda lo que el chat recuerda fuera de los mensajes: hoy, solo
`ya_recomendados`. El perfil del usuario no se guarda: se arma por SQL en cada
mensaje (08/10/2026). Los mensajes y `contexto` los escribe
`servicio.guardar_turno()`.
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
            "JSONB con lo que el chat recuerda fuera de los mensajes. Hoy solo "
            "`ya_recomendados`: las últimas 30 tarjetas mostradas, sin repetir, como "
            "{id_tmdb, tipo, titulo, anio}. Lo escribe `guardar_turno()` y lo lee el "
            "prompt. El perfil no se guarda acá: se arma por SQL en cada mensaje "
            "(08/10/2026)."
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
        constraints = [
            models.UniqueConstraint(
                fields=["usuario"],
                name="uq_chat_usuario_mvp",
            ),
        ]

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
            "TEXT, como indica el diagrama de tablas (doc 03): una respuesta del "
            "LLM puede superar los 250 caracteres que tenía antes."
        ),
    )
    autor = models.CharField("autor", max_length=25, choices=TipoAutor.choices)
    tarjetas = models.JSONField(
        "tarjetas",
        # `list` y no `[]`: Django llama a `list()` por cada mensaje nuevo. Un `[]`
        # literal sería una sola lista compartida por todos.
        default=list,
        blank=True,
        help_text=(
            "Hasta 3 tarjetas que el bot mostró con la respuesta, tal como se "
            "vieron: {id_tmdb, tipo, titulo, poster, anio}, en el idioma del turno. "
            "Sin FK a la producción (09/10/2026). En los mensajes del usuario, "
            "lista vacía."
        ),
    )
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
