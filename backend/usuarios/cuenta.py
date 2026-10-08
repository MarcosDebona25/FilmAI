"""Preferencias propias y baja lógica de la cuenta (CU-007)."""

from typing import ClassVar

from django.conf import settings
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from .models import EstadoCuenta, Usuario
from .perfil import bloquear_usuario, cerrar_sesion


class PreferenciasSerializer(serializers.ModelSerializer):
    idioma = serializers.ChoiceField(
        choices=settings.IDIOMAS_SOPORTADOS, required=False, allow_null=False
    )

    class Meta:
        model = Usuario
        fields = (
            "tema",
            "idioma",
            "perfil_publico",
            "notif_recomendaciones",
            "notif_resenas",
            "notif_novedades",
        )

    def update(self, instance, validated_data):
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save(update_fields=list(validated_data))
        return instance


class PreferenciasLecturaSerializer(PreferenciasSerializer):
    """Las cuentas anteriores pueden leerse con idioma nulo, sin permitir borrarlo."""

    idioma = serializers.ChoiceField(
        choices=settings.IDIOMAS_SOPORTADOS, allow_null=True, read_only=True
    )


class PreferenciasView(GenericAPIView):
    serializer_class = PreferenciasSerializer
    permission_classes: ClassVar[list] = [permissions.IsAuthenticated]

    @extend_schema(responses=PreferenciasLecturaSerializer)
    def get(self, request):
        return Response(PreferenciasLecturaSerializer(request.user).data)

    @extend_schema(responses=PreferenciasLecturaSerializer)
    def put(self, request):
        with transaction.atomic():
            usuario = bloquear_usuario(request)
            serializer = self.get_serializer(usuario, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(PreferenciasLecturaSerializer(usuario).data)


class DesactivarCuentaView(GenericAPIView):
    serializer_class = serializers.Serializer
    permission_classes: ClassVar[list] = [permissions.IsAuthenticated]

    def post(self, request):
        with transaction.atomic():
            usuario = bloquear_usuario(request)
            usuario.estado = EstadoCuenta.BAJA
            usuario.save(update_fields=["estado"])
            # No se borra ningún dato de dominio. El estado bloquea los access;
            # la blacklist impide reutilizar refresh emitidos en otros dispositivos.
            for token in OutstandingToken.objects.filter(user=usuario).iterator():
                BlacklistedToken.objects.get_or_create(token=token)
            return cerrar_sesion(
                request, "Tu cuenta fue dada de baja. Tus datos se conservan."
            )
