"""Pruebas HTTP de C-08: calificaciones y reseñas del usuario (CU-015).

Van en su propio módulo porque `catalogo/tests.py` ya tiene ~2.950 líneas. El
runner de Django descubre cualquier `test*.py`, así que no hay nada que
registrar.

`materializar()` va mockeada en las pruebas de contrato —su enriquecimiento ya
tiene suite propia— y real en las de integración del final, que son las que
verifican el efecto y no solo la llamada. Es la lección de C-04b: un test con
todo mockeado prueba el llamado, no el resultado.
"""

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from catalogo.factories import ProduccionAudiovisualFactory
from catalogo.models import (
    Calificacion,
    ProduccionAudiovisual,
    ProduccionEmbedding,
    Resena,
    TipoProduccion,
)
from catalogo.tests import _ParchesDeMaterializacion
from usuarios.factories import UsuarioFactory

_RESENA = "Ridley Scott construye un futuro húmedo y usado."


class _BaseResenas(TestCase):
    """Usuario autenticado, una producción en la base y `materializar` mockeada.

    El mock devuelve la producción que el test ya creó: lo que se prueba acá es
    el contrato HTTP, no el enriquecimiento. Las pruebas de integración del
    final lo usan de verdad.
    """

    def setUp(self):
        self.usuario = UsuarioFactory()
        self.cliente = APIClient()
        self.cliente.force_authenticate(self.usuario)
        self.produccion = ProduccionAudiovisualFactory(
            id_tmdb=550, tipo=TipoProduccion.PELICULA, titulo="Blade Runner"
        )
        parche = patch(
            "catalogo.reviews.materializar",
            side_effect=lambda id_tmdb, tipo_tmdb: ProduccionAudiovisual.objects.get(
                id_tmdb=id_tmdb
            ),
        )
        self.materializar = parche.start()
        self.addCleanup(parche.stop)

    def _calificar(self, **campos):
        """POST con el payload mínimo, sobreescribible por cada caso."""
        payload = {"id_tmdb": 550, "tipo": "movie", "valor": 9, **campos}
        return self.cliente.post("/api/reviews/", payload, format="json")

    def _calificacion_existente(self, *, valor=9, texto=None, usuario=None):
        calificacion = Calificacion.objects.create(
            usuario=usuario or self.usuario, produccion=self.produccion, valor=valor
        )
        if texto is not None:
            Resena.objects.create(calificacion=calificacion, texto=texto)
        return calificacion


class CrearCalificacionTests(_BaseResenas):
    """`POST /api/reviews/`: calificar, con o sin texto."""

    def test_califica_sin_texto_y_no_crea_resena(self):
        # El texto es opcional (CU-015): calificar 9/10 y no escribir nada es
        # un caso normal, no una reseña vacía.
        respuesta = self._calificar()

        self.assertEqual(respuesta.status_code, 201)
        calificacion = Calificacion.objects.get()
        self.assertEqual(calificacion.valor, 9)
        self.assertEqual(calificacion.usuario, self.usuario)
        self.assertEqual(calificacion.produccion, self.produccion)
        self.assertFalse(Resena.objects.exists())
        # El id viaja porque el frontend lo necesita para editar y borrar.
        self.assertEqual(respuesta.data["id"], calificacion.pk)
        self.assertIsNone(respuesta.data["texto"])

    def test_califica_con_texto_y_crea_la_resena(self):
        respuesta = self._calificar(texto=_RESENA)

        self.assertEqual(respuesta.status_code, 201)
        resena = Resena.objects.get()
        self.assertEqual(resena.texto, _RESENA)
        self.assertEqual(resena.calificacion, Calificacion.objects.get())
        self.assertEqual(respuesta.data["texto"], _RESENA)

    def test_materializa_la_produccion_antes_de_calificar(self):
        # Se puede calificar desde un resultado de búsqueda que ninguna ficha
        # abrió: la FK tiene que apuntar a una fila completa, y el único camino
        # de escritura del catálogo es `materializar()`.
        self._calificar()

        self.materializar.assert_called_once_with(550, "movie")

    def test_calificar_dos_veces_la_misma_produccion_es_conflicto(self):
        # Hay un UniqueConstraint; el punto es que el usuario vea un 409 con su
        # código y no un 500 por el IntegrityError.
        self._calificacion_existente()

        respuesta = self._calificar(valor=4)

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(respuesta.data["codigo"], "calificacion_duplicada")
        self.assertEqual(Calificacion.objects.count(), 1)
        self.assertEqual(Calificacion.objects.get().valor, 9)  # no la pisó

    def test_la_misma_produccion_la_califican_dos_usuarios(self):
        # La unicidad es por (usuario, producción): el 409 de arriba no debe
        # bloquear a otra persona.
        self._calificacion_existente(usuario=UsuarioFactory())

        respuesta = self._calificar()

        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(Calificacion.objects.count(), 2)


class ValidacionCalificacionTests(_BaseResenas):
    """Rango, longitud y campos obligatorios.

    Cada caso comprueba el status **y qué campo** nombra el error: el modal de
    §5d resalta el campo que falló, así que un 400 sin campo no le alcanza.
    """

    def test_el_valor_fuera_de_1_a_10_se_rechaza(self):
        for valor in (0, 11, -3):
            with self.subTest(valor=valor):
                respuesta = self._calificar(valor=valor)

                self.assertEqual(respuesta.status_code, 400)
                self.assertIn("valor", respuesta.data)
                self.assertFalse(Calificacion.objects.exists())

    def test_calificar_es_obligatorio(self):
        # "Publicar sin calificación → error" es criterio de aceptación de C-08:
        # una reseña sin nota no existe en este modelo.
        respuesta = self.cliente.post(
            "/api/reviews/",
            {"id_tmdb": 550, "tipo": "movie", "texto": _RESENA},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("valor", respuesta.data)

    def test_el_texto_no_pasa_de_1000_caracteres(self):
        respuesta = self._calificar(texto="x" * 1001)

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("texto", respuesta.data)
        self.assertFalse(Calificacion.objects.exists())

    def test_mil_caracteres_justos_entran(self):
        # El límite es inclusivo: 1000 es válido. Sin este caso, un `<` en vez
        # de `<=` pasaría inadvertido.
        respuesta = self._calificar(texto="x" * 1000)

        self.assertEqual(respuesta.status_code, 201)

    def test_el_tipo_tiene_que_ser_movie_o_tv(self):
        respuesta = self._calificar(tipo="person")

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("tipo", respuesta.data)
        self.materializar.assert_not_called()

    def test_no_se_llama_a_tmdb_si_el_payload_es_invalido(self):
        # Validar antes de materializar: un valor de 11 no debe costar tres
        # llamadas a TMDB ni dejar una producción materializada de rebote.
        self._calificar(valor=11)

        self.materializar.assert_not_called()
        self.assertEqual(ProduccionAudiovisual.objects.count(), 1)  # la del setUp


class ActualizarCalificacionTests(_BaseResenas):
    """`PUT /api/reviews/{id}/`: cambiar la nota, el texto, o ambos."""

    def test_cambia_solo_el_valor(self):
        calificacion = self._calificacion_existente(valor=9, texto=_RESENA)

        respuesta = self.cliente.put(
            f"/api/reviews/{calificacion.pk}/", {"valor": 6}, format="json"
        )

        self.assertEqual(respuesta.status_code, 200)
        calificacion.refresh_from_db()
        self.assertEqual(calificacion.valor, 6)
        self.assertEqual(calificacion.resena.texto, _RESENA)  # intacto

    def test_cambia_solo_el_texto(self):
        calificacion = self._calificacion_existente(valor=9, texto=_RESENA)

        respuesta = self.cliente.put(
            f"/api/reviews/{calificacion.pk}/",
            {"texto": "Otra lectura."},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 200)
        calificacion.refresh_from_db()
        self.assertEqual(calificacion.valor, 9)
        self.assertEqual(calificacion.resena.texto, "Otra lectura.")

    def test_le_agrega_texto_a_una_calificacion_que_no_lo_tenia(self):
        # Califiqué sin escribir y después me dieron ganas de escribir: no hay
        # `Resena` que actualizar, hay que crearla.
        calificacion = self._calificacion_existente(valor=9)

        respuesta = self.cliente.put(
            f"/api/reviews/{calificacion.pk}/", {"texto": _RESENA}, format="json"
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(calificacion.resena.texto, _RESENA)

    def test_cambia_las_dos_cosas_a_la_vez(self):
        calificacion = self._calificacion_existente(valor=9, texto=_RESENA)

        respuesta = self.cliente.put(
            f"/api/reviews/{calificacion.pk}/",
            {"valor": 3, "texto": "Me arrepentí."},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 200)
        calificacion.refresh_from_db()
        self.assertEqual(calificacion.valor, 3)
        self.assertEqual(calificacion.resena.texto, "Me arrepentí.")

    def test_el_texto_vacio_se_rechaza(self):
        # Vaciar el texto es el DELETE de `/texto/`. Si el PUT también lo
        # hiciera habría dos caminos para lo mismo, y uno de los dos quedaría
        # sin tests el día que cambie la regla.
        calificacion = self._calificacion_existente(valor=9, texto=_RESENA)

        respuesta = self.cliente.put(
            f"/api/reviews/{calificacion.pk}/", {"texto": ""}, format="json"
        )

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("texto", respuesta.data)
        self.assertEqual(calificacion.resena.texto, _RESENA)

    def test_el_valor_sigue_validandose_al_actualizar(self):
        calificacion = self._calificacion_existente(valor=9)

        respuesta = self.cliente.put(
            f"/api/reviews/{calificacion.pk}/", {"valor": 0}, format="json"
        )

        self.assertEqual(respuesta.status_code, 400)
        calificacion.refresh_from_db()
        self.assertEqual(calificacion.valor, 9)

    def test_un_put_sin_nada_que_cambiar_se_rechaza(self):
        calificacion = self._calificacion_existente(valor=9)

        respuesta = self.cliente.put(
            f"/api/reviews/{calificacion.pk}/", {}, format="json"
        )

        self.assertEqual(respuesta.status_code, 400)


class EliminarCalificacionTests(_BaseResenas):
    """Los dos borrados, que hacen cosas distintas a propósito (decisión 26/09)."""

    def test_borrar_el_texto_conserva_la_calificacion(self):
        # Es el 🗑️ del modal. El texto es opcional, así que borrarlo no debería
        # arrastrar una nota que el usuario no pidió borrar.
        calificacion = self._calificacion_existente(valor=9, texto=_RESENA)

        respuesta = self.cliente.delete(f"/api/reviews/{calificacion.pk}/texto/")

        self.assertEqual(respuesta.status_code, 204)
        self.assertFalse(Resena.objects.exists())
        calificacion.refresh_from_db()
        self.assertEqual(calificacion.valor, 9)

    def test_borrar_el_texto_de_una_calificacion_sin_texto_no_falla(self):
        # Idempotente: el frontend puede reintentar sin recibir un error que no
        # describe ningún problema real.
        calificacion = self._calificacion_existente(valor=9)

        respuesta = self.cliente.delete(f"/api/reviews/{calificacion.pk}/texto/")

        self.assertEqual(respuesta.status_code, 204)
        self.assertTrue(Calificacion.objects.filter(pk=calificacion.pk).exists())

    def test_borrar_la_calificacion_se_lleva_el_texto(self):
        # Es lo que el error de L-01 le pide al usuario para poder quitar algo
        # de "Vistas". La `Resena` cae por CASCADE.
        calificacion = self._calificacion_existente(valor=9, texto=_RESENA)

        respuesta = self.cliente.delete(f"/api/reviews/{calificacion.pk}/")

        self.assertEqual(respuesta.status_code, 204)
        self.assertFalse(Calificacion.objects.exists())
        self.assertFalse(Resena.objects.exists())

    def test_el_borrado_es_fisico_no_logico(self):
        # `activa` significa una sola cosa: moderado por un admin (AD-01'). Si
        # el borrado del usuario lo reusara, "¿por qué no se ve esta reseña?"
        # no tendría respuesta. CU-015 pide eliminar "permanentemente".
        calificacion = self._calificacion_existente(valor=9, texto=_RESENA)

        self.cliente.delete(f"/api/reviews/{calificacion.pk}/")

        self.assertFalse(
            Calificacion.objects.filter(pk=calificacion.pk).exists(),
            "la fila tiene que desaparecer, no quedar con activa=False",
        )


class PropiedadYAutenticacionTests(_BaseResenas):
    """Nadie toca la calificación de otro, y los anónimos no entran."""

    def setUp(self):
        super().setUp()
        self.ajena = self._calificacion_existente(
            valor=7, texto="De otra persona.", usuario=UsuarioFactory()
        )

    def test_la_calificacion_de_otro_usuario_es_404_no_403(self):
        # Misma política que L-01: un 403 confirmaría que esa calificación
        # existe. Para quien no es su dueño, no existe.
        rutas = (
            ("put", f"/api/reviews/{self.ajena.pk}/"),
            ("delete", f"/api/reviews/{self.ajena.pk}/"),
            ("delete", f"/api/reviews/{self.ajena.pk}/texto/"),
        )
        for metodo, ruta in rutas:
            with self.subTest(metodo=metodo, ruta=ruta):
                respuesta = getattr(self.cliente, metodo)(
                    ruta, {"valor": 1}, format="json"
                )

                self.assertEqual(respuesta.status_code, 404)

        self.ajena.refresh_from_db()
        self.assertEqual(self.ajena.valor, 7)
        self.assertEqual(self.ajena.resena.texto, "De otra persona.")

    def test_una_calificacion_que_no_existe_es_404(self):
        respuesta = self.cliente.delete("/api/reviews/999999/")

        self.assertEqual(respuesta.status_code, 404)

    def test_los_anonimos_no_pueden_operar(self):
        anonimo = APIClient()
        propia = self._calificacion_existente(valor=5)
        llamadas = (
            lambda: anonimo.post(
                "/api/reviews/",
                {"id_tmdb": 550, "tipo": "movie", "valor": 9},
                format="json",
            ),
            lambda: anonimo.put(
                f"/api/reviews/{propia.pk}/", {"valor": 1}, format="json"
            ),
            lambda: anonimo.delete(f"/api/reviews/{propia.pk}/"),
            lambda: anonimo.delete(f"/api/reviews/{propia.pk}/texto/"),
        )
        for indice, llamada in enumerate(llamadas):
            with self.subTest(llamada=indice):
                self.assertEqual(llamada().status_code, 401)

        propia.refresh_from_db()
        self.assertEqual(propia.valor, 5)


# ---------------------------------------------------------------------------
# Integración: con `materializar()` real, y con la API de listas (L-01)
# ---------------------------------------------------------------------------
# Los fixtures de TMDB se importan de `tests.py` en vez de copiarse: son los
# contrastados contra la API real (C-04a), y un fixture inventado mantiene los
# tests en verde mientras la realidad es otra —pasó con un `job: "Director"`
# que ninguna serie tenía—.


class CalificarMaterializaTests(_ParchesDeMaterializacion, TestCase):
    """`POST` con `materializar()` REAL y TMDB falso: qué queda en la base.

    El mixin parchea el servicio de TMDB dentro de `materialization.py`, así que
    el enriquecimiento corre de verdad contra respuestas falsas.
    """

    def setUp(self):
        super().setUp()
        self.usuario = UsuarioFactory()
        self.cliente = APIClient()
        self.cliente.force_authenticate(self.usuario)

    def test_calificar_deja_la_produccion_enriquecida(self):
        # Nadie abrió la ficha de Fight Club: la producción no existía. Calificar
        # desde un resultado de búsqueda tiene que dejar una fila completa, no
        # un cascarón con el id.
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.cliente.post(
                "/api/reviews/",
                {"id_tmdb": 550, "tipo": "movie", "valor": 10, "texto": _RESENA},
                format="json",
            )

        self.assertEqual(respuesta.status_code, 201)
        produccion = ProduccionAudiovisual.objects.get(id_tmdb=550)
        self.assertEqual(produccion.titulo, "Fight Club")
        self.assertEqual(produccion.directores, ["David Fincher"])
        self.assertTrue(produccion.generos)
        self.assertTrue(produccion.reparto)
        self.assertIsNotNone(produccion.fecha_enriquecimiento)
        # Y quedó encolado su embedding, como cualquier otra materialización.
        self.assertTrue(
            ProduccionEmbedding.objects.filter(produccion=produccion).exists()
        )

    def test_calificar_algo_ya_materializado_no_vuelve_a_pedir_la_ficha(self):
        # La fila fresca no se re-enriquece: calificar no debería costar tres
        # llamadas a TMDB por cada estrella que alguien toque.
        with self.captureOnCommitCallbacks(execute=True):
            self.cliente.post(
                "/api/reviews/",
                {"id_tmdb": 550, "tipo": "movie", "valor": 8},
                format="json",
            )
        self.servicio.get_movie_detail.reset_mock()

        otro = APIClient()
        otro.force_authenticate(UsuarioFactory())
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = otro.post(
                "/api/reviews/",
                {"id_tmdb": 550, "tipo": "movie", "valor": 6},
                format="json",
            )

        self.assertEqual(respuesta.status_code, 201)
        self.servicio.get_movie_detail.assert_not_called()


class CalificacionYReglaDeVistasTests(_ParchesDeMaterializacion, TestCase):
    """El círculo que C-08 cierra: la regla de CU-011 que L-01 implementó.

    L-01 responde 409 al quitar de «Vistas» algo calificado, diciendo
    «Eliminá la calificación antes de quitar esta producción de Vistas». Hasta
    C-08 esa instrucción era **imposible de cumplir**: no existía endpoint que
    borrara una calificación, así que la regla no podía dispararse ni obedecerse.
    Esta prueba recorre el flujo entero por HTTP, de punta a punta.
    """

    def setUp(self):
        super().setUp()
        self.usuario = UsuarioFactory()
        self.cliente = APIClient()
        self.cliente.force_authenticate(self.usuario)
        self.vistas = self.usuario.listas.get(nombre="Vistas")

    def _agregar_a_vistas(self):
        respuesta = self.cliente.post(
            f"/api/lists/{self.vistas.pk}/items/",
            {"id_tmdb": 550, "tipo": "movie"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 201)
        return respuesta.data["item_id"]

    def _quitar_de_vistas(self, item_id):
        return self.cliente.delete(f"/api/lists/{self.vistas.pk}/items/{item_id}/")

    def test_el_flujo_completo_de_cu_011(self):
        with self.captureOnCommitCallbacks(execute=True):
            item_id = self._agregar_a_vistas()

            # Sin calificar todavía: se puede quitar sin problema.
            self.assertEqual(self._quitar_de_vistas(item_id).status_code, 204)
            item_id = self._agregar_a_vistas()

            calificar = self.cliente.post(
                "/api/reviews/",
                {"id_tmdb": 550, "tipo": "movie", "valor": 9, "texto": _RESENA},
                format="json",
            )
            calificacion_id = calificar.data["id"]

            # Ahora la regla se dispara — por primera vez en la vida del proyecto.
            bloqueado = self._quitar_de_vistas(item_id)
            self.assertEqual(bloqueado.status_code, 409)
            self.assertEqual(
                bloqueado.data["codigo"], "calificacion_impide_quitar_de_vistas"
            )

            # Borrar SOLO el texto no alcanza: la regla mira la calificación.
            # Es el caso donde alguien podría asumir lo contrario.
            self.assertEqual(
                self.cliente.delete(
                    f"/api/reviews/{calificacion_id}/texto/"
                ).status_code,
                204,
            )
            self.assertEqual(self._quitar_de_vistas(item_id).status_code, 409)

            # Borrar la calificación sí: es lo que el mensaje de error pedía.
            self.assertEqual(
                self.cliente.delete(f"/api/reviews/{calificacion_id}/").status_code, 204
            )
            self.assertEqual(self._quitar_de_vistas(item_id).status_code, 204)

        self.assertFalse(Calificacion.objects.exists())
        self.assertFalse(self.vistas.items.exists())

    def test_calificar_no_agrega_a_vistas_por_su_cuenta(self):
        # Fuera de alcance a propósito: escribir en las tablas de otro módulo en
        # silencio sorprendería a quien lea el código de listas. Si la ficha
        # quiere ofrecerlo, es una decisión de C-07.
        with self.captureOnCommitCallbacks(execute=True):
            self.cliente.post(
                "/api/reviews/",
                {"id_tmdb": 550, "tipo": "movie", "valor": 9},
                format="json",
            )

        self.assertFalse(self.vistas.items.exists())
