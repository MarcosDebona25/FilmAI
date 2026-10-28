"""F2 de la auditoría: login, registro y reenvío de confirmación sin límite.

Cada caso mide qué pasa en el N-ésimo pedido de una rafaga. Antes del arreglo
ninguna rafaga recibía 429 (Too Many Requests): se podían probar contraseñas sin
tope y disparar correos sin tope.
"""

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .factories import UsuarioFactory
from .models import Usuario

LOGIN = "/api/auth/login/"
REGISTRO = "/api/auth/registration/"
REENVIO = "/api/auth/registration/resend-email/"


class ThrottleBase(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.client = APIClient()

    def rafaga(self, ruta, cuerpos, **extra):
        return [
            self.client.post(ruta, cuerpo, format="json", **extra).status_code
            for cuerpo in cuerpos
        ]


class LoginThrottleTests(ThrottleBase):
    def test_intentos_fallidos_contra_una_cuenta_terminan_en_429(self):
        usuario = UsuarioFactory()
        cuerpo = {"email": usuario.correo, "password": "incorrecta"}
        estados = self.rafaga(LOGIN, [cuerpo] * 12)
        self.assertEqual(estados[:10], [400] * 10)
        self.assertEqual(estados[10:], [429, 429])

    def test_con_la_cuenta_bloqueada_ni_la_contrasena_correcta_pasa(self):
        usuario = UsuarioFactory()
        self.rafaga(LOGIN, [{"email": usuario.correo, "password": "mala"}] * 11)
        respuesta = self.client.post(
            LOGIN,
            {"email": usuario.correo, "password": "Password123!"},
            format="json",
        )
        self.assertEqual(respuesta.status_code, 429)
        self.assertIn("Retry-After", respuesta)

    def test_el_limite_de_una_cuenta_no_bloquea_a_otra(self):
        a, b = UsuarioFactory(), UsuarioFactory()
        self.rafaga(LOGIN, [{"email": a.correo, "password": "mala"}] * 11)
        respuesta = self.client.post(
            LOGIN, {"email": b.correo, "password": "Password123!"}, format="json"
        )
        self.assertEqual(respuesta.status_code, 200)

    def test_el_correo_se_compara_sin_distinguir_mayusculas(self):
        usuario = UsuarioFactory()
        cuerpos = [
            {"email": variante, "password": "mala"}
            for variante in (usuario.correo.upper(), usuario.correo.lower()) * 6
        ]
        self.assertEqual(self.rafaga(LOGIN, cuerpos)[-1], 429)

    def test_el_nombre_de_usuario_tambien_cuenta_como_cuenta(self):
        usuario = UsuarioFactory()
        cuerpo = {"username": usuario.nombre_usuario, "password": "mala"}
        self.assertEqual(self.rafaga(LOGIN, [cuerpo] * 11)[-1], 429)

    def test_un_nombre_de_usuario_numerico_en_json_tambien_se_limita(self):
        """Un `username` enviado como número no debe esquivar el límite."""
        cuerpo = {"username": 12345678, "password": "mala"}
        estados = self.rafaga(LOGIN, [cuerpo] * 12)
        self.assertEqual(estados[:10], [400] * 10)
        self.assertEqual(estados[10:], [429, 429])

    def test_numero_y_texto_comparten_el_mismo_contador(self):
        cuerpos = [{"username": 777, "password": "mala"}] * 6 + [
            {"username": "777", "password": "mala"}
        ] * 5
        self.assertEqual(self.rafaga(LOGIN, cuerpos)[-1], 429)

    def test_listas_y_objetos_como_identidad_no_rompen_ni_se_cuentan_por_cuenta(self):
        for valor in ([1, 2], {"a": 1}, True, None):
            with self.subTest(valor=valor):
                respuesta = self.client.post(
                    LOGIN, {"username": valor, "password": "mala"}, format="json"
                )
                self.assertEqual(respuesta.status_code, 400)

    def test_un_atacante_que_prueba_muchas_cuentas_desde_una_ip_termina_en_429(self):
        cuerpos = [
            {"email": f"victima{i}@example.com", "password": "x"} for i in range(35)
        ]
        estados = self.rafaga(LOGIN, cuerpos)
        self.assertNotIn(429, estados[:30])
        self.assertEqual(estados[30:], [429] * 5)

    def test_rotar_x_forwarded_for_no_evita_el_limite_por_ip(self):
        estados = []
        for i in range(35):
            respuesta = self.client.post(
                LOGIN,
                {"email": f"victima{i}@example.com", "password": "x"},
                format="json",
                HTTP_X_FORWARDED_FOR=f"10.1.{i}.1",
            )
            estados.append(respuesta.status_code)
        self.assertEqual(estados[-1], 429)

    def test_el_429_usa_el_sobre_estandar(self):
        usuario = UsuarioFactory()
        cuerpo = {"email": usuario.correo, "password": "mala"}
        self.rafaga(LOGIN, [cuerpo] * 10)
        respuesta = self.client.post(LOGIN, cuerpo, format="json")
        self.assertEqual(respuesta.status_code, 429)
        self.assertEqual(respuesta.json()["code"], "throttled")


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CorreoThrottleTests(ThrottleBase):
    def pendiente(self):
        self.client.post(
            REGISTRO,
            {
                "correo": "nueva@example.com",
                "nombre_usuario": "nueva123",
                "nombre": "María",
                "apellido": "Pérez",
                "fecha_nacimiento": "1990-01-01",
                "genero": "no_especifica",
                "pais": "AR",
                "acepta_terminos": True,
                "password1": "NuevaClave456!",
                "password2": "NuevaClave456!",
            },
            format="json",
        )
        self.assertEqual(len(mail.outbox), 1)

    def test_el_reenvio_al_mismo_correo_tiene_enfriamiento(self):
        self.pendiente()
        cuerpo = {"email": "nueva@example.com"}
        primero = self.client.post(REENVIO, cuerpo, format="json")
        segundo = self.client.post(REENVIO, cuerpo, format="json")
        self.assertEqual(primero.status_code, 200)
        self.assertEqual(segundo.status_code, 429)
        self.assertEqual(len(mail.outbox), 2)

    def test_el_reenvio_al_mismo_correo_tiene_tope_por_hora(self):
        self.pendiente()
        cuerpo = {"email": "nueva@example.com"}
        for _ in range(8):
            self.client.post(REENVIO, cuerpo, format="json")
            self._saltar_enfriamiento()  # el enfriamiento se prueba aparte
        self.assertLessEqual(len(mail.outbox), 1 + 3)

    def _saltar_enfriamiento(self):
        """Vacía solo el contador del enfriamiento de 1 minuto."""
        from .throttles import ReenvioEnfriamientoThrottle

        throttle = ReenvioEnfriamientoThrottle()
        cache.delete(
            throttle.cache_format
            % {
                "scope": throttle.scope,
                "ident": throttle.identidad_de("nueva@example.com"),
            }
        )

    def test_reenviar_a_muchos_correos_desde_una_ip_termina_en_429(self):
        estados = self.rafaga(
            REENVIO, [{"email": f"otro{i}@example.com"} for i in range(15)]
        )
        self.assertEqual(estados[-1], 429)

    def test_el_registro_repetido_con_el_mismo_correo_termina_en_429(self):
        cuerpos = [{"correo": "mismo@example.com"}] * 8
        self.assertEqual(self.rafaga(REGISTRO, cuerpos)[-1], 429)

    def test_el_registro_masivo_desde_una_ip_termina_en_429(self):
        cuerpos = [{"correo": f"masivo{i}@example.com"} for i in range(15)]
        self.assertEqual(self.rafaga(REGISTRO, cuerpos)[-1], 429)

    def test_sin_pasarse_del_limite_el_flujo_normal_sigue_andando(self):
        self.pendiente()
        self.assertEqual(Usuario.objects.filter(correo="nueva@example.com").count(), 1)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ResetContrasenaThrottleTests(ThrottleBase):
    """Reset de contraseña: cuerpo inválido sin 500 (Internal Server Error) y tope por IP.

    Antes, `{"email": 5}` rompía el throttle (`.strip()` sobre un entero) y el
    pedido no tenía límite por IP: se podían pedir correos de reset a miles de
    cuentas distintas, cada una con su propio contador por correo.
    """

    RUTAS = ("/api/auth/password/reset/", "/api/auth/password/reset")

    def test_un_correo_que_no_es_texto_responde_400_y_nunca_500(self):
        for ruta in self.RUTAS:
            for valor in (5, None, ["a"], {"a": 1}, True, 1.5):
                with self.subTest(ruta=ruta, valor=valor):
                    cache.clear()
                    respuesta = self.client.post(ruta, {"email": valor}, format="json")
                    self.assertEqual(respuesta.status_code, 400)
                    self.assertEqual(respuesta.json()["code"], "validation_error")

    def test_un_cuerpo_que_no_es_un_objeto_responde_400_y_nunca_500(self):
        for ruta in self.RUTAS:
            for cuerpo in (["a@b.com"], "a@b.com", 5, None):
                with self.subTest(ruta=ruta, cuerpo=cuerpo):
                    cache.clear()
                    respuesta = self.client.post(ruta, cuerpo, format="json")
                    self.assertEqual(respuesta.status_code, 400)

    def test_los_pedidos_invalidos_caen_al_limite_por_ip(self):
        estados = self.rafaga(self.RUTAS[0], [{"email": 5}] * 7)
        self.assertEqual(estados[:5], [400] * 5)
        self.assertEqual(estados[5:], [429, 429])

    def test_la_ip_n_mas_uno_recibe_429_aunque_cambie_el_correo(self):
        for ruta in self.RUTAS:
            cache.clear()
            with self.subTest(ruta=ruta):
                cuerpos = [{"email": f"victima{i}@example.com"} for i in range(12)]
                estados = self.rafaga(ruta, cuerpos)
                self.assertEqual(estados[:10], [200] * 10)
                self.assertEqual(estados[10:], [429, 429])

    def test_el_limite_por_ip_no_depende_del_x_forwarded_for(self):
        estados = [
            self.client.post(
                self.RUTAS[0],
                {"email": f"victima{i}@example.com"},
                format="json",
                HTTP_X_FORWARDED_FOR=f"10.2.{i}.1",
            ).status_code
            for i in range(12)
        ]
        self.assertEqual(estados[-1], 429)

    def test_el_limite_por_correo_sigue_vigente(self):
        for ruta in self.RUTAS:
            cache.clear()
            with self.subTest(ruta=ruta):
                estados = self.rafaga(ruta, [{"email": "mismo@example.com"}] * 7)
                self.assertEqual(estados[:5], [200] * 5)
                self.assertEqual(estados[5:], [429, 429])

    def test_el_429_por_ip_usa_el_sobre_estandar(self):
        self.rafaga(
            self.RUTAS[0], [{"email": f"victima{i}@example.com"} for i in range(10)]
        )
        respuesta = self.client.post(
            self.RUTAS[0], {"email": "otra@example.com"}, format="json"
        )
        self.assertEqual(respuesta.status_code, 429)
        self.assertEqual(respuesta.json()["code"], "throttled")

    def test_el_mensaje_de_intentos_restantes_sigue_en_la_respuesta(self):
        respuesta = self.client.post(
            self.RUTAS[0], {"email": "ana@example.com"}, format="json"
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["intentos_restantes"], 4)
