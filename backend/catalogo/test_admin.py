"""Pruebas HTTP del Admin de usuarios y moderación de reseñas (AD-01')."""

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Calificacion, ProduccionAudiovisual, Resena, TipoProduccion
from usuarios.factories import UsuarioFactory
from usuarios.models import EstadoCuenta, Usuario


class ResenaAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = UsuarioFactory(is_staff=True, is_superuser=True)
        cls.autor = UsuarioFactory(nombre_usuario="autorrese")
        cls.otro_autor = UsuarioFactory(nombre_usuario="otroautor")
        pelicula = ProduccionAudiovisual.objects.create(
            id_tmdb=100, tipo=TipoProduccion.PELICULA, titulo="Película Alfa"
        )
        serie = ProduccionAudiovisual.objects.create(
            id_tmdb=101, tipo=TipoProduccion.SERIE, titulo="Serie Beta"
        )
        cls.calificacion = Calificacion.objects.create(
            usuario=cls.autor, produccion=pelicula, valor=8
        )
        otra_calificacion = Calificacion.objects.create(
            usuario=cls.otro_autor, produccion=serie, valor=4
        )
        cls.resena = Resena.objects.create(
            calificacion=cls.calificacion, texto="Texto especial alfa"
        )
        cls.otra_resena = Resena.objects.create(
            calificacion=otra_calificacion, texto="Texto beta", activa=False
        )
        cls.lista_url = reverse("admin:catalogo_resena_changelist")
        cls.cambio_url = reverse("admin:catalogo_resena_change", args=[cls.resena.pk])

    def setUp(self):
        self.client.force_login(self.admin)

    def _ids_listados(self, parametros=None):
        respuesta = self.client.get(self.lista_url, parametros or {})
        self.assertEqual(respuesta.status_code, 200)
        return {resena.pk for resena in respuesta.context["cl"].result_list}

    def test_listado_muestra_relaciones_y_resenas_inactivas(self):
        respuesta = self.client.get(self.lista_url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, self.autor.nombre_usuario)
        self.assertContains(respuesta, "Película Alfa")
        self.assertContains(respuesta, "8")
        self.assertEqual(
            {resena.pk for resena in respuesta.context["cl"].result_list},
            {self.resena.pk, self.otra_resena.pk},
        )

    def test_busqueda_por_texto_usuario_y_produccion(self):
        for consulta in (
            "especial alfa",
            self.autor.nombre_usuario,
            self.autor.correo,
            "Película Alfa",
        ):
            with self.subTest(consulta=consulta):
                self.assertEqual(self._ids_listados({"q": consulta}), {self.resena.pk})

    def test_filtros_por_estado_y_tipo(self):
        self.assertEqual(self._ids_listados({"activa__exact": "1"}), {self.resena.pk})
        self.assertEqual(
            self._ids_listados({"activa__exact": "0"}), {self.otra_resena.pk}
        )
        self.assertEqual(
            self._ids_listados({"calificacion__produccion__tipo__exact": "pelicula"}),
            {self.resena.pk},
        )

    def test_edicion_cambia_texto_y_estado_sin_cambiar_calificacion(self):
        respuesta = self.client.get(self.cambio_url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, str(self.calificacion))
        self.assertNotContains(respuesta, 'name="calificacion"')

        respuesta = self.client.post(
            self.cambio_url,
            {
                "texto": "Texto moderado",
                "activa": "on",
                "calificacion": self.otra_resena.calificacion_id,
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.resena.refresh_from_db()
        self.assertEqual(self.resena.texto, "Texto moderado")
        self.assertEqual(self.resena.calificacion_id, self.calificacion.pk)
        self.assertTrue(self.resena.activa)

    def test_accion_desactiva_sin_borrar_y_permite_reactivar(self):
        respuesta = self.client.post(
            self.lista_url,
            {"action": "desactivar_resenas", "_selected_action": [self.resena.pk]},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.resena.refresh_from_db()
        self.assertFalse(self.resena.activa)
        self.assertTrue(Calificacion.objects.filter(pk=self.calificacion.pk).exists())
        self.assertEqual(
            self._ids_listados({"activa__exact": "0"}),
            {self.resena.pk, self.otra_resena.pk},
        )

        respuesta = self.client.post(
            self.cambio_url, {"texto": self.resena.texto, "activa": "on"}
        )
        self.assertEqual(respuesta.status_code, 302)
        self.resena.refresh_from_db()
        self.assertTrue(self.resena.activa)

    def test_admin_no_ofrece_alta_ni_borrado_fisico(self):
        self.assertNotContains(
            self.client.get(self.lista_url), reverse("admin:catalogo_resena_add")
        )
        self.assertEqual(
            self.client.get(reverse("admin:catalogo_resena_add")).status_code, 403
        )
        self.assertEqual(
            self.client.get(
                reverse("admin:catalogo_resena_delete", args=[self.resena.pk])
            ).status_code,
            403,
        )
        respuesta = self.client.post(
            self.lista_url,
            {"action": "delete_selected", "_selected_action": [self.resena.pk]},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Resena.objects.filter(pk=self.resena.pk).exists())
        self.assertTrue(Calificacion.objects.filter(pk=self.calificacion.pk).exists())

    def test_acceso_segun_rol_y_permisos_del_modelo(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.lista_url).status_code, 302)
        self.client.force_login(self.autor)
        self.assertEqual(self.client.get(self.lista_url).status_code, 302)

        staff = UsuarioFactory(is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(self.lista_url).status_code, 403)

        staff.user_permissions.add(Permission.objects.get(codename="view_resena"))
        self.assertEqual(self.client.get(self.lista_url).status_code, 200)
        self.assertEqual(self.client.get(self.cambio_url).status_code, 200)
        self.assertEqual(
            self.client.post(self.cambio_url, {"texto": "Intento"}).status_code, 403
        )
        staff.user_permissions.add(Permission.objects.get(codename="change_resena"))
        self.assertEqual(self.client.get(self.cambio_url).status_code, 200)


class UsuarioAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = UsuarioFactory(is_staff=True, is_superuser=True)
        cls.usuario = UsuarioFactory(
            nombre_usuario="adminbusca", correo="adminbusca@filmai.com"
        )
        cls.otro = UsuarioFactory(nombre_usuario="otrobusca")
        cls.lista_url = reverse("admin:usuarios_usuario_changelist")
        cls.cambio_url = reverse("admin:usuarios_usuario_change", args=[cls.usuario.pk])

    def setUp(self):
        self.client.force_login(self.admin)

    def test_busqueda_y_filtro_existentes(self):
        respuesta = self.client.get(self.lista_url, {"q": "adminbusca@filmai.com"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            {usuario.pk for usuario in respuesta.context["cl"].result_list},
            {self.usuario.pk},
        )
        respuesta = self.client.get(
            self.lista_url, {"estado__exact": EstadoCuenta.ACTIVA}
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(self.usuario, respuesta.context["cl"].result_list)

    def test_edicion_estado_y_borrado_existentes(self):
        respuesta = self.client.get(self.cambio_url)
        self.assertEqual(respuesta.status_code, 200)
        datos = {
            "correo": self.usuario.correo,
            "password": self.usuario.password,
            "nombre_usuario": self.usuario.nombre_usuario,
            "nombre": "Nombre moderado",
            "apellido": self.usuario.apellido,
            "fecha_nacimiento": self.usuario.fecha_nacimiento.isoformat(),
            "genero": self.usuario.genero,
            "avatar_id": self.usuario.avatar_id,
            "estado": EstadoCuenta.BAJA,
            "pais": self.usuario.pais,
            "perfil_publico": "on",
            "notif_recomendaciones": "on",
            "notif_resenas": "on",
            "notif_novedades": "on",
        }
        respuesta = self.client.post(self.cambio_url, datos)
        self.assertEqual(respuesta.status_code, 302)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.nombre, "Nombre moderado")
        self.assertEqual(self.usuario.estado, EstadoCuenta.BAJA)

        borrar_url = reverse("admin:usuarios_usuario_delete", args=[self.usuario.pk])
        self.assertEqual(self.client.get(borrar_url).status_code, 200)
        self.assertEqual(self.client.post(borrar_url, {"post": "yes"}).status_code, 302)
        self.assertFalse(Usuario.objects.filter(pk=self.usuario.pk).exists())

    def test_permisos_de_usuario_admin(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.lista_url).status_code, 302)
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(self.lista_url).status_code, 302)
        staff = UsuarioFactory(is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(self.lista_url).status_code, 403)
        staff.user_permissions.add(Permission.objects.get(codename="view_usuario"))
        self.assertEqual(self.client.get(self.lista_url).status_code, 200)
        self.assertEqual(self.client.post(self.cambio_url, {}).status_code, 403)
