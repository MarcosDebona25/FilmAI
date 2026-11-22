"""
Comando de desarrollo: `python manage.py seed_masivo`.

Pobla la base con cuentas ficticias y actividad a gran escala (por defecto 500
cuentas, ~38 calificaciones por cuenta, 80 % con reseña) sobre el catálogo que
ya haya (`seed_catalogo`). Las reseñas salen del corpus versionado
`backend/seed_data/resenas.jsonl.gz`; sin entrada para un título usa las
plantillas de `seed_real`. La lógica está en `usuarios/seed_masivo.py`.

Uso:
    python manage.py seed_masivo                # agrega las cuentas que falten
    python manage.py seed_masivo --reiniciar    # DESTRUCTIVO: borra todo lo no staff
    python manage.py seed_masivo --usuarios 50 --semilla 7

Sin `--reiniciar` no borra nada y es idempotente por correo: solo crea las
cuentas que faltan. No toca el comando `seed`.
"""

from django.core.management.base import BaseCommand

from usuarios import seed_masivo
from usuarios.management.commands.seed import SEED_PASSWORD


class Command(BaseCommand):
    help = "Siembra cientos de cuentas con calificaciones, reseñas, listas y chats."

    def add_arguments(self, parser):
        parser.add_argument("--usuarios", type=int, default=500)
        parser.add_argument("--semilla", type=int, default=42)
        parser.add_argument(
            "--reiniciar",
            action="store_true",
            help=(
                "DESTRUCTIVO: borra todo usuario no staff con sus correos, "
                "cuentas sociales, calificaciones, reseñas, listas y chats. "
                "Conserva staff y catálogo."
            ),
        )
        parser.add_argument("--calificaciones-medias", type=int, default=38)
        parser.add_argument("--porcentaje-resenas", type=int, default=80)

    def handle(self, *args, **opciones):
        resumen = seed_masivo.sembrar(
            self.stdout,
            usuarios=opciones["usuarios"],
            semilla=opciones["semilla"],
            reiniciar_todo=opciones["reiniciar"],
            calificaciones_medias=opciones["calificaciones_medias"],
            porcentaje_resenas=opciones["porcentaje_resenas"],
        )
        self.stdout.write(self.style.SUCCESS("Seed masivo completado."))
        for etiqueta, clave in (
            ("Cuentas creadas", "usuarios"),
            ("Calificaciones", "calificaciones"),
            ("Reseñas", "resenas"),
            ("  inactivas", "resenas_inactivas"),
            ("Listas", "listas"),
            ("Ítems de lista", "items"),
            ("Chats", "chats"),
            ("Mensajes", "mensajes"),
        ):
            self.stdout.write(f"  {etiqueta}: {resumen[clave]}")
        self.stdout.write(
            self.style.WARNING(
                f"Credenciales: usuario001..003@filmai.com y "
                f"masivo0001..@filmai.com, contraseña {SEED_PASSWORD}"
            )
        )
