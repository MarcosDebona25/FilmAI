---
name: explicar-al-implementar
description: "Trigger: implementar, agregar, modificar, depurar, crear, escribir, generar, editar, refactorizar, optimizar, corregir, arreglar, construir, desarrollar, programar, testear, probar, configurar, integrar, conectar, migrar, actualizar, cambiar, ajustar, mejorar, extender, ampliar, simplificar, documentar, comentar, explicar, enseñar, aprender, entender, analizar, revisar, auditar, inspeccionar, explorar, investigar, diagnosticar, resolver, solucionar. Siempre activa cuando se genera o modifica código en este repo. Explicar mientras se construye, para un equipo que está aprendiendo los frameworks del stack. No dar por sabido ningún concepto. Diagrama de componentes cuando se toque arquitectura o comunicación entre servicios. Cada test se explica al escribirlo. Apuntar a la versión corta, y expandir donde el concepto lo pida: la brevedad nunca se paga con una explicación que falta."
license: Apache-2.0
metadata:
  author: "gonzag8, marcosdebona"
  version: "1.2"
---

# Explicar al implementar

## Por qué existe

FilmAI es un proyecto académico (UTN-FRSF). Quienes lo escriben están
aprendiendo Django, DRF, Celery, Redis, Docker y Next.js **mientras** los usan.
Un agente que entrega código correcto sin explicarlo deja un repo que nadie del
equipo puede mantener, extender ni defender en una entrega.

El objetivo no es documentar: es que después de cada tramo, quien lo pidió
pueda explicar qué se hizo y por qué.

## Activación

Siempre que se implemente, modifique o depure algo en este repo. No hace falta
que la pidan.

## Reglas

### 1. No dar por sabido ningún concepto de framework

Ni los básicos. Si aparece por primera vez en la conversación, se explica en
una línea antes de usarlo: qué es una migración, un volumen de Docker, una
señal, un serializer, un Server Component, un TTL, un decorador de tarea.

Si el concepto ya se explicó antes en la conversación, mencionarlo ("ya lo
vimos arriba") y repetirlo de forma compacta en una línea, no asumir que el
usuario lo recuerda.

Mal: "agrego el `@shared_task` y lo encolo con `.delay()`".
Bien: "`@shared_task` convierte una función normal en algo que Celery puede
ejecutar en otro proceso; `.delay()` no la ejecuta, escribe un mensaje en la
cola para que el worker la levante."

### 2. Diagrama cuando se toque arquitectura o comunicación entre componentes

Si el cambio involucra a más de un servicio, o cómo se hablan entre sí, va un
diagrama de cajas y flechas en texto **antes** del código. Cada flecha dice
por dónde va (HTTP, SQL, cola de Redis) — es lo que no se ve leyendo un
archivo.

```
celery-beat ──03:00──▶ Redis DB 1 ──▶ celery-worker ──HTTP──▶ TMDB
                                            │
                                            └──SQL──▶ Postgres
```

Tres cosas que conviene repetir cuando aplican: qué proceso corre qué código,
quién le habla a quién y **por dónde**, y qué estado comparten.

### 3. Explicar cada test al escribirlo

Nunca aparecen decenas de líneas en `tests.py` sin que se sepa qué se probó.
Por cada test: qué caso cubre y por qué importa. Una tabla de dos columnas
alcanza cuando son varios.

Vale también la regla inversa: si un test pasa antes y después del cambio, no
es un RED y hay que decirlo, no tildarlo.

### 4. Breve, pero sin perder claridad

Menos prosa, misma cobertura. Preferir tablas, listas cortas y un ejemplo
concreto antes que párrafos. No repetir en el texto lo que el código ya dice;
explicar lo que el código **no** dice.

El orden es: **apuntar a la versión corta, y expandir donde el concepto lo
pida**. Las dos mitades importan. Escribir de más cansa y hace que se salteen
la respuesta; escribir de menos deja un cambio que nadie puede defender.

**Ante la duda, explicar.** Si una explicación es necesaria para entender el
cambio, va — aunque haga la respuesta más larga. La brevedad nunca se paga con
una explicación que falta.

### 5. Avanzar en unidades chicas

No volcar todos los cambios de un plan de una vez. Un paso, su explicación, su
verificación, y recién ahí el siguiente. Al terminar cada uno: qué comando
correr y qué se espera ver.

### 6. Explicar un archivo antes de tocarlo si está abierto

Si el usuario tiene abierto el archivo que se va a modificar (si el contexto
lo permite), explicar qué hace y qué se le va a cambiar antes de editarlo.

### 7. Ofrecer opciones solo cuando son reales

Dar a elegir entre alternativas genuinas, con el trade-off de cada una. Cuando
hay una sola respuesta razonable, decirlo así — "esto no es una elección, es
X, por esto" — en vez de fabricar un menú.

### 8. Verificar antes de afirmar

Este repo integra una API externa (TMDB). Nunca afirmar qué devuelve sin
haberlo consultado, y nunca inventar un fixture: en C-04a un `job: "Director"`
fabricado mantuvo 172 tests en verde mientras ninguna serie tenía director en
producción. Lo mismo con las sugerencias de bots de revisión: verificar contra
el archivo real antes de aplicarlas.

## Qué NO hace esta skill

- No convierte cada respuesta en un tutorial: si el concepto ya se explicó en
  la conversación, se menciona que ya se vio y se repite de forma compacta.
- No narra línea por línea lo que el código ya expresa.
- No reemplaza a `docs/decisiones.md`: las decisiones de arquitectura se
  registran ahí igual (regla de `AGENTS.md`).
