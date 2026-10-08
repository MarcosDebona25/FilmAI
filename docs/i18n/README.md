# Curaduría de textos para multiidioma

`equivalencias.json` conserva la tabla original. `claves.csv` agrega destinos
semánticos y textos completos para revisión; no crea catálogos de producción.
La siembra corresponde a OT-77, después de la revisión editorial de OT-13.

Cada `origen_id` es la posición original, empezando en 1. Hay una fila por
entrada y se conservan exactamente `es_original`, `en_original` y `pantallas`.
Los textos curados pueden cambiar sin perder esa referencia.

| Columna                   | Qué contiene                                                         |
| ------------------------- | -------------------------------------------------------------------- |
| `clave` / `namespace`     | Destino que describe una función, por ejemplo `search.results.count` |
| `estado`                  | Clasificación que decide si se puede revisar para siembra            |
| `es_curado` / `en_curado` | Mensaje completo, con argumentos y plurales cuando corresponde       |
| `grupo`                   | IDs de los fragmentos que forman una sola frase                      |
| `observaciones`           | Motivo del cambio, datos variables y revisiones pendientes           |
