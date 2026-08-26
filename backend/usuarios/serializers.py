"""
Serializers de autenticación: registro tradicional (CU-001) y Google OAuth.

- `RegisterSerializer`: extiende el de dj-rest-auth para aceptar los 8 campos
  del modelo `Usuario` (correo, nombre_usuario, nombre, apellido,
  fecha_nacimiento, genero, password1, password2).
- `GoogleSocialLoginSerializer`: login con Google mediante `id_token` (Google
  Identity Services). Para usuarios nuevos valida los campos que Google no
  provee; la persistencia la hace `UsuarioSocialAccountAdapter.populate_user`.
"""

import logging
import re
from datetime import date

from allauth.account import app_settings as allauth_account_settings
from allauth.account.adapter import get_adapter
from allauth.account.forms import default_token_generator
from allauth.account.utils import url_str_to_user_pk, user_pk_to_url_str
from allauth.socialaccount.helpers import complete_social_login
from allauth.socialaccount.models import SocialAccount
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from dj_rest_auth.registration.serializers import (
    RegisterSerializer as BaseRegisterSerializer,
)
from dj_rest_auth.registration.serializers import (
    SocialLoginSerializer as BaseSocialLoginSerializer,
)
from dj_rest_auth.serializers import LoginSerializer as BaseLoginSerializer
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db import IntegrityError
from django.http import HttpResponseBadRequest
from django.template.loader import render_to_string
from requests.exceptions import HTTPError, RequestException
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from .models import EstadoCuenta, TipoGenero, Usuario

logger = logging.getLogger(__name__)

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

    Distingue dos casos según exista o no un `SocialAccount` vinculado al
    `uid` de Google: si existe, es un login (no se exigen campos extra); si no,
    es un registro nuevo y Google no provee `nombre_usuario`, `fecha_nacimiento`
    ni `genero`, que se validan aquí (pantalla intermedia del frontend). La
    creación del `Usuario` con estos campos la realiza
    `UsuarioSocialAccountAdapter.populate_user`, que los recibe pegados al
    request (`request.google_extra`) en vez de releer el body (consumido por DRF).
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
        # Los campos que Google no provee viajan al adapter pegados al request,
        # no releídos de `request.body`: en un view de DRF el body ya fue
        # consumido por el parser al construir `request.data`, y releerlo dentro
        # de `populate_user` lanza RawPostDataException (500). Ver
        # docs/decisiones.md (26/08/2026).
        request.google_extra = {
            campo: attrs.get(campo) for campo in CAMPOS_FALTANTES_GOOGLE
        }
        try:
            login = self.get_social_login(
                adapter, app, token, response={"id_token": id_token}
            )
        except (
            DjangoPermissionDenied,
            OAuth2Error,
            HTTPError,
            RequestException,
        ) as err:
            logger.exception(
                "Google login: error al verificar el id_token (%s)", type(err).__name__
            )
            raise serializers.ValidationError(
                "No se pudo autenticar con Google."
            ) from err

        # Determinar si la cuenta de Google YA está vinculada (login) o es
        # nueva (registro). `login.is_existing` todavía es False acá porque
        # allauth recién resuelve el `lookup()` dentro de `complete_social_login`;
        # por eso se consulta el `SocialAccount` directamente, con el mismo
        # criterio que el `_lookup_by_socialaccount` interno de allauth. Sin
        # esto, el login de una cuenta existente siempre caía en la rama de
        # "campos faltantes" (400) y el frontend la mandaba a /completar-google.
        es_existente = SocialAccount.objects.filter(
            provider=login.account.provider, uid=login.account.uid
        ).exists()

        if not es_existente:
            # Campos que Google no provee: obligatorios para cuentas nuevas.
            # Validar ANTES de complete_social_login para evitar que allauth
            # persista un usuario incompleto.
            faltantes = [
                campo for campo in CAMPOS_FALTANTES_GOOGLE if not attrs.get(campo)
            ]
            if faltantes:
                raise serializers.ValidationError(
                    dict.fromkeys(
                        faltantes, "Este campo es obligatorio para completar tu cuenta."
                    )
                )

        try:
            ret = complete_social_login(request, login)
        except (
            DjangoPermissionDenied,
            OAuth2Error,
            HTTPError,
            RequestException,
        ) as err:
            logger.exception(
                "Google login: error en complete_social_login (%s)",
                type(err).__name__,
            )
            raise serializers.ValidationError(
                "No se pudo autenticar con Google."
            ) from err
        if isinstance(ret, HttpResponseBadRequest):
            raise serializers.ValidationError(ret.content)

        if not login.is_existing:
            if allauth_account_settings.UNIQUE_EMAIL:
                # El modelo custom expone `correo`, no `email` (dj-rest-auth
                # copia este check con `email`; acá se corrige para que el
                # chequeo de email duplicado realmente aplique).
                user_obj = getattr(login, "user", None) or getattr(
                    getattr(login, "account", None), "user", None
                )
                correo = getattr(user_obj, "correo", None)
                if correo and Usuario.objects.filter(correo__iexact=correo).exists():
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


class EnlaceRestablecimientoInvalido(Exception):
    """El `uid` o el `token` del enlace de restablecimiento son inválidos.

    Se lanza desde `validate()` y la vista la convierte en
    `400 {"codigo": "invalido"}` (mismo contrato que ConfirmarCorreoView).
    Django no distingue token inválido de expirado (`check_token` devuelve
    False en ambos casos), así que un único código alcanza.
    """


class RecuperarContrasenaSerializer(serializers.Serializer):
    """Solicitud de restablecimiento de contraseña (CU-020).

    Envía un email con un enlace al frontend solo si existe una cuenta ACTIVA
    con ese correo; en cualquier otro caso no hace nada. La respuesta HTTP es
    idéntica siempre para no revelar si el correo está registrado.
    """

    email = serializers.EmailField()

    def save(self):
        usuario = Usuario.objects.filter(
            correo__iexact=self.validated_data["email"].strip(),
            estado=EstadoCuenta.ACTIVA,
        ).first()
        if usuario is None:
            return None

        uid = user_pk_to_url_str(usuario)
        token = default_token_generator.make_token(usuario)
        reset_url = f"{settings.FRONTEND_URL}/restablecer-contrasena/{uid}/{token}/"
        # Clave "user" para ser consistente con los templates de allauth
        # (los de confirmación también la usan).
        contexto = {"user": usuario, "reset_url": reset_url}

        try:
            asunto = render_to_string(
                "registration/recuperar_contrasena_subject.txt", contexto
            ).strip()
            cuerpo_texto = render_to_string(
                "registration/recuperar_contrasena_message.txt", contexto
            )
            cuerpo_html = render_to_string(
                "registration/recuperar_contrasena_message.html", contexto
            )
            send_mail(
                asunto,
                cuerpo_texto,
                settings.DEFAULT_FROM_EMAIL,
                [usuario.correo],
                html_message=cuerpo_html,
            )
        except Exception:
            # Un fallo en el render o en el envío no debe romper el request ni
            # revelar que la cuenta existe: se loguea y se responde igual que
            # para un correo desconocido.
            logger.exception(
                "Error enviando email de restablecimiento para %s", usuario.correo
            )
            return None
        return usuario


class RestablecerContrasenaSerializer(serializers.Serializer):
    """Confirmación del restablecimiento con nueva contraseña (CU-020).

    Valida el par `uid`/`token` firmado, aplica la política de contraseña del
    CU-001 vía AUTH_PASSWORD_VALIDATORS y persiste la nueva contraseña.
    """

    password1 = serializers.CharField()
    password2 = serializers.CharField()
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, attrs):
        if attrs["password1"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"password2": ["Las contraseñas no coinciden."]}
            )

        try:
            self.usuario = Usuario.objects.get(pk=url_str_to_user_pk(attrs["uid"]))
        except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist) as err:
            raise EnlaceRestablecimientoInvalido from err

        # check_token devuelve False por firma inválida O enlace vencido
        # (PASSWORD_RESET_TIMEOUT = 1 hora).
        if not default_token_generator.check_token(self.usuario, attrs["token"]):
            raise EnlaceRestablecimientoInvalido

        try:
            validate_password(attrs["password1"], user=self.usuario)
        except DjangoValidationError as err:
            raise serializers.ValidationError({"password1": err.messages}) from err

        return attrs

    def save(self):
        self.usuario.set_password(self.validated_data["password1"])
        self.usuario.save(update_fields=["password"])
        return self.usuario
