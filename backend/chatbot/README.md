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
Con `--golden` recorre el set dorado (`golden.yaml`) y mide los tiempos contra
RNF #6.
Para ver cómo fue un turno, buscá en el log del backend la línea `Turno:` del logger
`chatbot.orquestador`.

## Qué hace cada archivo

| Archivo | Para qué sirve |
|---|---|
| `eventos.py` | El contrato entre el Motor y el Canal: qué eventos entrega `responder()` |
| `orquestador.py` | `responder()`: el ida y vuelta entre el modelo y las herramientas. Al cerrar cada turno escribe una línea de log INFO (`Turno: tools=… vueltas=… ultima_sin_tools=… tarjetas=…`) con las tools pedidas y su cantidad de resultados, sin la pregunta ni la respuesta. Si pasa el tope de 4 vueltas con tools o termina sin texto, hace una última llamada sin tools para que responda con lo que ya encontró. Las tarjetas salen de los marcadores `[[n]]` que escribe el modelo (ver `marcadores.py`); el log suma `marcadores_validos`, `marcadores_invalidos`, `negritas_propias` y `reintento_forzado`. Si el modelo recomienda sin haber buscado (un `[[n]]` sin candidato o una negrita), descarta ese primer intento y repite la llamada una vez con `tool_choice="required"`; por eso la primera vuelta del turno se retiene entera hasta saber si hubo tools. Las tarjetas del último mensaje del asistente entran como candidatos numerados («¿y las tarjetas?») |
| `orquestador_falso.py` | Un `responder()` de mentira, para construir la vista sin el modelo |
| `servicio.py` | `guardar_turno()` (pregunta, respuesta y `ya_recomendados`, todo o nada) y el historial |
| `views.py` | `POST /api/chat/preparar/`; `MensajesView`: el historial (`GET`) y la pregunta con su respuesta en streaming (`POST`) |
| `sse.py` | El formato de cada evento del stream (`event:` y `data:`) |
| `limites.py` | El candado «una respuesta a la vez» y el tope de mensajes por hora |
| `serializers.py` | Cómo sale cada mensaje y cada tarjeta en el historial |
| `puente.py` | `en_hilo`: el único paso de código async a código común |
| `llm.py` | El proveedor del modelo, y `ProveedorFalso` para los tests |
| `prompts.py` | Las instrucciones del modelo. La fecha de hoy va en la parte variable (junto al perfil), para no perder el caché del texto fijo |
| `idioma.py` | `detectar_idioma()`: en qué idioma responder, según el mensaje |
| `management/commands/chatear.py` | Hablar con el bot desde la terminal; con `--golden`, correr el set dorado |
| `golden.yaml` | El set dorado: preguntas fijas, cada una con lo que se espera de la respuesta |
| `contexto.py` | Arma el perfil del usuario desde la base |
| `anonimizar.py` | Limpia datos personales de lo que va al proveedor: correos y nombres, sin importar apóstrofos curvos, tildes sueltas ni letras como `ł`, `ø`, `ı` o `ß` (que valen como `l`, `o`, `i` y «ss») |
| `tools/__init__.py` | La puerta de las herramientas: `ejecutar()`, que antes revisa los argumentos contra el esquema y devuelve `invalid_arguments` si están mal |
| `tools/esquemas.py` | La descripción de cada herramienta, que lee el modelo, con el largo máximo de los textos y el rango de los números |
| `tools/busqueda.py` | Las herramientas que buscan títulos. `descubrir` y `buscar_semantico` aceptan `basada_en_libro` (keyword de TMDB «based on novel or book»); `detalle` de una serie trae `temporadas` y `episodios` |
| `marcadores.py` | `FiltroDeMarcadores`: mientras el texto sale por SSE, cambia cada `[[n]]` por `**Título** (año)` y suma la tarjeta (hasta 3, sin repetir; un marcador sin candidato se elimina y se loguea) |
| `tools/personales.py` | `mis_listas` (solo las listas activas) |
| `tools/turno.py` | `ContextoTurno`: el estado de una pregunta y su respuesta, incluidos los títulos encontrados, numerados por orden de aparición (`candidatos()`, el `ref` de cada resultado) |

## Fuera de esta carpeta

- `catalogo/services/semantica.py`: la búsqueda por significado.
- `catalogo/services/embeddings.py`: habla con Ollama.
- `catalogo/client.py` y `catalogo/cache.py`: hablan con TMDB.

## Palabras que aparecen

- **Turno**: una pregunta y su respuesta, no toda la conversación.
- **Tool o herramienta**: una función que el modelo pide y el backend ejecuta.
- **Motor y Canal**: lo que piensa la respuesta y lo que la transporta. Reparto en
  `openspec/changes/chatbot/tasks.md`.
