"""
Comando de desarrollo: `python manage.py seed`.

Pobla la base de datos con datos de prueba consistentes para desarrollar la UI
(F-05 del plan de desarrollo). Es **destructivo e idempotente**: borra los datos
de las apps de negocio y los recrea desde cero en cada ejecución.

Uso:
    python manage.py seed
"""

import random

from django.core.management.base import BaseCommand
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
from listas.models import Lista, Tiene, TipoLista
from usuarios.factories import UsuarioFactory
from usuarios.models import Usuario

# Contraseña común para todos los usuarios de prueba (útil para login manual).
SEED_PASSWORD = "Password123!"

# Listas predeterminadas que se crean para cada usuario (CU-009).
LISTAS_PREDETERMINADAS = ["Favoritos", "Pendientes", "Vistas"]

CANTIDAD_USUARIOS = 3
CANTIDAD_PRODUCCIONES = 50


class Command(BaseCommand):
    help = (
        "Pobla la BD con datos de desarrollo (usuarios, producciones, listas, "
        "calificaciones, reseñas y chats). Destructivo e idempotente."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        self._limpiar()
        usuarios = self._crear_usuarios()
        producciones = self._crear_producciones()
        self._crear_calificaciones_y_resenas(usuarios, producciones)
        self._crear_listas(usuarios, producciones)
        self._crear_chats(usuarios)
        self._resumen(usuarios)

    def _limpiar(self):
        """Borra los datos de las apps de negocio (orden de hijos a padres).

        El borrado en cascada limpiaría el resto, pero se listan todos los
        modelos explícitamente para que el comando sea legible y no dependa
        del orden de las FK.
        """
        for modelo in (
            Mensaje,
            Resena,
            Calificacion,
            Tiene,
            Chat,
            Lista,
            ProduccionAudiovisual,
            Usuario,
        ):
            modelo.objects.all().delete()

    def _crear_usuarios(self):
        """Crea los usuarios de prueba con credenciales deterministas."""
        usuarios = []
        for i in range(1, CANTIDAD_USUARIOS + 1):
            usuario = UsuarioFactory.create(
                nombre_usuario=f"usuario{i:03d}",
                correo=f"usuario{i:03d}@filmai.com",
                password=SEED_PASSWORD,
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

    def _crear_calificaciones_y_resenas(self, usuarios, producciones):
        """Cada usuario califica un subconjunto aleatorio del catálogo.

        Se pasan `usuario` y `produccion` explícitos para no crear instancias
        nuevas desde los SubFactory y respetar la unicidad
        (usuario, produccion).
        """
        for usuario in usuarios:
            producciones_usuario = random.sample(producciones, random.randint(8, 15))
            for produccion in producciones_usuario:
                calificacion = CalificacionFactory.create(
                    usuario=usuario, produccion=produccion
                )
                # ~60% de las calificaciones llevan reseña escrita.
                if random.random() < 0.6:
                    ResenaFactory.create(calificacion=calificacion)

    def _crear_listas(self, usuarios, producciones):
        """Crea las 3 listas predeterminadas y algunas personalizadas por usuario."""
        for usuario in usuarios:
            listas = {}
            # Las listas predeterminadas ya las crea la señal post_save de
            # `usuarios` al dar de alta el usuario; aquí solo se reutilizan.
            for nombre in LISTAS_PREDETERMINADAS:
                lista, _ = Lista.objects.get_or_create(
                    usuario=usuario,
                    nombre=nombre,
                    defaults={"tipo": TipoLista.PREDETERMINADA},
                )
                listas[nombre] = lista

            for _ in range(random.randint(1, 2)):
                ListaFactory.create(usuario=usuario)

            # Puebla las predeterminadas a través de la tabla intermedia Tiene.
            self._poblar_lista(listas["Favoritos"], producciones, 4)
            self._poblar_lista(listas["Pendientes"], producciones, 5)
            self._poblar_lista(listas["Vistas"], producciones, 3)

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
