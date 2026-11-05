from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from catalogo.services.semantica import pedir_carga_del_modelo


class PrepararChatView(APIView):
    """Se llama al abrir el panel, para que el modelo cargue mientras se escribe."""

    @extend_schema(
        request=None,
        responses={202: OpenApiResponse(description="Carga pedida.")},
    )
    def post(self, request):
        pedir_carga_del_modelo()
        return Response(status=status.HTTP_202_ACCEPTED)
