"""Repara listas predeterminadas y chat faltantes de usuarios existentes."""

from django.core.management.base import BaseCommand
from django.db import transaction

from usuarios.models import Usuario
from usuarios.provisioning import (
    LISTAS_PREDETERMINADAS,
    provisionar_recursos_por_defecto,
)


class Command(BaseCommand):
    help = "Asegura las listas predeterminadas y el chat único del MVP."

    def add_arguments(self, parser):
        parser.add_argument("--usuario-id", type=int)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        usuarios = Usuario.objects.order_by("pk")
        if usuario_id := options["usuario_id"]:
            usuarios = usuarios.filter(pk=usuario_id)

        if not usuarios.exists():
            self.stdout.write(self.style.WARNING("No se encontraron usuarios."))
            return

        if options["dry_run"]:
            for usuario in usuarios:
                listas = usuario.listas.filter(
                    nombre__in=LISTAS_PREDETERMINADAS
                ).count()
                self.stdout.write(
                    f"{usuario.pk}: listas {listas}/3, chats {usuario.chats.count()}/1"
                )
            return

        listas_creadas = chats_creados = 0
        for usuario_id in usuarios.values_list("pk", flat=True):
            with transaction.atomic():
                usuario = Usuario.objects.select_for_update().get(pk=usuario_id)
                listas, chat = provisionar_recursos_por_defecto(usuario)
                listas_creadas += listas
                chats_creados += chat

        self.stdout.write(
            self.style.SUCCESS(
                f"Reparación finalizada: {listas_creadas} listas y "
                f"{chats_creados} chats creados."
            )
        )
