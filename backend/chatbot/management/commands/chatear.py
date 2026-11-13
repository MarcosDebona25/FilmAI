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
from datetime import timedelta
from pathlib import Path

import yaml
from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from catalogo.presupuesto import contar_llamadas
from chatbot.eventos import ErrorDelTurno, Estado, Resultado, Texto
from chatbot.llm import Vuelta, crear_proveedor
from chatbot.models import Chat, Mensaje, TipoAutor
from chatbot.orquestador import responder

GOLDEN = Path(__file__).resolve().parents[2] / "golden.yaml"
# RNF #6: segundos máximos para el turno completo.
LIMITES_RNF6 = {"simple": 5, "agregacion": 15}
_CAMPOS = {"id", "mensaje", "idioma", "rnf6", "espera", "historial"}
_OBLIGATORIOS = ("id", "mensaje", "rnf6", "espera")
# Un mensaje previo de un caso con `historial`: quién lo escribió y qué dijo. Solo el
# asistente lleva `tarjetas`, como las que quedan guardadas en `Mensaje.tarjetas`.
# `hace_min` (opcional) lo fecha hace tantos minutos: con más que la ventana de sesión
# (`CHAT_VENTANA_SESION_MINUTOS`), el mensaje es de otra sesión y el modelo no lo ve.
_CAMPOS_DE_MENSAJE = {"autor", "texto", "tarjetas", "hace_min"}
_AUTORES = {"usuario": TipoAutor.USUARIO, "asistente": TipoAutor.CHATBOT}


def _validar_historial(numero, historial):
    """Revisa el `historial` de una pregunta. Un error es un `CommandError` claro."""
    donde = f"La pregunta {numero}, `historial`"
    if not isinstance(historial, list) or not historial:
        raise CommandError(f"{donde}: tiene que ser una lista no vacía.")
    for orden, mensaje in enumerate(historial, start=1):
        if not isinstance(mensaje, dict):
            raise CommandError(f"{donde}, mensaje {orden}: no es un objeto.")
        if sobran := set(mensaje) - _CAMPOS_DE_MENSAJE:
            raise CommandError(f"{donde}, mensaje {orden}: campos de más {sobran}.")
        if mensaje.get("autor") not in _AUTORES:
            raise CommandError(
                f"{donde}, mensaje {orden}: `autor` es usuario o asistente."
            )
        texto = mensaje.get("texto")
        if not isinstance(texto, str) or not texto.strip():
            raise CommandError(f"{donde}, mensaje {orden}: falta `texto`.")
        hace_min = mensaje.get("hace_min", 0)
        # `bool` es un `int` en Python (`True == 1`): se descarta aparte.
        if isinstance(hace_min, bool) or not isinstance(hace_min, int) or hace_min < 0:
            raise CommandError(
                f"{donde}, mensaje {orden}: `hace_min` es un entero de 0 o más."
            )
        tarjetas = mensaje.get("tarjetas", [])
        if tarjetas and mensaje["autor"] != "asistente":
            raise CommandError(
                f"{donde}, mensaje {orden}: solo el asistente lleva tarjetas."
            )
        if not isinstance(tarjetas, list) or not all(
            isinstance(t, dict)
            and isinstance(t.get("id_tmdb"), int)
            and t.get("tipo") in ("movie", "tv")
            and isinstance(t.get("titulo"), str)
            for t in tarjetas
        ):
            raise CommandError(
                f"{donde}, mensaje {orden}: cada tarjeta lleva `id_tmdb`, `tipo` y `titulo`."
            )


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
        if "historial" in pregunta:
            _validar_historial(numero, pregunta["historial"])
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

    async def escribir(self, mensajes, esquemas, tool_choice=None):
        if not esquemas:
            # La última llamada del orquestador va sin tools: sirve para contarlas.
            self.escribir_linea("\n[última llamada sin tools]")
        if tool_choice:
            self.escribir_linea(f"\n[reintento forzado: tool_choice={tool_choice}]")
        async for item in self.proveedor.escribir(mensajes, esquemas, tool_choice):
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
            error, primer_texto = None, None
            # Los mensajes previos del caso se crean y se deshacen con la pregunta:
            # `set_rollback(True)` hace que `atomic` revierta todo al salir, haya
            # salido bien o mal el turno. Es como un `@Transactional` con rollback.
            with transaction.atomic():
                self._sembrar(chat, pregunta.get("historial", []))
                try:
                    _, primer_texto = async_to_sync(self._recorrer)(
                        chat, pregunta["mensaje"], pregunta["idioma"], proveedor
                    )
                except ErrorDelTurno as falla:
                    error = falla
                transaction.set_rollback(True)
            if error:
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

    def _sembrar(self, chat, historial):
        """Crea los mensajes previos de un caso, en orden, como si ya hubieran pasado."""
        for mensaje in historial:
            creado = Mensaje.objects.create(
                chat=chat,
                autor=_AUTORES[mensaje["autor"]],
                texto=mensaje["texto"],
                tarjetas=mensaje.get("tarjetas", []),
            )
            if hace_min := mensaje.get("hace_min"):
                # `auto_now_add` pisa la fecha al crear: se corrige con `update`, que
                # va directo al SQL.
                Mensaje.objects.filter(pk=creado.pk).update(
                    fecha_hora=timezone.now() - timedelta(minutes=hace_min)
                )
        if historial:
            self.stdout.write(
                f"[historial previo: {len(historial)} mensajes, no se guarda]"
            )

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
