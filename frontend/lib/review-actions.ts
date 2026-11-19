import { apiFetch } from "@/lib/api";
import { planEdicion, type MiCalificacion } from "@/lib/title";

/**
 * Las llamadas a la API para crear, editar y quitar una calificación (con su
 * reseña). Las comparten la ficha del título y «Calificaciones y reseñas».
 * Cada pantalla decide qué hacer con el resultado (su estado local, su foco y
 * qué se recarga); aquí solo se llama a la API y se dice qué cambió y qué aviso
 * corresponde.
 */

/** Claves de `title.feedback.*` que usan los avisos de estas acciones. */
export type ClaveAviso =
  | "ratingPublished"
  | "ratingReviewPublished"
  | "ratingUpdated"
  | "ratingReviewUpdated"
  | "reviewUpdated"
  | "reviewDeleted"
  | "ratingDeleted"
  | "ratingReviewDeleted";

/** Califica un título por primera vez (`POST /api/reviews/`). */
export async function crearCalificacion(datos: {
  idTmdb: number;
  tipo: string;
  valor: number;
  texto: string;
}) {
  const { idTmdb, tipo, valor, texto } = datos;
  const creada = await apiFetch<MiCalificacion>("/api/reviews/", {
    method: "POST",
    body: { id_tmdb: idTmdb, tipo, valor, ...(texto ? { texto } : {}) },
  });
  const aviso: ClaveAviso = texto ? "ratingReviewPublished" : "ratingPublished";
  return { creada, aviso };
}

export type ResultadoEdicion = {
  plan: ReturnType<typeof planEdicion>;
  /** Lo que respondió el `PUT`; `null` si no hubo cambios de nota ni de texto nuevo. */
  respuesta: Partial<MiCalificacion> | null;
  /** Aviso según lo que cambió; `null` si no cambió nada. */
  aviso: ClaveAviso | null;
};

/**
 * Edita una calificación. La API no acepta un texto vacío en el `PUT`: vaciar
 * una reseña es un `DELETE …/texto/` aparte (`planEdicion` lo decide).
 */
export async function editarCalificacion(
  previa: { id: number; valor: number; texto: string | null },
  valor: number,
  texto: string
): Promise<ResultadoEdicion> {
  const plan = planEdicion(previa, valor, texto);
  if (plan.borrarTexto) {
    await apiFetch(`/api/reviews/${previa.id}/texto/`, { method: "DELETE" });
  }
  let respuesta: Partial<MiCalificacion> | null = null;
  if (Object.keys(plan.cambios).length) {
    respuesta = await apiFetch<Partial<MiCalificacion>>(`/api/reviews/${previa.id}/`, {
      method: "PUT",
      body: plan.cambios,
    });
  }
  const nota = "valor" in plan.cambios;
  const textoCambio = "texto" in plan.cambios || plan.borrarTexto;
  let aviso: ClaveAviso | null = null;
  if (nota && textoCambio) aviso = "ratingReviewUpdated";
  else if (nota) aviso = "ratingUpdated";
  else if (plan.borrarTexto) aviso = "reviewDeleted";
  else if (textoCambio) aviso = "reviewUpdated";
  return { plan, respuesta, aviso };
}

/** Borra solo el texto de la reseña, la calificación queda (`DELETE …/texto/`). */
export async function borrarTextoDeResena(id: number) {
  await apiFetch(`/api/reviews/${id}/texto/`, { method: "DELETE" });
  const aviso: ClaveAviso = "reviewDeleted";
  return { aviso };
}

/** Quita la calificación y su reseña (`DELETE /api/reviews/{id}/`). */
export async function quitarCalificacion(previa: { id: number; texto: string | null }) {
  await apiFetch(`/api/reviews/${previa.id}/`, { method: "DELETE" });
  const aviso: ClaveAviso = previa.texto ? "ratingReviewDeleted" : "ratingDeleted";
  return { aviso };
}
