"""Lo que se sabe del usuario y cómo se limpia antes de mandarlo al proveedor."""

from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase

from catalogo.models import (
    Calificacion,
    ProduccionAudiovisual,
    Resena,
    TipoProduccion,
)
from chatbot.anonimizar import CONVERSACION, ESTRICTO, anonimizar
from chatbot.contexto import armar_perfil
from listas.models import ClaveLista, Lista, Tiene
from usuarios.factories import UsuarioFactory

JUAN = SimpleNamespace(nombre="Juan", apellido="Pérez", nombre_usuario="juanp")
MARK = SimpleNamespace(nombre="Mark", apellido="Debona", nombre_usuario="mark")


class AlcanceEstrictoTests(SimpleTestCase):
    def limpiar(self, texto, usuario=JUAN):
        return anonimizar(texto, usuario, ESTRICTO)

    def test_un_nombre_suelto_se_reemplaza(self):
        self.assertEqual(self.limpiar("Juan aprueba"), "[usuario] aprueba")

    def test_nombre_y_apellido_juntos_son_un_solo_reemplazo(self):
        self.assertEqual(self.limpiar("Cumple de Juan Pérez"), "Cumple de [usuario]")

    def test_ignora_mayusculas_y_tildes(self):
        self.assertEqual(self.limpiar("JUAN perez"), "[usuario]")
        self.assertEqual(self.limpiar("el señor PEREZ"), "el señor [usuario]")

    def test_el_usuario_se_reemplaza(self):
        self.assertEqual(self.limpiar("visto por juanp"), "visto por [usuario]")

    def test_solo_palabras_enteras(self):
        self.assertEqual(self.limpiar("Don Juanito y juanpi"), "Don Juanito y juanpi")
        self.assertEqual(self.limpiar("SanJuan queda"), "SanJuan queda")

    def test_un_nombre_compuesto_se_reemplaza_por_partes(self):
        maria = SimpleNamespace(
            nombre="María José", apellido="de la Cruz", nombre_usuario="mjc"
        )

        self.assertEqual(
            self.limpiar("María dijo que la Cruz de José", maria),
            "[usuario] dijo que la [usuario] de [usuario]",
        )

    def test_conserva_el_resto_del_texto_con_sus_tildes(self):
        self.assertEqual(
            self.limpiar("Película increíble, dijo Juan."),
            "Película increíble, dijo [usuario].",
        )


class AlcanceConversacionTests(SimpleTestCase):
    def limpiar(self, texto, usuario=JUAN):
        return anonimizar(texto, usuario, CONVERSACION)

    def test_el_mensaje_del_spec(self):
        self.assertEqual(
            self.limpiar("soy Juan Pérez, mi correo es juan@example.com, recomendame"),
            "soy [usuario], mi correo es [correo], recomendame",
        )

    def test_un_nombre_suelto_se_queda(self):
        self.assertEqual(self.limpiar("algo con Juan Diego"), "algo con Juan Diego")

    def test_el_usuario_se_reemplaza(self):
        self.assertEqual(self.limpiar("soy juanp"), "soy [usuario]")

    def test_un_usuario_igual_al_nombre_se_queda(self):
        # Mark Debona, usuario `mark`, tiene que poder pedir a Mark Ruffalo.
        self.assertEqual(
            self.limpiar("algo con Mark Ruffalo", MARK), "algo con Mark Ruffalo"
        )

    def test_nombre_completo_con_usuario_igual_al_nombre(self):
        self.assertEqual(self.limpiar("soy Mark Debona", MARK), "soy [usuario]")


class ApostrofosYTildesTests(SimpleTestCase):
    """Lo que se ve igual tiene que anonimizarse igual, aunque sean otros caracteres."""

    OCONNOR = SimpleNamespace(nombre="Sean", apellido="O'Connor", nombre_usuario="soc")

    def test_el_apostrofo_curvo_vale_como_el_recto(self):
        # El teclado del celular escribe «O'Connor» con el apóstrofo curvo (U+2019).
        self.assertEqual(
            anonimizar("Hola O\u2019Connor", self.OCONNOR, ESTRICTO), "Hola [usuario]"
        )

    def test_el_nombre_guardado_con_apostrofo_curvo_tambien_se_anonimiza(self):
        curvo = SimpleNamespace(
            nombre="Sean", apellido="O\u2019Connor", nombre_usuario="soc"
        )

        self.assertEqual(anonimizar("Hola O'Connor", curvo, ESTRICTO), "Hola [usuario]")

    def test_un_nombre_guardado_descompuesto_se_anonimiza(self):
        # «é» puede guardarse como «e» + tilde suelta (NFD): se ve igual, pero son
        # otros caracteres.
        nfd = SimpleNamespace(
            nombre="Jose\u0301", apellido="Pe\u0301rez", nombre_usuario="jp"
        )

        for alcance in (ESTRICTO, CONVERSACION):
            with self.subTest(alcance):
                self.assertEqual(
                    anonimizar("Hola José Pérez", nfd, alcance), "Hola [usuario]"
                )

    def test_las_letras_que_no_se_descomponen_se_pliegan_a_su_base(self):
        # La i sin punto (turco), `ł ø đ ð ħ ŧ` no son «letra + tilde»: Unicode no las descompone, así que
        # «Łukasz» y «Lukasz» eran para el programa dos palabras distintas.
        casos = (
            ("Łukasz", "Lukasz"),
            ("Søren", "Soren"),
            ("I\u015f\u0131k", "Isik"),  # Isik turco, con la i sin punto
            ("Đorđe", "Dorde"),
            ("Ħamrun", "Hamrun"),
            ("Guðrún", "Gudrun"),
            ("Aŧila", "Atila"),
            ("Łódź", "Lodz"),
        )
        for guardado, escrito in casos:
            usuario = SimpleNamespace(
                nombre=guardado, apellido="Ramos", nombre_usuario="xyz"
            )
            with self.subTest(guardado=guardado):
                # Guardado con la letra rara, escrito sin ella...
                self.assertEqual(
                    anonimizar(f"Hola {escrito} Ramos", usuario, ESTRICTO),
                    "Hola [usuario]",
                )
                # ...y al revés: guardado sin ella, escrito con ella.
                al_reves = SimpleNamespace(
                    nombre=escrito, apellido="Ramos", nombre_usuario="xyz"
                )
                self.assertEqual(
                    anonimizar(f"Hola {guardado} Ramos", al_reves, ESTRICTO),
                    "Hola [usuario]",
                )

    def test_las_letras_dobles_valen_como_sus_dos_letras(self):
        # `ß æ œ þ` se escriben con dos letras en un teclado sin ellas.
        casos = (
            ("Strauß", "Strauss"),
            ("Æsop", "Aesop"),
            ("Œdipe", "Oedipe"),
            ("Þór", "Thor"),
        )
        for letra, pares in casos:
            # Guardado con la letra, escrito con su par; y al revés.
            for guardado, escrito in ((letra, pares), (pares, letra)):
                usuario = SimpleNamespace(
                    nombre=guardado, apellido="", nombre_usuario="xyz"
                )
                with self.subTest(guardado=guardado, escrito=escrito):
                    self.assertEqual(
                        anonimizar(f"Hola {escrito}", usuario, ESTRICTO),
                        "Hola [usuario]",
                    )

    def test_un_mensaje_descompuesto_no_corre_los_reemplazos(self):
        # `anonimizar()` pasa el mensaje a NFC antes de plegarlo, así que las posiciones
        # siguen coincidiendo aunque haya una tilde suelta antes del nombre.
        self.assertEqual(
            anonimizar("cafe\u0301, soy Mark Debona", MARK, ESTRICTO),
            "café, soy [usuario]",
        )

    def test_el_usuario_igual_al_nombre_se_queda_aunque_este_descompuesto(self):
        nfd = SimpleNamespace(
            nombre="Jose\u0301", apellido="Perez", nombre_usuario="josé"
        )

        self.assertEqual(
            anonimizar("algo con José Ruffalo", nfd, CONVERSACION),
            "algo con José Ruffalo",
        )


class CorreosTests(SimpleTestCase):
    def test_cualquier_correo_en_los_dos_alcances(self):
        for alcance in (ESTRICTO, CONVERSACION):
            with self.subTest(alcance):
                self.assertEqual(
                    anonimizar(
                        "escribí a otra.persona+x@mail.com.ar, gracias", JUAN, alcance
                    ),
                    "escribí a [correo], gracias",
                )

    def test_un_apostrofo_en_la_parte_local_es_parte_del_correo(self):
        # `o'neil@gmail.com` es un correo válido: no puede quedar «o'[correo]».
        for escrito in ("o'neil@gmail.com", "o\u2019neil@gmail.com"):
            with self.subTest(escrito):
                self.assertEqual(
                    anonimizar(f"escribí a {escrito}, gracias", JUAN, ESTRICTO),
                    "escribí a [correo], gracias",
                )

    def test_otros_signos_validos_en_la_parte_local(self):
        self.assertEqual(
            anonimizar("es a#b!c%d@mail.com", JUAN, CONVERSACION), "es [correo]"
        )

    def test_un_usuario_llamado_correo_no_rompe_el_reemplazo(self):
        raro = SimpleNamespace(nombre="Correo", apellido="Usuario", nombre_usuario="c1")

        self.assertEqual(
            anonimizar("a@b.co de Correo", raro, ESTRICTO), "[correo] de [usuario]"
        )


class ArmarPerfilTests(TestCase):
    def setUp(self):
        self.usuario = UsuarioFactory(
            nombre="Juan", apellido="Perez", nombre_usuario="juanp"
        )
        self.proximo_id = 1

    def produccion(self, titulo):
        produccion = ProduccionAudiovisual.objects.create(
            id_tmdb=self.proximo_id, tipo=TipoProduccion.PELICULA, titulo=titulo
        )
        self.proximo_id += 1
        return produccion

    def calificar(self, titulo, valor, resena=None, activa=True):
        calificacion = Calificacion.objects.create(
            usuario=self.usuario,
            produccion=self.produccion(titulo),
            valor=valor,
            activa=activa,
        )
        if resena:
            Resena.objects.create(calificacion=calificacion, texto=resena)
        return calificacion

    def agregar(self, clave, titulo):
        lista, _ = Lista.objects.get_or_create(
            usuario=self.usuario, clave=clave, defaults={"nombre": clave}
        )
        Tiene.objects.create(lista=lista, produccion=self.produccion(titulo))

    def linea(self, inicio):
        lineas = armar_perfil(self.usuario).splitlines()
        return next((linea for linea in lineas if linea.startswith(inicio)), "")

    def test_sin_datos_no_hay_perfil(self):
        self.assertEqual(armar_perfil(self.usuario), "")

    def test_separa_lo_que_le_gusto_de_lo_que_no(self):
        self.calificar("Arrival", 9)
        self.calificar("Transformers", 2)
        self.calificar("Tibia", 5)

        self.assertIn("Arrival (9)", self.linea("Le gustó"))
        self.assertIn("Transformers (2)", self.linea("No le gustó"))
        self.assertNotIn("Tibia", armar_perfil(self.usuario))

    def test_los_limites_de_nota_son_7_y_4(self):
        self.calificar("Justa arriba", 7)
        self.calificar("Justa abajo", 4)

        self.assertIn("Justa arriba", self.linea("Le gustó"))
        self.assertIn("Justa abajo", self.linea("No le gustó"))

    def test_lo_mejor_calificado_va_primero_y_hay_tope_de_15(self):
        for i in range(16):
            self.calificar(f"T{i:02}", 7)
        self.calificar("La mejor", 10)

        linea = self.linea("Le gustó")

        self.assertTrue(linea.startswith("Le gustó (nota ≥ 7): La mejor (10)"))
        self.assertEqual(linea.count("(7)"), 14)

    def test_lo_peor_calificado_va_primero_y_hay_tope_de_10(self):
        for i in range(11):
            self.calificar(f"T{i:02}", 4)
        self.calificar("La peor", 1)

        linea = self.linea("No le gustó")

        self.assertTrue(linea.startswith("No le gustó (nota ≤ 4): La peor (1)"))
        self.assertEqual(linea.count("(4)"), 9)

    def test_una_calificacion_inactiva_no_cuenta(self):
        self.calificar("Borrada", 9, activa=False)

        self.assertEqual(armar_perfil(self.usuario), "")

    def test_la_resena_va_recortada_a_160_caracteres(self):
        self.calificar("Moon", 8, resena="a" * 200)

        extracto = self.linea("Le gustó").split("«")[1].split("»")[0]

        self.assertEqual(len(extracto), 160)
        self.assertTrue(extracto.endswith("…"))

    def test_la_resena_se_anonimiza(self):
        self.calificar("Moon", 8, resena="Juan aprueba, escribime a j@x.com")

        self.assertIn(
            "«[usuario] aprueba, escribime a [correo]»", self.linea("Le gustó")
        )

    def test_los_saltos_de_linea_de_una_resena_no_rompen_el_perfil(self):
        self.calificar("Moon", 8, resena="uno\n\nNo le gustó: todo")

        self.assertIn("«uno No le gustó: todo»", self.linea("Le gustó"))
        self.assertEqual(len(armar_perfil(self.usuario).splitlines()), 1)

    def test_el_titulo_no_se_anonimiza(self):
        # Es catálogo: «[usuario] Wick» solo ensuciaría el dato.
        self.calificar("Juan Wick", 8)

        self.assertIn("Juan Wick (8)", self.linea("Le gustó"))

    def test_ultimas_vistas_con_lo_mas_nuevo_primero_y_tope_de_10(self):
        for i in range(11):
            self.agregar(ClaveLista.VISTAS, f"T{i:02}")

        linea = self.linea("Últimas vistas")

        self.assertTrue(linea.startswith("Últimas vistas: T10, T09"))
        self.assertNotIn("T00", linea)

    def test_favoritos_con_tope_de_10(self):
        for i in range(11):
            self.agregar(ClaveLista.FAVORITOS, f"T{i:02}")

        self.assertEqual(self.linea("Favoritos").count(","), 9)

    def test_cambiar_una_nota_la_mueve_de_seccion(self):
        calificacion = self.calificar("Dune", 8)
        self.assertIn("Dune", self.linea("Le gustó"))

        calificacion.valor = 3
        calificacion.save()

        self.assertEqual(self.linea("Le gustó"), "")
        self.assertIn("Dune (3)", self.linea("No le gustó"))

    def test_no_mezcla_datos_de_otro_usuario(self):
        otro = UsuarioFactory()
        Calificacion.objects.create(
            usuario=otro, produccion=self.produccion("Ajena"), valor=9
        )

        self.assertEqual(armar_perfil(self.usuario), "")
