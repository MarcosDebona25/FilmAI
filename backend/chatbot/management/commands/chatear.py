"""`python manage.py chatear --usuario juanp`: hablar con el bot desde la terminal.

Prueba el orquestador real sin panel ni vista. Sirve para desarrollar y para las
preguntas de prueba. Usa la clave de `.env`, así que cada mensaje tiene costo.

Con `--golden` recorre `chatbot/golden.yaml` (el set dorado): por cada pregunta
muestra la expectativa, los eventos, las tools que pidió el modelo con sus
argumentos, y cuánto tardó el primer texto y el turno completo. No guarda nada.
Para comparar con thinking, se corre de nuevo con `LLM_THINKING=true`.

Es síncrono, como todo comando de Django: `async_to_sync` corre `responder()`, que
es async, y espera a que termine.
"""

import time
from pathlib import Path

import yaml
from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from catalogo.presupuesto import contar_llamadas
from chatbot.eventos import ErrorDelTurno, Estado, Resultado, Texto
from chatbot.llm import Vuelta, crear_proveedor
from chatbot.models import Chat, Mensaje, TipoAutor
from chatbot.orquestador import responder

GOLDEN = Path(__file__).resolve().parents[2] / "golden.yaml"
# RNF #6: segundos máximos para el turno completo.
LIMITES_RNF6 = {"simple": 5, "agregacion": 15}
_CAMPOS = {"id", "mensaje", "idioma", "rnf6", "espera"}
_OBLIGATORIOS = ("id", "mensaje", "rnf6", "espera")


def cargar_golden(ruta):
    """Las preguntas del archivo, validadas. Un archivo mal armado es un `CommandError`.

    `safe_load` y no `load`: `load` puede construir objetos de Python desde el YAML.
    """
    try:
        preguntas = yaml.safe_load(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise CommandError(f"No se pudo leer {ruta}: {error}") from error
    if not isinstance(preguntas, list) or not preguntas:
        raise CommandError(f"{ruta} tiene que ser una lista de preguntas.")

    vistos = set()
    for numero, pregunta in enumerate(preguntas, start=1):
        if not isinstance(pregunta, dict):
            raise CommandError(f"La pregunta {numero} no es un objeto.")
        if sobran := set(pregunta) - _CAMPOS:
            raise CommandError(f"La pregunta {numero} tiene campos de más: {sobran}.")
        for campo in _OBLIGATORIOS:
            if not isinstance(pregunta.get(campo), str) or not pregunta[campo].strip():
                raise CommandError(f"A la pregunta {numero} le falta `{campo}`.")
        pregunta.setdefault("idioma", "es")
        if pregunta["idioma"] not in ("es", "en"):
            raise CommandError(f"La pregunta {numero}: `idioma` es es o en.")
        if pregunta["rnf6"] not in LIMITES_RNF6:
            raise CommandError(f"La pregunta {numero}: `rnf6` es simple o agregacion.")
        if pregunta["id"] in vistos:
            raise CommandError(f"El id `{pregunta['id']}` está repetido.")
        vistos.add(pregunta["id"])
    return preguntas


class _Espia:
    """Envuelve al proveedor para mostrar qué tools pide el modelo y con qué argumentos.

    `responder()` no muestra las llamadas (solo un `Estado`). El set dorado necesita
    verlas, por ejemplo para saber si el modelo agrega `nota_minima` sin que se la
    pidan. Cumple `ProveedorLLM`, así que el orquestador no nota la diferencia.
    """

    def __init__(self, proveedor, escribir):
        self.proveedor = proveedor
        self.escribir_linea = escribir

    async def escribir(self, mensajes, esquemas):
        async for item in self.proveedor.escribir(mensajes, esquemas):
            if isinstance(item, Vuelta):
                for llamada in item.llamadas:
                    self.escribir_linea(
                        f"\n[tool: {llamada.nombre} {llamada.argumentos}]"
                    )
            yield item


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
        parser.add_argument(
            "--golden",
            nargs="?",
            const=str(GOLDEN),
            metavar="ARCHIVO",
            help="Corre el set dorado (por defecto, chatbot/golden.yaml) sin guardar.",
        )

    def handle(self, *args, **opciones):
        if opciones["golden"] and opciones["mensaje"]:
            raise CommandError("--golden y --mensaje no van juntos.")
        chat = Chat.objects.filter(usuario__nombre_usuario=opciones["usuario"]).first()
        if chat is None:
            raise CommandError("Ese usuario no existe o no tiene chat.")

        if opciones["golden"]:
            self._golden(chat, opciones["golden"])
            return
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
            resultado, _ = async_to_sync(self._recorrer)(
                chat, texto, opciones["idioma"]
            )
        except ErrorDelTurno as error:
            self.stderr.write(f"\n[error del turno: {error}]")
            return
        self.stdout.write(f"\n[{time.perf_counter() - inicio:.1f} s]")
        if not opciones["sin_guardar"]:
            Mensaje.objects.create(chat=chat, texto=texto, autor=TipoAutor.USUARIO)
            Mensaje.objects.create(
                chat=chat, texto=resultado.texto, autor=TipoAutor.CHATBOT
            )

    def _golden(self, chat, ruta):
        """Recorre el set dorado y cierra con una tabla de tiempos contra RNF #6."""
        preguntas = cargar_golden(ruta)
        configuracion = settings.LLM_PROVEEDORES[0]
        thinking = "on" if configuracion.get("thinking") else "off"
        self.stdout.write(
            f"Set dorado: {len(preguntas)} preguntas, modelo "
            f"{configuracion.get('modelo')}, thinking {thinking}."
        )
        # Un solo proveedor para todo el set, como uno por turno en la vista.
        proveedor = _Espia(crear_proveedor(), self.stdout.write)
        filas = []
        for pregunta in preguntas:
            self.stdout.write(
                f"\n\n=== {pregunta['id']} ({pregunta['idioma']}, {pregunta['rnf6']})"
                f"\nvos> {pregunta['mensaje'].strip()}"
                f"\nespera: {pregunta['espera'].strip()}\n"
            )
            inicio = time.perf_counter()
            try:
                _, primer_texto = async_to_sync(self._recorrer)(
                    chat, pregunta["mensaje"], pregunta["idioma"], proveedor
                )
            except ErrorDelTurno as error:
                self.stderr.write(f"\n[error del turno: {error}]")
                filas.append((pregunta, None, None))
                continue
            total = time.perf_counter() - inicio
            primero = primer_texto - inicio if primer_texto else None
            self.stdout.write(
                f"\n[primer texto {_segundos(primero)}, total {total:.1f} s]"
            )
            filas.append((pregunta, primero, total))
        self._resumen(filas)

    def _resumen(self, filas):
        self.stdout.write("\n\nResumen (RNF #6: simple < 5 s, agregacion < 15 s)")
        self.stdout.write(f"{'id':<26}{'primer texto':>14}{'total':>9}  RNF #6")
        for pregunta, primero, total in filas:
            limite = LIMITES_RNF6[pregunta["rnf6"]]
            if total is None:
                veredicto = "error"
            else:
                veredicto = "cumple" if total < limite else f"excede {limite} s"
            self.stdout.write(
                f"{pregunta['id']:<26}{_segundos(primero):>14}"
                f"{_segundos(total):>9}  {veredicto}"
            )

    async def _recorrer(self, chat, texto, idioma, proveedor=None):
        """Imprime cada evento apenas llega.

        Devuelve el `Resultado` y el momento del primer `Texto` (`None` si no hubo).
        """
        primer_texto = None
        with contar_llamadas():
            async for evento in responder(chat, texto, idioma, proveedor=proveedor):
                if isinstance(evento, Estado):
                    self.stdout.write("[buscando…]")
                elif isinstance(evento, Texto):
                    primer_texto = primer_texto or time.perf_counter()
                    self.stdout.write(evento.delta, ending="")
                    self.stdout.flush()
                elif isinstance(evento, Resultado):
                    for tarjeta in evento.tarjetas:
                        self.stdout.write(
                            f"\n[tarjeta: {tarjeta['titulo']} ({tarjeta['anio']})]",
                            ending="",
                        )
                    return evento, primer_texto


def _segundos(valor):
    return "—" if valor is None else f"{valor:.1f} s"
