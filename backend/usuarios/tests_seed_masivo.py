"""Pruebas del seed masivo (`seed_masivo`), con pocas cuentas y producciones."""

import random
import tempfile
from collections import Counter
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from catalogo.models import Calificacion, ProduccionAudiovisual, Resena
from chatbot.models import Chat, Mensaje
from listas.models import ClaveLista, Lista, Tiene, TipoLista
from listas.services import CLAVES_DE_ESTADO
from usuarios import corpus_resenas, seed_masivo, seed_real
from usuarios.factories import UsuarioFactory
from usuarios.models import EstadoCuenta, Usuario

GENEROS_PRUEBA = (28, 35, 18, 878)


def crear_catalogo(cantidad=40):
    """Producciones con póster de TMDB, repartidas en cuatro géneros."""
    for n in range(cantidad):
        ProduccionAudiovisual.objects.create(
            id_tmdb=1000 + n,
            tipo="pelicula" if n % 3 else "serie",
            titulo=f"Título {n}",
            poster=f"/p{n}.jpg",
            generos_ids=[GENEROS_PRUEBA[n % 4], GENEROS_PRUEBA[(n + 1) % 4]],
            calificacion_promedio=5 + (n % 5),
        )


class SeedMasivoBase(TestCase):
    def setUp(self):
        crear_catalogo()
        directorio = tempfile.TemporaryDirectory()
        self.addCleanup(directorio.cleanup)
        # Sin corpus por defecto: el archivo no existe.
        self.ruta = Path(directorio.name) / "resenas.jsonl.gz"
        parche = patch.object(corpus_resenas, "ruta_corpus", lambda: self.ruta)
        parche.start()
        self.addCleanup(parche.stop)

    def correr(self, **opciones):
        base = {"usuarios": 20, "calificaciones_medias": 8}
        salida = StringIO()
        call_command("seed_masivo", stdout=salida, **{**base, **opciones})
        return salida.getvalue()


class CuentasTests(SeedMasivoBase):
    def test_cuentas_conocidas_y_masivas(self):
        """Crea usuario001..003 con sus idiomas y masivoNNNN con la misma clave."""
        self.correr()

        self.assertEqual(Usuario.objects.count(), 23)
        for nombre, idioma in (("usuario001", "es"), ("usuario002", "en")):
            usuario = Usuario.objects.get(nombre_usuario=nombre)
            self.assertEqual(usuario.idioma, idioma)
            self.assertEqual(usuario.correo, f"{nombre}@filmai.com")
        self.assertEqual(Usuario.objects.get(nombre_usuario="usuario003").idioma, "es")
        usuario = Usuario.objects.get(correo="masivo0001@filmai.com")
        self.assertTrue(usuario.check_password("Password123!"))
        idiomas = Counter(
            Usuario.objects.filter(nombre_usuario__startswith="masivo").values_list(
                "idioma", flat=True
            )
        )
        self.assertEqual(idiomas, {"es": 10, "en": 10})

    def test_terminos_correo_y_recursos_por_defecto(self):
        """Cada cuenta acepta términos, tiene correo, 4 listas predeterminadas y chat."""
        self.correr()

        for usuario in Usuario.objects.all():
            self.assertIsNotNone(usuario.fecha_aceptacion_terminos)
            self.assertTrue(EmailAddress.objects.filter(user=usuario).exists())
            predeterminadas = Lista.objects.filter(
                usuario=usuario, tipo=TipoLista.PREDETERMINADA
            )
            self.assertEqual(
                set(predeterminadas.values_list("clave", flat=True)),
                set(ClaveLista.values),
            )
            self.assertEqual(Chat.objects.filter(usuario=usuario).count(), 1)

    def test_cuentas_sin_verificar_o_de_baja(self):
        """Con proporción 1 todas las masivas son pendientes o de baja, sin actividad."""
        with patch.object(seed_masivo, "PROPORCION_CUENTAS_ANOMALAS", 1.0):
            self.correr(usuarios=10)

        masivas = Usuario.objects.filter(nombre_usuario__startswith="masivo")
        self.assertFalse(masivas.filter(estado=EstadoCuenta.ACTIVA).exists())
        pendiente = masivas.filter(estado=EstadoCuenta.PENDIENTE).first()
        if pendiente:
            self.assertFalse(EmailAddress.objects.get(user=pendiente).verified)
        self.assertFalse(Calificacion.objects.filter(usuario__in=masivas).exists())
        self.assertTrue(Usuario.objects.get(nombre_usuario="usuario001").is_active)


class ActividadTests(SeedMasivoBase):
    def setUp(self):
        super().setUp()
        self.correr()

    def test_invariantes_de_listas(self):
        """Calificada ⇒ Vistas; Favoritos solo ≥ 9; un solo estado por título."""
        for usuario in Usuario.objects.filter(estado=EstadoCuenta.ACTIVA):
            notas = dict(
                Calificacion.objects.filter(usuario=usuario).values_list(
                    "produccion_id", "valor"
                )
            )
            estados = Counter()
            por_clave = {}
            for clave, produccion in Tiene.objects.filter(
                lista__usuario=usuario, lista__clave__in=CLAVES_DE_ESTADO
            ).values_list("lista__clave", "produccion_id"):
                estados[produccion] += 1
                por_clave.setdefault(clave, set()).add(produccion)
            self.assertTrue(all(n == 1 for n in estados.values()))
            self.assertTrue(set(notas) <= por_clave.get(ClaveLista.VISTAS, set()))
            for clave in (ClaveLista.PENDIENTES, ClaveLista.VIENDO):
                self.assertFalse(por_clave.get(clave, set()) & set(notas))
            favoritos = Tiene.objects.filter(
                lista__usuario=usuario, lista__clave=ClaveLista.FAVORITOS
            ).values_list("produccion_id", flat=True)
            for produccion in favoritos:
                self.assertGreaterEqual(notas[produccion], 9)

    def test_calificaciones_validas_y_minimo(self):
        """Notas enteras de 1 a 10 y al menos 3 calificaciones por cuenta activa."""
        for valor in Calificacion.objects.values_list("valor", flat=True):
            self.assertTrue(1 <= valor <= 10)
        for usuario in Usuario.objects.filter(estado=EstadoCuenta.ACTIVA):
            self.assertGreaterEqual(usuario.calificaciones.count(), 3)

    def test_listas_personalizadas_tematicas(self):
        """Algunas cuentas tienen exactamente 2 listas personalizadas con títulos."""
        por_usuario = Counter(
            Lista.objects.filter(tipo=TipoLista.PERSONALIZADA).values_list(
                "usuario_id", flat=True
            )
        )
        self.assertTrue(por_usuario)
        self.assertTrue(all(n == 2 for n in por_usuario.values()))
        for lista in Lista.objects.filter(tipo=TipoLista.PERSONALIZADA):
            self.assertTrue(lista.items.exists())

    def test_ochenta_por_ciento_con_resena(self):
        """El 80 % de las calificaciones lleva reseña, una por calificación."""
        total = Calificacion.objects.count()
        self.assertEqual(Resena.objects.count(), round(total * 0.8))

    def test_una_de_cada_siete_inactiva(self):
        """1 de cada 7 reseñas creadas queda con activa=False."""
        resenas = Resena.objects.count()
        self.assertEqual(Resena.objects.filter(activa=False).count(), resenas // 7)

    def test_chats_con_mensajes_para_un_subconjunto(self):
        """Hay mensajes, pero no todas las cuentas los tienen."""
        con_mensajes = Chat.objects.filter(mensajes__isnull=False).distinct().count()
        self.assertTrue(Mensaje.objects.exists())
        self.assertLess(con_mensajes, Chat.objects.count())


class TextosTests(SeedMasivoBase):
    def test_respaldo_usa_plantillas_por_genero(self):
        """Sin corpus, las reseñas salen del archivo de plantillas por género."""
        self.correr()

        permitidas = {
            texto.replace("{t}", nombre)
            for por_idioma in corpus_resenas.plantillas_genero().values()
            for por_banda in por_idioma.values()
            for textos in por_banda.values()
            for texto in textos
            for nombre in ("película", "serie", "movie", "series")
        } | {
            texto.format(t=nombre)
            for por_banda in seed_real.TEXTOS.values()
            for textos in por_banda.values()
            for texto in textos
            for nombre in ("película", "serie", "movie", "series")
        }
        textos = list(Resena.objects.values_list("texto", flat=True))
        self.assertTrue(textos)
        for texto in textos:
            self.assertIn(texto, permitidas)

    def test_respaldo_sin_corpus_usa_plantillas(self):
        """Sin corpus ni plantillas por género, sale de las de seed_real."""
        with patch.object(corpus_resenas, "plantillas_genero", return_value={}):
            self.correr()

        plantillas = {
            texto.format(t=nombre)
            for por_banda in seed_real.TEXTOS.values()
            for textos in por_banda.values()
            for texto in textos
            for nombre in ("película", "serie", "movie", "series")
        }
        for texto in Resena.objects.values_list("texto", flat=True):
            self.assertIn(texto, plantillas)

    def test_usa_el_corpus_segun_titulo_idioma_y_banda(self):
        """Con corpus completo, el texto es uno de los de esa entrada."""
        entradas = {}
        for p in ProduccionAudiovisual.objects.all():
            tipo = corpus_resenas.TIPO_MODELO_A_CORPUS[p.tipo]
            for idioma in corpus_resenas.IDIOMAS:
                for banda in corpus_resenas.BANDAS:
                    entradas[(p.id_tmdb, tipo, idioma, banda)] = [
                        f"Texto A {p.id_tmdb} {idioma} {banda} con largo suficiente",
                        f"Texto B {p.id_tmdb} {idioma} {banda} con largo suficiente",
                    ]
        corpus_resenas.escribir_corpus(entradas)

        self.correr()

        for resena in Resena.objects.select_related("calificacion__produccion"):
            calificacion = resena.calificacion
            produccion = calificacion.produccion
            idioma = calificacion.usuario.idioma
            banda = corpus_resenas.banda_de_nota(calificacion.valor)
            tipo = corpus_resenas.TIPO_MODELO_A_CORPUS[produccion.tipo]
            self.assertIn(
                resena.texto, entradas[(produccion.id_tmdb, tipo, idioma, banda)]
            )

    def test_entrada_vacia_cae_a_plantillas(self):
        """Una entrada del corpus sin textos no se usa: se cae a las plantillas."""
        catalogo = seed_masivo.Catalogo(42)
        i = 0
        clave = (
            catalogo.id_tmdb[i],
            corpus_resenas.TIPO_MODELO_A_CORPUS[catalogo.tipo[i]],
            "es",
            "alta",
        )

        with patch.object(corpus_resenas, "plantillas_genero", return_value={}):
            texto = seed_masivo._texto(
                catalogo, i, "es", 9, {clave: []}, random.Random(1)
            )

        self.assertIn(
            texto,
            [t.format(t="película") for t in seed_real.TEXTOS["es"]["alta"]]
            + [t.format(t="serie") for t in seed_real.TEXTOS["es"]["alta"]],
        )

    def test_sin_corpus_usa_la_plantilla_del_genero(self):
        """Sin entrada por título, la frase sale de un género que tiene el título."""
        catalogo = seed_masivo.Catalogo(42)
        i = next(k for k, g in enumerate(catalogo.generos) if g)
        genero = sorted(catalogo.generos[i])[0]
        plantillas = {genero: {"es": {"alta": ["Frase del género {t}."]}}}

        with patch.object(corpus_resenas, "plantillas_genero", return_value=plantillas):
            texto = seed_masivo._texto(catalogo, i, "es", 9, {}, random.Random(1))

        self.assertIn(texto, ["Frase del género película.", "Frase del género serie."])


class IdempotenciaYDeterminismoTests(SeedMasivoBase):
    def instantanea(self):
        return sorted(
            Calificacion.objects.values_list(
                "usuario__correo", "produccion__id_tmdb", "valor"
            )
        ), sorted(Resena.objects.values_list("texto", "activa"))

    def test_repetir_no_crece(self):
        """Sin --reiniciar, una segunda corrida no agrega ni borra nada."""
        self.correr()
        antes = (Usuario.objects.count(), Calificacion.objects.count())
        instantanea = self.instantanea()

        salida = self.correr()

        self.assertEqual(antes, (Usuario.objects.count(), Calificacion.objects.count()))
        self.assertEqual(instantanea, self.instantanea())
        self.assertIn("a crear: 0", salida)

    def test_agrega_solo_las_que_faltan(self):
        """Pedir más cuentas suma solo las nuevas y deja intactas las viejas."""
        self.correr(usuarios=5)
        viejas = Calificacion.objects.filter(
            usuario__nombre_usuario="masivo0001"
        ).count()

        self.correr(usuarios=8)

        self.assertEqual(Usuario.objects.count(), 11)
        self.assertEqual(
            Calificacion.objects.filter(usuario__nombre_usuario="masivo0001").count(),
            viejas,
        )

    def test_determinista_con_la_semilla(self):
        """Misma semilla ⇒ mismos datos; otra semilla ⇒ otros."""
        self.correr(semilla=7, reiniciar=True)
        primera = self.instantanea()
        self.correr(semilla=7, reiniciar=True)
        self.assertEqual(primera, self.instantanea())
        self.correr(semilla=8, reiniciar=True)
        self.assertNotEqual(primera, self.instantanea())


class ReiniciarTests(SeedMasivoBase):
    def test_conserva_staff_y_catalogo(self):
        """--reiniciar borra lo no staff y deja staff, sus listas y el catálogo."""
        staff = UsuarioFactory.create(
            nombre_usuario="administrador1", is_staff=True, correo="adm@filmai.com"
        )
        EmailAddress.objects.create(
            user=staff, email=staff.correo, verified=True, primary=True
        )
        ajeno = UsuarioFactory.create(nombre_usuario="otraCuenta1")
        catalogo = ProduccionAudiovisual.objects.count()
        listas_staff = Lista.objects.filter(usuario=staff).count()
        self.correr(usuarios=5)

        self.correr(usuarios=5, reiniciar=True)

        self.assertTrue(Usuario.objects.filter(pk=staff.pk).exists())
        self.assertTrue(EmailAddress.objects.filter(user=staff).exists())
        self.assertEqual(Lista.objects.filter(usuario=staff).count(), listas_staff)
        self.assertEqual(Chat.objects.filter(usuario=staff).count(), 1)
        self.assertFalse(Usuario.objects.filter(pk=ajeno.pk).exists())
        self.assertEqual(ProduccionAudiovisual.objects.count(), catalogo)
        self.assertEqual(Usuario.objects.filter(is_staff=False).count(), 8)

    def test_sin_reiniciar_no_borra_cuentas_ajenas(self):
        """Sin --reiniciar, las cuentas existentes quedan donde estaban."""
        ajeno = UsuarioFactory.create(nombre_usuario="otraCuenta1")

        self.correr(usuarios=2)

        self.assertTrue(Usuario.objects.filter(pk=ajeno.pk).exists())

    def test_catalogo_insuficiente(self):
        """Con menos de 20 producciones elegibles aborta sin crear nada."""
        ProduccionAudiovisual.objects.filter(id_tmdb__gte=1010).delete()

        with self.assertRaises(CommandError):
            self.correr()

        self.assertFalse(Usuario.objects.exists())


class CantidadTests(TestCase):
    def test_cola_larga_con_la_media_pedida(self):
        """La media de las cantidades ronda la pedida, con mínimo 3 y máximo 300."""
        azar = seed_masivo._azar(1, "x")
        cantidades = [
            seed_masivo.cantidad_calificaciones(azar, 38) for _ in range(4000)
        ]

        self.assertTrue(30 <= sum(cantidades) / len(cantidades) <= 46)
        self.assertGreaterEqual(min(cantidades), 3)
        self.assertLessEqual(max(cantidades), 300)
        self.assertGreater(max(cantidades), 150)
