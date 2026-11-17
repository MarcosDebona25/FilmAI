"use client";

import { useRef, useState } from "react";
import { useTranslations } from "next-intl";

import { MS_SIMPLE, mostrarAvisoEstado } from "@/components/features/title/StatusToast";
import type { MediaType } from "@/lib/catalog";
import type { ListaFicha } from "@/lib/title-lists";
import { conEstado, estadoDe, guardarEstado, type Estado } from "@/lib/title-status";

/**
 * El estado único del título en la ficha (Watchlist, Watching, Watched o
 * ninguno): el cambio optimista, el toast con Undo y la vuelta atrás si el
 * servidor falla. Lo comparten el botón de estado y la calificación, que mueve
 * a Watched y tiene su propio Undo. La ficha pone las listas; aquí solo se
 * cambian y se avisa.
 */
export function useEstadoFicha({
  idTmdb,
  tipo,
  listas,
  onListasChange,
}: {
  idTmdb: number;
  tipo: MediaType;
  listas: ListaFicha[];
  onListasChange: (listas: ListaFicha[]) => void;
}) {
  const t = useTranslations();
  const [pendiente, setPendiente] = useState(false);
  // El Undo se pulsa mucho después de crear el toast: tiene que ver las listas
  // de ahora, no las de ese momento.
  const actuales = useRef(listas);
  actuales.current = listas;
  const enCurso = useRef(false);

  const nombre = (estado: Estado) => t(`enums.defaultList.${estado}`);

  async function cambiar(estado: Estado | null, { deshacer = true } = {}) {
    // Un cambio a la vez: el Undo de uno no puede pisar al siguiente.
    if (enCurso.current) return;
    const previas = actuales.current;
    if (estadoDe(previas) === estado) return;
    enCurso.current = true;
    setPendiente(true);
    onListasChange(conEstado(previas, estado));
    try {
      const respuesta = await guardarEstado({ idTmdb, tipo, estado });
      onListasChange(respuesta.listas);
      const anterior = respuesta.estado_anterior;
      mostrarAvisoEstado({
        texto: !estado
          ? t("title.status.removed")
          : deshacer
            ? t("title.status.movedTo", { status: nombre(estado) })
            : t("title.status.backTo", { status: nombre(estado) }),
        ms: deshacer ? undefined : MS_SIMPLE,
        deshacer: deshacer
          ? {
              etiqueta: t("title.status.undo"),
              anuncio: t("title.status.undoAnnouncement", {
                message: !estado
                  ? t("title.status.removed")
                  : t("title.status.movedTo", { status: nombre(estado) }),
                seconds: 6,
              }),
              onClick: () => void cambiar(anterior, { deshacer: false }),
            }
          : undefined,
      });
    } catch {
      onListasChange(previas);
      mostrarAvisoEstado({ texto: t("title.status.error"), tono: "error", ms: 6000 });
    } finally {
      enCurso.current = false;
      setPendiente(false);
    }
  }

  /**
   * Avisa de una calificación nueva. El servidor la mueve a Watched desde
   * cualquier estado; solo si venía de Watchlist o Watching hay Undo, que
   * devuelve ese estado y conserva la nota.
   */
  function avisarCalificacion({
    valor,
    previo,
    conResena,
  }: {
    valor: number;
    previo: Estado | null;
    conResena: boolean;
  }) {
    if (previo === "pendientes" || previo === "viendo") {
      const texto = t("title.status.ratedAndMoved", { rating: String(valor) });
      mostrarAvisoEstado({
        texto,
        deshacer: {
          etiqueta: t("title.status.undo"),
          anuncio: t("title.status.undoAnnouncement", { message: texto, seconds: 6 }),
          onClick: () => void cambiar(previo, { deshacer: false }),
        },
      });
    } else {
      mostrarAvisoEstado({
        texto: conResena
          ? t("title.feedback.ratingReviewPublished")
          : t("title.status.rated", { rating: String(valor) }),
        ms: conResena ? 4000 : MS_SIMPLE,
      });
    }
  }

  return { cambiar, pendiente, avisarCalificacion };
}
