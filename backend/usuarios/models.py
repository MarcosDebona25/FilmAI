"""
Modelos de la app `usuarios`.

FilmAI usa un único modelo de usuario (`Usuario`) como `AUTH_USER_MODEL`,
en lugar de heredar de `auth.User`. La jerarquía original del diagrama de
clases (Persona → Usuario/Administrador) se unificó en una sola entidad:

    Persona ──┬── Usuario          (antes: 3 tablas, herencia multi-tabla)
              └── Administrador
    --------------------------------------
    Usuario (AbstractBaseUser + PermissionsMixin)   (ahora: 1 sola tabla)

Motivo: la gestión de administradores se realiza a través del Django Admin
nativo (Módulo 6, AD-01'), que usa flags del propio usuario (`is_staff`,
`is_superuser`) y no una entidad separada. El "rol administrador" es un
atributo del usuario, no una clase distinta.

Nota sobre el campo `password`: se hereda de `AbstractBaseUser` (VARCHAR(128),
compatible con el hash de bcrypt, RNF #2). En el diagrama de datos corresponde
al campo `contraseña`.
"""

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models


class EstadoCuenta(models.TextChoices):
    """Estados del ciclo de vida de una cuenta de usuario (CU-001, CU-002, CU-007)."""

    PENDIENTE = "pendiente", "Pendiente de confirmación"
    ACTIVA = "activa", "Activa"
    BAJA = "baja", "Baja"


class TipoGenero(models.TextChoices):
    """Género autodeclarado por el usuario en el registro (CU-001)."""

    MASCULINO = "masculino", "Masculino"
    FEMENINO = "femenino", "Femenino"
    NO_ESPECIFICA = "no_especifica", "No especifica"


class Tema(models.TextChoices):
    """Preferencia de tema de la interfaz (doc 03: 'oscuro' | 'claro')."""

    OSCURO = "oscuro", "Oscuro"
    CLARO = "claro", "Claro"


class UsuarioManager(BaseUserManager):
    """Manager que usa `correo` como identificador de autenticación.

    `create_user`/`create_superuser` normalizan el correo y aplican el hash de
    contraseña a través de `set_password`.
    """

    use_in_migrations = True

    def _create_user(self, correo, password, **extra_fields):
        if not correo:
            raise ValueError("El correo electrónico es obligatorio.")
        correo = self.normalize_email(correo)
        usuario = self.model(correo=correo, **extra_fields)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, correo, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(correo, password, **extra_fields)

    def create_superuser(self, correo, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("estado", EstadoCuenta.ACTIVA)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("El superusuario debe tener is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("El superusuario debe tener is_superuser=True.")

        return self._create_user(correo, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Cliente de la plataforma y, según sus flags, administrador del panel.

    Concentra los campos de identidad que antes vivían en `Persona`
    (`nombre_usuario`, `correo`, `google_id`) junto con los campos propios
    del usuario y los flags técnicos de Django.
    """

    nombre_usuario = models.CharField(
        "nombre de usuario",
        max_length=25,
        unique=True,
        help_text="Alfanumérico, 5-25 caracteres, único (CU-001).",
    )
    correo = models.EmailField(
        "correo electrónico",
        max_length=100,
        unique=True,
        help_text="Formato usuario@dominio.com (CU-001).",
    )
    google_id = models.CharField(
        "id de Google",
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text="Solo para cuentas creadas con Google OAuth (doc 03).",
    )
    nombre = models.CharField("nombre", max_length=50)
    apellido = models.CharField("apellido", max_length=50)
    fecha_nacimiento = models.DateField("fecha de nacimiento")
    genero = models.CharField("género", max_length=25, choices=TipoGenero.choices)
    estado = models.CharField(
        "estado de cuenta",
        max_length=25,
        choices=EstadoCuenta.choices,
        default=EstadoCuenta.PENDIENTE,
    )
    fecha_registro = models.DateField("fecha de registro", auto_now_add=True)
    avatar_id = models.PositiveSmallIntegerField(
        "id de avatar",
        default=1,
        help_text="Identificador dentro del conjunto de 20 avatares (doc 03).",
    )
    tema = models.CharField(
        "tema",
        max_length=10,
        choices=Tema.choices,
        default=Tema.OSCURO,
    )
    perfil_publico = models.BooleanField("perfil público", default=True)
    notif_recomendaciones = models.BooleanField("notif. recomendaciones", default=True)
    notif_resenas = models.BooleanField("notif. reseñas", default=True)
    notif_novedades = models.BooleanField("notif. novedades", default=True)

    # --- Flags técnicos de Django ---
    # `is_staff` define el rol administrador (acceso al Django Admin). No forma
    # parte del ciclo de vida de la cuenta, por eso no vive en `estado`.
    is_staff = models.BooleanField(
        "es staff",
        default=False,
        help_text="Permite el acceso al Django Admin (rol administrador).",
    )

    @property
    def is_active(self):
        """Logueable solo si la cuenta está en estado Activa.

        Se deriva de `estado` para no duplicar la fuente de verdad: Django
        consulta este atributo en el login (ModelBackend.user_can_authenticate).
        """
        return self.estado == EstadoCuenta.ACTIVA

    @is_active.setter
    def is_active(self, value):
        """Permite que Django/allauth activen la cuenta (`is_active = True`).

        Solo actúa sobre `True` (estado → ACTIVA). `False` es un no-op para no
        degradar el estado: la "baja" es un flujo de negocio explícito, no un
        toggle. Ver docs/decisiones.md (22/08/2026, Opción A1).
        """
        if value:
            self.estado = EstadoCuenta.ACTIVA

    objects = UsuarioManager()

    USERNAME_FIELD = "correo"
    REQUIRED_FIELDS = [
        "nombre_usuario",
        "nombre",
        "apellido",
        "fecha_nacimiento",
        "genero",
    ]

    class Meta:
        db_table = "usuario"
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["id"]

    def __str__(self):
        return f"{self.nombre} {self.apellido} (@{self.nombre_usuario})"

    def get_full_name(self):
        return f"{self.nombre} {self.apellido}".strip()

    def get_short_name(self):
        return self.nombre
