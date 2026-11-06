from django.urls import path

from chatbot.views import MensajesView, PrepararChatView

urlpatterns = [
    path("preparar/", PrepararChatView.as_view(), name="chat-preparar"),
    # GET: el historial. POST: la pregunta, con la respuesta en streaming (PR 5).
    path("messages/", MensajesView.as_view(), name="chat-mensajes"),
]
