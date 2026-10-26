---
name: comparar-opciones
description: "Trigger: decidir, elegir, opciones, alternativas, pros y contras, cuadro comparativo, qué conviene, recomendación. Presenta una decisión del equipo como cuadro comparativo con una recomendación y la pregunta para elegir."
---

# Comparar opciones

Se usa cuando algo pide una decisión del equipo (alcance, diseño, seguridad, costo) y hay más de un camino razonable. Si un camino es claramente el correcto, no hace falta: se toma, se explica en una línea y se anota en `docs/decisiones.md`.

## 1. Antes del cuadro

- Verificar los datos que se van a comparar: leer el código, medir, o buscar en la documentación oficial. Nada de números inventados ni de "suele pasar".
- Entre 2 y 4 opciones, distintas de verdad. "No hacer nada" entra si es una opción real.
- Contar en dos o tres líneas el problema: qué pasa hoy, con un ejemplo concreto, y por qué hay que decidir.

## 2. El cuadro

Una tabla por decisión, con estas columnas:

| Opción | Qué hace | A favor | En contra | Costo |
|---|---|---|---|---|

- **Qué hace**: en términos de lo que ve el usuario de la app o de lo que cambia en el sistema, no del código.
- **A favor / En contra**: concretos y comparables entre filas (si una fila habla de latencia, las otras también).
- **Costo**: lo que lleva hacerlo (archivos, tests, migraciones) y lo que cuesta después (mantenimiento, llamadas a TMDB, memoria).
- La opción recomendada va primera y marcada con **(recomendada)**.

Debajo del cuadro, la recomendación en una o dos líneas: por qué esa y qué haría falta para cambiar de idea.

Si son varias decisiones a la vez, un cuadro por cada una, numeradas, y al final un resumen de una línea por decisión con la opción recomendada.

## 3. La pregunta

Después de los cuadros, preguntar con `AskUserQuestion` (no como una lista en el texto): una pregunta por decisión, hasta 4 por llamada, la recomendada primera y con "(Recommended)" en la etiqueta. Si hay más de 4, preguntar las más importantes y dejar el resto con la recomendada como opción por defecto, avisándolo.

## 4. Después de elegir

- Anotar la decisión en `docs/decisiones.md`: fecha, qué se eligió, por qué, y las opciones descartadas en una línea cada una.
- Si la decisión queda pendiente, anotarla igual como pendiente, con la recomendación.
