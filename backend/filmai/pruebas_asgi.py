"""Llama a la aplicación ASGI de verdad (`get_asgi_application()`), sin servidor.

`AsyncClient` de Django no pasa por el manejador ASGI: arma el pedido y llama a la
vista directamente. Por eso no puede simular lo que más importa del stream del
chat: que el navegador **corte la conexión** a mitad de la respuesta. Este helper
habla el protocolo ASGI a mano (`scope`, `receive`, `send`) y manda
`http.disconnect` cuando el test lo pide.

Para ver los datos del test desde el hilo que atiende el pedido hay que usar
`TransactionTestCase`: el manejador ASGI abre un hilo propio por pedido, y ese hilo
tiene su propia conexión a la base, que no ve la transacción de un `TestCase`.
"""

import asyncio
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from django.core.asgi import get_asgi_application


@dataclass
class RespuestaASGI:
    estado: int | None = None
    encabezados: dict = field(default_factory=dict)
    trozos: list = field(default_factory=list)

    @property
    def cuerpo(self):
        return b"".join(self.trozos)

    def json(self):
        import json

        return json.loads(self.cuerpo)


async def pedir(
    metodo,
    ruta,
    *,
    cuerpo=b"",
    encabezados=None,
    desconectar_si=None,
    desconexion=None,
):
    """Hace un pedido a la aplicación ASGI y devuelve lo que ella envió.

    `desconectar_si(trozo_recibido, respuesta)` se evalúa con cada trozo del cuerpo;
    si devuelve `True`, el cliente «corta». `desconexion` (un `asyncio.Event`)
    permite cortar desde afuera, por ejemplo cuando empieza el guardado.
    """
    aplicacion = get_asgi_application()
    partes = urlsplit(ruta)
    cabeceras = [
        (b"host", b"testserver"),
        *((k.lower().encode(), v.encode()) for k, v in (encabezados or {}).items()),
    ]
    if cuerpo:
        cabeceras.append((b"content-length", str(len(cuerpo)).encode()))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": metodo,
        "scheme": "http",
        "path": partes.path,
        "raw_path": partes.path.encode(),
        "query_string": partes.query.encode(),
        "headers": cabeceras,
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }
    desconexion = desconexion or asyncio.Event()
    respuesta = RespuestaASGI()
    cuerpo_enviado = False

    async def receive():
        nonlocal cuerpo_enviado
        if not cuerpo_enviado:
            cuerpo_enviado = True
            return {"type": "http.request", "body": cuerpo, "more_body": False}
        # Después del cuerpo, el servidor real avisa solo cuando el cliente corta.
        await desconexion.wait()
        return {"type": "http.disconnect"}

    async def send(mensaje):
        if mensaje["type"] == "http.response.start":
            respuesta.estado = mensaje["status"]
            respuesta.encabezados = {
                k.decode().lower(): v.decode() for k, v in mensaje["headers"]
            }
        elif mensaje["type"] == "http.response.body":
            trozo = mensaje.get("body", b"")
            respuesta.trozos.append(trozo)
            if desconectar_si and desconectar_si(trozo, respuesta):
                desconexion.set()

    await aplicacion(scope, receive, send)
    return respuesta
