"""Pruebas de los comandos del corpus de reseñas (preparar y compilar)."""

import gzip
import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from catalogo.models import ProduccionAudiovisual
from usuarios import corpus_resenas
from usuarios.management.commands import preparar_corpus_resenas as preparar
from usuarios.management.commands.preparar_corpus_resenas import recortar

TEXTO_A = "Una reseña de prueba con largo suficiente para validar."
TEXTO_B = "Otra reseña distinta, también con largo suficiente."


def linea(id_tmdb=1, tipo="movie", idioma="es", banda="alta", textos=None):
    return json.dumps(
        {
            "id_tmdb": id_tmdb,
            "tipo": tipo,
            "idioma": idioma,
            "banda": banda,
            "textos": [TEXTO_A, TEXTO_B] if textos is None else textos,
        }
    )


class CorpusBase(TestCase):
    def setUp(self):
        carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        self.dir = Path(carpeta.name)
        self.ruta = self.dir / "corpus" / "resenas.jsonl.gz"
        parche = patch.object(corpus_resenas, "ruta_corpus", lambda: self.ruta)
        parche.start()
        self.addCleanup(parche.stop)


class CompilarTests(CorpusBase):
    def compilar(self, *lineas, nombre="salida_01.jsonl"):
        entrada = self.dir / "entrada"
        entrada.mkdir(exist_ok=True)
        (entrada / nombre).write_text("\n".join(lineas) + "\n", encoding="utf-8")
        salida, error = StringIO(), StringIO()
        call_command(
            "compilar_corpus_resenas", str(entrada), stdout=salida, stderr=error
        )
        return salida.getvalue(), error.getvalue()

    def test_valida_y_descarta_las_invalidas(self):
        """Informa válidas e inválidas y guarda solo las válidas."""
        salida, error = self.compilar(
            linea(1),
            linea(2, idioma="fr"),
            linea(3, banda="extrema"),
            linea(4, tipo="serie"),
            linea(5, textos=[TEXTO_A]),
            linea(6, textos=[TEXTO_A, TEXTO_A]),
            linea(7, textos=["corto", TEXTO_B]),
            linea(8, textos=[TEXTO_A, "x" * 401]),
            linea(9, textos=[TEXTO_A, "   "]),
            "no es json",
        )

        self.assertIn("válidas: 1", salida)
        self.assertIn("Inválidas: 9", salida)
        self.assertIn("Total en el corpus: 1", salida)
        self.assertEqual(error.count("salida_01.jsonl:"), 9)
        self.assertEqual(
            list(corpus_resenas.cargar_corpus()), [(1, "movie", "es", "alta")]
        )

    def test_las_nuevas_pisan_a_las_viejas(self):
        """Fusiona con el corpus existente; la misma clave se reemplaza."""
        self.compilar(linea(1), linea(2))
        nuevos = [f"{TEXTO_A} (nuevo)", f"{TEXTO_B} (nuevo)"]

        salida, _ = self.compilar(linea(1, textos=nuevos), nombre="salida_02.jsonl")

        corpus = corpus_resenas.cargar_corpus()
        self.assertEqual(corpus[(1, "movie", "es", "alta")], nuevos)
        self.assertIn((2, "movie", "es", "alta"), corpus)
        self.assertIn("Total en el corpus: 2", salida)

    def test_orden_y_bytes_deterministas(self):
        """El orden de entrada no cambia el archivo: ordenado y gzip con mtime=0."""
        self.compilar(linea(2), linea(1, idioma="en"), linea(1, idioma="es"))
        primero = self.ruta.read_bytes()
        self.ruta.unlink()

        self.compilar(linea(1, idioma="es"), linea(1, idioma="en"), linea(2))

        self.assertEqual(primero, self.ruta.read_bytes())
        with gzip.open(self.ruta, "rt", encoding="utf-8") as archivo:
            claves = [
                (e["id_tmdb"], e["tipo"], e["idioma"], e["banda"])
                for e in map(json.loads, archivo)
            ]
        self.assertEqual(claves, sorted(claves))
        self.assertEqual(primero[4:8], b"\x00\x00\x00\x00")

    def test_sin_archivos_de_salida(self):
        """Un directorio sin salida_*.jsonl es un error."""
        with self.assertRaises(CommandError):
            call_command("compilar_corpus_resenas", str(self.dir), stdout=StringIO())


class PrepararTests(CorpusBase):
    def setUp(self):
        super().setUp()
        for n in range(1, 8):
            ProduccionAudiovisual.objects.create(
                id_tmdb=n,
                tipo="pelicula" if n % 2 else "serie",
                titulo=f"Título {n}",
                poster=f"/p{n}.jpg",
                sinopsis="palabra " * 100,
                generos=["Drama"],
                calificacion_promedio=float(n),
            )
        # Sin póster, sin sinopsis y lápida: quedan afuera.
        ProduccionAudiovisual.objects.create(id_tmdb=50, tipo="pelicula", titulo="Sin")
        ProduccionAudiovisual.objects.create(
            id_tmdb=51, tipo="pelicula", titulo="Sin promedio", poster="/x.jpg"
        )
        ProduccionAudiovisual.objects.create(
            id_tmdb=52,
            tipo="pelicula",
            titulo="Lápida",
            poster="/l.jpg",
            calificacion_promedio=10,
            disponible_en_tmdb=False,
        )
        self.salida = self.dir / "lotes"

    def preparar(self, **opciones):
        call_command(
            "preparar_corpus_resenas",
            salida=str(self.salida),
            stdout=StringIO(),
            **{"top": 5, "lote": 2, **opciones},
        )

    def leer(self, nombre):
        return json.loads((self.salida / nombre).read_text(encoding="utf-8"))

    def test_lotes_en_orden_de_insercion(self):
        """Escribe lotes de hasta --lote, en orden de inserción (proxy de popularidad), con el esquema."""
        self.preparar()

        archivos = sorted(p.name for p in self.salida.glob("entrada_*.json"))
        self.assertEqual(
            archivos, ["entrada_0001.json", "entrada_0002.json", "entrada_0003.json"]
        )
        primero = self.leer("entrada_0001.json")
        self.assertEqual([i["id_tmdb"] for i in primero], [1, 2])
        self.assertEqual(
            set(primero[0]),
            {"id_tmdb", "tipo", "titulo", "anio", "generos", "sinopsis"},
        )
        self.assertEqual(primero[0]["tipo"], "movie")
        self.assertEqual(primero[1]["tipo"], "tv")
        self.assertLessEqual(len(primero[0]["sinopsis"]), 300)
        self.assertEqual(len(self.leer("entrada_0003.json")), 1)

    def test_salta_producciones_ya_en_el_corpus(self):
        """Las que ya tienen las seis entradas no vuelven a salir."""
        entradas = {
            (1, "movie", idioma, banda): [TEXTO_A, TEXTO_B]
            for idioma in corpus_resenas.IDIOMAS
            for banda in corpus_resenas.BANDAS
        }
        corpus_resenas.escribir_corpus(entradas)

        self.preparar(top=2)

        ids = [i["id_tmdb"] for i in self.leer("entrada_0001.json")]
        self.assertEqual(ids, [2, 3])

    def test_omitir_existentes_continua_la_numeracion(self):
        """Con --omitir-existentes no repite lo ya escrito en la carpeta."""
        self.preparar(top=2)

        self.preparar(top=2, omitir_existentes=True)

        self.assertEqual([i["id_tmdb"] for i in self.leer("entrada_0002.json")], [3, 4])

    def test_por_votos_ordena_por_el_ranking_de_tmdb(self):
        """Con --por-votos manda el orden de `discover`, 3 películas por serie."""
        paginas = {
            ("movie", 1): [5, 3],
            ("movie", 2): [1, 7],
            ("tv", 1): [6, 2],
        }

        class Servicio:
            def discover(self, tipo, page, sort_by):
                self.orden = sort_by
                return {"results": [{"id": i} for i in paginas.get((tipo, page), [])]}

        servicio = Servicio()
        with patch.object(preparar, "get_catalog_service", return_value=servicio):
            self.preparar(top=4, por_votos=3)

        self.assertEqual(servicio.orden, "vote_count.desc")
        ids = [i["id_tmdb"] for i in self.leer("entrada_0001.json")]
        ids += [i["id_tmdb"] for i in self.leer("entrada_0002.json")]
        self.assertEqual(ids, [5, 3, 1, 6])

    def test_por_votos_salta_lo_que_no_esta_en_el_catalogo(self):
        """Un título del ranking que no está en la base no genera lote."""

        class Servicio:
            def discover(self, tipo, page, sort_by):
                ids = {"movie": [999, 3], "tv": []}[tipo] if page == 1 else []
                return {"results": [{"id": i} for i in ids]}

        with patch.object(preparar, "get_catalog_service", return_value=Servicio()):
            self.preparar(top=5, por_votos=1)

        self.assertEqual([i["id_tmdb"] for i in self.leer("entrada_0001.json")], [3])

    def test_recortar_sinopsis(self):
        """Recorta en una palabra entera y marca el corte con «…»."""
        texto = recortar("palabra " * 100)
        self.assertLessEqual(len(texto), 300)
        self.assertTrue(texto.endswith("palabra…"))
        self.assertEqual(recortar("corta"), "corta")
