from django.urls import path

from chatbot.views import PrepararChatView

urlpatterns = [
    path("preparar/", PrepararChatView.as_view(), name="chat-preparar"),
]
