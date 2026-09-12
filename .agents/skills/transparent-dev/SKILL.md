---
name: transparent-dev
description: Explica de manera clara y natural las decisiones de implementación, alternativas y límites de una solución de software. Usar solo cuando el usuario active explícitamente este modo mediante sus palabras de activación o al mencionar la skill.
---

# Transparent Dev

Esta skill busca que una entrega de software sea fácil de entender y evaluar. La explicación acompaña a la solución con un tono natural: presenta qué se resolvió, por qué se eligieron las decisiones relevantes, qué conviene vigilar y qué podría mejorarse después. No convierte la respuesta en una plantilla rígida ni repite lo que el código ya expresa por sí mismo.

## Activación explícita

Usar esta skill únicamente si el usuario:

- menciona `transparent-dev`, `Transparent Dev` o invoca la skill de forma directa;
- pide explícitamente una explicación de las decisiones, justificaciones, alternativas, trade-offs, límites o riesgos del código;
- usa una expresión equivalente como «explicá las decisiones», «mostrame por qué lo hiciste así», «desarrollá de forma transparente» o «quiero entender la implementación».

No activarla por el mero hecho de que el usuario pida crear, modificar, refactorizar o depurar código.

## Cómo presentar la entrega

Adaptar la explicación al tamaño y la complejidad reales de la tarea. Empezar con la solución o el cambio realizado; después, desarrollar solo la información que ayuda a comprenderla.

Cuando sea relevante, explicar con lenguaje directo:

- la decisión que condiciona el comportamiento, y la razón de haberla elegido;
- una alternativa razonable y el trade-off que llevó a descartarla;
- supuestos, casos límite, riesgos de seguridad, rendimiento o mantenimiento;
- mejoras concretas que serían útiles si cambian las necesidades del proyecto.

Intercalar explicaciones con fragmentos de código cuando eso ayude a seguir una implementación extensa. Para cambios pequeños, basta una explicación breve antes o después del código. No hay fases obligatorias, umbrales de líneas, número mínimo de alternativas ni formato fijo de títulos, tablas o resúmenes.

## Decisiones y preguntas

Tomar decisiones razonables dentro del contexto disponible y declararlas de forma breve. Preguntar al usuario solo si falta información que cambia materialmente el comportamiento, la arquitectura, la seguridad, el costo o el alcance. No pedir aprobación de un plan como requisito para empezar.

Si se trabaja con una suposición, indicarla junto con su efecto práctico. Si el usuario deja la elección al agente, elegir la opción más adecuada y explicar el criterio.

## Calidad de la explicación

Explicar el porqué de las decisiones, no narrar literalmente cada línea. Nombrar patrones solo si aporta claridad; no usar jerga ni inventar alternativas para llenar la respuesta. Mantener la atención en información verificable y útil para que el usuario pueda mantener, cambiar o revisar la solución.

Al cerrar, mencionar únicamente las limitaciones, precauciones o próximas mejoras que realmente apliquen. Si no existen cuestiones abiertas, no agregarlas por formalidad.
