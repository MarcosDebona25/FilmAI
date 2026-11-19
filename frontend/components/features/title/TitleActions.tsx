"use client";

import { useRef, useState } from "react";
import { ChevronDown, CirclePlus, Heart, ListPlus } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { ListsMenu } from "@/components/features/title/ListsMenu";
import { mensajeDeError } from "@/components/features/title/RatingDialog";
import { ICONO_ESTADO, StatusMenu } from "@/components/features/title/StatusMenu";
import { StarIcon } from "@/components/ui/StarIcon";
import { apiFetch } from "@/lib/api";
import type { MediaType } from "@/lib/catalog";
import { actualizarLista, conItem, sinItem, type ListaFicha } from "@/lib/title-lists";
import { estadoDe, type Estado } from "@/lib/title-status";
import { cn } from "@/lib/utils";

/**
 * Acciones de la ficha (canvas): calificar, Favorite, el botón de estado
 * (Watchlist, Watching o Watched) y «Add to list». Favorite y las listas
 * propias llaman a la API de listas de L-01 y devuelven las listas actualizadas
 * con `onListasChange`. El estado lo cambia quien llama (`onCambiarEstado`),
 * porque su toast con Undo también lo usa la calificación.
 */
export function TitleActions({
  titulo,
  idTmdb,
  tipo,
  listas,
  onListasChange,
  miCalificacion,
  onRate,
  onCambiarEstado,
  cambiandoEstado = false,
}: {
  titulo: string;
  idTmdb: number;
  tipo: MediaType;
  listas: ListaFicha[];
  onListasChange: (listas: ListaFicha[]) => void;
  miCalificacion: { id: number; valor: number; texto: string | null } | null;
  onRate: () => void;
  /** Pone el estado elegido, o `null` para quitarlo. */
  onCambiarEstado: (estado: Estado | null) => void;
  /** Hay un cambio de estado en camino: no se abre otro hasta que responda. */
  cambiandoEstado?: boolean;
}) {
  const t = useTranslations();
  const [pendiente, setPendiente] = useState<number | null>(null);
  const [menu, setMenu] = useState(false);
  const [menuEstado, setMenuEstado] = useState(false);
  const disparador = useRef<HTMLButtonElement>(null);
  const disparadorEstado = useRef<HTMLButtonElement>(null);
  const estado = estadoDe(listas);
  const IconoEstado = estado ? ICONO_ESTADO[estado] : CirclePlus;
  const porClave = (clave: ListaFicha["clave"]) => listas.find((lista) => lista.clave === clave);
  const propias = listas.filter((lista) => lista.tipo === "personalizada");

  function aviso(lista: ListaFicha, agregada: boolean) {
    if (lista.clave === "favoritos")
      return t(agregada ? "title.feedback.favoriteAdded" : "title.feedback.favoriteRemoved");
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
        await agregar(lista);
        toast.success(aviso(lista, true));
      }
    } catch (motivo) {
      toast.error(mensajeDeError(motivo));
    } finally {
      setPendiente(null);
    }
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

  function cerrarMenuEstado() {
    setMenuEstado(false);
    disparadorEstado.current?.focus();
  }

  function elegirEstado(elegido: Estado | null) {
    cerrarMenuEstado();
    if (elegido !== estado) onCambiarEstado(elegido);
  }

  // Mismo botón en las dos medidas: en celular, ícono arriba y texto chico;
  // en escritorio, fila con ícono y texto.
  const accion = (activa: boolean) =>
    cn(
      "flex h-16 cursor-pointer flex-col items-center justify-center gap-1 rounded-lg text-xs focus-visible:outline-2 focus-visible:outline-ring disabled:cursor-wait md:h-12 md:flex-row md:gap-2 md:px-4 md:text-[0.9375rem]",
      activa
        ? "bg-raised-2 font-semibold text-foreground"
        : "font-medium text-fg-2 shadow-[inset_0_0_0_1px_var(--line)] hover:text-foreground"
    );

  const favorita = porClave("favoritos");

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
          "flex h-[3.25rem] cursor-pointer items-center justify-center gap-2 rounded-lg px-5 text-[1.0625rem] font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring md:h-12 md:text-base",
          miCalificacion
            ? "bg-raised-2 text-foreground"
            : "bg-primary text-primary-foreground md:px-[1.375rem]"
        )}
      >
        <StarIcon
          className={cn(
            "size-5 md:size-[1.125rem]",
            miCalificacion ? "fill-primary" : "fill-current"
          )}
        />
        {miCalificacion ? (
          <>
            <span className="md:hidden">{t("title.rating.yourRating")}</span>
            <span className="tabular-nums">{miCalificacion.valor}</span>
          </>
        ) : (
          t("common.rating.rate")
        )}
      </button>

      <div className="grid grid-cols-3 gap-2 md:contents">
        {favorita && (
          <button
            type="button"
            aria-pressed={favorita.contiene}
            disabled={pendiente === favorita.id}
            onClick={() => alternar(favorita)}
            className={accion(favorita.contiene)}
          >
            {/* Activo, el corazón se rellena con el color de acento (como la estrella de la nota). */}
            <Heart
              aria-hidden="true"
              className={cn(
                "size-5 md:size-[1.125rem]",
                favorita.contiene && "fill-current text-primary"
              )}
            />
            {t("common.media.favorite")}
          </button>
        )}
        {listas.some((lista) => lista.clave === "viendo") && (
          <div className="md:relative">
            <button
              ref={disparadorEstado}
              type="button"
              aria-label={
                estado
                  ? t("title.status.current", { status: t(`enums.defaultList.${estado}`) })
                  : undefined
              }
              aria-haspopup="menu"
              aria-expanded={menuEstado}
              aria-disabled={cambiandoEstado || undefined}
              onClick={() => !cambiandoEstado && setMenuEstado(!menuEstado)}
              className={cn(accion(estado !== null), "w-full md:pr-3.5")}
            >
              <IconoEstado
                aria-hidden="true"
                className={cn(
                  "size-5 md:size-[1.125rem]",
                  estado && estado !== "vistas" && "text-primary"
                )}
              />
              {estado ? t(`enums.defaultList.${estado}`) : t("title.status.label")}
              <ChevronDown aria-hidden="true" className="hidden size-4 md:block" />
            </button>
            {menuEstado && (
              <StatusMenu
                titulo={titulo}
                estado={estado}
                onElegir={elegirEstado}
                onClose={cerrarMenuEstado}
              />
            )}
          </div>
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
            <ListPlus aria-hidden="true" className="size-5 md:size-[1.125rem]" />
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
    </div>
  );
}
