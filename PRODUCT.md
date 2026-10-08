# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Usuarios casuales de cine y series (doc 01 §4) que quieren registrar lo que vieron y recibir ayuda para elegir qué ver. Interfaz en español rioplatense e inglés (multi-idioma desde el 08/10/2026). No son críticos ni cinéfilos expertos. Lo usan sobre todo en casa, de noche, buscando qué mirar, en desktop y en el celular.

## Product Purpose

Ayudar a decidir qué ver y a llevar registro: catálogo de películas y series de TMDB, calificaciones 1-10 con reseña opcional, listas (Favoritos, Pendientes, Vistas y personalizadas) y recomendaciones personalizadas. Éxito: encontrar algo para ver rápido, y volver a registrar lo que se vio.

## Positioning

Las recomendaciones salen de tu propio historial (lo que calificaste, viste y guardaste), y un chatbot conversa sobre eso anclado en títulos reales del catálogo, sin inventar. Las listas genéricas no conocen tu historial.

## Operating Context

Proyecto académico (Seminario Integrador, UTN-FRSF) de dos personas, que se presenta en una demo. Contenido de TMDB en el idioma del usuario, con el inglés como respaldo para lo que no tiene traducción (OT-60 a OT-63, 08/10/2026). Calificar una producción la marca como vista.

## Capabilities and Constraints

- Módulos: auth (local + Google), catálogo (Home, Buscar, Ficha), calificaciones y reseñas, listas, perfil y preferencias, chatbot (FAB, solo con sesión), moderación en el Admin.
- Home y Ficha se ven sin sesión; calificar, listas y chatbot exigen sesión.
- Pendiente: chatbot (B-02 a B-06) sin implementar; arquitectura acordada el 08/10/2026 (`docs/decisiones.md`).

## Brand Commitments

- Nombre FilmAI. Oscuro por defecto, claro opcional (switch en Preferencias).
- Acento dorado `#f5c518`, ligado a calificar (estrellas).
- Evolución del estilo existente, no reemplazo (decisión del 03/10/2026).
- Wordmark y favicon propios, en reemplazo del ícono de icons8.
- Voz: rioplatense, directa, sin exageraciones.

## Evidence on Hand

- Pósters, backdrops y metadatos reales vía TMDB; 26 avatares en `frontend/public/avatars/`; collage de la landing en `frontend/public/collage-posters/`.
- No hay usuarios reales, testimonios ni métricas: no se inventan.

## Product Principles

1. El contenido manda: los pósters y títulos son la interfaz.
2. Elegir rápido: pocos pasos entre abrir la app y encontrar qué ver.
3. Registrar sin fricción: calificar o marcar como vista en un toque; confirmación solo cuando se pierde algo.
4. Recomendar con honestidad: si no hay datos, se dice.

## Accessibility & Inclusion

WCAG AA: contraste de 4,5:1 o más en los dos temas, uso completo con teclado, foco visible y respeto de `prefers-reduced-motion`.
