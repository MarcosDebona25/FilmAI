# FilmAI — Lineamientos de Diseño de Interfaces

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
└── [Avatar]               ← dropdown: Mi perfil / Mis reseñas / Preferencias / Cerrar sesión
```

**Navbar definitiva**: `[Logo]  Inicio  Buscar  Listas                    [Avatar]`

- 3 links de navegación + avatar a la derecha.
- El avatar reemplaza el ítem "Perfil" y despliega un menú con "Mi perfil", "Mis reseñas", "Preferencias" y "Cerrar sesión".
- "Buscar" abre un panel overlay que reemplaza la vista actual con el catálogo completo (grid + filtros + toggle Películas/Series).
- El chatbot se accede desde un FAB flotante presente en todas las pantallas.

---

## 2. Inventario de Pantallas

| #   | Pantalla                                      | Caso de Uso    | Acceso              |
| --- | --------------------------------------------- | -------------- | ------------------- |
| 1   | Login                                         | CU-003         | Pública             |
| 2   | Registro                                      | CU-001         | Pública             |
| 3   | Confirmación de cuenta                        | CU-002         | Pública (vía email) |
| 4   | Home (autenticado)                            | CU-013         | Autenticada         |
| 5   | Buscar (panel overlay con catálogo unificado) | CU-008, CU-010 | Mixta*              |
| 6   | Ficha de detalle                              | CU-008, CU-011 | Mixta*              |
| 7   | Modal: Publicar/Modificar reseña              | CU-015         | Autenticada         |
| 8   | Modal: Confirmación (genérico)                | Varios         | Autenticada         |
| 9   | Sección Listas (vista general)                | CU-009         | Autenticada         |
| 10  | Detalle de Lista                              | CU-009         | Autenticada         |
| 11  | Modal: Crear/Renombrar lista                  | CU-012         | Autenticada         |
| 12  | Perfil (con edición inline)                   | CU-005, CU-006 | Autenticada         |
| 13  | Mis reseñas                                   | CU-015         | Autenticada         |
| 14  | Preferencias                                  | CU-005, CU-007 | Autenticada         |
| 15  | 404 — Página no encontrada                    | Varios         | Mixta               |
| 16  | Error genérico (500 / timeout)                | Varios         | Mixta               |

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
│  [FilmAI]  Inicio  Buscar  Listas             [Avatar]  │
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
  - Avatar click → dropdown: "Mi perfil", "Mis reseñas", "Preferencias", "Cerrar sesión".
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

| Fila                | Visible para                          | Fuente de datos                                   |
| ------------------- | ------------------------------------- | ------------------------------------------------- |
| Hero                | Todos                                 | TMDB trending (rotativo o destacado fijo)         |
| Recomendado para ti | Solo autenticados con ≥1 calificación | TMDB `/discover` filtrado por géneros             |
| Tendencias          | Todos                                 | TMDB `/trending`                                  |
| Novedades           | Todos                                 | TMDB `/movie/now_playing`, `/discover` año actual |

- Cada fila: título + opcional "Ver más →" + scroll horizontal de MediaCards.
- Las filas mezclan películas y series, con badge de tipo en cada card.
- Flechas de navegación en hover (desktop), swipe nativo (mobile).
- Si una fila no tiene datos (ej. usuario nuevo sin recomendaciones), se oculta completamente.

### Estados del Home

| Estado                    | Comportamiento                                                        |
| ------------------------- | --------------------------------------------------------------------- |
| No autenticado            | Hero + Tendencias + Novedades. FAB chatbot inactivo.                  |
| Autenticado sin historial | Ídem, FAB activo, sin fila "Recomendado para ti".                     |
| Autenticado con historial | Las 3 filas completas.                                                |
| Loading                   | Skeleton cards (4-5 placeholders) por fila.                           |
| Error TMDB                | Toast "No se pudo cargar el contenido." + datos cacheados si existen. |

---

## 5b. Buscar (Panel Overlay)

Se activa al clickear "Buscar" en la navbar. Reemplaza el content area del Home con un
panel overlay a pantalla completa.

```
┌──────────────────────────────────────────────────────────┐
│  TOOLBAR DE BÚSQUEDA                                     │
│  [🔍 Buscar...__________]  [Todo|Pelis|Series]  [Género] [Año] [⭐ mín] │
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

| Estado                  | Qué se muestra                                                                             |
| ----------------------- | ------------------------------------------------------------------------------------------ |
| Default (sin búsqueda)  | Grilla completa con resultados populares, ordenados por popularidad.                       |
| Búsqueda con resultados | Resultados paginados coincidentes. Contador "N resultados encontrados".                    |
| Búsqueda sin resultados | Empty state: ilustración + "No se encontraron resultados" + sugerencia de ajustar filtros. |
| Error API               | "No se pudo recuperar el catálogo." + botón reintentar.                                    |

---

## 5c. Ficha de Detalle

Se accede clickeando cualquier MediaCard desde Home, Buscar, o Listas. Reemplaza el content
area dentro del shell (navbar + FAB se mantienen). La navegación hacia atrás es vía breadcrumb.

```
┌──────────────────────────────────────────────────────────────────┐
│  Inicio > Breaking Bad                                             │  ← breadcrumb
│                                                                    │
│ ┌────────────────────────────────────────────────────────────────┐ │
│ │  ┌──────────┐                                                  │ │
│ │  │          │   Breaking Bad                     [Serie]       │ │
│ │  │  POSTER  │   2008  ·  5 temporadas  ·  62 episodios        │ │
│ │  │          │   ⭐ 9.5/10 (TMDB)                               │ │
│ │  │  96×144  │   [Drama] [Crimen] [Thriller]                    │ │
│ │  │          │                                                  │ │
│ │  │          │   [⭐ Calificar] [♥ Favoritos] [👁 Vista] [🕐 Pendiente]  │ │
│ │  │          │   [+ Agregar a lista ▾]                          │ │
│ │  └──────────┘                                                  │ │
│ │                                                                │ │
│ │  ┌─────────────────────────────────────────────────────────┐   │ │
│ │  │ Director: Vince Gilligan                                 │   │ │
│ │  │ Cast: Bryan Cranston, Aaron Paul, Anna Gunn, Dean Norris, │   │ │
│ │  │       Betsy Brandt, RJ Mitte, Bob Odenkirk, Giancarlo    │   │ │
│ │  │       Esposito, Jonathan Banks, ... [mostrar más ▾]      │   │ │
│ │  └─────────────────────────────────────────────────────────┘   │ │
│ │                                                                │ │
│ │  Sinopsis                                                      │ │
│ │  Walter White, un profesor de química de secundaria...         │ │
│ │  [leer más ▾]                                                  │ │
│ │                                                                │ │
│ │  ───────────────────────────────────────────────────────────── │ │
│ │  Reseñas (42)                                                  │ │
│ │  ┌──────────────────────────────────────────────────────────┐  │ │
│ │  │ Tu reseña                                [Editar] [Eliminar]│  │ │
│ │  │ 9/10                                                       │  │ │
│ │  │ "Una obra maestra de principio a fin..."                   │  │ │
│ │  └──────────────────────────────────────────────────────────┘  │ │
│ │  ┌──────────────────────────────────────────────────────────┐  │ │
│ │  │ @maria_lopez                               10/10          │  │ │
│ │  │ "La mejor serie que he visto en mi vida..."               │  │ │
│ │  └──────────────────────────────────────────────────────────┘  │ │
│ │  ┌──────────────────────────────────────────────────────────┐  │ │
│ │  │ @cinefilo_ok                               8/10           │  │ │
│ │  │ "Excelente desarrollo de personajes..."                   │  │ │
│ │  └──────────────────────────────────────────────────────────┘  │ │
│ │  ...                                                            │ │
│ │  [Cargar más reseñas]                                           │ │
│ └────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

### Origen y breadcrumb

| Desde                   | Breadcrumb                         |
| ----------------------- | ---------------------------------- |
| Home (fila concreta)    | Inicio > {título}                  |
| Buscar                  | Inicio > Buscar > {título}         |
| Listas (sección navbar) | Listas > {nombre lista} > {título} |

El breadcrumb es navegable, cada tramo es un link. Reemplaza al botón "Volver".

### Bloques y contenido

| Bloque                | Datos                                                                                                                                                                                                                                                                                                                                                                                                                               | Fuente                                          |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| **Hero**              | Poster (2:3, ~300×450 px), título, badge de tipo (Película/Serie), año de lanzamiento, duración (`Xh Ymin` para pelis o `N temporadas · M episodios` para series), calificación TMDB (formato `X/10`), géneros como chips                                                                                                                                                                                                           | `ProduccionAudiovisual` + TMDB                  |
| **Acciones directas** | **Calificar** (btn primary, abre modal de reseña, CU-015), **Favoritos** (♥ toggle, CU-011), **Vista** (ícono ojo 👁 toggle, CU-011), **Pendiente** (ícono reloj 🕐 toggle, CU-011), **Agregar a lista** (dropdown con checklist de listas personalizadas del usuario)                                                                                                                                                               | `Lista`                                         |
| **Sinopsis**          | Card dentro del info-col (columna derecha), debajo de los botones de acción. Texto completo colapsable con "[leer más ▾]" si excede 300 caracteres.                                                                                                                                                                                                                                                                                 | `ProduccionAudiovisual.sinopsis`                |
| **CastCard**          | Card full-width debajo del Hero: Director (nombre) + Cast (lista de actores). Colapsable con "[mostrar más ▾]" si hay más de 10 actores. **Sin fotos**.                                                                                                                                                                                                                                                                             | `ProduccionAudiovisual.reparto` + `.directores` |
| **Reseñas**           | Dos secciones con headers separados: "Tu reseña" (card destacada con borde acento, solo si el usuario ya publicó) y "Reseñas de la comunidad (N)". En tu reseña: acciones con iconos (✏️ editar, 🗑️ eliminar). En las de la comunidad: solo lectura. Cada ReviewCard: avatar, @usuario, rating en formato `X/10` (sin estrellas), fecha, texto. Se muestran únicamente reseñas que tengan texto. Botón "Cargar más reseñas" al pie. | `Calificacion` + `Reseña` + `Usuario`           |

### Acciones directas — comportamiento

| Acción            | Estado inicial                 | Click                                        | Estado final                                                             |
| ----------------- | ------------------------------ | -------------------------------------------- | ------------------------------------------------------------------------ |
| Favoritos (♥)     | Borde (no está en favoritos)   | Agrega a favoritos                           | Relleno sólido                                                           |
| Favoritos (♥)     | Relleno (ya está en favoritos) | Quita de favoritos                           | Borde                                                                    |
| Vista (👁)         | Borde                          | Agrega a Vistas                              | Relleno sólido                                                           |
| Vista (👁)         | Relleno (ya está en Vistas)    | Quita de Vistas                              | Borde (verifica: si tiene calificación, pide eliminarla primero, CU-011) |
| Pendiente (🕐)    | Borde                          | Agrega a Pendientes                          | Relleno sólido                                                           |
| Pendiente (🕐)    | Relleno                        | Quita de Pendientes                          | Borde                                                                    |
| Calificar         | —                              | Abre modal de reseña (CU-015)                | —                                                                        |
| Agregar a lista ▾ | —                              | Despliega checklist de listas personalizadas | Check/uncheck toggle                                                     |

Los botones de acción directa son visibles solo para usuarios autenticados. Para no autenticados, se muestra "Inicia sesión para calificar o guardar" con link a Login.

### Breadcrumb — comportamiento

- Único elemento de navegación hacia atrás (sin botón Volver extra).
- Desktop: top-left del content area, 14px, color secundario.
- Mobile: mismo comportamiento, scroll horizontal si no entra en el ancho.
- Cada tramo es un link clickeable excepto el último (página actual, en negrita).
- El penúltimo tramo (origen) restaura la vista anterior preservando scroll y resultados si es Buscar.

### Estados

| Estado         | Qué se muestra                                                                                  |
| -------------- | ----------------------------------------------------------------------------------------------- |
| Loading        | Skeleton del Hero (poster placeholder + líneas) + skeleton de 3 ReviewCards.                    |
| Éxito          | Contenido completo como se describe arriba.                                                     |
| No autenticado | Contenido visible, acciones directas reemplazadas por "Inicia sesión para calificar o guardar". |
| Error TMDB     | Toast "No se pudo cargar la información. Intente nuevamente." + botón Reintentar.               |
| Sin reseñas    | Encabezado "Reseñas (0)" + texto "Sé el primero en dejar una reseña." + botón Calificar.        |

### Responsive

| Breakpoint       | Layout                                                                                                             |
| ---------------- | ------------------------------------------------------------------------------------------------------------------ |
| Desktop (1440px) | Poster left + info right (two-column, sinopsis incluida en columna derecha). CastCard y reseñas full-width debajo. |
| Tablet (768px)   | Poster más chico (200×300 px). Misma estructura two-column.                                                        |
| Mobile (375px)   | Single column. Poster centrado arriba, info debajo. Acciones en fila de iconos.                                    |

---

## 5d. Modal de Calificar / Reseña

Modal superpuesto (overlay) que se abre desde la Ficha de Detalle para publicar, editar o eliminar
una reseña. No reemplaza la página. Fondo con blur + opacidad.

### Variantes

| Variante     | Disparador                               | Contenido                                                                                                                                                                           | Botones               |
| ------------ | ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- |
| **Publicar** | Click en "Calificar" (sin reseña previa) | Widget de estrellas interactivo (1-10, ver abajo), campo de texto opcional (máx 1000 chars, ~6 líneas), contador de caracteres                                                      | Cancelar / Publicar   |
| **Editar**   | Click en icono ✏️ (desde tu reseña)      | Mismo widget con calificación y texto precargados. Las estrellas del rating anterior que quedarían fuera de la nueva selección se muestran en un amarillo apagado durante el hover. | Cancelar / Actualizar |
| **Eliminar** | Click en icono 🗑️ (desde tu reseña)      | Sin formulario. Título: "¿Eliminar reseña?" — Cuerpo: "Esta acción no se puede deshacer."                                                                                           | Cancelar / Confirmar  |

### Widget de estrellas

- Único lugar del sistema donde se usan estrellas visuales (en la ficha y reseñas se usa formato `X/10`).
- 10 estrellas en fila horizontal.
- **Hover**: las estrellas se iluminan progresivamente según la posición del puntero, mostrando la
  calificación que se asignaría (1-10). En modo edición, las estrellas que estaban en el rating previo
  pero quedarían fuera de la nueva selección se muestran en un amarillo apagado (`rgba(245,197,24, 0.22)`).
- **Click**: fija la calificación seleccionada. Las estrellas quedan pintadas hasta ese valor. Las
  que estaban apagadas (deselected) vuelven al gris default.
- **Al quitar el mouse** sin clickear, el widget vuelve a la calificación fijada (o a 0 si no hay).
- Debajo del widget, label que refleja el valor actual: `5/10`, o vacío si no hay selección.
- Solo se aceptan valores enteros.

### Validaciones

| Regla                           | Comportamiento                                                                                |
| ------------------------------- | --------------------------------------------------------------------------------------------- |
| Publicar sin calificación       | Mensaje de error inline: "Debés seleccionar una calificación." Botón Publicar se deshabilita. |
| Editar y dejar sin calificación | Ídem. No se permite quitar la calificación y dejar solo texto.                                |
| Texto > 1000 caracteres         | El textarea limita la entrada. Contador muestra `N/1000`.                                     |

### Post-acción

| Acción                | Efecto                                                                                                                       |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Publicar / Actualizar | Cierra modal, toast "Reseña publicada." / "Reseña actualizada.". La sección de reseñas en la ficha se actualiza al instante. |
| Eliminar              | Cierra modal, toast "Reseña eliminada.". Tu reseña desaparece de la ficha. El botón "Calificar" vuelve a mostrarse.          |
| Cancelar              | Cierra modal sin cambios.                                                                                                    |

### Estados del modal

| Estado              | Qué se muestra                                  |
| ------------------- | ----------------------------------------------- |
| Default             | Modal limpio (publicar) o precargado (editar).  |
| Error de validación | Mensaje inline en rojo.                         |
| Submitting          | Spinner en el botón de acción, campos disabled. |

### Modales como componentes

Los tres modales comparten estructura base (overlay + caja centrada). Se definen como variants
de un componente "Modal" en Figma:

- **ModalForm**: título + campos + Cancelar/Acción (Publicar y Editar).
- **ModalConfirm**: título + mensaje + Cancelar/Confirmar (Eliminar). Botón Confirmar en rojo (danger).

---

## 5e. Sección Listas (CU-009, CU-012)

> Las listas son personales. Las predeterminadas (Favoritos, Pendientes, Vistas) se crean automáticamente al registrarse y no pueden renombrarse, eliminarse ni reordenarse.
> Las listas personalizadas se gestionan con modales dedicados y se reordenan con drag & drop.

### Vista General de Listas

```
┌─────────────────────────────────────────────────────────────────┐
│  [FilmAI]  Inicio  Buscar  [Listas]                [Avatar]     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Listas                                                          │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐│
│  │  Favoritos       │  │  Pendientes      │  │  Vistas          ││
│  │  12 películas     │  │  5 películas     │  │  28 películas    ││
│  │  ┌──┐┌──┐┌──┐   │  │  ┌──┐┌──┐┌──┐  │  │  ┌──┐┌──┐┌──┐  ││
│  │  └──┘└──┘└──┘   │  │  └──┘└──┘└──┘  │  │  └──┘└──┘└──┘  ││
│  │  [Predeterminada]│  │  [Predeterminada]│  │  [Predeterminada]││
│  └──────────────────┘  └──────────────────┘  └──────────────────┘│
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐│
│  │  Sci-Fi        ⋮  │  │  Maratón finde ⋮  │  │  ┌────────────┐ ││
│  │  8 películas      │  │  3 películas     │  │  │     +      │ ││
│  │  ┌──┐┌──┐┌──┐   │  │  ┌──┐┌──┐       │  │  │            │ ││
│  │  └──┘└──┘└──┘   │  │  └──┘└──┘       │  │  │ Crear nueva│ ││
│  │                  │  │                  │  │  │   lista    │ ││
│  └──────────────────┘  └──────────────────┘  │  └────────────┘ ││
│                                               └──────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

#### Breadcrumb

| Vista                  | Breadcrumb                         |
| ---------------------- | ---------------------------------- |
| Listas (vista general) | Listas                             |
| Detalle de lista       | Listas > {nombre lista}            |
| Ficha desde lista      | Listas > {nombre lista} > {título} |

#### ListCard

- **Nombre**: texto, máx 80 chars visibles con truncado en 2 líneas.
- **Cantidad de items**: "N películas" / "N series" / "N items" (genérico si hay mezcla).
- **Mini preview**: 3 posters solapados en thumbnail (32×48px). Si la lista tiene menos de 3 items, se muestran los que haya. Si está vacía, se muestra un placeholder gris.
- **Badge**: "Predeterminada" en listas del sistema. Color gris neutro, esquina superior izquierda.
- **Menú contextual** (`⋮` vertical, esquina superior derecha): solo en listas personalizadas. Click → dropdown: Renombrar / Eliminar. Visible siempre, no solo en hover.
- **Comportamiento**: click en la card → navega al detalle de la lista.

#### Orden y reordenamiento

1. **Predeterminadas fijas**: primera fila, orden inmutable: Favoritos → Pendientes → Vistas. No se arrastran ni se mueven. No tienen menú.
2. **Personalizadas**: ordenadas por fecha de creación (más reciente al final). El usuario puede reordenarlas con **drag & drop**: al arrastrar una card, las demás se desplazan para hacer lugar (animación de transición). El nuevo orden se persiste en BD.

#### Card "Agregar" (esqueleto)

- Mismo tamaño y proporción que una ListCard (se integra en la grilla).
- Apariencia de esqueleto: borde sutil, fondo más claro que las cards reales, icono `+` centrado, texto "Crear nueva lista" debajo.
- Siempre al final del grid (última posición entre las personalizadas; si no hay personalizadas, primera celda de la segunda fila).
- No se puede arrastrar ni reordenar.
- Click → abre modal de creación.

#### Layout y responsive

| Breakpoint        | Columnas |
| ----------------- | -------- |
| Desktop (≥1440px) | 3        |
| Tablet (≥768px)   | 2        |
| Mobile (<768px)   | 1        |

#### Estados

| Estado        | Qué se muestra                                                                                                        |
| ------------- | --------------------------------------------------------------------------------------------------------------------- |
| Loading       | 3-6 skeletons de ListCard (rectángulo con placeholder de miniaturas).                                                 |
| Normal        | Grid de ListCards (predeterminadas + personalizadas + card esqueleto "Agregar").                                      |
| Empty parcial | Las 3 predeterminadas siempre existen. Si no hay personalizadas, la card esqueleto aparece en la primera celda libre. |
| Error         | Ilustración + "No se pudieron cargar las listas." + botón Reintentar.                                                 |

---

### Detalle de Lista

```
┌─────────────────────────────────────────────────────────────────┐
│  [FilmAI]  Inicio  Buscar  [Listas]                [Avatar]     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Listas > Sci-Fi                                 ⋮              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│  │ poster  │ │ poster  │ │ poster  │ │ poster  │ │ poster  │   │
│  │         │ │         │ │         │ │         │ │         │   │
│  │ Título  │ │ Título  │ │ Título  │ │ Título  │ │ Título  │   │
│  │ 2024    │ │ 2023    │ │ 2024    │ │ 2023    │ │ 2024    │   │
│  │     ✕   │ │     ✕   │ │     ✕   │ │     ✕   │ │     ✕   │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘   │
│                                                                  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐                            │
│  │ poster  │ │ poster  │ │ poster  │                            │
│  │         │ │         │ │         │                            │
│  │ Título  │ │ Título  │ │ Título  │                            │
│  │ 2024    │ │ 2023    │ │ 2024    │                            │
│  │     ✕   │ │     ✕   │ │     ✕   │                            │
│  └─────────┘ └─────────┘ └─────────┘                            │
│                                                                  │
│  (scroll vertical — carga más resultados al hacer scroll)         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Header de la lista

- **Nombre de la lista**: título de sección (heading).
- **Menú de acciones** (`⋮` vertical): solo en listas personalizadas. Dropdown: Renombrar / Eliminar.
- **Listas predeterminadas**: no muestran menú de acciones sobre la lista en sí. Solo se pueden quitar ítems individuales.

#### Grid de items

- **5 columnas desktop → 3 tablet → 2 mobile**.
- Cada **MediaCard** tiene un botón `✕` en la esquina superior derecha, visible solo en hover. Click → modal de confirmación para quitar el ítem.
- Click en la card → navega a Ficha de detalle (misma pantalla de la sección 5c). El breadcrumb se extiende a: `Listas > {nombre lista} > {título}`.
- **Scroll vertical**: sin paginación. Se cargan más resultados a medida que el usuario hace scroll.

#### Estados

| Estado  | Qué se muestra                                                                          |
| ------- | --------------------------------------------------------------------------------------- |
| Loading | Skeleton grid de MediaCards (5×2 filas).                                                |
| Normal  | Grid de items con scroll vertical.                                                      |
| Empty   | Ilustración + "Esta lista no contiene elementos." + botón "Explorar" (navega a Buscar). |
| Error   | Mensaje + botón Reintentar.                                                             |

---

### Modales de Gestión de Listas

Comparten la misma estructura base de modal (overlay + caja centrada de 480px).

#### Crear lista

| Trigger         | Botón "Crear nueva lista" en vista general.                                                                                    |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **Título**      | Crear nueva lista                                                                                                              |
| **Campo**       | Text input: "Nombre de la lista" (placeholder). Máx 80 caracteres alfanuméricos.                                               |
| **Validación**  | Nombre vacío: "El nombre no puede estar vacío." Nombre duplicado: "Ya tenés una lista con ese nombre." Mensaje inline en rojo. |
| **Botones**     | Cancelar / Crear                                                                                                               |
| **Post-acción** | Cierra modal, aparece nueva ListCard, toast "Lista creada."                                                                    |

#### Renombrar lista

| Trigger         | Opción "Renombrar" del menú `⋮` de una ListCard personalizada o del header en detalle.          |
| --------------- | ----------------------------------------------------------------------------------------------- |
| **Título**      | Renombrar lista                                                                                 |
| **Campo**       | Text input precargado con el nombre actual. Mismas reglas que Crear.                            |
| **Validación**  | Igual que Crear.                                                                                |
| **Botones**     | Cancelar / Guardar                                                                              |
| **Post-acción** | Cierra modal, se actualiza nombre en todos los lugares donde aparece, toast "Lista renombrada." |

#### Eliminar lista

| Trigger         | Opción "Eliminar" del menú `⋮`.                                              |
| --------------- | ---------------------------------------------------------------------------- |
| **Título**      | ¿Eliminar lista?                                                             |
| **Cuerpo**      | "Esta acción no se puede deshacer. Todos los ítems de la lista se perderán." |
| **Botones**     | Cancelar / Eliminar (botón danger, rojo).                                    |
| **Post-acción** | Cierra modal, desaparece ListCard, toast "Lista eliminada."                  |

#### Quitar ítem de lista

| Trigger         | Botón `✕` en MediaCard (detalle de lista).                            |
| --------------- | --------------------------------------------------------------------- |
| **Título**      | "¿Quitar "{título}" de {nombre lista}?"                               |
| **Cuerpo**      | —                                                                     |
| **Botones**     | Cancelar / Quitar                                                     |
| **Post-acción** | Cierra modal, desaparece la MediaCard del grid, toast "Ítem quitado." |

#### Responsive de modales

| Breakpoint       | Ancho del modal |
| ---------------- | --------------- |
| Desktop (≥768px) | 480px           |
| Mobile (<768px)  | 95vw, centrado  |

---

## 5f. Autenticación (CU-001, CU-002, CU-003)

> Login y Registro comparten la misma caja centrada. La transición entre ambos es inmediata: el contenido del form se reemplaza, el logo y el layout exterior permanecen fijos.

### Login

```
┌──────────────────────────────────────────┐
│                                          │
│               FilmAI                     │
│                                          │
│         Iniciar sesión                   │
│                                          │
│  Email o nombre de usuario               │
│  ┌──────────────────────────────────┐    │
│  └──────────────────────────────────┘    │
│                                          │
│  Contraseña                              │
│  ┌──────────────────────────────────┐    │
│  │                          [👁]    │    │
│  └──────────────────────────────────┘    │
│                                          │
│  ¿Olvidaste tu contraseña?              │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │      Iniciar sesión             │    │
│  └──────────────────────────────────┘    │
│                                          │
│  ────────── o ──────────                 │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │  G   Continuar con Google        │    │
│  └──────────────────────────────────┘    │
│                                          │
│  ¿No tenés cuenta? Registrate           │
│                                          │
└──────────────────────────────────────────┘
```

| Elemento                      | Comportamiento                                                                                                                                                                                 |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Campo principal**           | Acepta email o nombre de usuario. Label: "Email o nombre de usuario".                                                                                                                          |
| **Toggle contraseña**         | Ícono 👁 para mostrar/ocultar.                                                                                                                                                                  |
| **¿Olvidaste tu contraseña?** | Click → modal con campo de email + botón "Enviar enlace". Toast: "Te enviamos un email con instrucciones para restablecer tu contraseña." (mismo mensaje tanto si el email existe como si no). |
| **Google**                    | Botón secundario con logo de G. Inicia flujo OAuth.                                                                                                                                            |
| **"Registrate"**              | Reemplaza el form con el de Registro (transición del contenido, sin recargar).                                                                                                                 |
| **Error**                     | Mensaje inline: "Email, usuario o contraseña incorrectos." (genérico).                                                                                                                         |
| **Éxito**                     | Redirect al Home.                                                                                                                                                                              |

---

### Registro

```
┌──────────────────────────────────────────┐
│               FilmAI                     │
│         Crear cuenta                     │
│                                          │
│  Nombre                                  │
│  ┌──────────────────────────────────┐    │
│  └──────────────────────────────────┘    │
│  Apellido                                │
│  ┌──────────────────────────────────┐    │
│  └──────────────────────────────────┘    │
│  Nombre de usuario                       │
│  ┌──────────────────────────────────┐    │
│  └──────────────────────────────────┘    │
│    De 5 a 25 caracteres alfanuméricos   │
│  Email                                   │
│  ┌──────────────────────────────────┐    │
│  └──────────────────────────────────┘    │
│  Fecha de nacimiento                     │
│  ┌──────────────────────────────────┐    │
│  │ aaaa-mm-dd               [📅]   │    │
│  └──────────────────────────────────┘    │
│    Debés tener al menos 13 años         │
│  Género                                  │
│  ┌──────────────────────────────────┐    │
│  │ Seleccionar...              ▾    │    │
│  └──────────────────────────────────┘    │
│  Contraseña                              │
│  ┌──────────────────────────────────┐    │
│  │                          [👁]    │    │
│  └──────────────────────────────────┘    │
│    8-20 caracteres · 1 mayúscula ·      │
│    1 minúscula · 1 número · 1 especial  │
│    (@ # $ % & * !)                       │
│  Confirmar contraseña                    │
│  ┌──────────────────────────────────┐    │
│  │                          [👁]    │    │
│  └──────────────────────────────────┘    │
│  ┌──────────────────────────────────┐    │
│  │        Crear cuenta              │    │
│  └──────────────────────────────────┘    │
│  ────────── o ──────────                 │
│  ┌──────────────────────────────────┐    │
│  │  G   Registrarse con Google      │    │
│  └──────────────────────────────────┘    │
│  ¿Ya tenés cuenta? Iniciar sesión       │
└──────────────────────────────────────────┘
```

#### Campos y validaciones (según CU-001)

| Campo                | Restricción                                                                                     |
| -------------------- | ----------------------------------------------------------------------------------------------- |
| Nombre               | Solo letras, máx 50 caracteres. Obligatorio.                                                    |
| Apellido             | Solo letras, máx 50 caracteres. Obligatorio.                                                    |
| Nombre de usuario    | Alfanumérico, 5–25 caracteres, único. Validación inline de disponibilidad.                      |
| Email                | Formato válido usuario@dominio.com. Obligatorio.                                                |
| Fecha de nacimiento  | Selector de fecha nativo (`type="date"`), no futura, ≥13 años.                                  |
| Género               | Dropdown: Masculino / Femenino / No especificar.                                                |
| Contraseña           | 8-20 caracteres, al menos 1 mayúscula, 1 minúscula, 1 dígito y 1 carácter especial (`@#$%&*!`). |
| Confirmar contraseña | Debe coincidir con Contraseña.                                                                  |

#### Google OAuth

- Botón "Registrarse con Google" inicia flujo OAuth.
- Si la cuenta de Google ya está asociada → inicia sesión directamente.
- Si no → completa nombre, apellido y email desde Google; el usuario debe completar los campos faltantes (nombre de usuario, fecha de nacimiento, género) en una pantalla intermedia.
- El usuario nuevo creado con Google queda en estado **activa** directamente (Google ya verificó el correo; no requiere confirmación por email).
- La contraseña no aplica para cuentas Google (se omite del form).

#### Estados

| Estado                    | Comportamiento                                                                          |
| ------------------------- | --------------------------------------------------------------------------------------- |
| Error de validación       | Mensaje inline debajo de cada campo. Botón "Crear cuenta" deshabilitado hasta corregir. |
| Email o usuario duplicado | Error de servidor: "El email o nombre de usuario ya está registrado."                   |
| Registro exitoso          | Redirect a Confirmación de cuenta.                                                      |

---

### Confirmación de cuenta

```
┌──────────────────────────────────────────┐
│                                          │
│               FilmAI                     │
│                                          │
│                  ✉️                      │
│                                          │
│        Revisá tu bandeja de entrada      │
│                                          │
│  Te enviamos un enlace de confirmación   │
│  a marco@email.com. Si no lo encontrás,  │
│  revisá la carpeta de spam.              │
│                                          │
│          [Reenviar enlace]              │
│                                          │
│  ──────────────────────────────          │
│                                          │
│  ¿Ya confirmaste? Iniciar sesión        │
│                                          │
└──────────────────────────────────────────┘
```

- Se accede tras registro exitoso o desde el link del email. El token es el de confirmación de email de **allauth** (no un JWT propio); la ruta la resuelve el backend y Next.js muestra éxito/error.
- **Token válido**: toast "Cuenta confirmada." → redirect al Login.
- **Reenviar enlace**: toast "Enlace reenviado." Rate-limit: 1 cada 60 segundos.
- **"Iniciar sesión"**: vuelve al Login.

---

## 5g. Perfil (CU-005, CU-006) — Edición inline

> Una sola pantalla con dos modos: visualización y edición. Al clickear "Editar perfil" los campos pasan a inputs. El email es siempre solo lectura.

### Modo visualización

```
┌──────────────────────────────────────────┐
│  Perfil                                  │
│                                          │
│            ┌────────────┐                │
│            │  (avatar)   │               │
│            │   96×96     │               │
│            └────────────┘                │
│          Marco López                     │
│         @marco_lopez                     │
│       marco@email.com                    │
│    Miembro desde marzo 2025              │
│                                          │
│        [ ✏️ Editar perfil ]             │
│                                          │
└──────────────────────────────────────────┘
```

### Modo edición

```
┌──────────────────────────────────────────┐
│  Perfil                                  │
│                                          │
│            ┌────────────┐                │
│            │  (avatar)   │               │
│            │ [Cambiar]  │ ← hover        │
│            └────────────┘                │
│                                          │
│  Nombre                                  │
│  ┌──────────────────────────────────┐    │
│  │ Marco                            │    │
│  └──────────────────────────────────┘    │
│                                          │
│  Apellido                                │
│  ┌──────────────────────────────────┐    │
│  │ López                            │    │
│  └──────────────────────────────────┘    │
│                                          │
│  Nombre de usuario                       │
│  ┌──────────────────────────────────┐    │
│  │ @ │ marco_lopez                  │    │
│  └──────────────────────────────────┘    │
│    Disponible                           │
│                                          │
│  Email                                   │
│  marco@email.com                         │
│  ───────────────────────────────────     │
│                                          │
│  ──── Cambiar contraseña ────            │
│  (sección colapsable)                    │
│    Contraseña actual                     │
│    ┌────────────────────────────────┐    │
│    └────────────────────────────────┘    │
│    Contraseña nueva                      │
│    ┌────────────────────────────────┐    │
│    └────────────────────────────────┘    │
│    Repetir contraseña nueva              │
│    ┌────────────────────────────────┐    │
│    └────────────────────────────────┘    │
│                                          │
│    [Cancelar]    [Guardar cambios]       │
└──────────────────────────────────────────┘
```

| Elemento                | Comportamiento                                                                                                                      |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **Nombre**              | Solo letras, máximo 50 caracteres. Obligatorio.                                                                                     |
| **Apellido**            | Solo letras, máximo 50 caracteres. Obligatorio.                                                                                     |
| **Email**               | Solo lectura. Cambiarlo requiere re-verificación (fuera de scope).                                                                  |
| **Cambiar contraseña**  | Sección colapsable con link "¿Cambiar contraseña?". Se expande solo si el usuario clickea. Si no se toca, no se valida ni se envía. |
| **Validación @usuario** | Feedback inline: "Disponible" (verde) / "No disponible" (rojo).                                                                     |
| **Cancelar**            | Revierte a modo visualización sin guardar.                                                                                          |
| **Guardar**             | Actualiza datos. Si se cambió contraseña, valida actual + coincidencia de nueva. Toast: "Perfil actualizado."                       |
| **Avatar**              | Hover → overlay "Cambiar foto". Click → file picker. Preview instantánea.                                                           |
| **Breadcrumb**          | Perfil                                                                                                                              |

---

## 5h. Pantallas de Error

### 404 — Página no encontrada

```
┌──────────────────────────────────────────┐
│  [FilmAI]  Inicio  Buscar  Listas  [A]    │
├──────────────────────────────────────────┤
│                                          │
│                  🔍                      │
│        Página no encontrada              │
│  La página que buscás no existe o fue    │
│  movida.                                 │
│           [Volver al inicio]             │
└──────────────────────────────────────────┘
```

- Navbar siempre visible.
- Breadcrumb vacío.
- CTA primario al Home.

### Error genérico (500 / timeout)

```
┌──────────────────────────────────────────┐
│  [FilmAI]  Inicio  Buscar  Listas  [A]    │
├──────────────────────────────────────────┤
│                                          │
│                   ⚠️                     │
│         Algo salió mal                   │
│  Ocurrió un error inesperado. Intentá    │
│  de nuevo en unos minutos.               │
│           [Reintentar]                   │
└──────────────────────────────────────────┘
```

- Misma estructura: navbar + ilustración + mensaje + botón.
- "Reintentar" recarga la página actual.

---

## 5i. Mis reseñas

> Listado cronológico de todas las reseñas publicadas por el usuario. Se accede desde el dropdown del avatar.

```
┌──────────────────────────────────────────┐
│  [FilmAI]  Inicio  Buscar  Listas  [A]    │
├──────────────────────────────────────────┤
│  Mis reseñas                             │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │ 🎬 Breaking Bad      9/10          │  │
│  │ 12/03/2025              [✏️] [🗑️]  │  │
│  │ "Una obra maestra de principio     │  │
│  │  a fin. El desarrollo de Walter    │  │
│  │  White es simplemente perfecto..." │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │ 🎬 Interstellar       8/10         │  │
│  │ 28/02/2025              [✏️] [🗑️]  │  │
│  │ "Visualmente impresionante..."     │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ...scroll vertical...                   │
└──────────────────────────────────────────┘
```

### ReviewCard

| Elemento           | Comportamiento                                                |
| ------------------ | ------------------------------------------------------------- |
| **Título + badge** | Clickeable → ficha de detalle. Muestra tipo (Película/Serie). |
| **Rating**         | Formato `X/10`.                                               |
| **Fecha**          | Fecha de publicación.                                         |
| **Texto**          | Truncado a 3 líneas, expandible con "[leer más ▾]".           |
| **✏️ Editar**      | Abre modal de editar reseña (mismo de sección 5d).            |
| **🗑️ Eliminar**    | Abre modal de eliminar reseña ("¿Eliminar reseña?").          |

- **Orden**: más reciente primero.
- **Scroll vertical** sin paginación.

### Estados

| Estado  | Qué se muestra                                                                     |
| ------- | ---------------------------------------------------------------------------------- |
| Loading | Skeleton de ReviewCards.                                                           |
| Normal  | Listado cronológico.                                                               |
| Empty   | Ilustración + "Todavía no escribiste ninguna reseña." + botón "Explorar" → Buscar. |
| Error   | Mensaje + botón Reintentar.                                                        |

---

## 5j. Preferencias

> Se accede desde el dropdown del avatar. Configuración de cuenta y apariencia.

```
┌──────────────────────────────────────────┐
│  [FilmAI]  Inicio  Buscar  Listas  [A]    │
├──────────────────────────────────────────┤
│  Preferencias                            │
│                                          │
│  ──── Apariencia ────                    │
│                                          │
│  Tema                                    │
│  ┌──────────────────────────────────┐    │
│  │ ● Oscuro    ○ Claro              │    │
│  └──────────────────────────────────┘    │
│                                          │
│  ──── Privacidad ────                    │
│                                          │
│  Perfil público                          │
│  ┌──────────────────────────────────┐    │
│  │ [■■■■■■■■■■■■■■■■■■■■■■■■■] ●  │    │
│  └──────────────────────────────────┘    │
│  Tus reseñas son visibles para otros    │
│  usuarios.                              │
│                                          │
│  ──── Notificaciones ────                │
│                                          │
│  Recomendaciones semanales     [●━━━]    │
│  Reseñas en tus listas         [●━━━]    │
│  Novedades de FilmAI           [━━━━]    │
│                                          │
│  ──── Cuenta ────                        │
│                                          │
│  [Dar de baja cuenta]                    │
│                                          │
└──────────────────────────────────────────┘
```

### Secciones

| Sección            | Controles                           | Descripción                                                                                                                                                     |
| ------------------ | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Apariencia**     | Toggle Oscuro / Claro               | Cambio inmediato de tema. Default: Oscuro.                                                                                                                      |
| **Privacidad**     | Switch on/off para "Perfil público" | Cuando está apagado, tus reseñas no aparecen en las fichas de detalle ni tus listas son visibles para otros.                                                    |
| **Notificaciones** | 3 switches independientes           | Recomendaciones semanales (email con sugerencias), Reseñas en tus listas (email cuando alguien reseña algo tuyo), Novedades de FilmAI (changelog).              |
| **Cuenta**         | Botón danger "Dar de baja cuenta"   | Abre modal de confirmación: "¿Dar de baja tu cuenta? Esta acción es permanente. Perderás tus listas, reseñas y calificaciones." Botones Cancelar / Dar de baja. |

### Breadcrumb

`Preferencias`

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
- **Breadcrumb**: obligatorio en ficha de detalle (reemplaza botón Volver).

### 6.4 Cards

- **MediaCard**: poster (2:3), título, año, rating TMDB. Hover: escala 1.02 + sombra.
- **ListCard**: nombre, cantidad de items, mini preview de 3-4 posters.
- **ReviewCard**: avatar, @usuario, rating (formato `X/10`, sin estrellas), fecha, texto, acciones (editar/eliminar).
- **CastCard**: para reparto y equipo (director + actores). Sin fotos. Colapsable si hay más de N elementos.

### 6.5 Feedback

- **Rating stars**: widget interactivo 1-10 estrellas (solo en modal de calificar). Valores enteros. Fuera del modal se muestra formato `X/10`.
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

- **Panel de administrador**: CU-016 y CU-017 operan a través del Django Admin nativo (rol administrador con `is_staff`/`is_superuser`), sin UI dedicada.
- **Chats múltiples**: el modelo de clases los contempla, pero los CU solo definen la conversación activa en el chatbot principal.

---

## 9. Recomendaciones para Figma

1. Crear un **Design System file** separado con componentes, estilos de color y tipografía.
2. **Auto layout** en todos los componentes para iteración rápida.
3. **Variants** con propiedad "State" (default, hover, focus, disabled, error, loading, empty).
4. Priorizar diseño por sprints:
   - **Sprint 1**: Login, Registro, Home, Buscar (panel overlay). ← **Login y Registro implementados; Home y Buscar diseñados pero aún no implementados en el frontend** (08/09/2026)
   - **Sprint 2**: Ficha de detalle, Modales de reseña, Listas.
   - **Sprint 3**: Perfil, Modificar perfil, Pantallas de error/estado vacío, Confirmación de cuenta.
5. Prototipar flujos críticos:
   - Registro completo (registro → email → confirmación → login → home).
   - Publicar reseña (catálogo → detalle → modal → calificar → publicar → ver en perfil).
   - Chatbot (FAB → escribir → enviar → loading → respuesta / cancelar).

---

## 10. Pantallas Definidas

> Estado al 08/09/2026: la marca `[x]` indica que la pantalla está **definida/diseñada** en este documento, no necesariamente implementada. Implementadas hoy: Login, Registro, confirmación/restablecimiento y completado de Google. El resto (Home, Buscar, Detalle, Listas, Perfil, Mis reseñas, Preferencias, errores) queda como diseño aprobado para implementar según `docs/05_Plan_de_Desarrollo.md`.

- [x] Home — Sección 5
- [x] Buscar (panel overlay) — Sección 5b
- [x] Ficha de detalle — Sección 5c
- [x] Modales de reseña — Sección 5d
- [x] Listas — Sección 5e
- [x] Login / Registro / Confirmación de cuenta — Sección 5f
- [x] Perfil (edición inline) — Sección 5g
- [x] Pantallas de error (404, error genérico) — Sección 5h
- [x] Mis reseñas — Sección 5i
- [x] Preferencias — Sección 5j

---

## 11. Accesibilidad (WCAG 2.1 AA)

El sistema debe cumplir con los lineamientos de accesibilidad WCAG 2.1 nivel AA. A continuación se detallan los requisitos específicos para cada componente:

### 11.1 Requisitos generales

- **Contraste de color:** Relación mínima de 4.5:1 para texto normal y 3:1 para texto grande (≥18px o ≥14px negrita) contra el fondo. Verificar los colores del tema oscuro (`#e0e0e0` sobre `#0d0d14`) y del tema claro.
- **Navegación por teclado:** Todos los elementos interactivos deben ser accesibles y operables mediante teclado (Tab, Shift+Tab, Enter, Escape, flechas). El orden de foco debe seguir una secuencia lógica.
- **Foco visible:** Todos los elementos interactivos deben mostrar un indicador de foco visible (anillo de 2px en color de acento) al recibir el foco del teclado.
- **Etiquetas y textos alternativos:** Todos los campos de formulario deben tener `<label>` asociado. Las imágenes informativas (posters, avatares) deben tener texto alternativo (`alt`). Las imágenes decorativas deben tener `alt=""`.
- **Encabezados jerárquicos:** Usar una estructura de encabezados lógica (h1 → h2 → h3) sin saltar niveles.
- **Texto redimensionable:** El contenido debe ser legible con zoom del 200% sin pérdida de funcionalidad.

### 11.2 Componentes específicos

- **Modal:** Al abrirse, el foco debe moverse al primer elemento interactivo del modal. Al cerrarse, el foco debe retornar al elemento que lo disparó. La tecla Escape cierra el modal. El contenido detrás del modal debe estar oculto para lectores de pantalla (`aria-hidden`).
- **Star Widget:** Las estrellas deben ser navegables con teclado (flechas izquierda/derecha para seleccionar, Enter para confirmar). Cada estrella debe tener un `aria-label` con su valor (ej: "4 de 10 estrellas").
- **Drag & Drop de listas:** El reordenamiento de listas personalizadas debe ofrecer una alternativa accesible sin mouse: botones "Mover arriba" y "Mover abajo" visibles al recibir foco, o menú contextual con opciones "Mover arriba / Mover abajo". El drag & drop sigue siendo la interacción principal para usuarios de mouse/touch.
- **Toggle switches:** Deben tener roles ARIA apropiados (`role="switch"`, `aria-checked`).
- **FAB del chatbot:** Debe ser accesible por teclado y tener un `aria-label="Abrir chatbot de recomendaciones"`.
- **Toast/Notificaciones:** Deben usar `role="alert"` o `aria-live="polite"` para ser anunciadas por lectores de pantalla.

### 11.3 Validación

- Los formularios deben mostrar mensajes de error asociados mediante `aria-describedby`.
- Los campos con error deben tener el atributo `aria-invalid="true"`.
- Los mensajes de error deben ser visibles y comunicados por lectores de pantalla.
