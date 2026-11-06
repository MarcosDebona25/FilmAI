from django.urls import path

from chatbot.views import HistorialView, PrepararChatView

urlpatterns = [
    path("preparar/", PrepararChatView.as_view(), name="chat-preparar"),
    # El PR 5 suma el POST del stream en esta misma ruta. Como ese POST es una
    # vista async y esta es DRF (sync), no pueden ser una sola clase: el PR 5
    # cambia esta línea por una función que despacha según el método.
    path("messages/", HistorialView.as_view(), name="chat-mensajes"),
]
