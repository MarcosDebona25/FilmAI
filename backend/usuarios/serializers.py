"""
Serializers de autenticación: registro tradicional (CU-001) y Google OAuth.

- `RegisterSerializer`: extiende el de dj-rest-auth para aceptar los 8 campos
  del modelo `Usuario` (correo, nombre_usuario, nombre, apellido,
  fecha_nacimiento, genero, password1, password2).
- `GoogleSocialLoginSerializer`: login con Google mediante `id_token` (Google
  Identity Services). Para usuarios nuevos valida los campos que Google no
  provee; la persistencia la hace `UsuarioSocialAccountAdapter.populate_user`.
"""

import re
from datetime import date

from allauth.account import app_settings as allauth_account_settings
from allauth.account.adapter import get_adapter
from allauth.socialaccount.helpers import complete_social_login
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from dj_rest_auth.registration.serializers import (
    RegisterSerializer as BaseRegisterSerializer,
)
from dj_rest_auth.registration.serializers import (
    SocialLoginSerializer as BaseSocialLoginSerializer,
)
from dj_rest_auth.serializers import LoginSerializer as BaseLoginSerializer
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.db import IntegrityError
from django.http import HttpResponseBadRequest
from requests.exceptions import HTTPError, RequestException
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from .models import EstadoCuenta, TipoGenero, Usuario

USERNAME_REGEX = re.compile(r"^[A-Za-z0-9]{5,25}$")

# Campos que Google no provee y debe completar un usuario nuevo (docs/04:707).
CAMPOS_FALTANTES_GOOGLE = ("nombre_usuario", "fecha_nacimiento", "genero")


class LoginSerializer(BaseLoginSerializer):
    """Login por credenciales distinguiendo cuenta no activada (403).

    El backend por defecto devuelve 400 genérico para credenciales inválidas;
    acá detectamos el caso "cuenta existe pero no está activa" (estado
    pendiente o baja) y devolvemos 403 con un mensaje claro.
    """

    def validate(self, attrs):
        email = attrs.get("email")
        username = attrs.get("username")

        usuario = None
        if email:
            usuario = Usuario.objects.filter(correo__iexact=email).first()
        elif username:
            usuario = Usuario.objects.filter(nombre_usuario__iexact=username).first()

        if usuario is not None and not usuario.is_active:
            if usuario.estado == EstadoCuenta.BAJA:
                raise PermissionDenied("Tu cuenta fue dada de baja.")
            raise PermissionDenied(
                "Tu cuenta aún no está activa. Revisá tu correo para confirmarla."
            )

        return super().validate(attrs)

    @staticmethod
    def validate_email_verification_status(user, email=None):
        """No-op: la verificación de email la cubre el ciclo `estado`.

        dj-rest-auth chequea `user.emailaddress_set.filter(email=user.email, ...)`
        usando `user.email` (hardcodeado), que no existe en `usuarios.Usuario`
        (nuestro campo es `correo`). Además bloquearía a usuarios activos sin
        `EmailAddress` (p.ej. los del seed). Como una cuenta solo queda ACTIVA
        tras confirmar el correo (`confirm_email`), el login ya está gated por
        `is_active`.
        """
        return None


class RegisterSerializer(BaseRegisterSerializer):
    """Registro tradicional (CU-001) con los campos del modelo `Usuario`."""

    correo = serializers.EmailField(required=True)
    nombre_usuario = serializers.CharField(max_length=25)
    nombre = serializers.CharField(max_length=50)
    apellido = serializers.CharField(max_length=50)
    fecha_nacimiento = serializers.DateField(input_formats=["%Y-%m-%d", "%d/%m/%Y"])
    genero = serializers.ChoiceField(choices=TipoGenero.choices)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # El serializer base trae `username`/`email`; usamos `nombre_usuario`/`correo`.
        self.fields.pop("username", None)
        self.fields.pop("email", None)

    def validate_correo(self, value):
        value = get_adapter().clean_email(value)
        if Usuario.objects.filter(correo__iexact=value).exists():
            raise serializers.ValidationError("El correo ya está registrado.")
        return value

    def validate_nombre_usuario(self, value):
        if not USERNAME_REGEX.fullmatch(value):
            raise serializers.ValidationError("Alfanumérico, 5-25 caracteres.")
        if Usuario.objects.filter(nombre_usuario__iexact=value).exists():
            raise serializers.ValidationError(
                "El nombre de usuario ya está registrado."
            )
        return value

    def validate_fecha_nacimiento(self, value):
        hoy = date.today()
        if value > hoy:
            raise serializers.ValidationError(
                "La fecha de nacimiento no puede ser futura."
            )
        edad = hoy.year - value.year - ((hoy.month, hoy.day) < (value.month, value.day))
        if edad < 13:
            raise serializers.ValidationError("Debés tener al menos 13 años.")
        return value

    def get_cleaned_data(self):
        return {
            "correo": self.validated_data.get("correo", ""),
            "nombre_usuario": self.validated_data.get("nombre_usuario", ""),
            "nombre": self.validated_data.get("nombre", ""),
            "apellido": self.validated_data.get("apellido", ""),
            "fecha_nacimiento": self.validated_data.get("fecha_nacimiento"),
            "genero": self.validated_data.get("genero", TipoGenero.NO_ESPECIFICA),
            "password1": self.validated_data.get("password1", ""),
            "password2": self.validated_data.get("password2", ""),
        }


class GoogleSocialLoginSerializer(BaseSocialLoginSerializer):
    """Login/registro con Google OAuth (flujo `id_token`).

    Para usuarios nuevos, Google no provee `nombre_usuario`, `fecha_nacimiento`
    ni `genero`: se validan aquí (pantalla intermedia del frontend). La
    creación del `Usuario` con estos campos la realiza
    `UsuarioSocialAccountAdapter.populate_user` leyendo el body del request.
    """

    nombre_usuario = serializers.CharField(max_length=25, required=False)
    fecha_nacimiento = serializers.DateField(
        required=False, input_formats=["%Y-%m-%d", "%d/%m/%Y"]
    )
    genero = serializers.ChoiceField(choices=TipoGenero.choices, required=False)

    def validate_nombre_usuario(self, value):
        if not USERNAME_REGEX.fullmatch(value):
            raise serializers.ValidationError("Alfanumérico, 5-25 caracteres.")
        if Usuario.objects.filter(nombre_usuario__iexact=value).exists():
            raise serializers.ValidationError(
                "El nombre de usuario ya está registrado."
            )
        return value

    def validate_fecha_nacimiento(self, value):
        hoy = date.today()
        if value > hoy:
            raise serializers.ValidationError(
                "La fecha de nacimiento no puede ser futura."
            )
        edad = hoy.year - value.year - ((hoy.month, hoy.day) < (value.month, value.day))
        if edad < 13:
            raise serializers.ValidationError("Debés tener al menos 13 años.")
        return value

    def validate(self, attrs):
        view = self.context.get("view")
        request = self._get_request()
        adapter_class = getattr(view, "adapter_class", None)
        if not adapter_class:
            raise serializers.ValidationError("Define adapter_class en la vista.")

        id_token = attrs.get("id_token")
        if not id_token:
            raise serializers.ValidationError("Se requiere el id_token de Google.")

        adapter = adapter_class(request)
        app = adapter.get_provider().app
        # allauth's base `parse_token` espera la clave `access_token`; para el
        # flujo id_token de Google se pasa el id_token en ambas claves (el
        # adaptador decodifica el id_token desde `response` en complete_login).
        token = adapter.parse_token({"access_token": id_token, "id_token": id_token})
        token.app = app
        try:
            login = self.get_social_login(
                adapter, app, token, response={"id_token": id_token}
            )
            ret = complete_social_login(request, login)
        except (
            DjangoPermissionDenied,
            OAuth2Error,
            HTTPError,
            RequestException,
        ) as err:
            raise serializers.ValidationError(
                "No se pudo autenticar con Google."
            ) from err
        if isinstance(ret, HttpResponseBadRequest):
            raise serializers.ValidationError(ret.content)

        if not login.is_existing:
            # Campos que Google no provee: obligatorios para cuentas nuevas.
            faltantes = [
                campo for campo in CAMPOS_FALTANTES_GOOGLE if not attrs.get(campo)
            ]
            if faltantes:
                raise serializers.ValidationError(
                    dict.fromkeys(
                        faltantes, "Este campo es obligatorio para completar tu cuenta."
                    )
                )

            if allauth_account_settings.UNIQUE_EMAIL:
                email = getattr(login.user, "email", None)
                if email and Usuario.objects.filter(correo__iexact=email).exists():
                    raise serializers.ValidationError("El correo ya está registrado.")
            login.lookup()
            try:
                login.save(request, connect=True)
            except IntegrityError as err:
                raise serializers.ValidationError(
                    "El correo o nombre de usuario ya está registrado."
                ) from err
            self.post_signup(login, attrs)

        attrs["user"] = login.account.user
        return attrs


class UsuarioDetallesSerializer(serializers.ModelSerializer):
    """Representación del usuario autenticado (endpoints `/api/auth/user/`).

    El serializer por defecto de dj-rest-auth usa `username`/`email`/
    `first_name`/`last_name`, que no existen en `usuarios.Usuario`.
    """

    class Meta:
        model = Usuario
        fields = (
            "pk",
            "correo",
            "nombre_usuario",
            "nombre",
            "apellido",
            "fecha_nacimiento",
            "genero",
            "estado",
            "avatar_id",
            "fecha_registro",
        )
        read_only_fields = fields
