"use client";

import { useEffect, useRef } from "react";
import { useTranslations } from "next-intl";

import {
  MS_SIMPLE,
  cerrarAvisoEstado,
  mostrarAvisoEstado,
} from "@/components/features/title/StatusToast";
import type { ItemLista } from "@/lib/lists";
import { guardarEstado } from "@/lib/title-status";
import { useEscritorio } from "@/lib/use-escritorio";

/**
 * Los cambios de estado desde las tarjetas de la lista Watching: marcar como
 * terminada (pasa a Watched), quitar de Watching y calificar. Sigue la receta
 * de la ficha (`useEstadoFicha`): la tarjeta sale al instante, `PUT
 * /api/lists/status/` confirma, y el toast con Undo (el mismo `StatusToast`)
 * devuelve el título a su posición anterior. Si el servidor falla, la tarjeta
 * vuelve y el toast de error no trae Undo.
 *
 * La lista pone la grilla: `sacar` quita la tarjeta y dice en qué lugar estaba;
 * `meter` la vuelve a poner ahí. Un cambio a la vez, así el Undo de uno nunca
 * pisa al siguiente. Al salir de la página el toast se cierra y el cambio queda.
 */
export function useEstadoViendo({
  sacar,
  meter,
  onCalificar,
}: {
  sacar: (item: ItemLista) => number;
  meter: (item: ItemLista, indice: number) => void;
  /** «Rate it» del toast. */
  onCalificar: (item: ItemLista) => void;
}) {
  const t = useTranslations();
  const escritorio = useEscritorio();
  const enCurso = useRef(false);

  useEffect(() => cerrarAvisoEstado, []);

  const titulo = (item: ItemLista) =>
    item.disponible ? item.titulo : t("common.content.titleUnavailable");

  function mostrarConUndo(
    item: ItemLista,
    indice: number,
    texto: string,
    { conCalificar = false } = {}
  ) {
    mostrarAvisoEstado({
      texto,
      // En celular «Rate it» vive en la hoja del ⋯, no en el toast.
      accion:
        conCalificar && escritorio
          ? {
              etiqueta: t("lists.watching.rateItToast"),
              onClick: () => {
                cerrarAvisoEstado();
                onCalificar(item);
              },
            }
          : undefined,
      deshacer: {
        etiqueta: t("title.status.undo"),
        anuncio: t("title.status.undoAnnouncement", { message: texto, seconds: 6 }),
        onClick: () => void deshacer(item, indice),
      },
    });
  }

  function avisarError() {
    mostrarAvisoEstado({ texto: t("title.status.error"), tono: "error", ms: 6000 });
  }

  /** Vuelve el título a Watching y a su lugar en la grilla. */
  async function deshacer(item: ItemLista, indice: number) {
    if (enCurso.current) return;
    enCurso.current = true;
    try {
      const respuesta = await guardarEstado({
        idTmdb: item.id_tmdb,
        tipo: item.tipo,
        estado: "viendo",
      });
      // Volver a anotarlo crea un ingreso nuevo: la tarjeta toma su `item_id`.
      const nuevo = respuesta.listas.find((lista) => lista.clave === "viendo")?.item_id;
      meter({ ...item, item_id: nuevo ?? item.item_id }, indice);
      cerrarAvisoEstado();
    } catch {
      avisarError();
    } finally {
      enCurso.current = false;
    }
  }

  /** «Mark as finished» (`vistas`) y «Remove from Watching» (`null`). */
  async function mover(item: ItemLista, estado: "vistas" | null) {
    if (enCurso.current) return;
    enCurso.current = true;
    const indice = sacar(item);
    try {
      await guardarEstado({ idTmdb: item.id_tmdb, tipo: item.tipo, estado });
      mostrarConUndo(
        item,
        indice,
        estado
          ? t("lists.watching.movedToWatched", { title: titulo(item) })
          : t("lists.watching.removed", { title: titulo(item) }),
        { conCalificar: estado === "vistas" }
      );
    } catch {
      meter(item, indice);
      avisarError();
    } finally {
      enCurso.current = false;
    }
  }

  /**
   * Calificar desde Watching: el servidor la pasó a Watched, y la tarjeta sale
   * con el mismo aviso de la ficha («Rated ★ 8 · Moved to Watched») y su Undo.
   */
  function avisarCalificadaYMovida(item: ItemLista, valor: number) {
    const indice = sacar(item);
    mostrarConUndo(item, indice, t("title.status.ratedAndMoved", { rating: String(valor) }));
  }

  /** Calificar un título que ya estaba en Watched (o con reseña): solo avisa. */
  function avisarCalificada({ valor, conResena }: { valor: number; conResena: boolean }) {
    mostrarAvisoEstado({
      texto: conResena
        ? t("title.feedback.ratingReviewPublished")
        : t("title.status.rated", { rating: String(valor) }),
      ms: conResena ? 4000 : MS_SIMPLE,
    });
  }

  return { mover, avisarCalificadaYMovida, avisarCalificada };
}
