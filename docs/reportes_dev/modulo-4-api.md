# Módulo 4: contrato de perfil y sesiones

La API usa los nombres de campos del modelo en `snake_case`. Todas las rutas
tienen slash final. Las operaciones privadas requieren una cuenta activa y JWT
vigente; si el JWT viaja en cookie, las mutaciones exigen `X-CSRFToken`.

## Perfil y contraseña

| Ruta | Entrada / respuesta |
| --- | --- |
| `GET /api/profile/` | `pk`, `correo`, `nombre_usuario`, `nombre`, `apellido`, `fecha_nacimiento`, `genero`, `estado`, `avatar_id`, `fecha_registro`, `tiene_contrasena_local`. |
| `PUT /api/profile/` | Actualización parcial de `nombre`, `apellido`, `nombre_usuario`, `avatar_id`. Responde con el perfil actualizado. |
| `POST /api/profile/change-password/` | `old_password`, `password1`, `password2`. Responde 200 con `detail`; limpia cookies y exige login nuevo. |
| `POST /api/auth/password/reset/` | `email`. Mensaje genérico exista o no la cuenta. Solo envía enlaces para cuentas activas, incluidas Google sin contraseña local. |
| `POST /api/auth/password/reset/confirm/` | `uid`, `token`, `password1`, `password2`. Enlace de una hora y un solo uso; no inicia sesión. |

Los campos no editables o desconocidos del perfil se ignoran y no se persisten.
La contraseña nunca se devuelve. Validaciones fallidas devuelven 400 por campo;
un nombre de usuario ocupado devuelve 409. La comparación de nombres de usuario
no distingue mayúsculas. Se permiten letras Unicode en nombre y apellido, sin
espacios ni números, según CU-001.

## Por qué se verifican access y refresh

El access permite consultar o modificar recursos; el refresh permite obtener otro
access sin volver a escribir credenciales. Invalidar solo el primero dejaría al
segundo renovar una sesión anterior. Ambos se comparan con el hash de contraseña
vigente usando la capacidad `CHECK_REVOKE_TOKEN` de SimpleJWT. Los JWT emitidos
antes de habilitarla tampoco pasan la comprobación: el despliegue requiere volver
a iniciar sesión en todos los dispositivos.

La renovación mantiene rotación y blacklist. Si se envía por cookie, exige CSRF
incluso cuando el access ya venció. Si se envía explícitamente en el cuerpo,
se valida el token sin depender de las cookies.

## Recuperación y concurrencia

La escritura bloquea la fila del usuario dentro de una transacción. El bloqueo
hace esperar a otra operación sobre esa fila; después se vuelve a comprobar el
token y el estado. Así un enlace no puede usarse dos veces mediante solicitudes
que habían validado simultáneamente. La contraseña y las políticas no cambian si
hay un error de validación o persistencia.

La notificación por correo se programa con `transaction.on_commit`: solo se
envía si la base confirmó el cambio. Su fallo se registra, pero no revierte la
contraseña ni devuelve un error que sugiera que el cambio no ocurrió.

## Integración de UI

- Avisar antes de confirmar: «Se cerrarán tus sesiones en todos los dispositivos».
- Después de cambiar o restablecer, redirigir al login; nunca iniciar sesión
  automáticamente.
- Para `tiene_contrasena_local=false`, ofrecer recuperación por correo para crear
  la contraseña local. El botón Google sigue siendo válido después de crearla.
- El alias `/api/auth/password/change/` usa los mismos campos y validaciones del
  endpoint de perfil.

## Verificación y reversión

`backend/usuarios/test_perfil.py` explica cada prueba en su docstring. Cubre
permisos, CSRF, campos manipulados, validaciones, unicidad, rollback, sesiones de
varios dispositivos, JWT anteriores al despliegue, recuperación vencida/reutilizada
y acceso Google y local sobre la misma cuenta. Las pruebas OAuth simulan solo
la validación externa del token Google y ejecutan el resto del flujo allauth.

Comando focalizado: `docker compose exec -T backend python manage.py test usuarios --noinput`.
Resultado de la primera unidad: 82 pruebas correctas. Los casos HTTP se ejecutan
contra PostgreSQL temporal, sin modificar los datos de desarrollo.

La primera unidad se revierte retirando las rutas nuevas y sus serializers/vistas,
la comprobación de revocación y la migración `usuarios.0005`, junto con sus tests
y notas. No modifica datos del catálogo, listas ni preferencias.

## Fuentes

- [SimpleJWT: CHECK_REVOKE_TOKEN](https://django-rest-framework-simplejwt.readthedocs.io/en/latest/settings.html#check-revoke-token).
- [OWASP: Forgot Password](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html).
- [Google OpenID Connect: sub](https://developers.google.com/identity/openid-connect/openid-connect#an-id-tokens-payload).
