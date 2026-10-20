"""F5 de la auditoría: un staff con solo `change_usuario` podía escalar privilegios.

`UserAdmin` de Django trata «puede cambiar usuarios» como «administra todo»:
sin restricciones extra, quien tenga ese permiso puede marcarse `is_superuser`,
darse permisos y fijar la contraseña de un superusuario.
"""

from django.contrib.auth.models import Permission
from django.test import Client, TestCase

from .factories import UsuarioFactory
from .models import Usuario

CLAVE_NUEVA = "OtraClave789!"


def url_cambio(usuario):
    return f"/admin/usuarios/usuario/{usuario.pk}/change/"


def url_clave(usuario):
    return f"/admin/usuarios/usuario/{usuario.pk}/password/"


class AdminStaffParcialTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.superusuario = Usuario.objects.create_superuser(
            correo="root@example.com",
            password="ClaveRoot123!",
            nombre_usuario="rootadmin",
            nombre="Root",
            apellido="Admin",
            fecha_nacimiento="1990-01-01",
        )
        cls.staff = UsuarioFactory(is_staff=True)
        cls.staff.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="usuarios",
                content_type__model="usuario",
                codename__in=["view_usuario", "change_usuario"],
            )
        )
        cls.comun = UsuarioFactory()

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.staff)

    def datos_del_formulario(self, usuario, **cambios):
        respuesta = self.client.get(url_cambio(usuario))
        self.assertEqual(respuesta.status_code, 200)
        formulario = respuesta.context["adminform"].form
        datos = {}
        for nombre in formulario.fields:
            valor = formulario.initial.get(nombre)
            if valor in (None, False):
                continue
            datos[nombre] = (
                [getattr(v, "pk", v) for v in valor]
                if isinstance(valor, (list, tuple, set)) or hasattr(valor, "all")
                else valor
            )
        datos.update(cambios)
        return datos

    # --- Escalada de privilegios -------------------------------------------------

    def test_el_staff_no_puede_hacerse_superusuario(self):
        datos = self.datos_del_formulario(self.staff, is_superuser="on")
        self.client.post(url_cambio(self.staff), datos)
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.is_superuser)

    def test_el_staff_no_puede_darse_permisos_ni_grupos(self):
        permiso = Permission.objects.get(codename="delete_usuario")
        datos = self.datos_del_formulario(
            self.staff,
            user_permissions=[
                *self.staff.user_permissions.values_list("pk", flat=True),
                permiso.pk,
            ],
        )
        self.client.post(url_cambio(self.staff), datos)
        self.assertFalse(
            self.staff.user_permissions.filter(codename="delete_usuario").exists()
        )

    def test_el_staff_no_puede_dar_staff_a_otro_usuario(self):
        datos = self.datos_del_formulario(self.comun, is_staff="on")
        self.client.post(url_cambio(self.comun), datos)
        self.comun.refresh_from_db()
        self.assertFalse(self.comun.is_staff)

    def test_los_campos_de_privilegio_se_muestran_de_solo_lectura(self):
        formulario = self.client.get(url_cambio(self.comun)).context["adminform"].form
        for campo in ("is_superuser", "is_staff", "groups", "user_permissions"):
            self.assertNotIn(campo, formulario.fields)

    # --- Superusuarios intocables ------------------------------------------------

    def test_el_staff_no_ve_a_los_superusuarios_en_el_listado(self):
        respuesta = self.client.get("/admin/usuarios/usuario/")
        self.assertEqual(respuesta.status_code, 200)
        correos = {u.correo for u in respuesta.context["cl"].result_list}
        self.assertNotIn(self.superusuario.correo, correos)
        self.assertIn(self.comun.correo, correos)

    def test_el_formulario_de_un_superusuario_no_existe_para_el_staff(self):
        """El queryset lo excluye: Django responde como si no existiera
        (redirección al índice del admin con aviso, no 403 (Forbidden))."""
        respuesta = self.client.get(url_cambio(self.superusuario))
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta["Location"], "/admin/")

    def test_el_staff_no_puede_modificar_a_un_superusuario_por_post(self):
        datos = self.datos_del_formulario(self.comun, nombre="Hackeado")
        respuesta = self.client.post(url_cambio(self.superusuario), datos)
        self.assertEqual(respuesta.status_code, 302)
        self.superusuario.refresh_from_db()
        self.assertNotEqual(self.superusuario.nombre, "Hackeado")

    def test_el_staff_no_puede_cambiar_la_clave_de_un_superusuario(self):
        respuesta = self.client.post(
            url_clave(self.superusuario),
            {"password1": CLAVE_NUEVA, "password2": CLAVE_NUEVA},
        )
        # No existe para el staff: la vista de contraseña responde 404 (Not Found).
        self.assertEqual(respuesta.status_code, 404)
        self.superusuario.refresh_from_db()
        self.assertFalse(self.superusuario.check_password(CLAVE_NUEVA))
        self.assertTrue(self.superusuario.check_password("ClaveRoot123!"))

    def test_el_staff_no_puede_cambiar_la_clave_de_otro_staff(self):
        """Otro staff sí aparece en el queryset: la negativa es 403 (Forbidden)."""
        otro = UsuarioFactory(is_staff=True)
        respuesta = self.client.post(
            url_clave(otro), {"password1": CLAVE_NUEVA, "password2": CLAVE_NUEVA}
        )
        self.assertEqual(respuesta.status_code, 403)
        otro.refresh_from_db()
        self.assertFalse(otro.check_password(CLAVE_NUEVA))

    def test_el_staff_ve_a_otro_staff_solo_para_leer_y_no_lo_edita(self):
        """Con `view_usuario` abre la ficha en modo lectura; guardar da 403 (Forbidden)."""
        otro = UsuarioFactory(is_staff=True)
        ficha = self.client.get(url_cambio(otro))
        self.assertEqual(ficha.status_code, 200)
        self.assertFalse(ficha.context["has_change_permission"])
        respuesta = self.client.post(url_cambio(otro), {"nombre": "Cambiado"})
        self.assertEqual(respuesta.status_code, 403)
        nombre = otro.nombre
        otro.refresh_from_db()
        self.assertEqual(otro.nombre, nombre)

    def test_el_staff_si_puede_editarse_a_si_mismo_pero_sin_privilegios(self):
        datos = self.datos_del_formulario(
            self.staff, nombre="Propio", is_superuser="on"
        )
        respuesta = self.client.post(url_cambio(self.staff), datos)
        self.assertEqual(respuesta.status_code, 302)
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.nombre, "Propio")
        self.assertFalse(self.staff.is_superuser)

    # --- Lo legítimo sigue andando ----------------------------------------------

    def test_el_staff_puede_editar_datos_de_un_usuario_comun(self):
        datos = self.datos_del_formulario(self.comun, nombre="Renombrado")
        respuesta = self.client.post(url_cambio(self.comun), datos)
        self.assertEqual(respuesta.status_code, 302)
        self.comun.refresh_from_db()
        self.assertEqual(self.comun.nombre, "Renombrado")

    def test_el_staff_puede_cambiar_la_clave_de_un_usuario_comun(self):
        self.client.post(
            url_clave(self.comun), {"password1": CLAVE_NUEVA, "password2": CLAVE_NUEVA}
        )
        self.comun.refresh_from_db()
        self.assertTrue(self.comun.check_password(CLAVE_NUEVA))


class AdminBorradoTests(TestCase):
    """Un staff con `delete_usuario` no puede borrar a quien no puede editar."""

    @classmethod
    def setUpTestData(cls):
        cls.superusuario = Usuario.objects.create_superuser(
            correo="root@example.com",
            password="ClaveRoot123!",
            nombre_usuario="rootadmin",
            nombre="Root",
            apellido="Admin",
            fecha_nacimiento="1990-01-01",
        )
        cls.staff = UsuarioFactory(is_staff=True)
        cls.staff.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label="usuarios",
                content_type__model="usuario",
                codename__in=["view_usuario", "change_usuario", "delete_usuario"],
            )
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.staff)

    def borrar(self, usuario):
        return self.client.post(
            f"/admin/usuarios/usuario/{usuario.pk}/delete/", {"post": "yes"}
        )

    def borrado_masivo(self, *usuarios):
        return self.client.post(
            "/admin/usuarios/usuario/",
            {
                "action": "delete_selected",
                "_selected_action": [u.pk for u in usuarios],
                "post": "yes",
            },
        )

    def test_no_puede_borrar_a_otro_staff(self):
        otro = UsuarioFactory(is_staff=True)
        self.assertEqual(self.borrar(otro).status_code, 403)
        self.assertTrue(Usuario.objects.filter(pk=otro.pk).exists())

    def test_no_puede_borrar_a_otro_staff_con_la_accion_masiva(self):
        otro = UsuarioFactory(is_staff=True)
        self.borrado_masivo(otro)
        self.assertTrue(Usuario.objects.filter(pk=otro.pk).exists())

    def test_la_accion_masiva_no_arrastra_a_un_staff_junto_con_usuarios_comunes(self):
        comun, otro = UsuarioFactory(), UsuarioFactory(is_staff=True)
        self.borrado_masivo(comun, otro)
        self.assertTrue(Usuario.objects.filter(pk=otro.pk).exists())

    def test_no_ve_ni_borra_a_un_superusuario(self):
        respuesta = self.borrar(self.superusuario)
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Usuario.objects.filter(pk=self.superusuario.pk).exists())
        self.borrado_masivo(self.superusuario)
        self.assertTrue(Usuario.objects.filter(pk=self.superusuario.pk).exists())

    def test_si_puede_borrar_a_un_usuario_comun(self):
        comun = UsuarioFactory()
        self.assertEqual(self.borrar(comun).status_code, 302)
        self.assertFalse(Usuario.objects.filter(pk=comun.pk).exists())

    def test_el_borrado_masivo_de_usuarios_comunes_sigue_andando(self):
        a, b = UsuarioFactory(), UsuarioFactory()
        self.borrado_masivo(a, b)
        self.assertFalse(Usuario.objects.filter(pk__in=[a.pk, b.pk]).exists())

    def test_el_listado_conserva_la_accion_de_borrado_masivo(self):
        """No se desactiva el borrado globalmente: `obj=None` sigue permitido."""
        respuesta = self.client.get("/admin/usuarios/usuario/")
        self.assertIn(
            "delete_selected",
            respuesta.context["action_form"].fields["action"].choices[1],
        )


class AdminSuperusuarioTests(TestCase):
    """El superusuario conserva el control total."""

    @classmethod
    def setUpTestData(cls):
        cls.root = Usuario.objects.create_superuser(
            correo="root@example.com",
            password="ClaveRoot123!",
            nombre_usuario="rootadmin",
            nombre="Root",
            apellido="Admin",
            fecha_nacimiento="1990-01-01",
        )
        cls.otro_root = Usuario.objects.create_superuser(
            correo="root2@example.com",
            password="ClaveRoot123!",
            nombre_usuario="rootadmin2",
            nombre="Root",
            apellido="Dos",
            fecha_nacimiento="1990-01-01",
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.root)

    def test_ve_a_todos_y_puede_editar_privilegios(self):
        respuesta = self.client.get("/admin/usuarios/usuario/")
        correos = {u.correo for u in respuesta.context["cl"].result_list}
        self.assertIn(self.otro_root.correo, correos)
        formulario = (
            self.client.get(url_cambio(self.otro_root)).context["adminform"].form
        )
        for campo in ("is_superuser", "is_staff", "groups", "user_permissions"):
            self.assertIn(campo, formulario.fields)

    def test_puede_cambiar_la_clave_de_otro_superusuario(self):
        self.client.post(
            url_clave(self.otro_root),
            {"password1": CLAVE_NUEVA, "password2": CLAVE_NUEVA},
        )
        self.otro_root.refresh_from_db()
        self.assertTrue(self.otro_root.check_password(CLAVE_NUEVA))
