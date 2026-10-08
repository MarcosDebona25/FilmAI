# SEMINARIO INTEGRADOR

## PLANTILLA 03: MODELOS DE DATOS Y DE DISEÑO

**TÍTULO DE LA IDEA/PROYECTO: FilmAI**

| Fecha de Presentación |
| :-------------------: |
|      12/12/2025       |

### Integrantes del equipo de trabajo

| Integrante             |
| :--------------------- |
| Debona, Marcos Joel    |
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

- **Chat - Mensaje:** La cardinalidad establecida indica que un chat puede existir con o sin mensajes (B-01: al crear la cuenta se genera automáticamente un chat por defecto con `contexto` inicial; implementado en `usuarios/signals.py`). Los mensajes se van persistiendo conforme el usuario y el chatbot intercambian respuestas. La relación se modela como composición porque un mensaje no puede existir sin un chat asociado sobre el cual fue enviado. (Actualizado 08/09/2026: el texto anterior describía persistencia del chat "al primer mensaje"; la implementación acordada crea el chat al registrar el usuario.)

- **Usuario - Calificación:** La cardinalidad establecida permite que un usuario no tenga calificaciones asociadas (por ejemplo, al crear la cuenta) o tenga múltiples calificaciones (cuenta con trayectoria en el sistema).

- **Usuario - Lista:** La cardinalidad se justifica porque no existen listas compartidas entre usuarios y porque por defecto cada usuario cuenta con las listas de Vistos, Pendientes y Favoritos, las cuales no pueden ser eliminadas. Además, cada usuario tiene la posibilidad de crear otras listas personalizadas.

- **Reseña - Calificación:** La cardinalidad establecida refleja que una calificación (numérica) opcionalmente puede tener una reseña (textual) asociada. Se modela como relación de composición dado que una reseña no puede existir sin su respectiva calificación.

- **Calificación - Producción Audiovisual:** La cardinalidad se debe a que una producción puede tener múltiples calificaciones (incluyendo cero) y, consecuentemente, múltiples reseñas. Por otro lado, cada calificación corresponde a una única producción audiovisual.

- **Lista - Producción Audiovisual:** La relación muchos a muchos se debe a que una película o serie puede estar en múltiples listas distintas simultáneamente. Del mismo modo, múltiples listas pueden contener una misma producción audiovisual.

- **Invariante «calificada ⇒ en Vistas» (30/09/2026):** toda calificación de un usuario tiene su producción en la lista predeterminada «Vistas» de ese mismo usuario (a través de la tabla `Tiene`). Calificar agrega el ítem en la misma transacción que la nota, y borrar la calificación lo quita; modificar la nota o borrar solo el texto no cambian «Vistas». La inversa no rige: una producción puede estar en «Vistas» sin estar calificada (CU-011). Las calificaciones creadas antes de la regla se reparan con la migración de datos `listas.0004_calificadas_en_vistas`.

**Observaciones:**

Se considera que hubiera sido conveniente para la especificación de los métodos haber realizado mockups (maquetas) con el objetivo de prever y evaluar de forma anticipada el ciclo de las relaciones y cómo estas pueden modificar los atributos internos de las entidades. Por cuestiones de tiempo no fue posible realizarlo, aunque está previsto para la entrega final. Además, esto hubiera permitido analizar al detalle los atributos de las entidades en sí y agregar o eliminar según cada caso (por ejemplo, en la clase Producción Audiovisual).

Se descartó la herencia entre Producción Audiovisual, Película y Serie porque no existe comportamiento diferenciado que justifique la creación de subclases. Además, los IDs de TMDB no garantizan unicidad entre películas y series, lo que volvería más complejo el manejo de claves y referencias. Debido a esto, se unificaron ambos tipos en una única entidad con un atributo "tipo" que permite un diseño más simple.

El desarrollo se fundamenta en una arquitectura MVC (Model-View-Controller) apoyada en un diseño por capas (Controller, Service, Repository, Entidades) para separar la lógica de negocio del origen de los datos. Las llamadas a datos se centralizan exclusivamente en la capa Repository, la cual gestionará 2 fuentes de información distintas:

- **Repositorio Externo (API TMDB):** Se utilizará para realizar consultas complejas de búsqueda, filtrado y obtención de detalles respecto al catálogo global de peliculas y series.
- **Repositorio Local (base de datos propia):** Se usará para la persistencia del dominio: Usuarios, Reseñas, Calificaciones, Chats (y Mensajes), Listas y el catálogo materializado `ProduccionAudiovisual` (corpus de búsqueda semántica).

**Catálogo materializado global y progresivo (08/09/2026):** las películas y series se materializan en la base de datos local en cuanto el catálogo las expone, se consulta su detalle o un usuario interactúa con ellas. La materialización NO depende de que una producción pertenezca a una lista o tenga calificación: `ProduccionAudiovisual` es un catálogo global compartido por todos los usuarios, no un catálogo personal. Este corpus materializado es el espacio de búsqueda de `buscar_semantico` (pgvector); los datos personales (calificaciones, listas, historial) se usan vía SQL para personalizar y reordenar resultados, nunca para acotar qué es buscable. El poblamiento combina: (1) seed inicial global (populares, tendencias, novedades y muestra diversa por género/año/tipo) para evitar cold start; (2) materialización de lo expuesto por discovery en vivo; (3) incorporación progresiva de la cola larga. No se sincroniza todo TMDB de entrada.

**Sincronización con TMDB:** La actualización del catálogo se realiza mediante tareas Celery (beat diario a las 3 AM, ejecutadas por workers) en horario de baja actividad. Este proceso sincroniza los metadatos completos (título, póster, sinopsis, reparto, directores, géneros, calificación promedio, duración, temporadas y episodios) de las producciones populares, en tendencia y novedades desde TMDB hacia la tabla ProduccionAudiovisual, y encola la generación de embeddings de las producciones nuevas o modificadas. La sincronización respeta los límites de uso de la API de TMDB y utiliza mecanismos de caché para evitar solicitudes duplicadas (CU-021). Es un mecanismo de mantenimiento/seed, no un prerrequisito del discovery, que se sirve en vivo desde TMDB con caché Redis (decisión 25/08/2026).

**Chats múltiples:** El modelo de clases contempla la posibilidad de chats múltiples por usuario (1..*), pero en la versión inicial (MVP) solo se implementa un chat por usuario, garantizado por una restricción de unicidad sobre `Chat.usuario`. La funcionalidad de chats múltiples queda documentada como mejora futura y requerirá reemplazar esa restricción mediante una migración.

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
- `avatar_id` (SMALLINT positivo, NOT NULL, DEFAULT 1): identificador de un avatar predefinido elegido por el usuario. La cantidad de opciones puede crecer; no existe un límite funcional de 20 avatares. El valor por defecto es 1. El usuario no sube fotos propias: las imágenes son recursos estáticos de la aplicación.

El catálogo de `avatar_id` se genera desde las imágenes individuales de
`frontend/public/avatars/recortados/` y conserva los IDs existentes al añadir
nuevos archivos. Un archivo retirado deja su ID inactivo para que nunca se
reutilice con otra imagen. Hoy hay 26 imágenes seleccionables. El mosaico PNG de la carpeta
superior es una lámina de origen, no una opción del selector. El catálogo generado
se usa para validar la API y exponer las opciones al frontend.

- `tema` (VARCHAR(10), NOT NULL, DEFAULT 'oscuro'): Preferencia de tema de la interfaz. Valores posibles: 'oscuro', 'claro'.
- `perfilPublico` (BOOLEAN, NOT NULL, DEFAULT TRUE): Indica si las reseñas y listas del usuario son visibles para otros usuarios.
- `notifRecomendaciones` (BOOLEAN, NOT NULL, DEFAULT TRUE): Indica si el usuario desea recibir notificaciones por correo electrónico sobre recomendaciones semanales.
- `notifReseñas` (BOOLEAN, NOT NULL, DEFAULT TRUE): Indica si el usuario desea recibir notificaciones por correo electrónico cuando alguien reseña contenido en sus listas.
- `notifNovedades` (BOOLEAN, NOT NULL, DEFAULT TRUE): Indica si el usuario desea recibir notificaciones por correo electrónico sobre novedades de FilmAI.

Los nombres y apellidos compuestos conservan un espacio entre palabras; antes de
persistir se eliminan espacios iniciales, finales y repetidos. No se separan los
nombres compuestos en columnas nuevas.

**Campo en Usuario para OAuth:**

- `googleId` (VARCHAR(100), UNIQUE, NULLABLE): Identificador estable `sub` de la cuenta Google, sincronizado con `SocialAccount.uid`; no se utiliza el correo como identificador social. Al crear la cuenta por Google, `password` contiene una contraseña **inutilizable** creada con `set_unusable_password()`, no `NULL`. La cuenta activa puede establecer una contraseña local mediante el enlace temporal de recuperación por correo. Se actualiza el mismo `Usuario`, sin eliminar ni reemplazar su vínculo Google; después admite login Google y local (correo o nombre de usuario y contraseña). El cambio invalida los JWT anteriores y requiere nuevo login.

**Baja de Usuario (CU-007, 24/09/2026):** se modifica únicamente `estado` a `baja`
y se revocan las sesiones. La fila del usuario y todas sus relaciones se conservan,
incluidos sus datos de perfil, preferencias y vínculo social. No se ejecutan
borrados en cascada al dar de baja una cuenta.

**Cambio en Usuario:**

- `contraseña` cambia de VARCHAR(50) a VARCHAR(128) para alojar el hash de bcrypt (60+ caracteres), en concordancia con el RNF #2.

> **Consistencia de autenticación:** `is_active` NO es columna de BD; es una
> propiedad derivada de `estado` (`is_active` es `True` solo si
> `estado == activa`). El campo `googleId` se mantiene y se sincroniza con el
> `uid` de la cuenta social de allauth (`SocialAccount.uid`). Así el modelo de
> datos queda en concordia total con la autenticación (registro tradicional +
> Google OAuth vía dj-rest-auth/allauth).

**Cambio en Mensaje:**

- `texto` cambia de VARCHAR(250) a TEXT para no truncar respuestas del chatbot (una respuesta del LLM puede superar 250 caracteres).

**Cambio en Reseña:**

- `texto` cambia de VARCHAR(250) a VARCHAR(1000) para permitir reseñas de hasta 1000 caracteres, en concordancia con los lineamientos de UI.
- `sinopsis` en ProduccionAudiovisual cambia de VARCHAR(250) a VARCHAR(2000) para almacenar sinopsis completas sincronizadas desde TMDB.

**Cambios para retrieval semántico del chatbot (decisión 18/08/2026, ver `docs/decisiones.md`):**

- `keywords` (VARCHAR[]) en ProduccionAudiovisual: keywords temáticos de TMDB sincronizados en C-04 (`/movie/{id}/keywords`, `/tv/{id}/keywords`). Se usan como parte del texto a embebear para la búsqueda semántica.
- `ProduccionEmbedding` (nueva, fase posterior del Módulo 5): relación **1:1** con ProduccionAudiovisual (`produccion_id` con restricción UNIQUE, no una FK común; nunca dos filas de embedding por producción) + columna vectorial `vector(1024)` (extensión pgvector) + índice HNSW `vector_cosine_ops`. Almacena el embedding del texto canónico `Title + Genres + Directors + Cast + Keywords + Synopsis` (normalizado: espacios, vacíos y orden de arrays). Los campos cuantitativos (calificación promedio, año, duración, tipo, estatus) no se embedbean: se filtran por SQL sobre los resultados. No se aplica unicidad al vector (producciones distintas pueden tener vectores iguales o muy similares).
- **Campos de control e idempotencia (08/09/2026):** `source_hash` (SHA-256 del texto canónico), `model_version` (versión/proveedor del modelo de embeddings) y `estado` (`pending` | `processing` | `ready` | `failed`). Antes de invocar al proveedor se compara hash y versión: si no cambiaron y el estado es `ready`, no se recomputa. Si cambia el contenido o el modelo, la regeneración es legítima.
- **Generación asíncrona (08/09/2026, reemplaza la decisión del 25/08/2026 de embeddings síncronos):** la materialización persiste la producción y crea el registro con estado `pending`; una tarea Celery genera el vector sin bloquear catálogo ni detalle, con reintentos/backoff, backfill para `failed` y claim/lease idempotente (Celery puede duplicar tareas; la persistencia es condicional al claim vigente). La búsqueda semántica solo considera embeddings `ready`; las producciones pendientes o fallidas siguen visibles y se resuelven on-demand vía TMDB.

### Idioma de aplicación (OT-20, 08/10/2026)

`Usuario.idioma` es un VARCHAR(2) nullable con opciones `en` y `es`. La
migración no rellena las cuentas anteriores. Una operación usa el idioma
guardado, luego `Accept-Language` con pesos y regiones, y por último `en`.
Esta resolución es explícita y no modifica el idioma global de Django.
La exposición en preferencias y el guardado en registros se completan en
las entregas siguientes de OT-20.
