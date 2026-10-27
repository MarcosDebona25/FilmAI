---
name: cerrar-tramo
description: Cierra un tramo de FilmAI antes de abrir su PR. Corre los mismos chequeos que el CI, lanza agentes que revisan el tramo en paralelo, verifica cada hallazgo, deja `docs/decisiones.md` y graphify al día y hace el commit. No hace push ni mergea sin el OK del usuario.
disable-model-invocation: true
---

# Cerrar un tramo

Se usa cuando un tramo está terminado en su rama. Lo que llega al PR tiene que pasar el CI (`.github/workflows/ci.yml`) y traer la documentación al día.

## 1. Dónde estamos

- `git branch --show-current` tiene que dar la rama del tramo (`feat/…`, `fix/…`, `chore/…`, `docs/…`), nunca `main` ni `develop`. Si es una de esas, frenar y avisar.
- `git status --short` y `git log --oneline origin/main..HEAD` muestran qué falta commitear y qué trae el tramo. Si la rama está apilada sobre otra que todavía no está en `main`, decirlo: el PR va contra esa rama y hay que cambiarle la base cuando la otra entre.
- No usar `git stash` (ver AGENTS.md y la memoria del proyecto).

## 2. Los chequeos del CI

Los mismos de `ci.yml`. Frenar en el primero que falle, arreglarlo y volver a correrlos.

Backend (los tests con `run --rm`, que levanta solo db y redis):

```
docker compose run --rm -T backend sh -c "ruff format --check . && ruff check . && python manage.py test --noinput"
```

Frontend, desde `frontend/`:

```
npx eslint . --max-warnings=0
npx prettier --check .
npm run test:unit
npm run i18n:check
npx tsc --noEmit
npm run build
```

- Si el tramo cambió `package.json`, reconstruir la imagen del frontend (`build` + `up -d -V frontend`) y correr `npm install` en el host.
- Si cambió textos de la interfaz: `npm run i18n:generate` y regenerar los `.d.json.ts`.
- Si cambió vistas o serializers: regenerar `contracts/openapi.yaml` y `error-codes.json` y revisar el diff.
- Si tocó perfil, reseñas o listas: `npm run test:e2e -- --workers=1` con la app levantada.
- La suite del backend tarda unos 9 minutos. Correrla en segundo plano y no cambiar de rama mientras corre: el contenedor monta `./backend`.
- Si Docker está apagado, pedirle al usuario que lo encienda (memoria de WSL). Con Docker encendido, `run --rm` se puede usar sin preguntar; `docker compose up` y `build` de la app, no.

## 3. Revisión con agentes en paralelo

Con los chequeos en verde, lanzar los subagentes en un mismo mensaje para que corran a la vez. Si el tramo no tocó el frontend, alcanza con A y B. Si es solo documentación o configuración, saltear este paso.

| Agente | Qué revisa |
|---|---|
| A. Errores y seguridad | Entradas raras en la URL y en el cuerpo (ids que no existen, fuera de rango, tipos equivocados); permisos y datos de otra cuenta; throttles y topes (escritura, TMDB por pedido y por IP); llamadas a TMDB que se multiplican; N+1; carreras entre pedidos en paralelo; lo que llega al log |
| B. Tests y contrato | Comportamientos sin test; tests que pasan sin probar lo que dice su nombre; códigos de error que faltan en `error-codes.json`; diferencias entre el contrato OpenAPI y la respuesta real; un boceto de cada test que falta |
| C. Frontend y accesibilidad | Componentes que cambiaron, con la skill `vercel-quality`; foco, teclado y ARIA; estados de carga, vacío y error; textos que no salen de `traducciones/`; SSR y caché |

Los agentes arrancan sin saber nada de esta conversación. Cada uno recibe:

- Qué es FilmAI y el stack (Django + DRF, Next.js, Postgres, Redis, Celery, TMDB), qué hace el tramo y qué documentos de `docs/` lo describen.
- Cómo ver el tramo: `git diff origin/main` más los archivos nuevos (`??` en `git status --short`). Que lean los archivos completos cuando les haga falta contexto, y `graphify-out/GRAPH_REPORT.md` para ubicarse.
- Qué queda pendiente a propósito, para que no lo informen como error.
- Solo lectura: no editar, no commitear, no cambiar de rama, no instalar nada, no correr tests ni `manage.py shell`. Los tests ya corrieron en el paso 2.
- Cómo informar: hasta 8 hallazgos, de más grave a menos grave, cada uno con `archivo:línea`, qué está mal, un escenario concreto (qué entrada lleva a qué resultado), gravedad y confianza. Nada de estilo. Cero hallazgos es una respuesta válida.

Mientras revisan, seguir con el paso 4, que no toca código. No cambiar de rama: los agentes leen esta carpeta.

Con los informes:

1. Verificar cada hallazgo leyendo el código o con un test que lo reproduzca. Para el test, commitear el arreglo antes de probar el RED (`git checkout <base> -- archivos`, correr, `git checkout HEAD -- archivos`). Lo que no se verificó no se arregla ni se informa como cierto.
2. Si está confirmado, es chico y es del tramo: arreglarlo y volver al paso 2.
3. Si cambia el alcance, una decisión o el diseño: preguntar al usuario con la skill `comparar-opciones`.
4. Si es de otro tramo: anotarlo en `docs/decisiones.md` como pendiente.

## 4. Documentación, en el mismo commit que el código

- `docs/decisiones.md`: una entrada arriba de todo por cada decisión del tramo, con fecha, qué, por qué y archivos afectados. Los falsos positivos de una revisión también, con el motivo.
- `docs/01` a `06`: si el tramo cambia algo que describen, corregirlos.
- `openspec/`: si el tramo tiene un cambio de openspec, marcar las tareas hechas (sin archivar).
- `graphify update .` si se tocaron archivos de código, y agregar `graphify-out/` al commit.

## 5. Commit

- Con la skill `conventional-commits`, en español, en el tono de `git log --oneline -10`.
- Sin `Co-Authored-By` y sin menciones a Claude ni a IA.
- El pre-commit corre ruff, eslint y prettier. Si cambia archivos, agregarlos y volver a commitear.

## 6. PR y merge

- Push y PR solo con el OK del usuario. El PR va contra `main` (o contra la rama de abajo si está apilado).
- El CI corre en PRs a `main`, `develop` y `feat/**`: un PR apilado sobre una rama `fix/…` no lo dispara hasta que su base pase a `main`. Al cambiar la base hace falta un push nuevo (por ejemplo, rebasear sobre `origin/main`).
- PR-Agent es informativo: leer sus comentarios, verificar cada uno como en el paso 3 y anotar los falsos positivos. El que bloquea es `ci.yml`.
- Se mergea con el CI en verde y con el OK explícito del usuario para ese PR: `gh pr merge N --merge --delete-branch`. En una pila, cambiar antes la base del PR de arriba a `main` (`gh pr edit N --base main`), así no se cierra al borrar la rama.

## 7. Qué decirle al usuario

- Qué se hizo y por qué, en términos simples, con cada concepto nuevo explicado en una o dos líneas (skill `explicar-al-implementar`).
- Qué encontró la revisión: qué se arregló, qué se descartó y por qué, y qué quedó pendiente.
- Cómo probarlo en el navegador: direcciones, pasos y qué debería ver.
- Qué archivos vale la pena leer y cuáles puede saltear.
