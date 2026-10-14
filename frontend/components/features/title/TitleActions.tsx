"use client";

import { useRef, useState, type ReactNode } from "react";
import { ChevronDown, Clock, Eye, Heart, ListPlus } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { ConfirmDialog } from "@/components/features/title/ConfirmDialog";
import { ListsMenu } from "@/components/features/title/ListsMenu";
import { mensajeDeError } from "@/components/features/title/RatingDialog";
import { ApiError, apiFetch } from "@/lib/api";
import type { MediaType } from "@/lib/catalog";
import { actualizarLista, conItem, sinItem, type ListaFicha } from "@/lib/title-lists";
import { cn } from "@/lib/utils";

const ESTRELLA =
  "12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2";

// Toast de cada lista predeterminada al agregar y al quitar.
const AVISOS = {
  favoritos: ["title.feedback.favoriteAdded", "title.feedback.favoriteRemoved"],
  vistas: ["title.feedback.watchedAdded", "title.feedback.watchedRemoved"],
  pendientes: ["title.feedback.watchlistAdded", "title.feedback.watchlistRemoved"],
} as const;

/**
 * Acciones de la ficha (canvas): calificar, Favorite, Watched, Watchlist y
 * «Add to list». Llama a la API de listas de L-01 y devuelve las listas
 * actualizadas con `onListasChange`. Quitar de Vistas algo calificado responde
 * 409: pide confirmar y reintenta con `?borrar_calificacion=true`.
 */
export function TitleActions({
  titulo,
  idTmdb,
  tipo,
  listas,
  onListasChange,
  miCalificacion,
  onRate,
  onCalificacionBorrada,
}: {
  titulo: string;
  idTmdb: number;
  tipo: MediaType;
  listas: ListaFicha[];
  onListasChange: (listas: ListaFicha[]) => void;
  miCalificacion: { id: number; valor: number; texto: string | null } | null;
  onRate: () => void;
  onCalificacionBorrada: () => void;
}) {
  const t = useTranslations();
  const [pendiente, setPendiente] = useState<number | null>(null);
  const [menu, setMenu] = useState(false);
  const [confirmarVistas, setConfirmarVistas] = useState<ListaFicha | null>(null);
  const disparador = useRef<HTMLButtonElement>(null);
  const porClave = (clave: ListaFicha["clave"]) => listas.find((lista) => lista.clave === clave);
  const propias = listas.filter((lista) => lista.tipo === "personalizada");

  function aviso(lista: ListaFicha, agregada: boolean) {
    if (lista.clave) return t(AVISOS[lista.clave][agregada ? 0 : 1]);
    return t(agregada ? "title.lists.addedFeedback" : "title.lists.removedFeedback", {
      title: titulo,
      listName: lista.nombre,
    });
  }

  async function agregar(lista: ListaFicha, base = listas) {
    const item = await apiFetch<{ item_id: number }>(`/api/lists/${lista.id}/items/`, {
      method: "POST",
      body: { id_tmdb: idTmdb, tipo },
    });
    const nuevas = actualizarLista(base, lista.id, conItem(lista, item.item_id));
    onListasChange(nuevas);
    return nuevas;
  }

  async function alternar(lista: ListaFicha) {
    if (pendiente !== null) return;
    setPendiente(lista.id);
    try {
      if (lista.contiene && lista.item_id !== null) {
        await apiFetch(`/api/lists/${lista.id}/items/${lista.item_id}/`, { method: "DELETE" });
        onListasChange(actualizarLista(listas, lista.id, sinItem(lista)));
        toast.success(aviso(lista, false));
      } else {
        const nuevas = await agregar(lista);
        // Lo que ya viste deja de estar pendiente: el servidor la sacó de
        // Watchlist en la misma operación (regla del 14/10/2026).
        const pendientes = porClave("pendientes");
        if (lista.clave === "vistas" && pendientes?.contiene) {
          onListasChange(actualizarLista(nuevas, pendientes.id, sinItem(pendientes)));
          toast.success(t("title.feedback.watchedAddedFromWatchlist"));
        } else {
          toast.success(aviso(lista, true));
        }
      }
    } catch (motivo) {
      if (motivo instanceof ApiError && motivo.code === "rating_blocks_removal_from_watched") {
        setConfirmarVistas(lista);
      } else {
        toast.error(mensajeDeError(motivo));
      }
    } finally {
      setPendiente(null);
    }
  }

  async function quitarDeVistasConCalificacion(lista: ListaFicha) {
    await apiFetch(`/api/lists/${lista.id}/items/${lista.item_id}/?borrar_calificacion=true`, {
      method: "DELETE",
    });
    onListasChange(actualizarLista(listas, lista.id, sinItem(lista)));
    onCalificacionBorrada();
    setConfirmarVistas(null);
    toast.success(
      t(
        miCalificacion?.texto
          ? "title.feedback.ratingReviewDeleted"
          : "title.feedback.ratingDeleted"
      )
    );
  }

  async function crearYAgregar(nombre: string) {
    const nueva = await apiFetch<ListaFicha>("/api/lists/", { method: "POST", body: { nombre } });
    const lista = { ...nueva, contiene: false, item_id: null };
    await agregar(lista, [...listas, lista]);
    toast.success(t("title.lists.createdAddedFeedback", { listName: nueva.nombre, title: titulo }));
  }

  function cerrarMenu() {
    setMenu(false);
    disparador.current?.focus();
  }

  // Mismo botón en las dos medidas: en celular, ícono arriba y texto chico;
  // en escritorio, fila con ícono y texto.
  const accion = (activa: boolean) =>
    cn(
      "flex h-16 cursor-pointer flex-col items-center justify-center gap-1 rounded-lg text-xs focus-visible:outline-2 focus-visible:outline-ring disabled:cursor-wait md:h-12 md:flex-row md:gap-2 md:px-4 md:text-[15px]",
      activa
        ? "bg-raised-2 font-semibold text-foreground"
        : "font-medium text-fg-2 shadow-[inset_0_0_0_1px_var(--line)] hover:text-foreground"
    );

  // Función que devuelve el botón, no un componente: un componente definido
  // adentro de otro se vuelve a montar en cada redibujo y el botón pierde el foco.
  function toggle(
    clave: "favoritos" | "vistas" | "pendientes",
    icono: ReactNode,
    etiqueta: string
  ) {
    const lista = porClave(clave);
    if (!lista) return null;
    return (
      <button
        type="button"
        aria-pressed={lista.contiene}
        disabled={pendiente === lista.id}
        onClick={() => alternar(lista)}
        className={accion(lista.contiene)}
      >
        {icono}
        {etiqueta}
      </button>
    );
  }

  // Ícono de una lista predeterminada: activo, se rellena con el color de acento
  // (como la estrella de la nota propia). La pupila del ojo y las agujas del
  // reloj toman el color del fondo del botón para seguir viéndose.
  const icono = (clave: "favoritos" | "vistas" | "pendientes", recorte: string) =>
    cn(
      "size-5 md:size-[18px]",
      porClave(clave)?.contiene && cn("fill-current text-primary", recorte)
    );

  return (
    <div className="flex flex-col gap-3 md:flex-row md:flex-wrap md:items-center md:gap-2.5">
      <button
        type="button"
        onClick={onRate}
        aria-label={
          miCalificacion
            ? t.markup("title.rating.editSummary", {
                rating: String(miCalificacion.valor),
                edit: (chunks) => chunks,
              })
            : undefined
        }
        className={cn(
          "flex h-[52px] cursor-pointer items-center justify-center gap-2 rounded-lg px-5 text-[17px] font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring md:h-12 md:text-base",
          miCalificacion
            ? "bg-raised-2 text-foreground"
            : "bg-primary text-primary-foreground md:px-[22px]"
        )}
      >
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className={cn("size-5 md:size-[18px]", miCalificacion ? "fill-primary" : "fill-current")}
        >
          <polygon points={ESTRELLA} />
        </svg>
        {miCalificacion ? (
          <>
            <span className="md:hidden">{t("title.rating.yourRating")}</span>
            <span className="tabular-nums">{miCalificacion.valor}</span>
          </>
        ) : (
          t("common.rating.rate")
        )}
      </button>

      <div className="grid grid-cols-4 gap-2 md:contents">
        {toggle(
          "favoritos",
          <Heart aria-hidden="true" className={icono("favoritos", "")} />,
          t("common.media.favorite")
        )}
        {toggle(
          "vistas",
          <Eye
            aria-hidden="true"
            className={icono("vistas", "[&>circle]:fill-raised-2 [&>circle]:stroke-raised-2")}
          />,
          t("common.media.watched")
        )}
        {toggle(
          "pendientes",
          <Clock aria-hidden="true" className={icono("pendientes", "[&>path]:stroke-raised-2")} />,
          t("common.media.watchlist")
        )}
        <div className="md:relative">
          <button
            ref={disparador}
            type="button"
            aria-label={t("title.lists.addTitleLabel", { title: titulo })}
            aria-haspopup="dialog"
            aria-expanded={menu}
            onClick={() => setMenu(!menu)}
            className={cn(accion(false), "w-full md:pr-3.5")}
          >
            <ListPlus aria-hidden="true" className="size-5 md:size-[18px]" />
            <span className="md:hidden">{t("nav.main.lists")}</span>
            <span className="hidden md:inline">{t("common.lists.add")}</span>
            <ChevronDown aria-hidden="true" className="hidden size-4 md:block" />
          </button>
          {menu && (
            <ListsMenu
              titulo={titulo}
              listas={propias}
              pendiente={pendiente}
              onAlternar={alternar}
              onCrear={crearYAgregar}
              onClose={cerrarMenu}
            />
          )}
        </div>
      </div>

      {confirmarVistas && miCalificacion && (
        <ConfirmDialog
          titulo={t("title.watched.removeConfirmTitle")}
          descripcion={t(
            miCalificacion.texto
              ? "title.rating.removeBothDescription"
              : "title.rating.removeOnlyDescription",
            { title: titulo }
          )}
          preview={miCalificacion.texto}
          confirmar={t("title.watched.remove")}
          onConfirm={() => quitarDeVistasConCalificacion(confirmarVistas)}
          onCancel={() => setConfirmarVistas(null)}
        />
      )}
    </div>
  );
}
