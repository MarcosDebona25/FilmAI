# Glosario de multiidioma

Referencia para la copia de los catálogos; las claves describen la función del
texto y se escriben en inglés/camelCase. Los valores de campos y enumeraciones
que viajan por API conservan sus identificadores actuales en español.

| Concepto             | Inglés            | Español                | Uso                                    |
| -------------------- | ----------------- | ---------------------- | -------------------------------------- |
| Cuenta               | Account           | Cuenta                 | Cuenta del usuario, distinta de perfil |
| Perfil               | Profile           | Perfil                 | Datos personales                       |
| Preferencias         | Settings          | Preferencias           | Configuración y selector de idioma     |
| Inicio de sesión     | Log in            | Iniciar sesión         | Acción de autenticarse                 |
| Registro             | Sign up           | Crear cuenta           | Alta de cuenta                         |
| Calificación         | Rating            | Calificación           | Nota entera de 1 a 10                  |
| Reseña               | Review            | Reseña                 | Texto asociado a una calificación      |
| Favoritos            | Favorites         | Favoritos              | Lista con `clave=favoritos`            |
| Pendientes           | Watchlist         | Pendientes             | Lista con `clave=pendientes`           |
| Vistas               | Watched           | Vistas                 | Lista con `clave=vistas`               |
| Género de producción | Genre             | Género                 | Filtro del catálogo                    |
| Género de persona    | Gender            | Género                 | Campo del perfil                       |
| Género no declarado  | Prefer not to say | No especificar         | Valor `no_especifica`                  |
| Tema oscuro          | Dark              | Oscuro                 | Valor `oscuro`                         |
| Tema claro           | Light             | Claro                  | Valor `claro`                          |
| Película             | Movie             | Película               | API `movie`, dominio `pelicula`        |
| Serie                | TV show           | Serie                  | API `tv`, dominio `serie`              |
| Confirmación         | Confirm account   | Confirmar cuenta       | Activación mediante enlace             |
| Restablecimiento     | Reset password    | Restablecer contraseña | Recuperación mediante enlace           |
| Reenvío de enlace    | Resend link       | Reenviar enlace        | Acción de las pantallas de correo      |

La tabla original de equivalencias sigue inmutable. Estas equivalencias sirven
para unificar conceptos; los textos completos se revisan en `claves.csv` y se
siembran desde allí. Genre y Gender usan claves distintas aunque coincidan en
español. Rating y Review nunca son intercambiables.

El español usa voseo: «elegí», «guardá», «podés», «volvé». Se eliminan tuteo y
trato de usted en la copia migrada, conservando el significado. La copia de
baja de cuenta permanece sin cambios por decisión del usuario.

No se traducen nombres de usuario, personas, películas ingresadas por el
usuario, nombres de listas personalizadas ni reseñas de la comunidad.
El catálogo TMDB suministra los títulos de producciones por idioma; sus nombres
no se incorporan como mensajes fijos de la interfaz.

Se excluyen las mesas de trabajo y documentación de diseño, datos de ejemplo y
textos del chatbot. Las frases con cantidades, nombres y enlaces se escriben
completas con argumentos ICU o texto enriquecido, sin fragmentos concatenables.
La copia nueva de errores y selector requiere aprobación en OT-13.
