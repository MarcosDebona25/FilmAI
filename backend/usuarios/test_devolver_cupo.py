"""`devolver_cupo`: quita del historial de cada throttle el último intento."""

from django.core.cache import cache
from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from .throttles import PorIPThrottle, RegistroCorreoThrottle, devolver_cupo


class _PorIP(PorIPThrottle):
    scope = "registro_ip"


class _Vista(APIView):
    throttle_classes = (RegistroCorreoThrottle, _PorIP)


class DevolverCupoTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.vista = _Vista()

    def pedido(self, cuerpo):
        request = self.vista.initialize_request(
            APIRequestFactory().post("/x/", cuerpo, format="json")
        )
        self.vista.request = request
        return request

    def intentos(self, request):
        """Cuántas marcas tiene cada throttle (lo que DRF compara con la tasa)."""
        resultado = []
        for throttle in self.vista.get_throttles():
            clave = throttle.get_cache_key(request, self.vista)
            resultado.append(len(cache.get(clave, [])))
        return resultado

    def anotar(self, request):
        """Lo que hace DRF antes de la vista: `allow_request` anota el intento."""
        for throttle in self.vista.get_throttles():
            self.assertTrue(throttle.allow_request(request, self.vista))

    def test_quita_una_marca_de_cada_throttle_de_la_vista(self):
        request = self.pedido({"correo": "a@example.com"})
        self.anotar(request)
        self.anotar(request)
        self.assertEqual(self.intentos(request), [2, 2])
        devolver_cupo(request, self.vista)
        self.assertEqual(self.intentos(request), [1, 1])

    def test_sin_historial_no_falla_ni_crea_claves(self):
        request = self.pedido({"correo": "a@example.com"})
        devolver_cupo(request, self.vista)
        self.assertEqual(self.intentos(request), [0, 0])

    def test_un_throttle_sin_clave_se_saltea(self):
        """Sin correo en el cuerpo el throttle por cuenta no anota nada: solo el de IP."""
        request = self.pedido({})
        self.anotar(request)
        self.assertEqual(self.intentos(request)[1], 1)
        devolver_cupo(request, self.vista)
        self.assertEqual(self.intentos(request)[1], 0)

    def test_no_toca_el_historial_de_otros_correos(self):
        ana = self.pedido({"correo": "ana@example.com"})
        self.anotar(ana)
        luis = self.pedido({"correo": "luis@example.com"})
        self.anotar(luis)
        devolver_cupo(luis, self.vista)
        self.assertEqual(self.intentos(ana)[0], 1)
        self.assertEqual(self.intentos(luis)[0], 0)
