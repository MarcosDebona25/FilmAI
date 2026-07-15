# FilmIA — Lineamientos de Diseño de Interfaces

> Documento de trabajo para guiar el diseño en Figma. Se actualiza incrementalmente.

---

## 1. Arquitectura de Información

```
Página Pública (sin sesión)
├── Landing / Login
└── Registro

App Autenticada
├── Inicio (Home)          ← descubrimiento: recomendaciones, tendencias, novedades
├── Buscar                 ← panel overlay con catálogo unificado + toggle Películas/Series + filtros
├── Listas                 ← favoritos, pendientes, vistas + personalizadas
└── [Avatar]               ← dropdown: Mi perfil / Cerrar sesión
```

**Navbar definitiva**: `[Logo]  Inicio  Buscar  Listas                    [Avatar]`

- 3 links de navegación + avatar a la derecha.
- El avatar reemplaza el ítem "Perfil" y despliega un menú con "Mi perfil" y "Cerrar sesión".
- "Buscar" abre un panel overlay que reemplaza la vista actual con el catálogo completo (grid + filtros + toggle Películas/Series).
- El chatbot se accede desde un FAB flotante presente en todas las pantallas.

---

## 2. Inventario de Pantallas

| # | Pantalla | Caso de Uso | Acceso |
|---|----------|-------------|--------|
| 1 | Login | CU-003 | Pública |
| 2 | Registro | CU-001 | Pública |
| 3 | Confirmación de cuenta | CU-002 | Pública (vía email) |
| 4 | Home (autenticado) | CU-013 | Autenticada |
| 5 | Buscar (panel overlay con catálogo unificado) | CU-008, CU-010 | Mixta* |
| 6 | Ficha de detalle | CU-008, CU-011 | Mixta* |
| 7 | Modal: Publicar/Modificar reseña | CU-015 | Autenticada |
| 8 | Modal: Confirmación (genérico) | Varios | Autenticada |
| 9 | Sección Listas (vista general) | CU-009 | Autenticada |
| 10 | Detalle de Lista | CU-009 | Autenticada |
| 11 | Modal: Crear/Renombrar lista | CU-012 | Autenticada |
| 12 | Perfil de usuario | CU-005 | Autenticada |
| 13 | Modificar perfil | CU-006 | Autenticada |
| 14 | Pantallas de error/estado vacío | Varios | Mixta |

> \* Mixta = visible sin login, pero acciones (calificar, agregar a listas) requieren autenticación.

---

## 3. Decisiones de Diseño

### 3.1 Chatbot: Flotante (FAB)

**Decisión**: FAB (botón flotante) en esquina inferior derecha, abre/cierra un panel tipo drawer.

**Justificación**:
- Estándar de la industria (Intercom, Zendesk, Crisp).
- No compite visualmente con la grilla de contenido.
- Funciona naturalmente en desktop (drawer lateral) y mobile (bottom sheet).
- Coincide con la semántica de los CU: el usuario "abre" la interfaz del chatbot.

**Comportamiento**:
- FAB fijo en bottom-right con ícono de chat/burbuja.
- Al clickear: panel de ~400px (desktop) o bottom sheet fullscreen (mobile).
- Animación slide-in desde derecha (desktop) / slide-up (mobile).
- Badge sutil en el FAB cuando hay respuesta nueva sin leer.
- Visible en todas las pantallas; inactivo si el usuario no está autenticado.

### 3.2 Home: Solo Descubrimiento + Búsqueda como Panel Overlay

**Decisión**: Home es exclusivamente una página de descubrimiento pasivo con filas de contenido
(Recomendado, Tendencias, Novedades). El catálogo completo para exploración activa se accede
desde el link "Buscar" en la navbar, que abre un panel overlay con grid, toggle de tipo
(Todo / Películas / Series) y filtros.

**Justificación**:
- Distinción clara entre descubrir (Home) y buscar (panel overlay). No se mezclan.
- El modelo IMDb/MUBI: feed principal + búsqueda como acción separada.
- La entidad `ProduccionAudiovisual` unifica películas y series con atributo `tipo`; la UI
  refleja esto ofreciendo un catálogo unificado con toggle en lugar de dos secciones duplicadas.
- 3 items en navbar (vs. 5 del diseño original) = menos carga cognitiva.

**Nota**: El RF de navegación y los CU-008/010 en el doc 02 fueron actualizados para reflejar
este modelo (Inicio, Buscar, Listas + avatar).

### 3.3 Recomendaciones: Camino Algorítmico (TMDB)

**Decisión**: "Recomendado para ti" usa endpoints de TMDB (`/discover`) con heurísticas basadas en géneros mejor calificados por el usuario.

**Justificación**:
- Sin dependencia del LLM para esta funcionalidad (menor latencia, sin costo por llamada).
- TMDB provee filtros por género, popularidad y puntuación suficientes para una primera versión.
- El LLM se reserva para interacciones conversacionales del chatbot.
- Se documenta el camino basado en LLM como mejora futura.

**Lógica**:
1. Géneros de producciones calificadas con 7+ por el usuario.
2. Llamada a `/discover/movie` o `/discover/tv` con filtro de géneros, ordenado por `popularity.desc`.
3. Excluir IDs que el usuario ya tiene en sus listas (vistas, pendientes, calificadas).
4. Devolver 10-15 resultados.

---

## 4. Layout Base (Shell)

Todas las pantallas autenticadas comparten:

```
┌──────────────────────────────────────────────────────────┐
│  HEADER (navbar fijo, ~64px)                             │
│  [FilmIA]  Inicio  Buscar  Listas             [Avatar]  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  CONTENT AREA                                            │
│                                                          │
│                                                    ┌──┐  │
│                                                    │💬│  │ ← FAB chatbot
│                                                    └──┘  │
└──────────────────────────────────────────────────────────┘
```

- **Navbar**: 3 links funcionales (Inicio, Buscar, Listas) + avatar a la derecha.
  - Link activo resaltado con color de acento.
  - Avatar click → dropdown: "Mi perfil", "Cerrar sesión".
  - "Buscar" click → panel overlay que reemplaza el content area con el buscador.
- **Footer**: mínimo, sin prioridad en esta etapa.
- **FAB**: fixed, bottom-right 32px, z-index superior al contenido.

---

## 5. Home

```
┌──────────────────────────────────────────┐
│  ┌─ HERO (opcional) ──────────────────┐  │
│  │  Backdrop + overlay                │  │
│  │  Título + botón "Ver detalle"      │  │
│  └─────────────────────────────────────┘  │
│                                          │
│  ── Recomendado para ti ────────────── │
│  [card] [card] [card] [card] [card] →  │  ← scroll horizontal
│                                          │
│  ── Tendencias de la semana ────────── │
│  [card] [card] [card] [card] [card] →  │
│                                          │
│  ── Novedades ──────────────────────── │
│  [card] [card] [card] [card] [card] →  │
└──────────────────────────────────────────┘
```

El Home es **solo descubrimiento**. No tiene catálogo completo, ni tabs, ni grid con filtros.
Para buscar, el usuario clickea "Buscar" en la navbar.

### Secciones

| Fila | Visible para | Fuente de datos |
|------|-------------|-----------------|
| Hero | Todos | TMDB trending (rotativo o destacado fijo) |
| Recomendado para ti | Solo autenticados con ≥1 calificación | TMDB `/discover` filtrado por géneros |
| Tendencias | Todos | TMDB `/trending` |
| Novedades | Todos | TMDB `/movie/now_playing`, `/discover` año actual |

- Cada fila: título + opcional "Ver más →" + scroll horizontal de MediaCards.
- Las filas mezclan películas y series, con badge de tipo en cada card.
- Flechas de navegación en hover (desktop), swipe nativo (mobile).
- Si una fila no tiene datos (ej. usuario nuevo sin recomendaciones), se oculta completamente.

### Estados del Home

| Estado | Comportamiento |
|--------|---------------|
| No autenticado | Hero + Tendencias + Novedades. FAB chatbot inactivo. |
| Autenticado sin historial | Ídem, FAB activo, sin fila "Recomendado para ti". |
| Autenticado con historial | Las 3 filas completas. |
| Loading | Skeleton cards (4-5 placeholders) por fila. |
| Error TMDB | Toast "No se pudo cargar el contenido." + datos cacheados si existen. |

---

## 5b. Buscar (Panel Overlay)

Se activa al clickear "Buscar" en la navbar. Reemplaza el content area del Home con un
panel overlay a pantalla completa.

```
┌──────────────────────────────────────────────────────────┐
│  TOOLBAR DE BÚSQUEDA                                     │
│  [🔍 Buscar...__________]  [Todo|Pelis|Series]  [Género] │
│                                                          │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐           │
│  │    │ │    │ │    │ │    │ │    │ │    │           │
│  │post│ │post│ │post│ │post│ │post│ │post│           │   ← grid responsive
│  │Tít.│ │Tít.│ │Tít.│ │Tít.│ │Tít.│ │Tít.│           │
│  └────┘ └────┘ └────┘ └────┘ └────┘ └────┘           │
│  ...                                                    │
│  [←] [1] [2] [3] ... [15] [→]                          │
└──────────────────────────────────────────────────────────┘
```

### Comportamiento

- Panel overlay que cubre todo el viewport debajo del navbar.
- Se abre/cierra con click en "Buscar" o tecla Escape.
- Campo de búsqueda con autofocus al abrir.
- **Toggle de tipo**: Todo / Películas / Series. Cambia el placeholder del input y el filtro
  aplicado a la grilla.
- **Filtros**: dropdowns de Género, Año, Calificación mínima.
- **Resultados**: grid de MediaCards con badge de tipo (Película/Serie) y rating.
- Paginación clásica al pie.

### Estados

| Estado | Qué se muestra |
|--------|---------------|
| Default (sin búsqueda) | Grilla completa con resultados populares, ordenados por popularidad. |
| Búsqueda con resultados | Resultados paginados coincidentes. Contador "N resultados encontrados". |
| Búsqueda sin resultados | Empty state: ilustración + "No se encontraron resultados" + sugerencia de ajustar filtros. |
| Error API | "No se pudo recuperar el catálogo." + botón reintentar. |

---

## 6. Componentes Base (Design System)

### 6.1 Botones
- **Primary**: acción principal (CTA), color de acento, full width en forms.
- **Secondary**: acción alternativa (cancelar, volver).
- **Danger/Ghost**: acciones destructivas (eliminar, dar de baja).
- **Icon button**: acciones compactas (editar, eliminar, toggle).
- **Toggle**: listas predeterminadas (agregar/quitar de favoritos, vistas, pendientes).

### 6.2 Inputs
- **Text input**: con/sin ícono, estados: default, focus, error, disabled.
- **Password input**: con toggle mostrar/ocultar (ícono ojo).
- **Search input**: con ícono de lupa, disabled hasta que se ingrese texto.
- **Select/Dropdown**: género, filtros.
- **Datepicker**: fecha de nacimiento en registro.

### 6.3 Navegación
- **Navbar**: links con estado active/inactive, avatar con dropdown.
- **Paginación**: prev/next + números (clásica).
- **Breadcrumb**: opcional en fichas de detalle.

### 6.4 Cards
- **MediaCard**: poster (2:3), título, año, rating TMDB. Hover: escala 1.02 + sombra.
- **ListCard**: nombre, cantidad de items, mini preview de 3-4 posters.
- **ReviewCard**: estrellas, texto, fecha, acciones (editar/eliminar).

### 6.5 Feedback
- **Rating stars**: widget 1-10 estrellas, solo valores enteros.
- **Spinner/Loader**: indicador de carga genérico.
- **Skeleton**: placeholder rectangular animado para carga de contenido.
- **Toast/Notificación**: mensaje de éxito/error, posicionado top-right o bottom-center.
- **Progress bar**: indicador durante procesamiento del chatbot.

### 6.6 Chat
- **ChatPanel**: drawer/popover accionado por FAB.
- **ChatBubble**: mensaje de usuario (alineado derecha) y bot (alineado izquierda).
- **ChatInput**: campo de texto + botón enviar.
- **TypingIndicator**: tres puntos animados mientras el bot procesa.

### 6.7 Modales
- **Modal genérico**: overlay + contenido centrado + botones de acción.
- **Modal de confirmación**: título + mensaje + Cancelar/Confirmar.
- **Modal de formulario**: título + campos + Cancelar/Guardar.

### 6.8 Estados
- **Empty state**: ilustración + mensaje descriptivo.
- **Error state**: ilustración + mensaje + botón "Reintentar".
- **404**: ilustración + "Página no encontrada" + link a Home.

### 6.9 Indicadores
- **Badge**: etiqueta "Predeterminada" en listas del sistema.
- **Tag**: género de película/serie.
- **Status dot**: estado de cuenta (activa, pendiente, baja).

---

## 7. Recomendaciones Visuales

### 7.1 Tema
- **Modo oscuro como default** (cine/entretenimiento), con opción de modo claro.
- Fondo: `#121212` o `#1a1a2e`.
- Acento: dorado/ámbar `#f5c518` o naranja `#e67e22`.

### 7.2 Tipografía
- UI: Inter o Roboto.
- Títulos (opcional): Playfair Display (serif).
- Escala: 12, 14, 16, 18, 20, 24, 32, 40 px.

### 7.3 Espaciado
- Base 8px: 4, 8, 12, 16, 24, 32, 48, 64 px.

### 7.4 Bordes
- Cards: 8px.
- Botones: 6px.
- Inputs: 4px.

### 7.5 Breakpoints
- Desktop: 1440px (12 columnas).
- Tablet: 768px (8 columnas).
- Mobile: 375px (4 columnas).
- MediaCard grid: 5 cols desktop → 3 tablet → 2 mobile.

---

## 8. Lo que NO requiere pantalla

- **Panel de administrador**: CU-016 y CU-017 operan vía BD/API, sin UI dedicada.
- **Chats múltiples**: el modelo de clases los contempla, pero los CU solo definen la conversación activa en el chatbot principal.

---

## 9. Recomendaciones para Figma

1. Crear un **Design System file** separado con componentes, estilos de color y tipografía.
2. **Auto layout** en todos los componentes para iteración rápida.
3. **Variants** con propiedad "State" (default, hover, focus, disabled, error, loading, empty).
4. Priorizar diseño por sprints:
   - **Sprint 1**: Login, Registro, Home, Buscar (panel overlay).  ← completado
   - **Sprint 2**: Ficha de detalle, Modales de reseña, Listas.
   - **Sprint 3**: Perfil, Modificar perfil, Pantallas de error/estado vacío, Confirmación de cuenta.
5. Prototipar flujos críticos:
   - Registro completo (registro → email → confirmación → login → home).
   - Publicar reseña (catálogo → detalle → modal → calificar → publicar → ver en perfil).
   - Chatbot (FAB → escribir → enviar → loading → respuesta / cancelar).

---

## 10. Pantallas Definidas

- [x] **Home** — Sección 5
- [x] **Buscar (panel overlay)** — Sección 5b
- [ ] Ficha de detalle
- [ ] Modales de reseña
- [ ] Listas
- [ ] Perfil
- [ ] Login / Registro
- [ ] Confirmación de cuenta
- [ ] Modificar perfil
- [ ] Pantallas de error/estado vacío
