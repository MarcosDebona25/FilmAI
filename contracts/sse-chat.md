# Contrato del stream del chat (`POST /api/chat/messages/`)

drf-spectacular no puede describir un stream SSE, así que este archivo es la
referencia. `contracts/openapi.yaml` declara el `POST` con su cuerpo, el `200` como
`text/event-stream` y los rechazos previos al stream. La especificación canónica
es `openspec/specs/chat-api/` (mientras el cambio siga abierto:
`openspec/changes/chatbot/specs/chat-api/spec.md`).

## Pedido

```
POST /api/chat/messages/
Content-Type: application/json
Accept: text/event-stream
X-CSRFToken: <cookie csrftoken>
Cookie: access=<JWT>; csrftoken=<token>

{"texto": "algo como Interstellar pero más corto"}
```

`texto`: de 1 a 500 caracteres una vez recortados los espacios. El idioma de las
tarjetas y de los estados es el de la cuenta; si no tiene, el de `Accept-Language`.
El idioma de la prosa lo decide el backend según lo que escribió el usuario.

## Antes de abrir el stream

Si el pedido se rechaza, la respuesta es JSON común con el sobre de errores
`{code, params, errors}` y no se guarda nada.

| Estado | `code` | Cuándo |
|---|---|---|
| 400 (Bad Request) | `validation_error` | Texto vacío o de más de 500 caracteres; `errors[0].field` es `texto` |
| 401 (Unauthorized) | `not_authenticated` | Sin sesión |
| 401 (Unauthorized) | `session_revoked` | La cuenta se dio de baja y el JWT todavía no venció (igual que el resto de la API) |
| 403 (Forbidden) | `permission_denied` | Falta o falló el token CSRF |
| 409 (Conflict) | `chat_request_in_progress` | Ya hay una respuesta en curso para este chat |
| 429 (Too Many Requests) | `throttled` | Más de `CHAT_MENSAJES_POR_HORA` (20) mensajes en la hora; trae `retry_after_seconds` y el encabezado `Retry-After` |

Un 400 y un 409 no gastan cupo de la hora. Un 429 devuelve el candado.

## El stream

Respuesta `200 OK` con `Content-Type: text/event-stream`, `Cache-Control: no-cache`
y `X-Accel-Buffering: no`. Cada evento es:

```
event: <nombre>
data: <una sola línea de JSON>

```

El `data` va siempre en una línea: los saltos de línea del texto viajan escapados
(`\n`), así que un evento nunca se parte.

| Evento | `data` | Cuándo |
|---|---|---|
| `estado` | `{"code": "searching"}` | Empieza una búsqueda. El front traduce el código |
| `texto` | `{"delta": "..."}` | Un pedazo de la respuesta; se concatenan en orden |
| `tarjetas` | `{"tarjetas": [{"id_tmdb", "tipo", "titulo", "poster", "anio"}]}` | **Una vez**, después de guardar y justo antes de `fin`; puede venir vacío. Nunca en un turno que termina en `error` |
| `fin` | `{"id": <pk de la respuesta>, "id_pregunta": <pk de la pregunta>}` | La pareja quedó guardada. Es el único cierre exitoso |
| `error` | `{"code": "chat_unavailable", "params": {}, "errors": []}` | Terminal. No se guardó nada |

El stream termina con exactamente un `fin` o un `error`. **Un stream que se corta
sin ninguno de los dos es un error de red** para el front (decisión del 09/10/2026).

Orden: `estado`* y `texto`* (mezclados, en el orden en que ocurren), luego
`tarjetas` y `fin`; o bien `error` en cualquier punto.

`chat_unavailable` es un solo código para todas las causas (proveedor caído, cuota,
tiempo agotado, tope de rondas de herramientas, fallo al guardar): el usuario no
puede hacer nada distinto en cada caso. La causa queda en el log del servidor.

## Cancelar

Cancelar es abortar el `fetch`. El servidor recibe la desconexión y cancela el
turno: **antes del guardado no queda nada** y el candado se suelta. Si el corte
llega durante el guardado, el guardado termina (la transacción decide) y el candado
se suelta al terminar; la respuesta aparecerá en el historial la próxima vez que se
lea (postcondición de falla de CU-014, aceptada el 08/10/2026).

## Límites

- Una respuesta a la vez por chat. El candado vence solo a los
  `LLM_TIMEOUT_SECONDS + 35` s (60 con el valor por defecto) si el proceso muere.
- Un turno dura como máximo `LLM_TIMEOUT_SECONDS` (25 s), herramientas incluidas. El
  guardado queda fuera de ese tope.
- `CHAT_MENSAJES_POR_HORA` (20) por usuario, en ventana fija de reloj.
