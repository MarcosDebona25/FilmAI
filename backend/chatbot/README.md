# Cómo se conecta el chatbot

El recorrido de un mensaje, de punta a punta.

```
Panel del chat (PR 6)
  │  al abrirse: POST /api/chat/preparar/ ── carga bge-m3 en segundo plano
  │  al abrirse: GET /api/chat/messages/ ── el historial, de a 20 (views.py)
  │  al preguntar: POST /api/chat/messages/
  ▼
MensajesView.post (PR 5)    valida, toma el candado y transmite los eventos;
  │                          guarda el turno con servicio.guardar_turno()
  │  llama a responder()
  ▼
orquestador.py              habla con el modelo y conecta todo lo de abajo
  ├─▶ contexto.py            ¿qué le gusta a este usuario?
  ├─▶ anonimizar.py          saca nombres y correos antes de enviar
  ├─▶ idioma.py              ¿en qué idioma escribió el mensaje?
  ├─▶ prompts.py             las instrucciones del modelo
  ├─▶ llm.py                 habla con DeepSeek
  ├─▶ marcadores.py          cambia los [[n]] del modelo por el título y arma las tarjetas
  └─▶ tools/ ejecutar()      el modelo pidió una herramienta (por puente.py)
        ├─▶ busqueda.py      TMDB y búsqueda semántica
        └─▶ personales.py    listas del usuario
              └─▶ turno.py   recuerda qué apareció en este turno
```

Entre la vista y el orquestador está el contrato de `eventos.py`; el del stream hacia el navegador, en `contracts/sse-chat.md`. Para probarlo
sin la vista: `python manage.py chatear --usuario juanp`. Cada mensaje tiene costo,
porque usa la clave de `.env`.
Por defecto no guarda nada, así que se puede probar con un usuario real sin ensuciar
su chat; con `--guardar` cada turno se guarda como lo hace la app (`guardar_turno()`:
tarjetas y `ya_recomendados` incluidos).
Con `--golden` recorre el set dorado (`golden.yaml`) y mide los tiempos contra
RNF #6.
Para ver cómo fue un turno, buscá en el log del backend la línea `Turno:` del logger
`chatbot.orquestador`. Además de cómo fue (tools, vueltas, marcadores y
`titulos_sin_tarjeta`: los recomendados que superaron el tope de 3), trae lo que
costó: `llamadas`, `tokens_entrada`, `tokens_salida`, `cache_acierto` y `cache_fallo`
(tokens de la entrada que DeepSeek ya tenía en caché o no; `?` si el proveedor no los
informa), `cortado_por_largo` (alguna llamada terminó por `length`) y
`segundos_por_llamada` y `segundos_total`. Nunca lleva texto de la pregunta ni de la
respuesta.

## Los pasos de `responder()`

`responder()` es corta a propósito: solo dice en qué orden van los pasos. Cada paso
es una función de `orquestador.py`, y todos comparten un objeto `_Turno` (la
conversación con el modelo, el texto que ya salió, lo que se anota para el log).

```
responder(chat, texto, idioma)
  │
  ├─ 1. _abrir_turno          lee la base (perfil, historial, tarjetas anteriores)
  │                           y arma los mensajes para el modelo
  │
  ├─ 2. _conversar            hasta 5 vueltas (4 con tools y la respuesta)
  │       │  por cada vuelta:
  │       ├─ _escuchar                    una llamada al modelo; retiene el texto
  │       │                               o lo transmite ──▶ Texto
  │       ├─ _hay_que_forzar_la_busqueda  ¿recomendó sin buscar? se descarta y se
  │       │                               repite una vez con tool_choice="required"
  │       ├─ _cerrar_texto_de_la_vuelta   entrega lo retenido, salvo un «ya busco»
  │       ├─ ¿no pidió tools? ── fin del paso 2
  │       └─ _buscar                      ──▶ Estado("searching"); corre las tools
  │                                       (en otro hilo) y suma los resultados
  │       si se acaban las vueltas: _ultima_llamada (sin tools)
  │
  ├─ 3. _asegurar_respuesta   ¿ni una palabra? _ultima_llamada (sin tools)
  ├─ 4. _armar_tarjetas       red sin marcadores y una parte por saga
  ├─ 5. _registrar_turno      la línea `Turno:` del log
  └─ ──▶ Resultado(texto, tarjetas)    lo único que la vista guarda
```

Cuando el plazo aprieta, el paso 2 termina antes (ver «El plazo del turno»).

Los pasos que entregan eventos son generadores async (`async def` con `yield`):
`responder()` los recorre con `async for` y reenvía cada evento. Se partió el
15/11/2026 sin cambiar la conducta; `tests_responder_caracterizacion.py` tiene la
foto de la secuencia de eventos de antes del cambio.

## El plazo del turno

Un turno tiene 25 s para responder (`LLM_TIMEOUT_SECONDS`), modelo y tools incluidos.
Desde el 15/11/2026 ese tiempo lo administra el orquestador: sabe cuánto queda y, si
no alcanza, **cierra con lo que tiene** en vez de dejar que la vista lo corte con un
error. Las piezas están en `plazo.py`: `Plazo` (cuánto queda) y `Corte` (dejar de
esperar algo a una hora dada).

```
0 s                                         17,5 s              25 s      30 s
├────────────────── buscar ───────────────────┼───── cerrar ──────┤·········┤
│  llamadas al modelo con tools y las tools   │ reserva: 7,5 s    │  red de │
│                                             │ para la respuesta │ la vista│
```

| Momento | Regla | Con 25 s |
|---|---|---|
| Antes de otra vuelta con tools | Tiene que quedar el 40 % del plazo. Si no, última llamada sin tools | 10 s |
| Llamada al modelo que todavía no escribió nada | Se corta cuando queda solo la reserva (30 %), y se pide la respuesta de cierre | a los 17,5 s |
| Llamada al modelo que ya está escribiendo | Puede seguir hasta el final del plazo | a los 25 s |
| Tools de una vuelta | Tienen lo que queda menos la reserva. Adentro, TMDB espera 3 s y reintenta 1 vez (`CHAT_TMDB_TIMEOUT`, `CHAT_TMDB_REINTENTOS`) en vez de 5 s y 3 veces, y ni TMDB ni Ollama esperan más de lo que queda | hasta los 17,5 s |
| Sagas (`una_parte_por_saga`) | 2 s, o lo que quede si es menos | — |
| Red de la vista (`views.tope_de_la_vista`) | Un 20 % más que el plazo. No debería cumplirse nunca | 30 s |

**Qué ve el usuario si se acaba el tiempo:**

- *Se acabó el tiempo para buscar* (vueltas lentas, TMDB caído, un modelo que no
  contesta): recibe una respuesta normal, hecha con lo que se encontró hasta ahí.
  Mismos eventos de siempre, hasta `fin`. Antes era un `error` y no se guardaba nada.
- *Se acabó con la respuesta a medio escribir*: el texto queda hasta donde llegó y
  termina en «…». El turno cierra normal (tarjetas, `fin`, se guarda).
- *Se acabó sin una sola palabra*: `error` (`chat_unavailable`), como antes.

En el log, la línea `Turno:` lo anota en `sin_tiempo=no|busqueda|respuesta`, y una
tool que no llegó a correr o a terminar figura como `nombre(sin_tiempo)`.

**Por qué las tools llevan su propio plazo.** Las tools son código común y corren en
un hilo (`en_hilo`). Un hilo no se puede cancelar desde afuera: el `Corte` hace que
el orquestador deje de esperarlo, pero el hilo sigue. Por eso el tiempo también viaja
hacia adentro: `_correr_tools` abre un `plazo_de_red` (`catalogo/plazo.py`) y los
clientes de TMDB y Ollama lo consultan antes de cada pedido, así la tool termina sola
a la misma hora. Fuera del chat no hay plazo abierto y nada cambia.

**Qué historial ve el modelo**: los últimos 10 mensajes **de la sesión actual**. Una
sesión se corta con un silencio mayor a `CHAT_VENTANA_SESION_MINUTOS` (45 por defecto,
medido hacia atrás desde el mensaje que llega), y a lo que dijo el asistente se le
quitan las `**` en la copia que viaja (lo guardado no cambia). En `golden.yaml`, un
mensaje de `historial` con `hace_min` simula una sesión anterior.

## Qué hace cada archivo

| Archivo | Para qué sirve |
|---|---|
| `eventos.py` | El contrato entre el Motor y el Canal: qué eventos entrega `responder()` |
| `orquestador.py` | `responder()`: el ida y vuelta entre el modelo y las herramientas, partido en pasos (ver «Los pasos de `responder()`»). Al cerrar cada turno escribe una línea de log INFO (`Turno: tools=… vueltas=… ultima_sin_tools=… tarjetas=…`) con las tools pedidas y su cantidad de resultados, sin la pregunta ni la respuesta. Si pasa el tope de 4 vueltas con tools o termina sin texto, hace una última llamada sin tools para que responda con lo que ya encontró. Las tarjetas salen de los marcadores `[[n]]` que escribe el modelo (ver `marcadores.py`); el log suma `marcadores_validos`, `marcadores_invalidos`, `negritas_propias`, `reintento_forzado` y `saga_descartadas` (tarjetas salteadas por ser otra parte de una saga que ya tenía la suya). Si el modelo recomienda sin haber buscado (un `[[n]]` sin candidato o una negrita), descarta ese primer intento y repite la llamada una vez con `tool_choice="required"`; por eso la primera vuelta del turno se retiene entera hasta saber si hubo tools. Las tarjetas del último mensaje del asistente entran como candidatos numerados («¿y las tarjetas?») |
| `orquestador_falso.py` | Un `responder()` de mentira, para construir la vista sin el modelo |
| `servicio.py` | `guardar_turno()` (pregunta, respuesta y `ya_recomendados`, todo o nada) y el historial |
| `views.py` | `POST /api/chat/preparar/`; `MensajesView`: el historial (`GET`) y la pregunta con su respuesta en streaming (`POST`) |
| `sse.py` | El formato de cada evento del stream (`event:` y `data:`) |
| `limites.py` | El candado «una respuesta a la vez» y el tope de mensajes por hora |
| `serializers.py` | Cómo sale cada mensaje y cada tarjeta en el historial |
| `plazo.py` | `Plazo` (cuánto le queda al turno) y `Corte` (dejar de esperar a una hora dada, con `asyncio.timeout_at`). Ver «El plazo del turno» |
| `puente.py` | `en_hilo`: el único paso de código async a código común |
| `llm.py` | El proveedor del modelo, y `ProveedorFalso` para los tests |
| `prompts.py` | Las instrucciones del modelo. La fecha de hoy va en la parte variable (junto al perfil), para no perder el caché del texto fijo. El tope de 3 se le pide como tope de títulos recomendados (contando un extra en el cierre), no de marcadores: un cuarto marcador sale en el texto, sin tarjeta |
| `idioma.py` | `detectar_idioma()`: en qué idioma responder, según el mensaje |
| `management/commands/chatear.py` | Hablar con el bot desde la terminal; con `--golden`, correr el set dorado |
| `golden.yaml` | El set dorado: preguntas fijas, cada una con lo que se espera de la respuesta |
| `contexto.py` | Arma el perfil del usuario desde la base |
| `anonimizar.py` | Limpia datos personales de lo que va al proveedor: correos y nombres, sin importar apóstrofos curvos, tildes sueltas ni letras como `ł`, `ø`, `ı` o `ß` (que valen como `l`, `o`, `i` y «ss») |
| `tools/__init__.py` | La puerta de las herramientas: `ejecutar()`, que antes revisa los argumentos contra el esquema y devuelve `invalid_arguments` si están mal |
| `tools/esquemas.py` | La descripción de cada herramienta, que lee el modelo, con el largo máximo de los textos y el rango de los números |
| `tools/busqueda.py` | Las herramientas que buscan títulos. `descubrir` y `buscar_semantico` aceptan `basada_en_libro` (keyword de TMDB «based on novel or book»); `detalle` de una serie trae `temporadas` y `episodios` |
| `marcadores.py` | `FiltroDeMarcadores`: mientras el texto sale por SSE, cambia cada `[[n]]` por `**Título** (año)` y suma la tarjeta (hasta 3, sin repetir; un marcador sin candidato se elimina y se loguea); un marcador sin candidato se elimina y se loguea). `una_parte_por_saga` corre al final del turno y deja una sola película por colección de TMDB (detalles en paralelo, solo de las candidatas, máximo 2 s; si TMDB falla, las tarjetas quedan como estaban) |
| `tools/personales.py` | `mis_listas` (solo las listas activas) |
| `tools/turno.py` | `ContextoTurno`: el estado de una pregunta y su respuesta, incluidos los títulos encontrados, numerados por orden de aparición (`candidatos()`, el `ref` de cada resultado) |

## Fuera de esta carpeta

- `catalogo/services/semantica.py`: la búsqueda por significado.
- `catalogo/services/embeddings.py`: habla con Ollama.
- `catalogo/client.py` y `catalogo/cache.py`: hablan con TMDB.
- `catalogo/plazo.py`: el plazo de red que las tools abren para TMDB y Ollama.

## Palabras que aparecen

- **Turno**: una pregunta y su respuesta, no toda la conversación.
- **Tool o herramienta**: una función que el modelo pide y el backend ejecuta.
- **Motor y Canal**: lo que piensa la respuesta y lo que la transporta. Su especificación está en
  `openspec/specs/chat-api/` y las decisiones de diseño en `docs/decisiones.md`.
