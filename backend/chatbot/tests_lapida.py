"""El chatbot no ofrece ni nombra títulos que TMDB ya no tiene (#180)."""

from catalogo.factories import CalificacionFactory
from catalogo.models import ProduccionAudiovisual, TipoProduccion
from chatbot.contexto import armar_perfil
from chatbot.tests_tools import BaseTools
from chatbot.tools import ejecutar
from listas.models import ClaveLista, Tiene


def lapida(id_tmdb=900):
    return ProduccionAudiovisual.objects.create(
        id_tmdb=id_tmdb,
        tipo=TipoProduccion.PELICULA,
        titulo="",
        disponible_en_tmdb=False,
    )


class LapidaEnElChatbotTests(BaseTools):
    def test_mis_listas_no_incluye_la_lapida(self):
        lista = self.lista(ClaveLista.PENDIENTES, "Pendientes")
        Tiene.objects.create(lista=lista, produccion=self.produccion("Moon"))
        Tiene.objects.create(lista=lista, produccion=lapida())

        resultado = ejecutar(self.contexto(), "mis_listas", {"lista": "pendientes"})

        self.assertEqual([r["titulo"] for r in resultado["resultados"]], ["Moon"])

    def test_el_perfil_no_nombra_titulos_vacios_de_lapidas(self):
        CalificacionFactory(usuario=self.usuario, produccion=lapida(), valor=9)
        Tiene.objects.create(
            lista=self.lista(ClaveLista.VISTAS, "Vistas"), produccion=lapida(901)
        )

        # Sin otra actividad, el perfil queda vacío: no hay «Le gustó:  (9)».
        self.assertEqual(armar_perfil(self.usuario), "")
