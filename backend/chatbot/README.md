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
  └─▶ tools/ ejecutar()      el modelo pidió una herramienta (por puente.py)
        ├─▶ busqueda.py      TMDB y búsqueda semántica
        └─▶ personales.py    listas del usuario y tarjetas
              └─▶ turno.py   recuerda qué apareció en este turno
```

Entre la vista y el orquestador está el contrato de `eventos.py`; el del stream hacia el navegador, en `contracts/sse-chat.md`. Para probarlo
sin la vista: `python manage.py chatear --usuario juanp`. Cada mensaje tiene costo,
porque usa la clave de `.env`.

## Qué hace cada archivo

| Archivo | Para qué sirve |
|---|---|
| `eventos.py` | El contrato entre el Motor y el Canal: qué eventos entrega `responder()` |
| `orquestador.py` | `responder()`: el ida y vuelta entre el modelo y las herramientas |
| `orquestador_falso.py` | Un `responder()` de mentira, para construir la vista sin el modelo |
| `servicio.py` | `guardar_turno()` (pregunta, respuesta y `ya_recomendados`, todo o nada) y el historial |
| `views.py` | `POST /api/chat/preparar/`; `MensajesView`: el historial (`GET`) y la pregunta con su respuesta en streaming (`POST`) |
| `sse.py` | El formato de cada evento del stream (`event:` y `data:`) |
| `limites.py` | El candado «una respuesta a la vez» y el tope de mensajes por hora |
| `serializers.py` | Cómo sale cada mensaje y cada tarjeta en el historial |
| `puente.py` | `en_hilo`: el único paso de código async a código común |
| `llm.py` | El proveedor del modelo, y `ProveedorFalso` para los tests |
| `prompts.py` | Las instrucciones del modelo |
| `idioma.py` | `detectar_idioma()`: en qué idioma responder, según el mensaje |
| `management/commands/chatear.py` | Hablar con el bot desde la terminal |
| `contexto.py` | Arma el perfil del usuario desde la base |
| `anonimizar.py` | Limpia datos personales de lo que va al proveedor |
| `tools/__init__.py` | La puerta de las herramientas: `ejecutar()` |
| `tools/esquemas.py` | La descripción de cada herramienta, que lee el modelo |
| `tools/busqueda.py` | Las herramientas que buscan títulos |
| `tools/personales.py` | `mis_listas` y `mostrar_tarjetas` |
| `tools/turno.py` | `ContextoTurno`: el estado de una pregunta y su respuesta |

## Fuera de esta carpeta

- `catalogo/services/semantica.py`: la búsqueda por significado.
- `catalogo/services/embeddings.py`: habla con Ollama.
- `catalogo/client.py` y `catalogo/cache.py`: hablan con TMDB.

## Palabras que aparecen

- **Turno**: una pregunta y su respuesta, no toda la conversación.
- **Tool o herramienta**: una función que el modelo pide y el backend ejecuta.
- **Motor y Canal**: lo que piensa la respuesta y lo que la transporta. Reparto en
  `openspec/changes/chatbot/tasks.md`.
