# Decisiones y Cambios — FilmIA

Registro de decisiones de diseño y cambios relevantes del proyecto.
Formato: fecha (DD/MM/AAAA), título y descripción (qué, por qué, archivos afectados).

---

## 13/08/2026 — Unificación de Persona/Usuario/Administrador en un único `Usuario`

- **Descripción**: Se eliminaron las entidades `Persona` y `Administrador`.
  El modelo quedó con una única entidad `Usuario` que es el `AUTH_USER_MODEL`
  de Django, heredando de `AbstractBaseUser` + `PermissionsMixin`. Sus campos
  de identidad (`nombreUsuario`, `correo`, `contraseña`, `googleId`) se absorben
  en `Usuario`.
- **Motivo**: La gestión de administradores se realiza a través del Django Admin
  nativo (Módulo 6), que usa flags `is_staff`/`is_superuser` y no una entidad
  separada. La herencia multi-tabla era especulativa (una sola subclase) y
  chocaba con el `AUTH_USER_MODEL`.
- **Archivos**: `backend/usuarios/models.py`, `backend/filmia/settings.py`,
  `backend/entrypoint.sh`.

## 13/08/2026 — `estado` como fuente única de verdad del ciclo de vida

- **Descripción**: `is_active` dejó de ser un campo de BD; ahora es una propiedad
  derivada de `estado` (`is_active` es `True` solo si `estado == Activa`).
- **Motivo**: evitar una doble fuente de verdad; `estado` representa el ciclo
  completo pendiente → activa → baja (CU-001, CU-002, CU-007).
- **Archivos**: `backend/usuarios/models.py`.

## 13/08/2026 — `contraseña` VARCHAR(50) → VARCHAR(128)

- **Descripción**: el hash de bcrypt mide 60+ caracteres; el campo se amplió a
  128 caracteres (coherente con RNF #2).
- **Archivos**: `backend/usuarios/models.py` (campo `password` heredado de
  `AbstractBaseUser`), `docs/03_DiagramaClases_DiagramaTablas.json`,
  `docs/03_Modelos de Datos y de Diseño.md`.

## 13/08/2026 — `Mensaje.texto` VARCHAR(250) → TextField

- **Descripción**: una respuesta del LLM puede superar 250 caracteres; se usa
  `TextField` para no truncar el contenido.
- **Motivo**: el límite VARCHAR(250) del diagrama de tablas no era adecuado
  para respuestas conversacionales del chatbot.
- **Archivos**: `backend/chatbot/models.py`.

## 13/08/2026 — Unicidades añadidas (integridad a nivel BD)

- **Descripción**: se añadieron restricciones de unicidad compuestas exigidas
  por los casos de uso, aunque no estuvieran explícitas en el diagrama:
  - `(idTMDB, tipo)` en `ProduccionAudiovisual` — los IDs de TMDB no son únicos
    entre películas y series.
  - `(usuario, produccion)` en `Calificacion` — una calificación por usuario y producción.
  - `(usuario, nombre)` en `Lista` — nombre de lista único por usuario.
  - `(lista, produccion)` en `Tiene` — PK compuesta del diagrama (no duplicar ítem).
- **Motivo**: integridad referencial a nivel de base de datos (última línea de defensa).
- **Archivos**: `backend/catalogo/models.py`, `backend/listas/models.py`.

## 13/08/2026 — Nombres camelCase → snake_case

- **Descripción**: los nombres de atributos del diagrama (camelCase, ej.
  `nombreUsuario`, `fechaNacimiento`) se normalizaron a snake_case en el código
  (`nombre_usuario`, `fecha_nacimiento`) por convención de Django/Python.
- **Archivos**: todos los `models.py`.

## 13/08/2026 — `Reseña` → `Calificacion` modelada como OneToOne

- **Descripción**: la composición "una calificación tiene 0..1 reseña" se modeló
  con `OneToOneField` (no FK simple), según el diagrama de clases.
- **Archivos**: `backend/catalogo/models.py`.
