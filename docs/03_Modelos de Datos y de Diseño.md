# SEMINARIO INTEGRADOR

## PLANTILLA 03: MODELOS DE DATOS Y DE DISEÑO

**TÍTULO DE LA IDEA/PROYECTO: FilmIA**

| Fecha de Presentación |
| :---: |
| 12/12/2025 |

### Integrantes del equipo de trabajo

| Integrante |
| :---- |
| Debona, Marcos Joel |
| Gaitan, Gonzalo Andrés |

### 1. Listado de modelos generados

- **MODELO 1:** Diagrama de Clases (estructura)
- **MODELO 2:** Diagrama de Tablas (datos)

---

### 2. Modelo 1

#### 2.1 Modelo 1: Gráfico

> **Nota:** El Diagrama de Clases debe regenerarse desde el archivo `03_DiagramaClases_DiagramaTablas.json` (página "Diagrama de Clases") para reflejar los cambios acordados.

#### 2.2 Modelo 1: Descripción y justificación de elementos más importantes

**Relaciones:**

- **Usuario (entidad unificada):** Las entidades Persona, Usuario y Administrador se unificaron en una única entidad `Usuario`, que es el modelo de usuario de Django (`AUTH_USER_MODEL`). El rol administrador se gestiona a través del Django Admin nativo (flags `is_staff`/`is_superuser`) y no mediante una entidad separada. Ver `docs/decisiones.md`.

- **Usuario - Chat:** La cardinalidad se justifica en que un usuario pueda realizar consultas en diversos chats, permitiendo separar temas de conversación. Esta funcionalidad está sujeta a viabilidad y análisis del alcance del proyecto.

- **Chat - Mensaje:** La cardinalidad establecida indica que para que un chat efectivamente exista, primero debe enviarse un mensaje (consulta). A partir de ese momento comenzará a persistir la relación entre ambas entidades. En primera instancia, el usuario podrá acceder a un chat vacío (solo vista), pero esto no implica que el chat exista lógicamente (en la BD), sino que éste se registrará una vez enviada la primera consulta, guardándose también el mensaje. La relación se modela como composición porque un mensaje no puede existir sin un chat asociado sobre el cual fue enviado.

- **Usuario - Calificación:** La cardinalidad establecida permite que un usuario no tenga calificaciones asociadas (por ejemplo, al crear la cuenta) o tenga múltiples calificaciones (cuenta con trayectoria en el sistema).

- **Usuario - Lista:** La cardinalidad se justifica porque no existen listas compartidas entre usuarios y porque por defecto cada usuario cuenta con las listas de Vistos, Pendientes y Favoritos, las cuales no pueden ser eliminadas. Además, cada usuario tiene la posibilidad de crear otras listas personalizadas.

- **Reseña - Calificación:** La cardinalidad establecida refleja que una calificación (numérica) opcionalmente puede tener una reseña (textual) asociada. Se modela como relación de composición dado que una reseña no puede existir sin su respectiva calificación.

- **Calificación - Producción Audiovisual:** La cardinalidad se debe a que una producción puede tener múltiples calificaciones (incluyendo cero) y, consecuentemente, múltiples reseñas. Por otro lado, cada calificación corresponde a una única producción audiovisual.

- **Lista - Producción Audiovisual:** La relación muchos a muchos se debe a que una película o serie puede estar en múltiples listas distintas simultáneamente. Del mismo modo, múltiples listas pueden contener una misma producción audiovisual.

**Observaciones:**

Se considera que hubiera sido conveniente para la especificación de los métodos haber realizado mockups (maquetas) con el objetivo de prever y evaluar de forma anticipada el ciclo de las relaciones y cómo estas pueden modificar los atributos internos de las entidades. Por cuestiones de tiempo no fue posible realizarlo, aunque está previsto para la entrega final. Además, esto hubiera permitido analizar al detalle los atributos de las entidades en sí y agregar o eliminar según cada caso (por ejemplo, en la clase Producción Audiovisual).

Se descartó la herencia entre Producción Audiovisual, Película y Serie porque no existe comportamiento diferenciado que justifique la creación de subclases. Además, los IDs de TMDB no garantizan unicidad entre películas y series, lo que volvería más complejo el manejo de claves y referencias. Debido a esto, se unificaron ambos tipos en una única entidad con un atributo "tipo" que permite un diseño más simple.

El desarrollo se fundamenta en una arquitectura MVC (Model-View-Controller) apoyada en un diseño por capas (Controller, Service, Repository, Entidades) para separar la lógica de negocio del origen de los datos. Las llamadas a datos se centralizan exclusivamente en la capa Repository, la cual gestionará 2 fuentes de información distintas:

- **Repositorio Externo (API TMDB):** Se utilizará para realizar consultas complejas de búsqueda, filtrado y obtención de detalles respecto al catálogo global de peliculas y series.
- **Repositorio Local (base de datos propia):** Se usará para la persistencia del dominio: Usuarios, Administradores, Reseñas, Calificaciones, Chats (y Mensajes) y Listas.

Las películas y series se guardarán en la base de datos local únicamente como referencias (datos esenciales como ID de TMDB, título, póster) cuando un usuario interactúe con ellas, por ejemplo, al agregarlas a una lista o calificarlas. Esto evita la duplicidad de la información detallada que ya está disponible en la API de TMDB.

**Sincronización con TMDB:** La actualización del catálogo se realiza mediante un cron job diario programado en horario de baja actividad. Este proceso sincroniza los metadatos completos (título, póster, sinopsis, reparto, directores, géneros, calificación promedio, duración, temporadas y episodios) de las producciones populares, en tendencia y novedades desde TMDB hacia la tabla ProduccionAudiovisual. La sincronización respeta los límites de uso de la API de TMDB y utiliza mecanismos de caché para evitar solicitudes duplicadas (CU-021).

**Chats múltiples:** El modelo de clases contempla la posibilidad de chats múltiples por usuario (1..*), pero en la versión inicial (MVP) solo se implementará un chat por usuario. La funcionalidad de chats múltiples queda documentada como mejora futura.

En la entidad Mensaje, el atributo autor permite distinguir si el mensaje proviene del usuario o del chatbot, sin necesidad de crear una segunda entidad para manejar los roles dentro del chat.

---

### 3. Modelo 2

#### 3.1 Modelo 2: Gráfico

> **Nota:** El Diagrama de Tablas debe regenerarse desde el archivo `03_DiagramaClases_DiagramaTablas.json` (página "Diagrama de Tablas") para reflejar los cambios acordados.

#### 3.2 Modelo 2: Descripción y justificación de elementos más importantes

**Relaciones:**

- **Lista - Produccion Audiovisual (tabla Tiene):** Como la relación entre estas dos tablas es N a N, se crea la tabla intermedia "Tiene". Los campos idLista e idProduccion funcionan como PK compuesta y también como FKs, lo que evita que una misma producción se repita dentro de una lista y mantiene la integridad referencial. Adicionalmente, la tabla Tiene incluye el campo `fechaAgregado` (TIMESTAMP) para registrar el momento en que un ítem fue añadido a una lista.

- **Usuario - Calificación:** En Calificación se incluye como FK el idUsuario. Esto modela una relación 1 a N donde un usuario puede hacer varias calificaciones, pero cada calificación pertenece a un único usuario. De esta forma, cualquier calificación siempre va a estar asociada a un usuario válido.

- **Usuario - Lista:** La tabla Lista tiene una FK idUsuario, lo que indica que cada lista le pertenece al usuario que la creó. Un usuario puede tener varias listas (tanto las predeterminadas como las personalizadas).

- **Usuario - Chat:** Chat también tiene una FK idUsuario, lo que muestra que cada chat es creado por un usuario en particular. Un usuario puede tener varios chats distintos.

- **Chat - Mensaje:** Mensaje contiene una FK idChat, de modo que todos los mensajes pertenecen a un chat específico. Un chat puede tener muchos mensajes, pero cada mensaje se guarda siempre dentro de un único chat.

- **Calificación - Reseña:** La relación se maneja como una composición: la Reseña depende de la Calificación. La FK idCalificacion en Reseña hace que una reseña no pueda existir por sí sola; siempre surge a partir de una calificación. La Calificación puede existir sin reseña, pero no al revés.

- **Calificación - Produccion Audiovisual:** Toda calificación debe estar asociada a una producción mediante la FK idProduccion. Esto permite que una producción tenga muchas calificaciones, pero cada calificación corresponde a una única producción.

- **Produccion Audiovisual (entidad base):** Esta tabla reúne todos los datos sincronizados desde TMDB (título, póster, géneros, reparto, duración, temporadas, etc.). Desde acá se relacionan tanto las calificaciones como los ítems que aparecen en las distintas listas.

**Observaciones:**

La herencia entre Persona, Usuario y Administrador fue eliminada: ahora existe una única tabla `Usuario` que concentra los campos de identidad (nombreUsuario, correo, contraseña, googleId) junto con los campos propios del usuario. El rol administrador se representa con el flag `is_staff` de Django y se gestiona a través del Django Admin nativo.

El campo "contexto" del Chat se guarda como JSONB (JSON Binary) porque la información almacenada puede variar considerablemente según el desarrollo de la conversación y no siempre sigue una estructura fija. De esta forma se pueden guardar cosas como un resumen del historial, parámetros que el chatbot viene usando o cualquier otro dato que necesite en el momento, sin crear tablas nuevas solo para eso. Además, PostgreSQL (la BD que tenemos pensado usar) permite buscar y actualizar partes del JSONB sin problemas, cuando con JSON hay ciertas limitantes, así que es una forma práctica y flexible de manejar estos datos sin complicar el modelo.

**Campos adicionales requeridos en Usuario:** Los siguientes campos deben agregarse a la tabla Usuario para dar soporte a las funcionalidades definidas en los lineamientos de UI y casos de uso:

- `fechaRegistro` (DATE, NOT NULL, DEFAULT NOW()): Fecha en que el usuario creó su cuenta. Se muestra en la sección de perfil como "Miembro desde [mes] [año]".
- `avatarId` (TINYINT, NOT NULL, DEFAULT 1): Identificador del avatar seleccionado por el usuario dentro de un conjunto de 20 avatares genéricos predefinidos. El valor por defecto es 1. No se almacenan archivos de imagen; los avatares son recursos estáticos del frontend.
- `tema` (VARCHAR(10), NOT NULL, DEFAULT 'oscuro'): Preferencia de tema de la interfaz. Valores posibles: 'oscuro', 'claro'.
- `perfilPublico` (BOOLEAN, NOT NULL, DEFAULT TRUE): Indica si las reseñas y listas del usuario son visibles para otros usuarios.
- `notifRecomendaciones` (BOOLEAN, NOT NULL, DEFAULT TRUE): Indica si el usuario desea recibir notificaciones por correo electrónico sobre recomendaciones semanales.
- `notifReseñas` (BOOLEAN, NOT NULL, DEFAULT TRUE): Indica si el usuario desea recibir notificaciones por correo electrónico cuando alguien reseña contenido en sus listas.
- `notifNovedades` (BOOLEAN, NOT NULL, DEFAULT TRUE): Indica si el usuario desea recibir notificaciones por correo electrónico sobre novedades de FilmIA.

**Campo en Usuario para OAuth:**
- `googleId` (VARCHAR(100), UNIQUE, NULLABLE): Identificador único de la cuenta de Google asociada. Solo se completa para cuentas creadas mediante autenticación con Google OAuth. En estos casos, el campo `password` (contraseña) puede ser NULL.

**Cambio en Usuario:**
- `contraseña` cambia de VARCHAR(50) a VARCHAR(128) para alojar el hash de bcrypt (60+ caracteres), en concordancia con el RNF #2.

**Cambio en Mensaje:**
- `texto` cambia de VARCHAR(250) a TEXT para no truncar respuestas del chatbot (una respuesta del LLM puede superar 250 caracteres).

**Cambio en Reseña:**
- `texto` cambia de VARCHAR(250) a VARCHAR(1000) para permitir reseñas de hasta 1000 caracteres, en concordancia con los lineamientos de UI.
- `sinopsis` en ProduccionAudiovisual cambia de VARCHAR(250) a VARCHAR(2000) para almacenar sinopsis completas sincronizadas desde TMDB.

**Cambios para retrieval semántico del chatbot (decisión 18/08/2026, ver `docs/decisiones.md`):**
- `keywords` (VARCHAR[]) en ProduccionAudiovisual: keywords temáticos de TMDB sincronizados en C-04 (`/movie/{id}/keywords`, `/tv/{id}/keywords`). Se usan como parte del texto a embebear para la búsqueda semántica.
- `ProduccionEmbedding` (nueva, fase posterior del Módulo 5): FK a ProduccionAudiovisual + columna vectorial `vector(1024)` (extensión pgvector) + índice HNSW `vector_cosine_ops`. Almacena el embedding del texto `Title + Genres + Directors + Cast + Keywords + Synopsis`. Los campos cuantitativos (calificación promedio, año, duración, tipo, estatus) no se embedbean: se filtran por SQL sobre los resultados.
