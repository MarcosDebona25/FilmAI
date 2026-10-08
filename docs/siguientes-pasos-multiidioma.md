# Multiidioma — estado y aceptación

Actualizado el 08/10/2026 sobre `develop`, partiendo de `f27e302`. No se hizo merge a `main` ni se publicó esta entrega.

## Implementado

| Fase         | Estado                                                                                                            |
| ------------ | ----------------------------------------------------------------------------------------------------------------- |
| F0–F6        | Backend e inventarios previos conservados; enlaces y contrato actualizados                                        |
| F7, OT-70–77 | Infraestructura, formatos, errores, validaciones, selector, sincronización, rutas y tres pilotos implementados    |
| F8, OT-80–83 | Paridad, lint, residuos, recorridos bilingües, tests por código y eliminación del contrato anterior implementados |
| F9, OT-90    | Documentación y material de revisión preparados; aceptación externa pendiente                                     |

El backend emite solo `{code, params, errors, debug?}` en errores; `debug` queda reservado al desarrollo y el frontend no lo consume. Los éxitos conservan datos de máquina y `code`, sin `detail`. Las referencias de API afirman el contrato nuevo.

El frontend manda `Accept-Language`, traduce errores por campo/código, usa formatos `en-US`/`es-AR` y consume enumeraciones estables. Cuenta y preferencias incluyen `idioma`: la cuenta prevalece sobre la cookie; un idioma nulo conserva la resolución del dispositivo. El selector autenticado espera que el PUT se confirme antes de cambiar cookie y render; un fallo conserva el idioma anterior.

Las pantallas bilingües son `/settings`, `/confirm-email/[key]` y `/reset-password/[uid]/[token]`. Se renombraron además `/profile`, `/my-reviews` y `/complete-signup`; `/lists` sigue protegido, sin pantalla nueva. El footer y los controles usan las ubicaciones aprobadas. Los demás archivos conservan las 13 excepciones de copia heredada, que deben retirarse al integrar sus diseños.

El usuario confirmó que abrir un correo respeta cookie → navegador → inglés del dispositivo receptor, aunque el mensaje esté escrito en otro idioma. No se agregó un parámetro de idioma a los enlaces.

## Evidencia local

- Línea base: Django 685 tests; Vitest 73 tests; ESLint, Prettier, TypeScript y build aprobados. La primera corrida Playwright coincidió con cambios en su servidor y no se toma como una línea base limpia.
- Implementación: Vitest **96 tests** y Playwright **37 recorridos** aprobados. Django pasó **686 tests**, incluyendo la nueva comprobación de marcas de respaldo en listas y reseñas.
- Ruff, ESLint sin warnings, TypeScript, build de producción, paridad y residuos verificados. La revisión visual incluyó 390 y 1280 px, con teclado, foco y ausencia de desborde.
- OpenAPI y referencias de correos regeneradas deliberadamente y comparadas por los tests. El generador OpenAPI conserva diagnósticos previos (incluidos errores de introspección) por vistas sin serializer declarado; la suite aprueba, pero esos diagnósticos no equivalen a una validación completa de todas las operaciones OpenAPI.
- Base de desarrollo: tres listas predeterminadas para admin. Cero producciones enriquecidas pendientes de traducción; 39 filas sin enriquecer se completan al materializarse. No se duplicaron modelos ni embeddings.

## Pendientes de aceptación externa

1. **CI remoto sobre esta entrega.** `gh run list --branch develop` no devuelve ejecuciones. El workflow ahora incluye pushes y PRs hacia `develop`, además de `main`, y el control de residuos. No se afirma CI verde sin una ejecución remota.
2. **Revisión de correos en un cliente real.** Están preparados los ocho EML y la [vista HTML](i18n/revision-correos/index.html). Se generaron con transporte en memoria, sin envío externo. Registrar cliente, versión y resultado al abrirlos; las pruebas de render no reemplazan esa comprobación.

La guía para implementar los diseños está en [i18n/guia.md](i18n/guia.md). Los controles y las pruebas ya permiten empezar a construirlos sin cambiar la infraestructura de idioma; la lista de aceptación del plan conserva el CI remoto pendiente.

## Pair programming del 09/10/2026: chatbot

Revisar cómo mantener el idioma durante una respuesta SSE, qué sucede si se cambia mientras una solicitud sigue en curso y cómo localizar tarjetas y errores. La decisión vigente es respuesta en `idioma_efectivo()`, español con voseo y tools TMDB localizadas. BGE-M3 y el corpus canónico inglés se conservan. B-02–B-06 no se implementaron en esta entrega.
