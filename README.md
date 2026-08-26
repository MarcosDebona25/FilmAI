# FilmAI

**Plataforma Web de Resenas Cinematograficas con Recomendaciones Inteligentes**

Proyecto correspondiente a la materia **Seminario Integrador** de la carrera **Analista Universitario en Sistemas de Informacion** (UTN-FRSF).

---

## Problematica

La sobreabundancia de contenido audiovisual disponible en plataformas de streaming genera una paradoja de eleccion: cuanto mas material existe, mas tiempo invierten los usuarios en decidir que ver. Las recomendaciones genericas, basadas unicamente en popularidad o en un historial de visualizacion superficial, rara vez capturan los matices de las preferencias individuales.

FilmAI aborda esta problematica combinando un catalogo actualizado de peliculas y series con un motor de recomendacion personalizado. El sistema analiza el historial de visualizacion, las calificaciones y las reseñas de cada usuario para generar sugerencias contextuales a traves de un chatbot basado en inteligencia artificial.

---

## Objetivos

### Objetivo general

Desarrollar una aplicacion web integral que permita gestionar, calificar y recibir recomendaciones personalizadas de peliculas y series, integrando un chatbot basado en IA para mejorar la experiencia del usuario.

### Objetivos especificos

- Implementar un sistema completo de registro, autenticacion (incluyendo OAuth con Google) y gestion de perfiles de usuario.
- Integrar el sistema con The Movie Database (TMDB) para mantener un catalogo actualizado con informacion detallada de cada produccion.
- Desarrollar un sistema de calificacion por estrellas (escala 1 a 10), resenas textuales y listas personalizadas (favoritos, pendientes, vistas y listas definidas por el usuario).
- Implementar un chatbot basado en modelos de lenguaje (LLM) que analice preferencias, historial y perfil del usuario para generar recomendaciones contextuales.

---

## Funcionalidades principales

### Catalogo y descubrimiento

- Catalogo unificado de peliculas y series sincronizado con TMDB.
- Pagina de inicio con filas de descubrimiento: recomendaciones personalizadas, tendencias semanales y novedades.
- Busqueda por texto con filtros por tipo (pelicula/serie), genero, ano y calificacion minima.
- Ficha de detalle con sinopsis, reparto, generos y calificacion promedio de la comunidad.

### Resenas y calificaciones

- Calificacion en escala numerica de 1 a 10 con widget interactivo de estrellas.
- Resenas textuales opcionales (hasta 1000 caracteres) asociadas a cada calificacion.
- Edicion y eliminacion de resenas propias desde la ficha de detalle o desde la seccion "Mis resenas".

### Listas personalizadas

- Tres listas predeterminadas por usuario: Favoritos, Pendientes y Vistas.
- Listas personalizadas con nombres definidos por el usuario, reordenables y gestionables mediante modales dedicados.
- Acciones directas desde la ficha de detalle: agregar o quitar una produccion de cualquier lista.

### Chatbot inteligente

- Accesible desde un boton flotante (FAB) en todas las pantallas de la aplicacion.
- Procesa consultas en lenguaje natural y genera recomendaciones basadas en el historial, calificaciones y preferencias del usuario.
- Los datos sensibles (email, nombre, apellido) se anonimizan antes de ser enviados al proveedor del LLM.
- Soporte para cancelacion de solicitudes en curso.

### Perfil y preferencias

- Edicion inline del perfil: nombre, apellido, nombre de usuario, avatar y contrasena.
- Seleccion de avatar desde una galeria de 20 opciones predefinidas.
- Configuracion de tema (oscuro por defecto, con opcion clara), privacidad del perfil y preferencias de notificaciones.
- Baja de cuenta con eliminacion logica (soft delete).

---

## Arquitectura y tecnologias

### Stack tecnologico

| Capa                  | Tecnologia                                                                 |
| --------------------- | -------------------------------------------------------------------------- |
| **Backend**           | Python 3.12, Django 5.x, Django REST Framework                             |
| **Frontend**          | Next.js 15 (App Router), Tailwind CSS v4, Shadcn/ui                        |
| **Base de datos**     | PostgreSQL 16                                                              |
| **Cache y colas**     | Redis (cache de TMDB, broker de Celery)                                    |
| **Tareas asincronas** | Celery + Celery Beat (sincronizacion programada con TMDB)                  |
| **Infraestructura**   | Docker, docker-compose (4 servicios: backend, frontend, PostgreSQL, Redis) |
| **Autenticacion**     | JWT (access + refresh tokens, sesion de 8 horas), Google OAuth 2.0, bcrypt |

### APIs externas

| Proveedor                               | Proposito                                                            |
| --------------------------------------- | -------------------------------------------------------------------- |
| **TMDB API**                            | Catalogo de peliculas y series, busqueda, tendencias, metadatos      |
| **LLM API** (OpenAI / Anthropic / Groq) | Procesamiento de lenguaje natural para el chatbot de recomendaciones |

### Modelo de datos

El sistema implementa 9 tablas relacionales:

- **Persona** (abstracta): nucleo de autenticacion con credenciales y soporte para Google OAuth.
- **Usuario**: extiende Persona con datos demograficos, preferencias de tema y notificaciones.
- **Administrador**: extiende Persona con nivel de acceso y estado administrativo.
- **ProduccionAudiovisual**: entidad unificada para peliculas y series, diferenciadas por un atributo `tipo`. Sincronizada desde TMDB.
- **Calificacion**: valor numerico (1-10) emitido por un usuario sobre una produccion.
- **Resena**: texto opcional vinculado uno a uno con una calificacion.
- **Lista**: colecciones de producciones (predeterminadas o personalizadas) asociadas a un usuario.
- **Chat**: conversacion asociada a un usuario, con contexto persistente en formato JSONB.
- **Mensaje**: unidad de dialogo dentro de un chat, con indicacion de autor (usuario o chatbot).
- **Tiene**: tabla intermedia entre Lista y ProduccionAudiovisual con fecha de agregado.

---

## Ejecución del proyecto

### Arranque rápido (cada vez)

```bash
docker compose up --build   # primera vez, o tras cambios en los Dockerfiles
docker compose up           # levantamiento rápido sin rebuild
docker compose down         # detener (conserva la base de datos y Redis)
```

### URLs

| Servicio           | URL                                |
| ------------------ | ---------------------------------- |
| Frontend (Next.js) | http://localhost:3000              |
| Backend (Django)   | http://localhost:8000              |
| Admin de Django    | http://localhost:8000/admin/       |
| PostgreSQL         | `localhost:5432` (db `filmai_dev`) |
| Redis              | `localhost:6379`                   |

### Comandos útiles

```bash
docker compose ps               # estado de los 4 servicios
docker compose logs -f backend  # seguir los logs de Django
docker compose logs -f frontend # seguir los logs de Next.js
docker compose down -v          # detener y borrar BD + Redis (datos)
```

### Configuración inicial (solo la primera vez)

1. **Crear el `.env`** desde la plantilla y completar las variables obligatorias:

   ```bash
   cp .env.example .env
   ```

   - `SECRET_KEY`: generar con `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`.
   - `POSTGRES_PASSWORD` y `DJANGO_SUPERUSER_PASSWORD`: contraseñas de desarrollo.
   - Las claves externas (`TMDB_API_KEY`, `GOOGLE_CLIENT_ID`, `LLM_API_KEY`) pueden quedar vacías hasta que se implementen esos módulos.

### Credenciales de desarrollo

El backend crea automáticamente un superusuario al arrancar, usando las variables `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL` y `DJANGO_SUPERUSER_PASSWORD` del `.env`. Entrar a `/admin/` con esos datos y cambiar la contraseña tras el primer acceso.

---

## Accesibilidad

FilmAI se desarrolla siguiendo los principios **POUR** de las **WCAG 2.1** con nivel de conformidad **AA**:

- **Perceptible (Perceivable):** la informacion y los componentes de la interfaz se presentan de forma que los usuarios puedan percibirlos. Contraste minimo de 4.5:1 para texto normal y 3:1 para texto grande. Textos alternativos en imagenes informativas. Estructura jerarquica de encabezados sin saltos de nivel.
- **Operable (Operable):** los componentes de la interfaz y la navegacion se operan completamente mediante teclado. Indicador de foco visible en todos los elementos interactivos. Alternativas accesibles para drag and drop (botones "Mover arriba" / "Mover abajo"). Tecla Escape para cerrar modales.
- **Comprensible (Understandable):** los formularios incluyen etiquetas asociadas, mensajes de error descriptivos vinculados mediante `aria-describedby` y validacion inline. El contenido permanece legible con zoom del 200%.
- **Robusto (Robust):** se utilizan roles ARIA apropiados (`role="switch"`, `role="alert"`, `aria-live`) para garantizar compatibilidad con lectores de pantalla y tecnologias de asistencia.

Referencia de verificacion: [WebAIM WCAG 2 Checklist](https://webaim.org/standards/wcag/checklist).

La especificacion detallada de accesibilidad por componente se encuentra en [`docs/04_Lineamientos_UI.md` (Seccion 11)](docs/04_Lineamientos_UI.md). La implementacion esta planificada en la tarea Q-01 del [Plan de Desarrollo](docs/05_Plan_de_Desarrollo.md).

---

## Documentacion relacionada

| Documento                                                                                     | Contenido                                                 |
| --------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| [`01_Presentacion Idea-Proyecto`](docs/01_Presentaci%C3%B3n%20Idea-Proyecto.docx.md)          | Propuesta inicial, problematica y objetivos               |
| [`02_Especificacion de Requerimientos`](docs/02_Especificaci%C3%B3n%20de%20Requerimientos.md) | Requerimientos funcionales, no funcionales y casos de uso |
| [`03_Modelos de Datos y de Diseno`](docs/03_Modelos%20de%20Datos%20y%20de%20Dise%C3%B1o.md)   | Diagrama de clases y modelo relacional                    |
| [`04_Lineamientos_UI`](docs/04_Lineamientos_UI.md)                                            | Diseno de interfaces, componentes y accesibilidad         |
| [`05_Plan_de_Desarrollo`](docs/05_Plan_de_Desarrollo.md)                                      | Plan de trabajo, modulos y estimaciones                   |

---

## Equipo

| Integrante             |
| ---------------------- |
| Debona, Marcos Joel    |
| Gaitan, Gonzalo Andres |
