"use client";

import { useRef } from "react";
import { useTranslations } from "next-intl";

import { MS_SIMPLE, mostrarAvisoEstado } from "@/components/features/title/StatusToast";
import { useAvisoGuardado } from "@/components/features/title/use-aviso-guardado";
import type { MediaType } from "@/lib/catalog";
import type { ListaFicha } from "@/lib/title-lists";
import { conEstado, estadoDe, fechaDeEstado, guardarEstado, type Estado } from "@/lib/title-status";

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
  const { guardando, empezar, terminar } = useAvisoGuardado();
  // El Undo se pulsa mucho después de crear el toast: tiene que ver las listas
  // de ahora, no las de ese momento.
  const actuales = useRef(listas);
  actuales.current = listas;
  // Red de seguridad además de `guardando`: dos toques en el mismo tick podrían
  // ver el estado de React todavía sin actualizar.
  const enCurso = useRef(false);

  const nombre = (estado: Estado) => t(`enums.defaultList.${estado}`);

  async function cambiar(
    estado: Estado | null,
    {
      deshacer = true,
      fechaAgregado = null,
    }: { deshacer?: boolean; fechaAgregado?: string | null } = {}
  ) {
    // Un cambio a la vez: el Undo de uno no puede pisar al siguiente.
    if (enCurso.current) return;
    const previas = actuales.current;
    if (estadoDe(previas) === estado) return;
    enCurso.current = true;
    empezar();
    onListasChange(conEstado(previas, estado));
    try {
      const respuesta = await guardarEstado({ idTmdb, tipo, estado, fechaAgregado });
      onListasChange(respuesta.listas);
      terminar();
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
              onClick: () =>
                void cambiar(anterior, {
                  deshacer: false,
                  fechaAgregado: fechaDeEstado(previas, anterior),
                }),
            }
          : undefined,
      });
    } catch {
      onListasChange(previas);
      terminar();
      mostrarAvisoEstado({ texto: t("title.status.error"), tono: "error", ms: 6000 });
    } finally {
      enCurso.current = false;
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
    // Con un cambio de estado en camino, el aviso de la nota lo pisaría: el
    // botón Rate está deshabilitado mientras se guarda, así que esto es la red
    // de seguridad para un toque que igual llegue.
    if (enCurso.current) return;
    // El servidor ya la movió a Watched; las listas de la ficha se recargan
    // después. Hasta entonces se muestran así, para que un Undo inmediato (o con
    // la recarga fallida) vea que hay algo que deshacer.
    const previas = actuales.current;
    onListasChange(conEstado(previas, "vistas"));
    if (previo === "pendientes" || previo === "viendo") {
      const texto = t("title.status.ratedAndMoved", { rating: String(valor) });
      mostrarAvisoEstado({
        texto,
        deshacer: {
          etiqueta: t("title.status.undo"),
          anuncio: t("title.status.undoAnnouncement", { message: texto, seconds: 6 }),
          onClick: () =>
            void cambiar(previo, {
              deshacer: false,
              fechaAgregado: fechaDeEstado(previas, previo),
            }),
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

  return { cambiar, guardando, avisarCalificacion };
}
