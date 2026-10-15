"""
Comando de desarrollo: `python manage.py seed`.

Pobla la base de datos con datos de prueba consistentes para desarrollar la UI
(F-05 del plan de desarrollo). Es **destructivo e idempotente** con las
cuentas, calificaciones, reseñas, listas y chats: los recrea desde cero.

Por defecto el catálogo es **real**: trae de TMDB los títulos más votados por
género (`seed_real`) y arma actividad con sentido sobre ellos, así cada
tarjeta lleva a su ficha verdadera. No borra producciones reales; solo las
sintéticas de Faker que hubiera. Necesita TMDB configurado y red.

Uso:
    python manage.py seed                     # catálogo real desde TMDB
    python manage.py seed --sintetico         # offline, producciones de Faker
    python manage.py seed --borrar-catalogo   # con --sintetico, si supera el umbral
    python manage.py seed --solo-resenas      # solo calificaciones y reseñas

Con `--sintetico` el catálogo se recrea de cero: por encima de
`UMBRAL_CATALOGO_PROTEGIDO` (lo pobló `seed_catalogo`, horas de TMDB) el comando
se niega a borrarlo salvo `--borrar-catalogo`. `--solo-resenas` es la
alternativa no destructiva: siembra calificaciones y reseñas sobre el
catálogo y los usuarios de desarrollo existentes, sin borrar nada.
"""

import random
from math import ceil

from allauth.account.models import EmailAddress
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalogo.factories import (
    CalificacionFactory,
    ProduccionAudiovisualFactory,
    ResenaFactory,
)
from catalogo.models import (
    Calificacion,
    ProduccionAudiovisual,
    Resena,
    TipoProduccion,
)
from chatbot.factories import MensajeFactory
from chatbot.models import Chat, Mensaje, TipoAutor
from listas.factories import ListaFactory
from listas.models import ClaveLista, Lista, Tiene, TipoLista
from listas.services import agregar_a_vistas
from usuarios import seed_real
from usuarios.factories import UsuarioFactory
from usuarios.models import EstadoCuenta, Usuario
from usuarios.provisioning import nombres_listas_predeterminadas

# Contraseña común para todos los usuarios de prueba (útil para login manual).
SEED_PASSWORD = "Password123!"


CANTIDAD_USUARIOS = 3
CANTIDAD_PRODUCCIONES = 50
CALIFICACIONES_POR_USUARIO_SOLO_RESENAS = 15

# Por encima de esto el catálogo no lo hizo este comando: lo poblaron
# `seed_catalogo`, la sync nocturna o la navegación, a tres llamadas a TMDB
# por fila. Borrarlo sin querer tira ese trabajo y, por CASCADE, las
# calificaciones, reseñas y entradas de listas que cuelgan de él (C-04c).
UMBRAL_CATALOGO_PROTEGIDO = 2 * CANTIDAD_PRODUCCIONES


class Command(BaseCommand):
    help = (
        "Pobla la BD con datos de desarrollo (usuarios, producciones, listas, "
        "calificaciones, reseñas y chats). Destructivo e idempotente."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--borrar-catalogo",
            action="store_true",
            help=(
                "Borra el catálogo aunque supere las "
                f"{UMBRAL_CATALOGO_PROTEGIDO} producciones."
            ),
        )
        parser.add_argument(
            "--sintetico",
            action="store_true",
            help=(
                "Usa producciones de Faker en vez de traerlas de TMDB (sin "
                "red). Sus id_tmdb pueden chocar con títulos reales."
            ),
        )
        parser.add_argument(
            "--solo-resenas",
            action="store_true",
            help=(
                "Crea calificaciones y reseñas sobre el catálogo y los "
                "usuarios de desarrollo existentes, sin borrar nada (útil "
                "cuando el catálogo está protegido por seed_catalogo)."
            ),
        )

    def handle(self, *args, **options):
        if options["solo_resenas"]:
            with transaction.atomic():
                self._solo_resenas()
            return
        if options["sintetico"]:
            with transaction.atomic():
                self._seed_sintetico(options["borrar_catalogo"])
            return
        self._seed_real()

    def _seed_real(self):
        """Catálogo de TMDB y actividad con sentido (modo por defecto).

        La red va ANTES de la transacción: `materializar` maneja sus propias
        carreras y no conviene una conexión abierta durante decenas de
        llamadas. Si TMDB no dejó un pool mínimo se aborta sin borrar nada.
        """
        self.stdout.write("Trayendo el catálogo de TMDB…")
        seed_real.materializar_catalogo(self.stdout)
        cantidad = seed_real.reales().count()
        if cantidad < seed_real.MINIMO_REALES:
            raise CommandError(
                f"Solo hay {cantidad} producciones reales (mínimo "
                f"{seed_real.MINIMO_REALES}): revisá TMDB_API_KEY y la red, o "
                "corré `seed --sintetico` para trabajar sin conexión."
            )
        with transaction.atomic():
            self._limpiar(conservar_reales=True)
            usuarios = self._crear_usuarios()
            seed_real.generar_actividad(usuarios)
            self._crear_chats(usuarios)
        self._resumen(usuarios)

    def _seed_sintetico(self, borrar_catalogo):
        self._verificar_catalogo(borrar_catalogo)
        self._limpiar()
        usuarios = self._crear_usuarios()
        producciones = self._crear_producciones()
        self._crear_calificaciones_y_resenas(usuarios, producciones)
        self._crear_listas(usuarios, producciones)
        self._crear_chats(usuarios)
        self._resumen(usuarios)

    def _solo_resenas(self):
        """Siembra solo calificaciones y reseñas sobre lo que ya existe.

        Modo no destructivo pensado para catálogos poblados por
        `seed_catalogo`: por encima del umbral de C-04c el seed completo se
        niega a resetear (y forzarlo tira horas de llamadas a TMDB). Acá se
        reutilizan el catálogo y las cuentas deterministas del seed
        (`@filmai.com`) para sumar actividad sin borrar una fila.
        """
        producciones = list(ProduccionAudiovisual.objects.all())
        if not producciones:
            raise CommandError(
                "No hay producciones en el catálogo: corré "
                "`python manage.py seed` para crear el set completo de datos "
                "de desarrollo."
            )
        usuarios = list(
            Usuario.objects.filter(
                estado=EstadoCuenta.ACTIVA,
                is_staff=False,
                correo__endswith="@filmai.com",
            )
        )
        if not usuarios:
            raise CommandError(
                "No hay usuarios de desarrollo (@filmai.com, activos, no "
                "staff): corré `python manage.py seed` para crearlos."
            )
        resenas_creadas = self._crear_calificaciones_y_resenas(
            usuarios,
            producciones,
            objetivo=CALIFICACIONES_POR_USUARIO_SOLO_RESENAS,
        )
        self._completar_resenas(usuarios, resenas_creadas)
        self.stdout.write(self.style.SUCCESS("Reseñas de desarrollo creadas."))
        self.stdout.write(f"  Calificaciones: {Calificacion.objects.count()}")
        self.stdout.write(f"  Reseñas:        {Resena.objects.count()}")
        self.stdout.write(
            f"  Reseñas inactivas (moderación): "
            f"{Resena.objects.filter(activa=False).count()}"
        )

    def _verificar_catalogo(self, borrar_catalogo):
        """Se niega a pisar un catálogo que costó horas, salvo pedido explícito.

        `CommandError` es la forma de abortar un comando: Django imprime el
        mensaje en rojo y sale con código 1, sin traceback. Va ANTES de
        `_limpiar()` y dentro del `atomic`, así que no queda nada a medias.
        """
        cantidad = ProduccionAudiovisual.objects.count()
        if cantidad > UMBRAL_CATALOGO_PROTEGIDO and not borrar_catalogo:
            raise CommandError(
                f"El catálogo tiene {cantidad} producciones (más de "
                f"{UMBRAL_CATALOGO_PROTEGIDO}): no lo creó este comando, y "
                "borrarlo tira horas de llamadas a TMDB además de las "
                "calificaciones, reseñas y listas que cuelgan de él. Si es lo "
                "que querés, corré `seed --borrar-catalogo`."
            )

    def _limpiar(self, conservar_reales=False):
        """Borra los datos de las apps de negocio, conservando al superusuario.

        Con `conservar_reales` el catálogo de TMDB queda: solo se borran las
        producciones sintéticas (póster que no es una ruta de TMDB).

        El borrado en cascada limpiaría el resto, pero se listan todos los
        modelos explícitamente para que el comando sea legible y no dependa
        del orden de las FK. Los usuarios `is_staff` se conservan (junto con
        sus EmailAddress): el README promete que el seed no elimina el
        superusuario que crea el entrypoint, y perder el acceso a /admin/ con
        un seed sería un autogol.
        """
        for modelo in (
            Mensaje,
            Resena,
            Calificacion,
            Tiene,
            Chat,
            Lista,
        ):
            modelo.objects.all().delete()
        if conservar_reales:
            ProduccionAudiovisual.objects.exclude(poster__startswith="/").delete()
        else:
            ProduccionAudiovisual.objects.all().delete()
        EmailAddress.objects.exclude(user__is_staff=True).delete()
        Usuario.objects.exclude(is_staff=True).delete()

    def _crear_usuarios(self):
        """Crea los usuarios de prueba con credenciales deterministas."""
        usuarios = []
        for i in range(1, CANTIDAD_USUARIOS + 1):
            # La factory fija `fecha_aceptacion_terminos` (cuenta con términos
            # aceptados, como exige el registro real).
            usuario = UsuarioFactory.create(
                nombre_usuario=f"usuario{i:03d}",
                correo=f"usuario{i:03d}@filmai.com",
                password=SEED_PASSWORD,
                idioma="es" if i % 2 else "en",
            )
            # allauth necesita un EmailAddress verificado para permitir el
            # login cuando ACCOUNT_EMAIL_VERIFICATION es "mandatory".
            EmailAddress.objects.create(
                user=usuario,
                email=usuario.correo,
                verified=True,
                primary=True,
            )
            usuarios.append(usuario)
        return usuarios

    def _crear_producciones(self):
        """Crea el catálogo repartido entre películas y series."""
        producciones = []
        mitad = CANTIDAD_PRODUCCIONES // 2
        for _ in range(mitad):
            producciones.append(
                ProduccionAudiovisualFactory.create(tipo=TipoProduccion.PELICULA)
            )
        for _ in range(CANTIDAD_PRODUCCIONES - mitad):
            producciones.append(
                ProduccionAudiovisualFactory.create(tipo=TipoProduccion.SERIE)
            )
        return producciones

    def _crear_calificaciones_y_resenas(self, usuarios, producciones, objetivo=None):
        """Cada usuario califica un subconjunto aleatorio del catálogo.

        Se pasan `usuario` y `produccion` explícitos para no crear instancias
        nuevas desde los SubFactory y respetar la unicidad
        (usuario, produccion).

        En `--solo-resenas`, `objetivo` fija el total por usuario. Se cuentan
        primero las calificaciones existentes y solo se crean las que faltan;
        al repetir el comando no cambian ni las notas ni las reseñas.

        Regla de moderación (AD-01'/CU-017): 1 de cada 7 reseñas nace con
        `activa=False` para que el Admin tenga ejemplos reales de filtro,
        desactivación y reactivación.
        """
        resenas_creadas = 0
        for usuario in usuarios:
            ya_calificadas = set(
                Calificacion.objects.filter(usuario=usuario).values_list(
                    "produccion_id", flat=True
                )
            )
            candidatas = [p for p in producciones if p.pk not in ya_calificadas]
            if not candidatas:
                continue
            cantidad = min(
                max(objetivo - len(ya_calificadas), 0)
                if objetivo is not None
                else random.randint(8, 15),
                len(candidatas),
            )
            if not cantidad:
                continue
            for produccion in random.sample(candidatas, cantidad):
                calificacion = CalificacionFactory.create(
                    usuario=usuario, produccion=produccion
                )
                # La factory no pasa por la API: la regla «calificada ⇒ en
                # Vistas» (30/09/2026) se aplica a mano, como en C-08.
                agregar_a_vistas(usuario, produccion)
                # ~60% de las calificaciones llevan reseña escrita.
                if random.random() < 0.6:
                    resena = ResenaFactory.create(calificacion=calificacion)
                    resenas_creadas += 1
                    if resenas_creadas % 7 == 0:
                        # `update_fields` limita el UPDATE SQL a esa columna.
                        resena.activa = False
                        resena.save(update_fields=["activa"])
        return resenas_creadas

    def _completar_resenas(self, usuarios, resenas_creadas):
        """Asegura texto para 9 de hasta 15 notas por cuenta de desarrollo.

        También cubre las calificaciones que ya existían antes de ejecutar
        `--solo-resenas`; no reemplaza textos ni estados de moderación previos.
        """
        for usuario in usuarios:
            calificaciones = list(Calificacion.objects.filter(usuario=usuario))
            con_texto = set(
                Resena.objects.filter(calificacion__usuario=usuario).values_list(
                    "calificacion_id", flat=True
                )
            )
            objetivo = ceil(
                min(len(calificaciones), CALIFICACIONES_POR_USUARIO_SOLO_RESENAS) * 0.6
            )
            faltantes = max(objetivo - len(con_texto), 0)
            sin_texto = [c for c in calificaciones if c.pk not in con_texto]
            for calificacion in random.sample(sin_texto, faltantes):
                resena = ResenaFactory.create(calificacion=calificacion)
                resenas_creadas += 1
                if resenas_creadas % 7 == 0:
                    resena.activa = False
                    resena.save(update_fields=["activa"])

    def _crear_listas(self, usuarios, producciones):
        """Crea las 3 listas predeterminadas y algunas personalizadas por usuario."""
        for usuario in usuarios:
            listas = {}
            # Las listas predeterminadas ya las crea la señal post_save de
            # `usuarios` al dar de alta el usuario; aquí solo se reutilizan.
            for clave in nombres_listas_predeterminadas():
                listas[clave] = usuario.listas.get(
                    clave=clave, tipo=TipoLista.PREDETERMINADA
                )

            for _ in range(random.randint(1, 2)):
                ListaFactory.create(usuario=usuario)

            # Puebla las predeterminadas a través de la tabla intermedia Tiene.
            self._poblar_lista(listas[ClaveLista.FAVORITOS], producciones, 4)
            self._poblar_lista(listas[ClaveLista.PENDIENTES], producciones, 5)
            self._poblar_lista(listas[ClaveLista.VISTAS], producciones, 3)

    @staticmethod
    def _poblar_lista(lista, producciones, cantidad):
        for produccion in random.sample(producciones, cantidad):
            Tiene.objects.get_or_create(lista=lista, produccion=produccion)

    def _crear_chats(self, usuarios):
        """Usa el chat por defecto (creado por la señal) y agrega mensajes."""
        for usuario in usuarios:
            chat, _ = Chat.objects.get_or_create(usuario=usuario, titulo="Chat")
            MensajeFactory.create(
                chat=chat,
                autor=TipoAutor.USUARIO,
                texto="¿Qué me recomendás para ver esta noche?",
            )
            MensajeFactory.create(
                chat=chat,
                autor=TipoAutor.CHATBOT,
                texto="¡Claro! Según tus géneros favoritos, te sugiero una película de ciencia ficción.",
            )
            MensajeFactory.create(
                chat=chat,
                autor=TipoAutor.USUARIO,
                texto="Dale, mostrame más opciones.",
            )
            MensajeFactory.create(
                chat=chat,
                autor=TipoAutor.CHATBOT,
                texto="Acá tenés tres opciones que encajan con lo que venís mirando.",
            )

    def _resumen(self, usuarios):
        self.stdout.write(self.style.SUCCESS("Seed completado."))
        self.stdout.write(f"  Usuarios:       {Usuario.objects.count()}")
        self.stdout.write(f"  Producciones:   {ProduccionAudiovisual.objects.count()}")
        self.stdout.write(f"  Calificaciones: {Calificacion.objects.count()}")
        self.stdout.write(f"  Reseñas:        {Resena.objects.count()}")
        self.stdout.write(f"  Listas:         {Lista.objects.count()}")
        self.stdout.write(f"  Chats:          {Chat.objects.count()}")
        self.stdout.write(f"  Mensajes:       {Mensaje.objects.count()}")
        self.stdout.write("")
        self.stdout.write(
            self.style.WARNING(
                f"Credenciales de prueba (contraseña común: {SEED_PASSWORD}):"
            )
        )
        for usuario in usuarios:
            self.stdout.write(f"  {usuario.correo}")
