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
from listas.factories import ListaFactory
from listas.models import Tiene
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

    def _vistas(self):
        # La crea la señal de alta del usuario (A-01), junto a las otras dos.
        return self.usuario.listas.get(nombre="Vistas")

    def _en_vistas(self):
        return self._vistas().items.filter(produccion=self.produccion).exists()


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
        self.assertEqual(respuesta.data["code"], "rating_duplicated")
        self.assertEqual(Calificacion.objects.count(), 1)
        self.assertEqual(Calificacion.objects.get().valor, 9)  # no la pisó

    def test_calificar_agrega_la_produccion_a_vistas(self):
        # Regla del 30/09/2026: si la calificaste, la viste. Es la mitad que
        # le faltaba a CU-011, que ya impedía sacar de «Vistas» algo calificado.
        respuesta = self._calificar()

        self.assertEqual(respuesta.status_code, 201)
        self.assertTrue(self._en_vistas())

    def test_calificar_algo_que_ya_estaba_en_vistas_no_lo_duplica(self):
        # Primero la marcó como vista a mano y después la califica: el ítem que
        # ya existía alcanza, y un segundo chocaría con el UNIQUE de `Tiene`.
        Tiene.objects.create(lista=self._vistas(), produccion=self.produccion)

        respuesta = self._calificar()

        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(self._vistas().items.count(), 1)

    def test_si_no_puede_entrar_a_vistas_tampoco_se_califica(self):
        # Las dos escrituras van en una transacción: o quedan las dos o
        # ninguna. Sin la lista «Vistas» (estado roto, lo repara
        # `reparar_recursos_usuarios`) calificar falla entero, en vez de dejar
        # una nota que viola la regla.
        self._vistas().delete()

        # `filmai_exception_handler` convierte lo no manejado en un 500 y lo
        # loguea; `assertLogs` además evita que ensucie la salida de la suite.
        with self.assertLogs("filmai.exceptions", level="ERROR"):
            respuesta = self._calificar()

        self.assertEqual(respuesta.status_code, 500)
        self.assertFalse(Calificacion.objects.exists())

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
                self.assertIn(
                    "valor", {entry["field"] for entry in respuesta.data["errors"]}
                )
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
        self.assertIn("valor", {entry["field"] for entry in respuesta.data["errors"]})

    def test_el_texto_no_pasa_de_1000_caracteres(self):
        respuesta = self._calificar(texto="x" * 1001)

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("texto", {entry["field"] for entry in respuesta.data["errors"]})
        self.assertFalse(Calificacion.objects.exists())

    def test_mil_caracteres_justos_entran(self):
        # El límite es inclusivo: 1000 es válido. Sin este caso, un `<` en vez
        # de `<=` pasaría inadvertido.
        respuesta = self._calificar(texto="x" * 1000)

        self.assertEqual(respuesta.status_code, 201)

    def test_el_tipo_tiene_que_ser_movie_o_tv(self):
        respuesta = self._calificar(tipo="person")

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("tipo", {entry["field"] for entry in respuesta.data["errors"]})
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
        self.assertIn("texto", {entry["field"] for entry in respuesta.data["errors"]})
        self.assertEqual(calificacion.resena.texto, _RESENA)

    def test_el_valor_sigue_validandose_al_actualizar(self):
        calificacion = self._calificacion_existente(valor=9)

        respuesta = self.cliente.put(
            f"/api/reviews/{calificacion.pk}/", {"valor": 0}, format="json"
        )

        self.assertEqual(respuesta.status_code, 400)
        calificacion.refresh_from_db()
        self.assertEqual(calificacion.valor, 9)

    def test_editar_no_saca_de_vistas(self):
        # Cambiar la nota o el texto no cambia que la hayas visto.
        calificacion = self._calificacion_existente(valor=9)
        Tiene.objects.create(lista=self._vistas(), produccion=self.produccion)

        respuesta = self.cliente.put(
            f"/api/reviews/{calificacion.pk}/", {"valor": 3}, format="json"
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(self._en_vistas())

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

    def test_borrar_la_calificacion_saca_de_vistas(self):
        # Si la descalificás, sale de «Vistas» (regla del 30/09/2026). La UI
        # lo avisa en el modal antes de confirmar, y se puede volver a marcar.
        calificacion = self._calificacion_existente(valor=9, texto=_RESENA)
        Tiene.objects.create(lista=self._vistas(), produccion=self.produccion)

        respuesta = self.cliente.delete(f"/api/reviews/{calificacion.pk}/")

        self.assertEqual(respuesta.status_code, 204)
        self.assertFalse(self._en_vistas())

    def test_borrar_la_calificacion_no_toca_las_otras_listas(self):
        # La regla es solo de «Vistas»: sigue siendo favorita aunque ya no
        # tenga nota.
        calificacion = self._calificacion_existente(valor=9)
        favoritos = self.usuario.listas.get(nombre="Favoritos")
        Tiene.objects.create(lista=self._vistas(), produccion=self.produccion)
        Tiene.objects.create(lista=favoritos, produccion=self.produccion)

        self.cliente.delete(f"/api/reviews/{calificacion.pk}/")

        self.assertTrue(favoritos.items.filter(produccion=self.produccion).exists())

    def test_borrar_la_calificacion_no_saca_de_las_vistas_de_otro(self):
        # El DELETE filtra por la lista del dueño de la calificación, no por
        # la producción: la de otro usuario no se toca.
        otro = UsuarioFactory()
        vistas_del_otro = otro.listas.get(nombre="Vistas")
        Tiene.objects.create(lista=vistas_del_otro, produccion=self.produccion)
        calificacion = self._calificacion_existente(valor=9)
        Tiene.objects.create(lista=self._vistas(), produccion=self.produccion)

        self.cliente.delete(f"/api/reviews/{calificacion.pk}/")

        self.assertTrue(vistas_del_otro.items.exists())

    def test_borrar_una_calificacion_que_no_estaba_en_vistas_no_falla(self):
        # Una calificación anterior a la regla puede no tener su ítem en
        # «Vistas»: la migración `listas.0004` las repara, pero borrar no puede
        # depender de que eso haya corrido.
        calificacion = self._calificacion_existente(valor=9)

        respuesta = self.cliente.delete(f"/api/reviews/{calificacion.pk}/")

        self.assertEqual(respuesta.status_code, 204)
        self.assertFalse(Calificacion.objects.exists())

    def test_borrar_solo_el_texto_no_saca_de_vistas(self):
        # La reseña es opcional: borrarla conserva la nota, y con la nota
        # sigue en «Vistas».
        calificacion = self._calificacion_existente(valor=9, texto=_RESENA)
        Tiene.objects.create(lista=self._vistas(), produccion=self.produccion)

        self.cliente.delete(f"/api/reviews/{calificacion.pk}/texto/")

        self.assertTrue(self._en_vistas())

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
    """La regla «calificada ⇒ en Vistas», de punta a punta por HTTP.

    CU-011 ya pedía una mitad: no se puede sacar de «Vistas» algo calificado
    (el 409 de L-01). La otra mitad es del 30/09/2026: calificar la agrega y
    borrar la calificación la saca. Lo que la regla NO exige es la vuelta:
    marcar como vista sin calificar sigue siendo válido.

    Los cuatro casos acordados con el usuario:

    - **Entra 1**: califica → entra a «Vistas».
    - **Entra 2**: la marca como vista, sin calificar.
    - **Sale 1**: borra la calificación → sale de «Vistas».
    - **Sale 2**: la saca de «Vistas» → 409; confirmado con
      `?borrar_calificacion=true`, se va también la calificación.
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

    def _quitar_de_vistas(self, item_id, *, confirmado=False):
        url = f"/api/lists/{self.vistas.pk}/items/{item_id}/"
        if confirmado:
            url = f"{url}?borrar_calificacion=true"
        return self.cliente.delete(url)

    def _calificar(self):
        respuesta = self.cliente.post(
            "/api/reviews/",
            {"id_tmdb": 550, "tipo": "movie", "valor": 9, "texto": _RESENA},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 201)
        return respuesta.data["id"]

    def _item_en_vistas(self):
        return self.vistas.items.values_list("pk", flat=True).first()

    def test_entra_1_y_sale_1_calificar_y_descalificar(self):
        with self.captureOnCommitCallbacks(execute=True):
            calificacion_id = self._calificar()

            # Entra 1: calificar la agregó a «Vistas», sin otra llamada.
            item_id = self._item_en_vistas()
            self.assertIsNotNone(item_id)

            # La regla de CU-011 se dispara sobre ese ítem.
            bloqueado = self._quitar_de_vistas(item_id)
            self.assertEqual(bloqueado.status_code, 409)
            self.assertEqual(
                bloqueado.data["code"], "rating_blocks_removal_from_watched"
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

            # Sale 1: borrar la calificación la saca de «Vistas».
            self.assertEqual(
                self.cliente.delete(f"/api/reviews/{calificacion_id}/").status_code, 204
            )

        self.assertFalse(Calificacion.objects.exists())
        self.assertFalse(self.vistas.items.exists())

    def test_entra_2_y_sale_2_marcar_como_vista_y_sacarla(self):
        with self.captureOnCommitCallbacks(execute=True):
            # Entra 2: marcar como vista no exige calificar, ni califica.
            item_id = self._agregar_a_vistas()
            self.assertFalse(Calificacion.objects.exists())

            # Calificarla después no duplica el ítem.
            self._calificar()
            self.assertEqual(self.vistas.items.count(), 1)

            # Sale 2: sacarla pide confirmar, y confirmado se lleva la nota.
            self.assertEqual(self._quitar_de_vistas(item_id).status_code, 409)
            confirmado = self._quitar_de_vistas(item_id, confirmado=True)
            self.assertEqual(confirmado.status_code, 204)

        self.assertFalse(Calificacion.objects.exists())
        self.assertFalse(self.vistas.items.exists())


# ---------------------------------------------------------------------------
# Lectura (fase 2): la comunidad, «Mis reseñas» y mi calificación en una ficha
# ---------------------------------------------------------------------------


class VistasSacaDePendientesTests(_ParchesDeMaterializacion, TestCase):
    """Lo que ya viste deja de estar pendiente (regla del 14/10/2026).

    Entrar a «Vistas» —con el botón Watched o calificando— saca la producción
    de «Pendientes» del mismo usuario. Rige solo en el momento en que entra:
    volver a agregarla a «Pendientes» para verla de nuevo sigue permitido.
    """

    def setUp(self):
        super().setUp()
        self.usuario = UsuarioFactory()
        self.cliente = APIClient()
        self.cliente.force_authenticate(self.usuario)
        self.vistas = self.usuario.listas.get(nombre="Vistas")
        self.pendientes = self.usuario.listas.get(nombre="Pendientes")

    def _agregar(self, lista, cliente=None):
        return (cliente or self.cliente).post(
            f"/api/lists/{lista.pk}/items/",
            {"id_tmdb": 550, "tipo": "movie"},
            format="json",
        )

    def _calificar(self):
        respuesta = self.cliente.post(
            "/api/reviews/",
            {"id_tmdb": 550, "tipo": "movie", "valor": 8},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 201)

    def _en(self, lista):
        return lista.items.exists()

    def test_el_boton_watched_la_saca_de_pendientes(self):
        self.assertEqual(self._agregar(self.pendientes).status_code, 201)

        self.assertEqual(self._agregar(self.vistas).status_code, 201)

        self.assertTrue(self._en(self.vistas))
        self.assertFalse(self._en(self.pendientes))

    def test_calificar_la_saca_de_pendientes(self):
        self._agregar(self.pendientes)

        self._calificar()

        self.assertTrue(self._en(self.vistas))
        self.assertFalse(self._en(self.pendientes))

    def test_volver_a_agregarla_a_pendientes_sigue_permitido(self):
        # Ya vista, la quiere volver a ver: la agrega a «Pendientes» y después
        # la califica. Calificar no la saca, porque ya estaba en «Vistas».
        self._agregar(self.vistas)
        self.assertEqual(self._agregar(self.pendientes).status_code, 201)

        self._calificar()

        self.assertTrue(self._en(self.pendientes))

    def test_otras_listas_no_tocan_pendientes(self):
        self._agregar(self.pendientes)
        personalizada = ListaFactory(usuario=self.usuario, nombre="Ciencia ficción")

        self._agregar(self.usuario.listas.get(nombre="Favoritos"))
        self._agregar(personalizada)

        self.assertTrue(self._en(self.pendientes))

    def test_solo_toca_los_pendientes_de_quien_la_marca(self):
        otro = UsuarioFactory()
        cliente_otro = APIClient()
        cliente_otro.force_authenticate(otro)
        pendientes_del_otro = otro.listas.get(nombre="Pendientes")
        self._agregar(pendientes_del_otro, cliente_otro)

        self._agregar(self.vistas)

        self.assertTrue(self._en(pendientes_del_otro))

    def test_quitarla_de_vistas_no_la_devuelve_a_pendientes(self):
        self._agregar(self.pendientes)
        item_id = self._agregar(self.vistas).data["item_id"]

        self.assertEqual(
            self.cliente.delete(
                f"/api/lists/{self.vistas.pk}/items/{item_id}/"
            ).status_code,
            204,
        )

        self.assertFalse(self._en(self.vistas))
        self.assertFalse(self._en(self.pendientes))

    def test_si_el_alta_en_vistas_falla_pendientes_queda_intacta(self):
        # Ya está en «Vistas» y la volvió a poner en «Pendientes»: un segundo
        # alta en «Vistas» responde 409 y no debe borrar nada.
        self._agregar(self.vistas)
        self._agregar(self.pendientes)

        self.assertEqual(self._agregar(self.vistas).status_code, 409)

        self.assertTrue(self._en(self.pendientes))


class _BaseLectura(TestCase):
    """Varios usuarios y varias producciones: leer es cruzar datos de otros."""

    def setUp(self):
        self.usuario = UsuarioFactory(nombre_usuario="gonza", avatar_id=3)
        self.cliente = APIClient()
        self.cliente.force_authenticate(self.usuario)
        self.pelicula = ProduccionAudiovisualFactory(
            id_tmdb=550, tipo=TipoProduccion.PELICULA, titulo="Blade Runner"
        )
        self.serie = ProduccionAudiovisualFactory(
            id_tmdb=1396, tipo=TipoProduccion.SERIE, titulo="Breaking Bad"
        )

    def _resena(
        self,
        *,
        usuario=None,
        produccion=None,
        valor=8,
        texto=_RESENA,
        activa=True,
        fecha=None,
    ):
        """Crea una calificación con su texto, con control de `activa` y `fecha`.

        `fecha` es `auto_now_add`, así que para fabricar un orden hay que
        pisarla con un UPDATE: asignarla antes del save no sirve.
        """
        calificacion = Calificacion.objects.create(
            usuario=usuario or self.usuario,
            produccion=produccion or self.pelicula,
            valor=valor,
        )
        if texto is not None:
            Resena.objects.create(calificacion=calificacion, texto=texto, activa=activa)
        if fecha is not None:
            Calificacion.objects.filter(pk=calificacion.pk).update(fecha=fecha)
            Resena.objects.filter(calificacion=calificacion).update(fecha=fecha)
        return calificacion


class ResenasDeLaComunidadTests(_BaseLectura):
    """`GET /api/reviews/?id_tmdb=&tipo=`: lo que la ficha muestra de los demás."""

    def test_devuelve_los_campos_de_la_review_card(self):
        # §5c del doc 04: avatar, @usuario, rating X/10, fecha y texto.
        otro = UsuarioFactory(nombre_usuario="marcos", avatar_id=7)
        self._resena(usuario=otro, valor=10, texto="Un clásico.")

        respuesta = self.cliente.get("/api/reviews/?id_tmdb=550&tipo=movie")

        self.assertEqual(respuesta.status_code, 200)
        fila = respuesta.data["results"][0]
        self.assertEqual(fila["nombre_usuario"], "marcos")
        self.assertEqual(fila["avatar_id"], 7)
        self.assertEqual(fila["valor"], 10)
        self.assertEqual(fila["texto"], "Un clásico.")
        self.assertIn("fecha", fila)

    def test_informa_el_total_para_el_encabezado(self):
        # El encabezado dice «Reseñas de la comunidad (N)», y la paginación por
        # cursor no trae `count` por diseño: se agrega explícito.
        for indice in range(3):
            self._resena(usuario=UsuarioFactory(nombre_usuario=f"u{indice}"))

        respuesta = self.cliente.get("/api/reviews/?id_tmdb=550&tipo=movie")

        self.assertEqual(respuesta.data["total"], 3)

    def test_no_incluye_la_resena_de_quien_pregunta(self):
        # La ficha la muestra aparte, arriba, en su propia card. Mandarla dos
        # veces obligaría a deduplicar a cada consumidor, y una lista paginada
        # no puede prometer que la propia caiga en la página 1.
        self._resena(texto="La mía.")
        self._resena(usuario=UsuarioFactory(nombre_usuario="otro"), texto="La ajena.")

        respuesta = self.cliente.get("/api/reviews/?id_tmdb=550&tipo=movie")

        textos = [fila["texto"] for fila in respuesta.data["results"]]
        self.assertEqual(textos, ["La ajena."])
        self.assertEqual(respuesta.data["total"], 1)

    def test_no_incluye_calificaciones_sin_texto(self):
        # Una nota sin escribir no tiene nada que leer (§5c).
        self._resena(usuario=UsuarioFactory(nombre_usuario="muda"), texto=None)
        self._resena(usuario=UsuarioFactory(nombre_usuario="escriba"), texto="Hola.")

        respuesta = self.cliente.get("/api/reviews/?id_tmdb=550&tipo=movie")

        self.assertEqual(respuesta.data["total"], 1)
        self.assertEqual(respuesta.data["results"][0]["nombre_usuario"], "escriba")

    def test_no_incluye_resenas_moderadas(self):
        # Decisión del 26/09: una reseña desactivada por el Admin (AD-01') no la
        # ve nadie salvo su autor.
        self._resena(usuario=UsuarioFactory(nombre_usuario="moderada"), activa=False)

        respuesta = self.cliente.get("/api/reviews/?id_tmdb=550&tipo=movie")

        self.assertEqual(respuesta.data["total"], 0)

    def test_filtra_por_produccion(self):
        self._resena(
            usuario=UsuarioFactory(nombre_usuario="a"), texto="De la película."
        )
        self._resena(
            usuario=UsuarioFactory(nombre_usuario="b"),
            produccion=self.serie,
            texto="De la serie.",
        )

        respuesta = self.cliente.get("/api/reviews/?id_tmdb=1396&tipo=tv")

        self.assertEqual(respuesta.data["total"], 1)
        self.assertEqual(respuesta.data["results"][0]["texto"], "De la serie.")

    def test_la_produccion_sin_resenas_devuelve_lista_vacia_no_404(self):
        # El estado «Sin reseñas» de §5c es una pantalla normal, no un error.
        respuesta = self.cliente.get("/api/reviews/?id_tmdb=1396&tipo=tv")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["total"], 0)
        self.assertEqual(respuesta.data["results"], [])

    def test_exige_id_tmdb_y_tipo_validos(self):
        casos = (
            "",
            "?id_tmdb=550",
            "?tipo=movie",
            "?id_tmdb=abc&tipo=movie",
            "?id_tmdb=550&tipo=person",
        )
        for query in casos:
            with self.subTest(query=query):
                respuesta = self.cliente.get(f"/api/reviews/{query}")

                self.assertEqual(respuesta.status_code, 400)

    def test_los_anonimos_leen_las_resenas_de_todos(self):
        # Cambió el 14/10/2026 (C-07): las reseñas son públicas y la ficha se ve
        # sin sesión. Sin usuario no hay «la propia» que sacar.
        self._resena(valor=9, texto="La mía, visible para un anónimo.")
        self._resena(usuario=UsuarioFactory(), valor=7, texto="De otra persona.")

        respuesta = APIClient().get("/api/reviews/?id_tmdb=550&tipo=movie")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["total"], 2)

    def test_los_anonimos_siguen_sin_poder_calificar(self):
        respuesta = APIClient().post(
            "/api/reviews/",
            {"id_tmdb": 550, "tipo": "movie", "valor": 9},
            format="json",
        )

        self.assertEqual(respuesta.status_code, 401)


class ComunidadOrdenYFiltroTests(_BaseLectura):
    """`orden`, `nota_min` y `nota_max` en las reseñas de la comunidad (C-07)."""

    URL = "/api/reviews/?id_tmdb=550&tipo=movie"

    def setUp(self):
        super().setUp()
        self.anonimo = APIClient()

    def _valores(self, respuesta):
        return [resena["valor"] for resena in respuesta.json()["results"]]

    def _sembrar(self):
        # Cuatro personas, notas y fechas distintas.
        for valor, fecha in (
            (6, "2026-09-01"),
            (10, "2026-09-03"),
            (3, "2026-09-02"),
            (8, "2026-09-04"),
        ):
            self._resena(usuario=UsuarioFactory(), valor=valor, fecha=fecha)

    def test_cada_orden_ordena_como_dice(self):
        self._sembrar()
        casos = {
            "fecha-desc": [8, 10, 3, 6],
            "fecha-asc": [6, 3, 10, 8],
            "nota-desc": [10, 8, 6, 3],
            "nota-asc": [3, 6, 8, 10],
        }
        for orden, esperado in casos.items():
            with self.subTest(orden=orden):
                respuesta = self.anonimo.get(f"{self.URL}&orden={orden}")

                self.assertEqual(self._valores(respuesta), esperado)

    def test_sin_orden_son_las_mas_nuevas_primero(self):
        self._sembrar()

        self.assertEqual(self._valores(self.anonimo.get(self.URL)), [8, 10, 3, 6])

    def test_un_orden_desconocido_responde_400(self):
        respuesta = self.anonimo.get(f"{self.URL}&orden=azar")

        self.assertEqual(respuesta.status_code, 400)
        error = respuesta.json()["errors"][0]
        self.assertEqual((error["field"], error["code"]), ("orden", "invalid_choice"))

    def test_nota_min_y_nota_max_filtran_incluyendo_los_bordes(self):
        self._sembrar()
        casos = {
            "&nota_min=8": [8, 10],
            "&nota_max=6": [3, 6],
            "&nota_min=6&nota_max=8": [8, 6],
        }
        for query, esperado in casos.items():
            with self.subTest(query=query):
                respuesta = self.anonimo.get(self.URL + query)

                self.assertEqual(self._valores(respuesta), esperado)

    def test_notas_fuera_de_rango_responden_400(self):
        for query in ("&nota_min=0", "&nota_max=11", "&nota_min=abc"):
            with self.subTest(query=query):
                self.assertEqual(self.anonimo.get(self.URL + query).status_code, 400)

    def test_total_cuenta_lo_filtrado_y_total_comunidad_todo(self):
        self._sembrar()

        datos = self.anonimo.get(f"{self.URL}&nota_min=8").json()

        self.assertEqual((datos["total"], datos["total_comunidad"]), (2, 4))

    def test_el_cursor_por_nota_no_repite_ni_saltea_con_muchas_notas_iguales(self):
        # 25 reseñas con la misma nota y 5 con otra: con páginas de 20, la
        # segunda página depende de desempatar bien entre los 8.
        for _ in range(25):
            self._resena(usuario=UsuarioFactory(), valor=8)
        for _ in range(5):
            self._resena(usuario=UsuarioFactory(), valor=9)

        vistas = []
        url = f"{self.URL}&orden=nota-desc"
        while url:
            datos = self.anonimo.get(url).json()
            vistas += [(r["nombre_usuario"], r["valor"]) for r in datos["results"]]
            url = datos["next"]

        self.assertEqual(len(vistas), 30)
        self.assertEqual(len(set(vistas)), 30)
        self.assertEqual([valor for _, valor in vistas], [9] * 5 + [8] * 25)


class MisResenasTests(_BaseLectura):
    """`GET /api/reviews/mias/`: la pantalla «Mis reseñas» (P-06)."""

    def test_devuelve_los_campos_de_la_review_card_de_p06(self):
        # P-06: título clicable, badge de tipo, X/10, fecha y texto.
        self._resena(valor=9, texto="Mi texto.")

        respuesta = self.cliente.get("/api/reviews/mias/")

        fila = respuesta.data["results"][0]
        self.assertEqual(fila["titulo"], "Blade Runner")
        self.assertEqual(fila["tipo"], "movie")
        self.assertEqual(fila["id_tmdb"], 550)
        self.assertEqual(fila["valor"], 9)
        self.assertEqual(fila["texto"], "Mi texto.")
        # El id de la calificación viaja: los botones de editar y eliminar lo
        # necesitan sin tener que volver a buscarla.
        self.assertIn("id", fila)

    def test_ordena_de_la_mas_reciente_a_la_mas_vieja(self):
        from datetime import date

        vieja = self._resena(texto="Vieja.", fecha=date(2026, 1, 1))
        nueva = self._resena(
            produccion=self.serie, texto="Nueva.", fecha=date(2026, 9, 1)
        )

        respuesta = self.cliente.get("/api/reviews/mias/")

        ids = [fila["id"] for fila in respuesta.data["results"]]
        self.assertEqual(ids, [nueva.pk, vieja.pk])

    def test_incluye_mi_resena_moderada(self):
        # La otra mitad de la decisión del 26/09: desaparece para la comunidad,
        # pero su autor la sigue viendo. Que su texto se esfume de sus propias
        # pantallas sin explicación posible es lo que se quiso evitar.
        self._resena(activa=False, texto="Moderada.")

        respuesta = self.cliente.get("/api/reviews/mias/")

        self.assertEqual(respuesta.data["total"], 1)
        self.assertEqual(respuesta.data["results"][0]["texto"], "Moderada.")

    def test_incluye_calificaciones_sin_texto(self):
        # Al revés que la comunidad: en «Mis reseñas» conviene ver lo que
        # calificaste sin escribir, porque desde ahí lo podés editar.
        self._resena(valor=6, texto=None)

        respuesta = self.cliente.get("/api/reviews/mias/")

        self.assertEqual(respuesta.data["total"], 1)
        self.assertIsNone(respuesta.data["results"][0]["texto"])

    def test_nunca_devuelve_la_resena_de_otro(self):
        self._resena(usuario=UsuarioFactory(nombre_usuario="ajeno"), texto="Ajena.")

        respuesta = self.cliente.get("/api/reviews/mias/")

        self.assertEqual(respuesta.data["total"], 0)

    def test_los_anonimos_no_tienen_resenas_propias(self):
        self.assertEqual(APIClient().get("/api/reviews/mias/").status_code, 401)


class MiCalificacionEnUnaFichaTests(_BaseLectura):
    """`GET /api/reviews/mias/?id_tmdb=&tipo=`: qué mostrar en la ficha."""

    def test_devuelve_mi_calificacion_de_esa_produccion(self):
        # Es lo que la ficha consulta al cargar: ¿el botón dice «Calificar» o
        # muestra 9/10?, ¿va la card «Tu reseña»?, ¿con qué precargo el modal?
        self._resena(valor=9, texto="Mi texto.")
        self._resena(produccion=self.serie, valor=4, texto="De la serie.")

        respuesta = self.cliente.get("/api/reviews/mias/?id_tmdb=550&tipo=movie")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["valor"], 9)
        self.assertEqual(respuesta.data["texto"], "Mi texto.")
        self.assertEqual(respuesta.data["id_tmdb"], 550)

    def test_es_un_objeto_solo_no_una_lista_paginada(self):
        # Con filtro hay a lo sumo una: el UNIQUE es (usuario, producción).
        # Devolver `{results: [...]}` obligaría al frontend a desempacar algo
        # que nunca tiene más de un elemento.
        self._resena(valor=9)

        respuesta = self.cliente.get("/api/reviews/mias/?id_tmdb=550&tipo=movie")

        self.assertNotIn("results", respuesta.data)
        self.assertIn("valor", respuesta.data)

    def test_404_cuando_todavia_no_la_califique(self):
        # El 404 es la respuesta: «no tenés calificación acá». La ficha lo lee
        # como «mostrar el botón Calificar vacío».
        respuesta = self.cliente.get("/api/reviews/mias/?id_tmdb=550&tipo=movie")

        self.assertEqual(respuesta.status_code, 404)

    def test_no_devuelve_la_calificacion_de_otro_en_esa_produccion(self):
        self._resena(usuario=UsuarioFactory(nombre_usuario="ajeno"), valor=10)

        respuesta = self.cliente.get("/api/reviews/mias/?id_tmdb=550&tipo=movie")

        self.assertEqual(respuesta.status_code, 404)

    def test_devuelve_mi_calificacion_moderada(self):
        self._resena(valor=9, texto="Moderada.", activa=False)

        respuesta = self.cliente.get("/api/reviews/mias/?id_tmdb=550&tipo=movie")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data["texto"], "Moderada.")

    def test_exige_los_dos_parametros_juntos(self):
        # Medio filtro es un error, no «todas mis reseñas»: sin esto, un bug del
        # frontend que olvide `tipo` devolvería la lista entera y la ficha
        # mostraría la calificación de otra película.
        self._resena(valor=9)

        respuesta = self.cliente.get("/api/reviews/mias/?id_tmdb=550")

        self.assertEqual(respuesta.status_code, 400)


class PaginacionDeResenasTests(_BaseLectura):
    """Cursor de 20, para los dos scrolls infinitos."""

    def _muchas(self, cantidad, *, propias):
        from datetime import date, timedelta

        creadas = []
        for indice in range(cantidad):
            produccion = ProduccionAudiovisualFactory(
                id_tmdb=9000 + indice, tipo=TipoProduccion.PELICULA
            )
            creadas.append(
                self._resena(
                    usuario=self.usuario
                    if propias
                    else UsuarioFactory(nombre_usuario=f"u{indice}"),
                    produccion=produccion if propias else self.pelicula,
                    texto=f"Reseña {indice}.",
                    fecha=date(2026, 1, 1) + timedelta(days=indice),
                )
            )
        return creadas

    def test_la_comunidad_llega_de_a_20(self):
        self._muchas(25, propias=False)

        respuesta = self.cliente.get("/api/reviews/?id_tmdb=550&tipo=movie")

        self.assertEqual(len(respuesta.data["results"]), 20)
        self.assertIsNotNone(respuesta.data["next"])
        self.assertEqual(respuesta.data["total"], 25)

    def test_la_segunda_pagina_trae_el_resto_sin_repetir(self):
        self._muchas(25, propias=False)

        primera = self.cliente.get("/api/reviews/?id_tmdb=550&tipo=movie")
        segunda = self.cliente.get(primera.data["next"])

        textos_primera = {fila["texto"] for fila in primera.data["results"]}
        textos_segunda = {fila["texto"] for fila in segunda.data["results"]}
        self.assertEqual(len(textos_segunda), 5)
        self.assertEqual(textos_primera & textos_segunda, set())

    def test_una_resena_nueva_no_desordena_la_paginacion_en_curso(self):
        # Es la razón de usar cursor y no `?page=2`: con offset, una reseña
        # nueva empuja todo una posición y la página 2 repite el último ítem de
        # la página 1. El cursor apunta a un valor, no a una posición.
        self._muchas(25, propias=False)
        primera = self.cliente.get("/api/reviews/?id_tmdb=550&tipo=movie")
        vistos = {fila["texto"] for fila in primera.data["results"]}

        from datetime import date

        self._resena(
            usuario=UsuarioFactory(nombre_usuario="recien"),
            texto="Llegó mientras scrolleabas.",
            fecha=date(2026, 12, 31),
        )
        segunda = self.cliente.get(primera.data["next"])

        textos_segunda = [fila["texto"] for fila in segunda.data["results"]]
        self.assertEqual(len(set(textos_segunda)), len(textos_segunda), "hay repetidos")
        self.assertEqual(vistos & set(textos_segunda), set())

    def test_segunda_pagina_propia_acepta_cursor_sin_filtro_de_produccion(self):
        # El cursor no es un filtro de ficha: la página 2 debe seguir siendo
        # un listado propio, sin IDs repetidos ni datos de otros usuarios.
        self._muchas(22, propias=True)
        primera = self.cliente.get("/api/reviews/mias/")
        segunda = self.cliente.get(primera.data["next"])

        self.assertEqual(segunda.status_code, 200)
        self.assertEqual(len(segunda.data["results"]), 2)
        ids_primera = {fila["id"] for fila in primera.data["results"]}
        ids_segunda = {fila["id"] for fila in segunda.data["results"]}
        self.assertFalse(ids_primera & ids_segunda)
        self.assertIsNone(segunda.data["next"])
        self.assertEqual(segunda.data["total"], 22)

    def test_mis_resenas_tambien_llegan_de_a_20(self):
        self._muchas(22, propias=True)

        respuesta = self.cliente.get("/api/reviews/mias/")

        self.assertEqual(len(respuesta.data["results"]), 20)
        self.assertEqual(respuesta.data["total"], 22)


class PaginadorCuentaSinAyudaDeLaVistaTests(TestCase):
    """El `total` no depende de que la vista se acuerde de pasarlo.

    Antes, `get_paginated_response()` recibía `total=` como argumento de la
    vista. Funcionaba, pero DRF llama a ese mismo método por su cuenta en las
    vistas genéricas (`ListAPIView.list()`), sin ese argumento: el día que
    alguien migrara estas vistas de `APIView` a una genérica, la respuesta
    empezaría a traer `"total": null` **sin fallar**, y un encabezado que dice
    «Reseñas ()» no se parece a un error lo suficiente como para investigarlo.

    Ahora el paginador cuenta en `paginate_queryset()`, donde ve el queryset
    completo. Esta prueba lo ejercita directamente, con la firma exacta que usa
    DRF, para que la garantía no dependa de cómo esté escrita la vista de hoy.
    """

    def setUp(self):
        self.usuario = UsuarioFactory()
        self.produccion = ProduccionAudiovisualFactory(
            id_tmdb=550, tipo=TipoProduccion.PELICULA
        )
        for indice in range(3):
            Calificacion.objects.create(
                usuario=UsuarioFactory(nombre_usuario=f"p{indice}"),
                produccion=ProduccionAudiovisualFactory(
                    id_tmdb=700 + indice, tipo=TipoProduccion.PELICULA
                ),
                valor=5,
            )

    @staticmethod
    def _pedido():
        """Un `Request` de DRF, que es lo que el paginador espera.

        `APIRequestFactory` devuelve el `WSGIRequest` de Django, sin
        `query_params`; envolverlo es lo que hace DRF en cada request real.
        """
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory

        return Request(APIRequestFactory().get("/api/reviews/mias/"))

    def test_el_total_sale_sin_pasarselo(self):
        from catalogo.pagination_reviews import ResenaCursorPagination

        paginador = ResenaCursorPagination()
        queryset = Calificacion.objects.all()
        pedido = self._pedido()

        pagina = paginador.paginate_queryset(queryset, pedido, view=None)
        # Exactamente como la llama DRF en una vista genérica: sin argumentos
        # extra.
        respuesta = paginador.get_paginated_response([])

        self.assertEqual(len(pagina), 3)
        self.assertEqual(respuesta.data["total"], 3)
