"""`python manage.py chatear --usuario juanp`: hablar con el bot desde la terminal.

Prueba el orquestador real sin panel ni vista. Sirve para desarrollar y para las
preguntas de prueba. Usa la clave de `.env`, así que cada mensaje tiene costo.

Es síncrono, como todo comando de Django: `async_to_sync` corre `responder()`, que
es async, y espera a que termine.
"""

import time

from asgiref.sync import async_to_sync
from django.core.management.base import BaseCommand, CommandError

from catalogo.presupuesto import contar_llamadas
from chatbot.eventos import ErrorDelTurno, Estado, Resultado, Texto
from chatbot.models import Chat, Mensaje, TipoAutor
from chatbot.orquestador import responder


class Command(BaseCommand):
    help = "Conversa con el chatbot desde la terminal."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", required=True, help="Su `nombre_usuario`.")
        parser.add_argument("--idioma", default="es", choices=["es", "en"])
        parser.add_argument("--mensaje", help="Manda solo este mensaje y termina.")
        parser.add_argument(
            "--sin-guardar",
            action="store_true",
            help="No guarda el turno: el historial del usuario queda como estaba.",
        )

    def handle(self, *args, **opciones):
        chat = Chat.objects.filter(usuario__nombre_usuario=opciones["usuario"]).first()
        if chat is None:
            raise CommandError("Ese usuario no existe o no tiene chat.")

        if opciones["mensaje"]:
            self._turno(chat, opciones["mensaje"], opciones)
            return
        self.stdout.write("Escribí tu mensaje. Con Ctrl+D salís.")
        try:
            while texto := input("\nvos> ").strip():
                self._turno(chat, texto, opciones)
        except EOFError:
            pass

    def _turno(self, chat, texto, opciones):
        """Corre un turno y lo guarda, que es lo que hará la vista en el PR 5."""
        inicio = time.perf_counter()
        try:
            resultado = async_to_sync(self._recorrer)(chat, texto, opciones["idioma"])
        except ErrorDelTurno as error:
            self.stderr.write(f"\n[error del turno: {error}]")
            return
        self.stdout.write(f"\n[{time.perf_counter() - inicio:.1f} s]")
        if not opciones["sin_guardar"]:
            Mensaje.objects.create(chat=chat, texto=texto, autor=TipoAutor.USUARIO)
            Mensaje.objects.create(
                chat=chat, texto=resultado.texto, autor=TipoAutor.CHATBOT
            )

    async def _recorrer(self, chat, texto, idioma):
        """Imprime cada evento apenas llega y devuelve el `Resultado`."""
        with contar_llamadas():
            async for evento in responder(chat, texto, idioma):
                if isinstance(evento, Estado):
                    self.stdout.write("[buscando…]")
                elif isinstance(evento, Texto):
                    self.stdout.write(evento.delta, ending="")
                    self.stdout.flush()
                elif isinstance(evento, Resultado):
                    for tarjeta in evento.tarjetas:
                        self.stdout.write(
                            f"\n[tarjeta: {tarjeta['titulo']} ({tarjeta['anio']})]",
                            ending="",
                        )
                    return evento
