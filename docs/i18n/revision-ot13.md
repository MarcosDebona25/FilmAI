# OT-13: borrador para revisión

Estado: preparado el 08/10/2026, **sin aprobación editorial**. No se crearon
catálogos, código ni tests. OT-11 y OT-12 se consultaron como borradores;
cuando se integren habrá que comprobar otra vez códigos y claves.

La propuesta está en `copia-propuesta.csv`: 65 errores públicos del borrador
OT-11, 9 respuestas exitosas, un respaldo desconocido, una variante de espera,
8 textos del selector, 6 mensajes específicos de campo y el asunto de reenvío.
Cada fila queda `pendiente_aprobacion`. La aprobación debe cubrir ambos idiomas,
los argumentos y el significado, además de las seis dudas de curaduría.

## Reglas de la propuesta

- ES usa voseo y EN usa las equivalencias del glosario de OT-10.
- Los nombres de idioma se muestran como `English` y `Español` en ambos locales.
- Parámetros numéricos obligatorios usan los nombres de OT-11. No se imprimen
  IDs de avatar, opciones internas, atributos del modelo ni nombres de campos.
- `errors.codes.throttled` no promete una espera desconocida;
  `throttledWithWait` es una variante editorial, no un código de backend.
  El helper convierte `retry_after_seconds` a `retryAfterSeconds` solo cuando existe.
- `unknown` es respaldo del frontend. Los textos de éxito usan la misma búsqueda
  por clave, sin obligar a que un éxito lleve el sobre de errores.
- `csrf_ready` tiene traducción por paridad; no se propone mostrar un toast de CSRF.
- `already_confirmed` evita afirmar que una cuenta dada de baja está activa:
  el código actual también incluye enlaces que no pueden reactivarla.
- El éxito de baja conserva exactamente el texto actual del backend. Las filas
  de baja 487–491 y 568 del CSV original no se modifican.
- El asunto de reenvío conserva el de registro; la tabla no aporta otro asunto.
  Correos: 24 horas para confirmar, 1 hora para restablecer; el contacto ya
  aprobado es `contacto@filmai.com`.

## Seis dudas: propuestas sin editar la curaduría

Los diseños Claude nuevos no están versionados. La tabla no permite verificar
por sí sola el uso de estas seis entradas; el wireframe anterior aporta solo
contexto. Ninguna propuesta se considera aprobada ni habilitada para siembra.

| ID | Propuesta para aprobación | Evidencia y límite |
| --- | --- | --- |
| 214 | ES: «Se eliminarán tu calificación de {rating}/10 y tu reseña, y {title} dejará de estar en Vistas. La calificación y la reseña no se pueden recuperar; podés volver a agregarla a Vistas cuando quieras.» EN: “Your {rating}/10 rating and review will be deleted, and {title} will be removed from Watched. The rating and review can’t be recovered; you can add it to Watched again whenever you want.” | `frontend/components/ReviewModal.tsx:169` y doc 03:51 confirman los efectos. Falta confirmar que esta variante del diseño es la de quitar con calificación y reseña. |
| 215 | ES: «Se eliminará tu calificación de {rating}/10 y {title} dejará de estar en Vistas. La calificación no se puede recuperar; podés volver a agregarla a Vistas cuando quieras.» EN: “Your {rating}/10 rating will be deleted, and {title} will be removed from Watched. The rating can’t be recovered; you can add it to Watched again whenever you want.” | Mismas fuentes para quitar con calificación sin texto. Si el diseño representa solo quitar pertenencia sin calificación, esta copia no corresponde; hay que confirmarlo. |
| 320 | ES: «Calificación {rating}/10». EN: “Rating {rating}/10”. | Doc 04:1055 fija enteros 1–10 y formato X/10 en visualización. No confirma si este rótulo de filtro representa una nota exacta, mínima o un rango; propuesta pendiente de ese contexto. |
| 355 | Usar la clave completa existente `auth.password.label`: «Contraseña» / “Password”, si es la etiqueta del campo; excluir la fila duplicada. | Doc 04:619 y frontend login usan etiqueta completa. La palabra minúscula compartida en la tabla podría ser un fragmento de otra frase; no se puede asignar ese uso sin el diseño. |
| 448 | Excluir del catálogo si es metadato de locale; si es un selector visible, usar nombres «Español» / “English” y las claves del selector, conservando `es`/`en` como valores de máquina. | El origen solo contiene `es` / `en` en detalle de lista. No hay evidencia de control visible. Confirmar antes de reclasificar. |
| 535 | Conservar «Incluye» / “Includes” como rótulo autónomo si encabeza recursos; si precede texto continuo, reemplazarlo por la frase completa del diseño. | La tabla lo ubica en acceso admin, pero no enumera contenido. `backend/filmai/urls.py:32-56` confirma esquema y Swagger existentes; no demuestra la estructura ni todos los recursos del nuevo diseño. |

## Checklist de continuación

- [ ] Confirmar integración y versión final de OT-11/OT-12.
- [ ] Aprobar las 91 filas de copia nueva ES/EN y revisar la curaduría completa.
- [ ] Resolver las seis filas con contexto del diseño o decisión explícita.
- [ ] Actualizar el CSV de curaduría conservando columnas originales inmutables.
- [ ] Validar sintaxis ICU con el analizador usado en OT-12 y paridad de argumentos.
- [ ] Revisar specs `i18n-core` y `emails`; quitar su estado de borrador solo al aprobar.
- [ ] Root registra decisión/traspaso, actualiza graphify y coordina formato/CI.

Se proponen dos unidades de revisión menores de 400 líneas: specs juntas;
y copia CSV más esta revisión. Esta entrega preserva trabajo preparado,
sin cerrar OT-13 ni iniciar implementación de F2.
