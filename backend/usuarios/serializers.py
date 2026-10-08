import logging
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
from django.db import IntegrityError, transaction
from django.http import HttpResponseBadRequest
from django.template.loader import render_to_string
from requests.exceptions import HTTPError, RequestException
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from filmai.errores.validacion import ErrorValidacion

from .avatares import es_avatar_valido
from .errores import CampoNombreUsuario, FronteraUsuarioMixin
from .exceptions import NombreUsuarioOcupado
from .models import EstadoCuenta, TipoGenero, Usuario
from .passwords import guardar_contrasena
from .validators import USERNAME_REGEX, validar_nombre_persona

logger = logging.getLogger(__name__)

# Campos que Google no provee y debe completar un usuario nuevo
CAMPOS_FALTANTES_GOOGLE = ("nombre_usuario", "fecha_nacimiento", "genero")


class LoginSerializer(BaseLoginSerializer):
    """Login por credenciales con errores específicos para cuentas inactivas."""

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
        """La activación por ``estado`` reemplaza el chequeo de allauth."""
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
        # FilmAI usa `nombre_usuario` y `correo`.
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

    def validate_nombre(self, value):
        try:
            return validar_nombre_persona(value)
        except DjangoValidationError as err:
            raise serializers.ValidationError(err.messages) from err

    def validate_apellido(self, value):
        return self.validate_nombre(value)

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
    """Login y registro con Google mediante ``id_token``."""

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
        # allauth espera `access_token`, aun en el flujo de `id_token` de Google.
        token = adapter.parse_token({"access_token": id_token, "id_token": id_token})
        token.app = app
        # DRF ya consumió el body; el adapter recibe estos datos desde el request.
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

        # allauth todavía no resolvió `is_existing`; consultamos el vínculo directo.
        cuenta_existente = (
            SocialAccount.objects.select_related("user")
            .filter(provider=login.account.provider, uid=login.account.uid)
            .first()
        )
        es_existente = cuenta_existente is not None

        if es_existente and not cuenta_existente.user.is_active:
            raise PermissionDenied("Tu cuenta no está activa.")

        if not es_existente:
            # Google no provee estos campos obligatorios del perfil FilmAI.
            faltantes = [
                campo for campo in CAMPOS_FALTANTES_GOOGLE if not attrs.get(campo)
            ]
            if faltantes:
                raise serializers.ValidationError(
                    dict.fromkeys(
                        faltantes, "Este campo es obligatorio para completar tu cuenta."
                    )
                )

            # Evita que allauth persista una cuenta con correo duplicado.
            if allauth_account_settings.UNIQUE_EMAIL:
                user_obj = getattr(login, "user", None) or getattr(
                    getattr(login, "account", None), "user", None
                )
                correo = getattr(user_obj, "correo", None)
                if correo and Usuario.objects.filter(correo__iexact=correo).exists():
                    raise serializers.ValidationError(
                        "Ya existe una cuenta registrada con este correo."
                        " Iniciá sesión con tu contraseña."
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
            login.lookup()
            try:
                with transaction.atomic():
                    login.save(request, connect=True)
            except IntegrityError as err:
                raise serializers.ValidationError(
                    "El correo o nombre de usuario ya está registrado."
                ) from err
            self.post_signup(login, attrs)

        attrs["user"] = login.account.user
        if not attrs["user"].is_active:
            raise PermissionDenied("Tu cuenta no está activa.")
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
            "idioma",
        )
        read_only_fields = fields


class EnlaceRestablecimientoInvalido(Exception):
    """Señala un ``uid`` o token de restablecimiento inválido o vencido."""


class RecuperarContrasenaSerializer(serializers.Serializer):
    """Solicitud de restablecimiento sin revelar si un correo está registrado."""

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
            # Mantiene la misma respuesta para no revelar la existencia de la cuenta.
            logger.exception(
                "Error enviando email de restablecimiento para %s", usuario.correo
            )
            return None
        return usuario


class RestablecerContrasenaSerializer(serializers.Serializer):
    """Valida el enlace y persiste la nueva contraseña."""

    password1 = serializers.CharField(trim_whitespace=False, write_only=True)
    password2 = serializers.CharField(trim_whitespace=False, write_only=True)
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

        # No distingue un token vencido de uno manipulado.
        if not self.usuario.is_active or not default_token_generator.check_token(
            self.usuario, attrs["token"]
        ):
            raise EnlaceRestablecimientoInvalido

        try:
            validate_password(attrs["password1"], user=self.usuario)
        except DjangoValidationError as err:
            raise serializers.ValidationError({"password1": err.messages}) from err

        return attrs

    def save(self):
        with transaction.atomic():
            self.usuario = Usuario.objects.select_for_update().get(pk=self.usuario.pk)
            # Revalidar bajo bloqueo evita consumir dos veces el mismo enlace.
            if not self.usuario.is_active or not default_token_generator.check_token(
                self.usuario, self.validated_data["token"]
            ):
                raise EnlaceRestablecimientoInvalido
            guardar_contrasena(self.usuario, self.validated_data["password1"])
        return self.usuario


class UsuarioPerfilSerializer(FronteraUsuarioMixin, serializers.ModelSerializer):
    """CU-006: solo nombre, apellido, nombre de usuario y avatar editables."""

    tiene_contrasena_local = serializers.SerializerMethodField()
    nombre_usuario = CampoNombreUsuario(USERNAME_REGEX, max_length=25)

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
            "avatar_id",
            "estado",
            "fecha_registro",
            "idioma",
            "tiene_contrasena_local",
        )
        read_only_fields = (
            "pk",
            "correo",
            "fecha_nacimiento",
            "genero",
            "estado",
            "fecha_registro",
            "idioma",
        )

    def get_tiene_contrasena_local(self, usuario):
        return usuario.has_usable_password()

    def validate_nombre_usuario(self, value):
        if (
            Usuario.objects.filter(nombre_usuario__iexact=value)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise NombreUsuarioOcupado()
        return value

    def validate_nombre(self, value):
        try:
            return validar_nombre_persona(value)
        except DjangoValidationError as err:
            raise ErrorValidacion.desde_django(err) from err

    def validate_apellido(self, value):
        return self.validate_nombre(value)

    def update(self, instance, validated_data):
        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save(update_fields=list(validated_data))
        return instance

    def validate_avatar_id(self, value):
        """Valida que avatar_id sea uno de los avatares disponibles."""
        if not es_avatar_valido(value):
            from .avatares import AVATAR_IDS_VALIDOS

            raise serializers.ValidationError(
                f"avatar_id inválido. Debe ser uno de: {sorted(AVATAR_IDS_VALIDOS)}",
                code="avatar_invalid",
            )
        return value

    def validate_fecha_nacimiento(self, value):
        """Valida que la fecha de nacimiento no sea futura y el usuario tenga al menos 13 años."""
        hoy = date.today()
        if value > hoy:
            raise serializers.ValidationError(
                "La fecha de nacimiento no puede ser futura."
            )
        edad = hoy.year - value.year - ((hoy.month, hoy.day) < (value.month, value.day))
        if edad < 13:
            raise serializers.ValidationError("Debés tener al menos 13 años.")
        return value
