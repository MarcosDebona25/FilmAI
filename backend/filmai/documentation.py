"""Acceso y respuesta de ayuda para la documentación de la API."""

from functools import wraps
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.cache import patch_cache_control, patch_vary_headers
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from usuarios.models import Usuario

from .errores.sobre import construir_sobre
from .idioma import idioma_efectivo

# Intentos fallidos por IP antes de bloquear el formulario (vence solo).
INTENTOS_MAXIMOS = 10
VENTANA_MINUTOS = 60
VENTANA_SEGUNDOS = VENTANA_MINUTOS * 60

# Rutas a las que el formulario puede devolver al usuario tras ingresar.
RUTAS_DOCUMENTACION = ("/api/docs/", "/api/schema/")

TEXTOS = {
    "en": {
        "pill": "Internal documentation",
        "login_title": "Admin access",
        "login_intro": (
            "Internal documentation is only for the FilmAI team. "
            "Log in with an admin account to continue."
        ),
        "resource": {
            "schema": "the OpenAPI schema",
            "swagger-ui": "Swagger UI",
        },
        "identifier_label": "Email or username",
        "password_label": "Password",
        "show_password": "Show password",
        "hide_password": "Hide password",
        "submit": "Log in as admin",
        "invalid_credentials": "Incorrect admin credentials.",
        "too_many_attempts": (
            "Too many failed attempts. Access is blocked for up to 60 minutes."
        ),
        "attempt_policy": (
            "For security, after 10 failed attempts access from this "
            "network is blocked for 60 minutes."
        ),
        "attempts_left_one": "1 attempt left before access is blocked.",
        "attempts_left_other": "{n} attempts left before access is blocked.",
        "not_member": "Not part of the team?",
        "back_to_app": "Back to FilmAI",
        "denied_title": "Your account has no access",
        "denied_intro_before": "You\u2019re logged in as",
        "denied_intro_after": (
            ", which isn\u2019t an admin account. To view the internal "
            "documentation, log in with an account that has that permission."
        ),
        "switch_account": "Switch account",
        "back_to_home": "Back to Home",
        "home_label": "FilmAI, go to Home",
        "page_title": "Admin access · FilmAI",
        "denied_page_title": "No access · FilmAI",
    },
    "es": {
        "pill": "Documentación interna",
        "login_title": "Acceso de administración",
        "login_intro": (
            "La documentación interna es solo para el equipo de FilmAI. "
            "Ingresá con una cuenta de administración para continuar."
        ),
        "resource": {
            "schema": "el esquema OpenAPI",
            "swagger-ui": "Swagger UI",
        },
        "identifier_label": "Correo o nombre de usuario",
        "password_label": "Contraseña",
        "show_password": "Mostrar contraseña",
        "hide_password": "Ocultar contraseña",
        "submit": "Ingresar como administrador",
        "invalid_credentials": "Credenciales de administración incorrectas.",
        "too_many_attempts": (
            "Demasiados intentos fallidos. El acceso queda bloqueado hasta 60 minutos."
        ),
        "attempt_policy": (
            "Por seguridad, tras 10 intentos fallidos el acceso desde esta "
            "red se bloquea durante 60 minutos."
        ),
        "attempts_left_one": "Te queda 1 intento antes de que se bloquee el acceso.",
        "attempts_left_other": "Te quedan {n} intentos antes de que se bloquee el acceso.",
        "not_member": "¿No sos parte del equipo?",
        "back_to_app": "Volver a FilmAI",
        "denied_title": "Tu cuenta no tiene acceso",
        "denied_intro_before": "Iniciaste sesión como",
        "denied_intro_after": (
            ", que no es una cuenta de administración. Para ver la "
            "documentación interna, ingresá con una cuenta que tenga ese permiso."
        ),
        "switch_account": "Cambiar de cuenta",
        "back_to_home": "Volver al inicio",
        "home_label": "FilmAI, ir al inicio",
        "page_title": "Acceso de administración · FilmAI",
        "denied_page_title": "Sin acceso · FilmAI",
    },
}


def _ip(request):
    return request.META.get("REMOTE_ADDR", "")


def _clave_intentos(request):
    return f"docs-login:{_ip(request)}"


def _destino_seguro(request, candidato):
    """Solo vuelve a Swagger o al esquema; cualquier otro `next` se ignora."""
    if candidato in RUTAS_DOCUMENTACION and url_has_allowed_host_and_scheme(
        candidato, allowed_hosts={request.get_host()}
    ):
        return candidato
    return reverse("swagger-ui")


def _respuesta_acceso(request, *, estado, ruta, error="", restantes=None, status=403):
    """Renderiza el estado «iniciar sesión» o «sin permisos» de la página."""
    idioma = idioma_efectivo(request)
    textos = TEXTOS[idioma]
    nombre_recurso = "schema" if ruta == reverse("schema") else "swagger-ui"
    usuario = request.user
    contexto = {
        "idioma": idioma,
        "t": textos,
        "estado": estado,
        "error": error,
        "aviso_restantes": (
            textos[
                "attempts_left_one" if restantes == 1 else "attempts_left_other"
            ].format(n=restantes)
            if restantes
            else ""
        ),
        "ruta": ruta,
        "recurso": textos["resource"][nombre_recurso],
        "url_login": reverse("docs-login"),
        "url_cuenta_otra": f"{ruta}?{urlencode({'cuenta': 'otra'})}",
        "url_app": settings.FRONTEND_URL,
        "nombre_usuario": getattr(usuario, "nombre_usuario", ""),
        "titulo": (
            textos["denied_page_title"]
            if estado == "sin_permisos"
            else textos["page_title"]
        ),
    }
    return render(
        request, "filmai/documentacion_restringida.html", contexto, status=status
    )


def documentacion_para_staff(vista, recurso):
    """Muestra una salida útil antes de delegar a la vista protegida de DRF.

    El esquema negocia YAML/JSON antes de evaluar permisos. Este control
    externo permite responder HTML a un navegador que pide `text/html`, sin
    cambiar el formato que reciben los clientes de API ni el permiso interno.
    """

    @wraps(vista)
    def protegida(request, *args, **kwargs):
        usuario = request.user
        if usuario.is_authenticated and usuario.is_staff:
            respuesta = vista(request, *args, **kwargs)
        elif "text/html" in request.headers.get("Accept", "").lower():
            # `?cuenta=otra` vuelve al formulario aunque haya una sesión sin
            # permisos: es lo que hace el botón «Cambiar de cuenta».
            ofrecer_cambio = request.GET.get("cuenta") == "otra"
            sin_permisos = usuario.is_authenticated and not ofrecer_cambio
            respuesta = _respuesta_acceso(
                request,
                estado="sin_permisos" if sin_permisos else "iniciar_sesion",
                ruta=request.path,
            )
        else:
            sobre = construir_sobre(
                "documentation_staff_required", 403, debug=settings.DEBUG
            )
            respuesta = JsonResponse(
                sobre,
                status=403,
            )

        patch_cache_control(respuesta, private=True, no_store=True)
        patch_vary_headers(respuesta, ("Accept", "Accept-Language", "Cookie"))
        return respuesta

    return protegida


def _buscar_usuario(identificador):
    """Resuelve correo o nombre de usuario sin distinguir mayúsculas."""
    if "@" in identificador:
        return Usuario.objects.filter(correo__iexact=identificador).first()
    return Usuario.objects.filter(nombre_usuario__iexact=identificador).first()


@csrf_protect
@require_POST
def ingresar_a_documentacion(request):
    """Inicia la sesión de Django para consultar la documentación.

    Solo admite cuentas staff. Una cuenta común o una contraseña incorrecta
    reciben el mismo aviso, para no revelar qué identificadores existen.
    """
    destino = _destino_seguro(request, request.POST.get("next", ""))
    clave = _clave_intentos(request)
    if cache.get(clave, 0) >= INTENTOS_MAXIMOS:
        respuesta = _respuesta_acceso(
            request,
            estado="iniciar_sesion",
            error="too_many_attempts",
            ruta=destino,
            status=429,
        )
    else:
        identificador = request.POST.get("usuario", "").strip()
        password = request.POST.get("clave", "")
        candidato = _buscar_usuario(identificador) if identificador else None
        usuario = (
            authenticate(request, username=candidato.correo, password=password)
            if candidato
            else None
        )
        if usuario is not None and usuario.is_active and usuario.is_staff:
            cache.delete(clave)
            login(request, usuario)
            respuesta = redirect(destino)
        else:
            if candidato is None:
                # Iguala el costo de hashear para no revelar si la cuenta existe.
                Usuario().set_password(password)
            cache.add(clave, 0, VENTANA_SEGUNDOS)
            fallidos = cache.incr(clave)
            respuesta = _respuesta_acceso(
                request,
                estado="iniciar_sesion",
                error="invalid_credentials",
                restantes=max(INTENTOS_MAXIMOS - fallidos, 0),
                ruta=destino,
                status=403,
            )

    patch_cache_control(respuesta, private=True, no_store=True)
    patch_vary_headers(respuesta, ("Accept-Language", "Cookie"))
    return respuesta
