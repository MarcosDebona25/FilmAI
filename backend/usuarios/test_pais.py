"""País de la cuenta (`Usuario.pais`): lista, migración, registro, Google y perfil."""

import json
from datetime import date
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from rest_framework_simplejwt.tokens import RefreshToken

from usuarios.paises import ROTACION, codigos_pais, es_pais_valido
from usuarios.serializers import CAMPOS_FALTANTES_GOOGLE, GoogleSocialLoginSerializer

from .factories import UsuarioFactory
from .models import Usuario

REGISTRO = {
    "correo": "pais@example.com",
    "nombre_usuario": "usuariopais",
    "nombre": "Cuenta",
    "apellido": "Nueva",
    "fecha_nacimiento": "1990-01-01",
    "genero": "no_especifica",
    "pais": "AR",
    "acepta_terminos": True,
    "password1": "Password123!",
    "password2": "Password123!",
}


class ListaDePaisesTests(SimpleTestCase):
    def test_son_249_codigos_iso_unicos_en_mayusculas(self):
        codigos = codigos_pais()

        self.assertEqual(len(codigos), 249)
        self.assertEqual(len(set(codigos)), 249)
        self.assertTrue(
            all(len(c) == 2 and c.isalpha() and c.isupper() for c in codigos)
        )

    def test_paridad_con_el_contrato_versionado(self):
        archivo = Path(settings.BASE_DIR).parent / "contracts" / "enums.json"
        versionado = json.loads(archivo.read_text(encoding="utf-8"))["paisCodes"]

        self.assertEqual(list(codigos_pais()), versionado)

    def test_la_rotacion_usa_solo_paises_validos(self):
        self.assertTrue(all(es_pais_valido(c) for c in ROTACION))
        for valor in ("", "ZZ", "ar", None, 5):
            self.assertFalse(es_pais_valido(valor))


class FactoryPaisTests(TestCase):
    def test_la_factory_rota_los_paises(self):
        paises = {UsuarioFactory().pais for _ in range(len(ROTACION))}

        self.assertEqual(paises, set(ROTACION))


class MigracionPaisTests(TransactionTestCase):
    anterior = ("usuarios", "0009_remove_usuario_tema")
    nueva = ("usuarios", "0010_usuario_pais")

    def test_asigna_en_rotacion_queda_no_nulo_y_es_reversible(self):
        executor = MigrationExecutor(connection)
        actuales = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate([self.anterior])
            Anterior = executor.loader.project_state([self.anterior]).apps.get_model(
                "usuarios", "Usuario"
            )
            ids = [
                Anterior.objects.create(
                    correo=f"m{i}@example.com",
                    nombre_usuario=f"migrado{i:02d}",
                    nombre="Cuenta",
                    apellido="Anterior",
                    fecha_nacimiento=date(1990, 1, 1),
                    genero="no_especifica",
                ).pk
                for i in range(10)
            ]

            executor = MigrationExecutor(connection)
            executor.migrate([self.nueva])
            Nuevo = executor.loader.project_state([self.nueva]).apps.get_model(
                "usuarios", "Usuario"
            )
            for pk in ids:
                self.assertEqual(
                    Nuevo.objects.get(pk=pk).pais, ROTACION[pk % len(ROTACION)]
                )
            self.assertFalse(Nuevo._meta.get_field("pais").null)
            with connection.cursor() as cursor:
                columnas = connection.introspection.get_table_description(
                    cursor, Nuevo._meta.db_table
                )
            self.assertFalse(next(c for c in columnas if c.name == "pais").null_ok)

            executor = MigrationExecutor(connection)
            executor.migrate([self.anterior])
            Revertido = executor.loader.project_state([self.anterior]).apps.get_model(
                "usuarios", "Usuario"
            )
            self.assertNotIn("pais", {f.name for f in Revertido._meta.fields})
            self.assertEqual(Revertido.objects.count(), len(ids))
        finally:
            MigrationExecutor(connection).migrate(actuales)


class RegistroPaisTests(TestCase):
    def _registrar(self, **cambios):
        datos = {**REGISTRO, **cambios}
        datos = {k: v for k, v in datos.items() if v is not None}
        return self.client.post(
            "/api/auth/registration/", datos, content_type="application/json"
        )

    def test_guarda_el_pais_elegido(self):
        respuesta = self._registrar(pais="PT")

        self.assertEqual(respuesta.status_code, 201, respuesta.content)
        self.assertEqual(Usuario.objects.get(correo=REGISTRO["correo"]).pais, "PT")

    def test_es_obligatorio(self):
        respuesta = self._registrar(pais=None)

        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(
            {"field": "pais", "code": "required", "params": {}},
            respuesta.json()["errors"],
        )
        self.assertFalse(Usuario.objects.filter(correo=REGISTRO["correo"]).exists())

    def test_rechaza_codigos_fuera_de_la_lista(self):
        for valor in ("ZZ", "ar", "A", "ARG", ""):
            with self.subTest(valor=valor):
                respuesta = self._registrar(pais=valor)

                self.assertEqual(respuesta.status_code, 400)
                codigos = {
                    e["code"]
                    for e in respuesta.json()["errors"]
                    if e["field"] == "pais"
                }
                self.assertTrue(codigos & {"country_invalid", "blank", "max_length"})
                self.assertFalse(
                    Usuario.objects.filter(correo=REGISTRO["correo"]).exists()
                )

    def test_un_codigo_con_formato_pero_inexistente_usa_el_codigo_propio(self):
        respuesta = self._registrar(pais="ZZ")

        self.assertIn(
            {"field": "pais", "code": "country_invalid", "params": {}},
            respuesta.json()["errors"],
        )


class GooglePaisTests(SimpleTestCase):
    def test_pais_es_un_campo_que_google_no_provee(self):
        self.assertIn("pais", CAMPOS_FALTANTES_GOOGLE)

    def test_el_serializer_valida_el_pais(self):
        serializer = GoogleSocialLoginSerializer()

        self.assertEqual(serializer.validate_pais("BR"), "BR")
        with self.assertRaises(Exception) as contexto:
            serializer.validate_pais("ZZ")
        self.assertEqual(contexto.exception.detail[0].code, "country_invalid")


class PerfilPaisTests(TestCase):
    def setUp(self):
        self.usuario = UsuarioFactory(pais="AR")
        token = RefreshToken.for_user(self.usuario).access_token
        self.client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"

    def _put(self, datos):
        return self.client.put("/api/profile/", datos, content_type="application/json")

    def test_el_perfil_expone_el_pais(self):
        self.assertEqual(self.client.get("/api/profile/").json()["pais"], "AR")

    def test_se_edita_con_un_codigo_valido(self):
        respuesta = self._put({"pais": "JP"})

        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(respuesta.json()["pais"], "JP")
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.pais, "JP")

    def test_un_codigo_invalido_no_cambia_nada(self):
        for valor in ("ZZ", "jp", "", None):
            with self.subTest(valor=valor):
                respuesta = self._put({"nombre": "Otro", "pais": valor})

                self.assertEqual(respuesta.status_code, 400)
                self.usuario.refresh_from_db()
                self.assertEqual(self.usuario.pais, "AR")
                self.assertNotEqual(self.usuario.nombre, "Otro")

    def test_omitirlo_lo_conserva(self):
        self.assertEqual(self._put({"nombre": "Otro"}).status_code, 200)
        self.usuario.refresh_from_db()
        self.assertEqual(self.usuario.pais, "AR")
