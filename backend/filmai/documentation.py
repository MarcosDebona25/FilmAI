"""Acceso y respuesta de ayuda para la documentación de la API."""

from functools import wraps
from urllib.parse import urlencode

from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.cache import patch_cache_control, patch_vary_headers


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
            url_login = f"{reverse('admin:login')}?{urlencode({'next': request.get_full_path()})}"
            respuesta = render(
                request,
                "filmai/documentacion_restringida.html",
                {
                    "recurso": recurso,
                    "url_login": url_login,
                    "sesion_iniciada": usuario.is_authenticated,
                },
                status=403,
            )
        else:
            respuesta = JsonResponse(
                {
                    "detail": "Para consultar esta documentación, ingresá al Admin con una cuenta staff."
                },
                status=403,
            )

        patch_cache_control(respuesta, private=True, no_store=True)
        patch_vary_headers(respuesta, ("Accept", "Cookie"))
        return respuesta

    return protegida
