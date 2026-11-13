"use client";

import { useEffect, useId, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Ellipsis, Film, Lock, PenLine } from "lucide-react";
import { useTranslations } from "next-intl";

import { DialogShell } from "@/components/features/title/DialogShell";
import { StarIcon } from "@/components/ui/StarIcon";
import { useFormats } from "@/lib/format";
import { tmdbImage, tmdbLoader } from "@/lib/catalog";
import { type MiResena } from "@/lib/reviews";
import { routes } from "@/lib/routes";
import { useDesborde } from "@/lib/use-desborde";
import { cn } from "@/lib/utils";

export type AccionResena = "editar" | "borrarTexto" | "quitar";

function Estrella({ className }: { className: string }) {
  return <StarIcon className={cn("shrink-0 fill-primary", className)} />;
}

/**
 * Una calificación de «Calificaciones y reseñas» (canvas): póster, título que
 * lleva a la ficha, nota, tipo y fecha, el texto recortado a tres líneas o
 * «Agregar reseña». En escritorio, «Editar» y el menú «Más acciones»; en
 * celular, un solo botón abre las tres acciones en una hoja.
 */
export function MyReviewItem({
  item,
  onAccion,
}: {
  item: MiResena;
  onAccion: (accion: AccionResena) => void;
}) {
  const t = useTranslations();
  const formats = useFormats();
  const tituloId = useId();
  const hojaTitulo = useId();
  const avisoId = useId();
  const hojaAvisoId = useId();
  const [desplegado, setDesplegado] = useState(false);
  const [textoRef, desborda] = useDesborde<HTMLParagraphElement>(desplegado, item.texto ?? "");
  const [posterFallido, setPosterFallido] = useState(false);
  const [menu, setMenu] = useState(false);
  const [hoja, setHoja] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const masRef = useRef<HTMLButtonElement>(null);
  const src = tmdbImage(item.poster, "w185");
  const href = routes.title(item.tipo, item.id_tmdb, "reviews");
  // Una lápida (TMDB ya no tiene el título) llega sin título ni póster: no hay
  // ficha a la que ir, pero la nota y el texto del usuario siguen y se pueden
  // borrar como siempre.
  const disponible = item.disponible;
  const titulo = disponible ? item.titulo : t("common.content.titleUnavailable");
  // La leyenda de la lápida ya viene en el idioma de la interfaz: el aviso de
  // `campos_en_ingles` habla del título de TMDB, que ahí no existe.
  const enIngles = disponible && item.campos_en_ingles?.includes("titulo") ? "en" : undefined;

  useEffect(() => {
    if (!menu) return;
    menuRef.current?.querySelector<HTMLElement>("[role='menuitem']")?.focus();
    function alClic(evento: MouseEvent) {
      const objetivo = evento.target as Node;
      if (!menuRef.current?.contains(objetivo) && !masRef.current?.contains(objetivo))
        setMenu(false);
    }
    function alApretar(evento: KeyboardEvent) {
      if (evento.key === "Escape") {
        setMenu(false);
        masRef.current?.focus();
      } else if (evento.key === "Tab") {
        setMenu(false);
      } else if (["ArrowDown", "ArrowUp", "Home", "End"].includes(evento.key)) {
        const items = Array.from(
          menuRef.current?.querySelectorAll<HTMLElement>("[role='menuitem']") ?? []
        );
        evento.preventDefault();
        const actual = items.indexOf(document.activeElement as HTMLElement);
        const siguiente =
          evento.key === "Home"
            ? 0
            : evento.key === "End"
              ? items.length - 1
              : evento.key === "ArrowDown"
                ? (actual + 1) % items.length
                : (actual - 1 + items.length) % items.length;
        items[siguiente]?.focus();
      }
    }
    document.addEventListener("mousedown", alClic);
    document.addEventListener("keydown", alApretar);
    return () => {
      document.removeEventListener("mousedown", alClic);
      document.removeEventListener("keydown", alApretar);
    };
  }, [menu]);

  // Moderada: el texto no se puede borrar (409 `review_moderated`). El ítem
  // queda a la vista pero inerte, y el aviso explica por qué.
  const moderada = item.moderada;

  function elegirDelMenu(accion: AccionResena) {
    if (accion === "borrarTexto" && moderada) return;
    // El foco vuelve al botón antes de abrir el diálogo: al cerrarse, el
    // diálogo lo devuelve ahí (el ítem del menú ya no existe).
    masRef.current?.focus();
    setMenu(false);
    onAccion(accion);
  }

  function elegirDeLaHoja(accion: AccionResena) {
    if (accion === "borrarTexto" && moderada) return;
    setHoja(false);
    onAccion(accion);
  }

  const itemMenu =
    "h-11 cursor-pointer rounded-lg px-3 text-left text-[0.9375rem] focus-visible:outline-2 focus-visible:outline-ring hover:bg-raised-2 focus:bg-raised-2";
  const itemHoja =
    "h-[3.25rem] cursor-pointer rounded-[0.625rem] px-3 text-left text-base focus-visible:outline-2 focus-visible:outline-ring";

  return (
    <li className="relative grid grid-cols-[3.5rem_minmax(0,1fr)_2.75rem] gap-3.5 border-t border-line py-5 md:grid-cols-[5rem_minmax(0,1fr)_auto] md:gap-6 md:py-7">
      <div className="relative h-[5.25rem] w-14 overflow-hidden rounded-md bg-raised-2 md:h-[7.5rem] md:w-20 md:rounded-lg">
        {src && !posterFallido ? (
          <Image
            loader={tmdbLoader}
            src={src}
            alt=""
            fill
            sizes="(min-width: 768px) 80px, 56px"
            className="object-cover"
            onError={() => setPosterFallido(true)}
          />
        ) : (
          <span className="grid h-full place-items-center text-fg-3">
            <Film aria-hidden="true" className="size-6" />
          </span>
        )}
      </div>

      <article aria-labelledby={tituloId} className="flex min-w-0 flex-col gap-1 md:gap-2">
        <h2
          id={tituloId}
          lang={enIngles}
          className="font-display text-2xl leading-none break-words md:text-[1.875rem]"
        >
          {disponible ? (
            <Link
              href={href}
              className="text-foreground no-underline hover:underline hover:underline-offset-4"
            >
              {item.titulo}
            </Link>
          ) : (
            <span className="text-fg-3">{titulo}</span>
          )}
        </h2>
        <p className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[0.8125rem] text-fg-3 md:gap-x-3 md:text-sm">
          <span className="inline-flex items-center gap-1 text-sm font-bold text-foreground tabular-nums md:gap-1.5 md:text-[0.9375rem]">
            <span className="sr-only">
              {t("reviews.card.ratingLabel", { rating: String(item.valor) })}
            </span>
            <Estrella className="size-[0.8125rem] md:size-[0.9375rem]" />
            <span aria-hidden="true">{item.valor}</span>
          </span>
          <span aria-hidden="true">·</span>
          <span>{t(item.tipo === "movie" ? "common.content.movie" : "common.content.tvShow")}</span>
          <span aria-hidden="true">·</span>
          <span>{t("reviews.card.ratedDate", { date: formats.date(item.fecha) })}</span>
        </p>
        {item.texto ? (
          <>
            <p
              ref={textoRef}
              className={cn(
                "mt-1 text-[0.9375rem] leading-[1.55] break-words whitespace-pre-wrap text-pretty md:text-base md:leading-[1.6]",
                !desplegado && "line-clamp-3"
              )}
            >
              {item.texto}
            </p>
            {moderada && (
              <p
                id={avisoId}
                className="flex items-start gap-1.5 text-[0.8125rem] text-fg-3 md:text-sm"
              >
                <Lock aria-hidden="true" className="mt-0.5 size-3.5 shrink-0" />
                {t("common.review.moderatedNotice")}
              </p>
            )}
            {(desborda || desplegado) && (
              <button
                type="button"
                aria-expanded={desplegado}
                onClick={() => setDesplegado(!desplegado)}
                className="h-11 cursor-pointer self-start px-1 text-sm font-semibold text-fg-2 md:h-9 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
              >
                {desplegado ? t("common.text.readLess") : t("common.text.readMore")}
              </button>
            )}
          </>
        ) : disponible ? (
          <Link
            href={href}
            aria-label={t("reviews.card.addReviewLabel", { title: item.titulo })}
            className="mt-1.5 flex h-12 items-center gap-2 rounded-[0.625rem] border-[1.5px] border-dashed border-line px-3.5 text-sm font-semibold text-fg-2 no-underline hover:text-foreground md:mt-1 md:h-14 md:gap-2.5 md:rounded-xl md:px-[1.125rem] md:text-[0.9375rem]"
          >
            <PenLine aria-hidden="true" className="size-4 md:size-[1.125rem]" />
            {t("common.review.add")}
          </Link>
        ) : null}
      </article>

      {/* Escritorio: «Editar» y el menú con lo que borra. */}
      <div className="hidden items-start gap-1.5 md:flex">
        <button
          type="button"
          onClick={() => onAccion("editar")}
          className="h-10 cursor-pointer rounded-lg px-3.5 text-sm font-semibold text-fg-2 shadow-[inset_0_0_0_1px_var(--line)] hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
        >
          {t("common.actions.edit")}
        </button>
        <button
          ref={masRef}
          type="button"
          aria-label={t("reviews.card.moreActionsLabel", { title: titulo })}
          aria-haspopup="menu"
          aria-expanded={menu}
          onClick={() => setMenu(!menu)}
          className="grid size-10 cursor-pointer place-items-center rounded-lg text-fg-2 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
        >
          <Ellipsis aria-hidden="true" className="size-5" />
        </button>
      </div>
      {menu && (
        <div
          ref={menuRef}
          role="menu"
          aria-label={t("reviews.card.moreActionsLabel", { title: titulo })}
          className="absolute top-[4.75rem] right-0 z-10 hidden w-[14.375rem] flex-col rounded-xl bg-raised p-1.5 shadow-[0_16px_40px_rgb(0_0_0/0.45),inset_0_0_0_1px_var(--line)] md:flex"
        >
          {item.texto && (
            <button
              type="button"
              role="menuitem"
              tabIndex={-1}
              aria-disabled={moderada || undefined}
              aria-describedby={moderada ? avisoId : undefined}
              onClick={() => elegirDelMenu("borrarTexto")}
              className={cn(
                itemMenu,
                "font-medium text-foreground",
                moderada && "cursor-not-allowed opacity-40"
              )}
            >
              {t("common.review.delete")}
            </button>
          )}
          <button
            type="button"
            role="menuitem"
            tabIndex={-1}
            onClick={() => elegirDelMenu("quitar")}
            className={cn(itemMenu, "font-semibold text-destructive")}
          >
            {t("common.rating.remove")}
          </button>
        </div>
      )}

      {/* Celular: un botón y las acciones en una hoja. */}
      <button
        type="button"
        aria-label={t("reviews.card.actionsLabel", { title: titulo })}
        aria-haspopup="dialog"
        onClick={() => setHoja(true)}
        className="grid size-11 cursor-pointer place-items-center text-fg-2 focus-visible:outline-2 focus-visible:outline-ring md:hidden"
      >
        <Ellipsis aria-hidden="true" className="size-5" />
      </button>
      {hoja && (
        <DialogShell labelledBy={hojaTitulo} onClose={() => setHoja(false)}>
          <div className="-my-2 flex flex-col">
            <h2
              id={hojaTitulo}
              className="mx-3 mb-1.5 flex items-center gap-1.5 text-[0.8125rem] font-normal text-fg-3"
            >
              <span lang={enIngles}>{titulo}</span>
              <span aria-hidden="true">·</span>
              <span className="inline-flex items-center gap-1 font-bold text-foreground tabular-nums">
                <span className="sr-only">
                  {t("reviews.card.ratingLabel", { rating: String(item.valor) })}
                </span>
                <Estrella className="size-3" />
                <span aria-hidden="true">{item.valor}</span>
              </span>
            </h2>
            {moderada && (
              <p id={hojaAvisoId} className="mx-3 mb-1.5 text-[0.8125rem] text-fg-3">
                {t("common.review.moderatedNotice")}
              </p>
            )}
            <button
              type="button"
              onClick={() => elegirDeLaHoja("editar")}
              className={cn(itemHoja, "font-medium text-foreground")}
            >
              {t("reviews.editor.title")}
            </button>
            {item.texto && (
              <button
                type="button"
                aria-disabled={moderada || undefined}
                aria-describedby={moderada ? hojaAvisoId : undefined}
                onClick={() => elegirDeLaHoja("borrarTexto")}
                className={cn(
                  itemHoja,
                  "font-medium text-foreground",
                  moderada && "cursor-not-allowed opacity-40"
                )}
              >
                {t("common.review.delete")}
              </button>
            )}
            <button
              type="button"
              onClick={() => elegirDeLaHoja("quitar")}
              className={cn(itemHoja, "font-semibold text-destructive")}
            >
              {t("common.rating.remove")}
            </button>
          </div>
        </DialogShell>
      )}
    </li>
  );
}
