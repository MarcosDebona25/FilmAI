"""API del perfil propio y gestión autenticada de contraseñas."""

from typing import ClassVar

from dj_rest_auth.jwt_auth import unset_jwt_cookies
from django.contrib.auth import logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import permissions, serializers
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from filmai.errores.serializadores import FronteraErroresMixin
from filmai.errores.sobre import agregar_codigo_exito
from filmai.errores.validacion import ErrorValidacion
from filmai.throttles import EscrituraThrottle

from .avatares import AVATARES
from .exceptions import NombreUsuarioOcupado
from .models import Usuario
from .passwords import guardar_contrasena
from .serializers import UsuarioPerfilSerializer


def bloquear_usuario(request):
    """Se usa dentro de atomic; vuelve a verificar la sesión tras tomar el bloqueo."""
    usuario = Usuario.objects.select_for_update().get(pk=request.user.pk)
    JWTAuthentication().get_user(request.auth)
    return usuario


def cerrar_sesion(request, mensaje, codigo):
    logout(request)
    response = agregar_codigo_exito(Response({"detail": mensaje}), codigo)
    unset_jwt_cookies(response)
    return response


class PerfilView(GenericAPIView):
    # Límite común de escrituras (26/10/2026); las lecturas no cuentan.
    throttle_classes: ClassVar[list] = [EscrituraThrottle]
    serializer_class = UsuarioPerfilSerializer
    permission_classes: ClassVar[list] = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(self.get_serializer(request.user).data)

    def put(self, request):
        try:
            with transaction.atomic():
                usuario = bloquear_usuario(request)
                serializer = self.get_serializer(
                    usuario, data=request.data, partial=True
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()
        except IntegrityError:
            # La restricción de BD resuelve una carrera entre usernames iguales.
            raise NombreUsuarioOcupado() from None
        return Response(serializer.data)


class AvataresView(APIView):
    """Opciones disponibles para el selector, con IDs estables."""

    permission_classes: ClassVar[list] = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(list(AVATARES.values()))


class CambiarContrasenaSerializer(FronteraErroresMixin, serializers.Serializer):
    old_password = serializers.CharField(trim_whitespace=False, write_only=True)
    password1 = serializers.CharField(trim_whitespace=False, write_only=True)
    password2 = serializers.CharField(trim_whitespace=False, write_only=True)

    def validate(self, attrs):
        usuario = self.context["usuario"]
        if not usuario.has_usable_password():
            raise serializers.ValidationError(
                {
                    "old_password": "Tu cuenta no tiene contraseña local. Puedes establecerla "
                    "mediante recuperación por correo.",
                },
                code="local_password_unavailable",
            )
        if not usuario.check_password(attrs["old_password"]):
            raise serializers.ValidationError(
                {"old_password": "La contraseña actual es incorrecta."},
                code="current_password_incorrect",
            )
        if attrs["password1"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"password2": "Las contraseñas no coinciden."},
                code="passwords_do_not_match",
            )
        try:
            validate_password(attrs["password1"], user=usuario)
        except DjangoValidationError as err:
            raise serializers.ValidationError(
                {"password1": ErrorValidacion.desde_django(err).detail}
            ) from err
        return attrs


class CambiarContrasenaView(GenericAPIView):
    serializer_class = CambiarContrasenaSerializer
    permission_classes: ClassVar[list] = [permissions.IsAuthenticated]
    throttle_classes: ClassVar[list] = [ScopedRateThrottle]
    throttle_scope = "restablecer_contrasena"

    def post(self, request):
        with transaction.atomic():
            usuario = bloquear_usuario(request)
            serializer = self.get_serializer(
                data=request.data, context={"usuario": usuario}
            )
            serializer.is_valid(raise_exception=True)
            guardar_contrasena(usuario, serializer.validated_data["password1"], request)
        return cerrar_sesion(
            request,
            "Contraseña actualizada. Inicia sesión nuevamente en tus dispositivos.",
            "password_updated",
        )
