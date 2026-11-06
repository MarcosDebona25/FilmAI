from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.pagination import CursorPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from catalogo.services.semantica import pedir_carga_del_modelo
from chatbot.serializers import MensajeSerializer
from chatbot.servicio import historial_de


class PrepararChatView(APIView):
    """Se llama al abrir el panel, para que el modelo cargue mientras se escribe."""

    @extend_schema(
        request=None,
        responses={202: OpenApiResponse(description="Carga pedida.")},
    )
    def post(self, request):
        pedir_carga_del_modelo()
        return Response(status=status.HTTP_202_ACCEPTED)


class MensajesCursorPagination(CursorPagination):
    """Cursor de 20 para el historial, que el panel carga hacia arriba.

    Cursor y no `?page=2`: en un chat llegan mensajes nuevos mientras se lee, y
    con offset cada uno empuja todo un lugar y la página siguiente repite el
    último mensaje de la anterior. El cursor dice «los anteriores a este», así que
    lo nuevo no lo mueve.

    Desempata por `-id`: si dos mensajes tienen la misma `fecha_hora`, el orden
    entre ellos tiene que ser fijo para que el cursor no pierda el hilo.

    Sin `total` (06/11/2026): el panel no muestra cuántos mensajes hay y `next`
    en `null` ya dice que no quedan más. Se ahorra un `COUNT(*)` por página.
    """

    page_size = 20
    ordering = ("-fecha_hora", "-id")


class HistorialView(ListAPIView):
    """El historial del chat del usuario, de más nuevo a más viejo, de a 20.

    Las tarjetas vuelven como se guardaron, en el idioma de su turno.
    """

    serializer_class = MensajeSerializer
    pagination_class = MensajesCursorPagination

    def get_queryset(self):
        return historial_de(self.request.user)
