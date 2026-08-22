"""
Adaptadores de allauth para el modelo de usuario personalizado de FilmAI.

allauth mapea por defecto los campos `email`, `username`, `first_name` y
`last_name`, que no existen en `usuarios.Usuario` (cuyos campos son `correo`,
`nombre_usuario`, `nombre` y `apellido`). Estos adaptadores traducen esa
convención y aplican el ciclo de vida definido en `docs/decisiones.md`:

- Registro tradicional: cuenta queda `pendiente` hasta confirmar el email; la
  confirmación (`confirm_email`) la pasa a `activa`.
- Google OAuth: usuario nuevo queda `activa` directo (Google ya verifica el
  email); los campos que Google no provee (`nombre_usuario`,
  `fecha_nacimiento`, `genero`) se leen del body del request (pantalla
  intermedia del frontend).
"""

import json

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.utils.dateparse import parse_date

from .models import EstadoCuenta, TipoGenero


def _extra_from_body(request):
    """Lee los campos extra del body JSON del request (si lo hay)."""
    try:
        body = request.body
        if isinstance(body, bytes):
            return json.loads(body or b"{}")
    except (json.JSONDecodeError, AttributeError, TypeError):
        return {}
    return {}


class UsuarioAccountAdapter(DefaultAccountAdapter):
    """Adaptador de cuenta para el registro tradicional (dj-rest-auth)."""

    def save_user(self, request, user, form, commit=True):
        """Persiste los campos propios del modelo `Usuario`.

        Reemplaza el mapeo por defecto de allauth (`email`/`username`/
        `first_name`/`last_name`) por los campos reales del modelo.
        """
        data = form.cleaned_data
        user.correo = data.get("correo", user.correo)
        user.nombre_usuario = data.get("nombre_usuario")
        user.nombre = data.get("nombre", "")
        user.apellido = data.get("apellido", "")
        user.fecha_nacimiento = data.get("fecha_nacimiento")
        user.genero = data.get("genero", TipoGenero.NO_ESPECIFICA)
        if "password1" in data:
            user.set_password(data["password1"])
        else:
            user.set_unusable_password()
        if commit:
            user.save()
        return user

    def confirm_email(self, request, email_address):
        """Al confirmar el email, la cuenta pasa a estado `activa`.

        `is_active` es una propiedad derivada de `estado` (Opción A1), así que
        activar la cuenta equivale a setear `estado = ACTIVA`.
        """
        usuario = email_address.user
        usuario.estado = EstadoCuenta.ACTIVA
        usuario.save(update_fields=["estado"])
        super().confirm_email(request, email_address)

    def get_email_confirmation_url(self, request, emailconfirmation):
        """El link de confirmación apunta al frontend (SPA Next.js).

        El frontend recibe la `key` y llama al endpoint `verify-email` de
        dj-rest-auth para completar la confirmación.
        """
        return f"{settings.FRONTEND_URL}/confirmar-correo/{emailconfirmation.key}/"


class UsuarioSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Adaptador social (Google OAuth) para `usuarios.Usuario`."""

    def populate_user(self, request, sociallogin, data):
        """Construye el `Usuario` a partir del perfil de Google.

        Se llama únicamente en el alta de usuarios nuevos (no en logins de
        usuarios existentes).
        """
        user = super().populate_user(request, sociallogin, data)

        nombre = data.get("given_name") or data.get("first_name") or ""
        apellido = data.get("family_name") or data.get("last_name") or ""
        if not nombre and data.get("name"):
            partes = data["name"].strip().split(" ", 1)
            nombre = partes[0]
            apellido = partes[1] if len(partes) > 1 else ""
        user.nombre = nombre
        user.apellido = apellido

        # Google ya verificó el email: la cuenta nace activa.
        user.estado = EstadoCuenta.ACTIVA

        extra = _extra_from_body(request)
        user.nombre_usuario = extra.get("nombre_usuario") or ""
        fecha = extra.get("fecha_nacimiento")
        user.fecha_nacimiento = parse_date(fecha) if isinstance(fecha, str) else fecha
        user.genero = extra.get("genero") or TipoGenero.NO_ESPECIFICA
        return user
