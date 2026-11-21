"use client";

import Image from "next/image";
import Link from "next/link";
import { useState, type CSSProperties, type HTMLAttributes, type Ref } from "react";
import { Clock, Eye, GripVertical, Heart, Play } from "lucide-react";
import { useTranslations } from "next-intl";

import { ListActionsMenu, type AccionLista } from "@/components/features/lists/ListActionsMenu";
import { tmdbImage, tmdbLoader } from "@/lib/catalog";
import { useFormats } from "@/lib/format";
import { esPredeterminada, type ClaveLista, type ResumenLista } from "@/lib/lists";
import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

const ICONOS = {
  favoritos: Heart,
  pendientes: Clock,
  viendo: Play,
  vistas: Eye,
} as const satisfies Record<ClaveLista, unknown>;

/** Hasta cuántos pósters caben apilados (escritorio, con 4 columnas; en celular se ven 3). */
const MAX_POSTERS = 4;
const POSTERS_CELULAR = 3;

/** El nombre a mostrar: las predeterminadas se nombran por su clave, no por el texto guardado. */
export function useNombreLista() {
  const t = useTranslations("enums.defaultList");
  return (lista: Pick<ResumenLista, "nombre" | "clave">) =>
    lista.clave ? t(lista.clave) : lista.nombre;
}

function Poster({ ruta, className }: { ruta: string; className: string }) {
  const [fallo, setFallo] = useState(false);
  const url = tmdbImage(ruta, "w185");
  // `block` va primero: si `className` trae `hidden`, tiene que ganarle.
  if (!url || fallo)
    return <span className={cn("block bg-raised-2", className)} aria-hidden="true" />;
  return (
    <span className={cn("relative block overflow-hidden bg-raised-2", className)}>
      <Image
        loader={tmdbLoader}
        src={url}
        alt=""
        fill
        sizes="64px"
        draggable={false}
        className="object-cover"
        onError={() => setFallo(true)}
      />
    </span>
  );
}

/**
 * Tarjeta de una lista (canvas «Lists»). Las predeterminadas van sin menú ni
 * manija; las personalizadas llevan la manija de arrastre (escritorio) y ⋯.
 * `arrastre` trae lo que dnd-kit necesita: los `listeners` de la tarjeta
 * entera (pulsación larga en celular), la manija con sus atributos y el estilo.
 */
export function ListCard({
  lista,
  acciones,
  arrastre,
}: {
  lista: ResumenLista;
  acciones?: AccionLista[];
  arrastre?: {
    refNodo: Ref<HTMLLIElement>;
    refManija: Ref<HTMLButtonElement>;
    atributos: HTMLAttributes<HTMLButtonElement>;
    escuchas: HTMLAttributes<HTMLLIElement> | undefined;
    estilo: CSSProperties;
    arrastrando: boolean;
  };
}) {
  const t = useTranslations();
  const formats = useFormats();
  const nombreDe = useNombreLista();
  const nombre = nombreDe(lista);
  const predeterminada = esPredeterminada(lista);
  const Icono = lista.clave ? ICONOS[lista.clave] : null;
  const posters = lista.preview_posters.slice(0, MAX_POSTERS);
  // «N more» cuenta lo que no se ve: en celular hay un póster menos a la vista.
  const masAlla = lista.cantidad_items - posters.length;
  const masAllaCelular = lista.cantidad_items - Math.min(posters.length, POSTERS_CELULAR);

  return (
    <li
      ref={arrastre?.refNodo}
      style={arrastre?.estilo}
      {...arrastre?.escuchas}
      // En celular la pulsación larga abre el menú del sistema (vista previa del
      // enlace, «copiar»): se anula para que solo arranque el arrastre.
      onContextMenu={(event) => {
        if (window.matchMedia?.("(pointer: coarse)").matches) event.preventDefault();
      }}
      className={cn(
        "relative list-none",
        !predeterminada && "[-webkit-touch-callout:none] select-none",
        arrastre?.arrastrando && "z-20"
      )}
    >
      <article
        className={cn(
          "relative flex h-full flex-col gap-3 rounded-2xl bg-raised p-4 shadow-[inset_0_0_0_1px_var(--line)] transition-shadow md:gap-3.5 md:p-6",
          arrastre?.arrastrando &&
            "shadow-[0_20px_50px_rgb(0_0_0/0.55),inset_0_0_0_1px_var(--fg-3)]"
        )}
      >
        {/* Fila del nombre (diseño 5E). La fuente se fija acá y todo lo de adentro
            usa `em`, así el ⋯ y la manija se centran contra la primera línea. */}
        <div className="relative flex items-center gap-2 text-[1.5rem] leading-[1.05] md:text-[1.75rem]">
          <h2
            className={cn(
              "flex min-w-0 flex-1 items-center gap-2.5 font-display text-[1em] leading-[inherit]",
              // Reserva el ancho del ⋯ (que sobresale 8 px en celular, 16 en escritorio).
              !predeterminada && acciones && "pr-9 md:pr-8"
            )}
          >
            {Icono && <Icono aria-hidden="true" className="size-6 flex-none text-primary" />}
            <Link
              href={routes.list(lista.id)}
              title={nombre}
              draggable={false}
              className="min-w-0 truncate text-foreground no-underline after:absolute after:inset-0 after:rounded-2xl focus-visible:outline-none focus-visible:after:outline-2 focus-visible:after:outline-ring"
            >
              {nombre}
            </Link>
          </h2>
          {predeterminada ? (
            <span className="inline-flex h-7 flex-none items-center rounded-full bg-raised-2 px-3 text-[0.8125rem] leading-none font-semibold text-fg-2">
              {t("common.lists.defaultBadge")}
            </span>
          ) : (
            acciones && (
              // Sin `z-index` a propósito: con `z-10` esta caja encerraba la capa
              // que cierra el menú (z-40) y el menú (z-50), que hacia afuera
              // valían 10 y quedaban debajo de la navbar fija (z-30). `absolute`
              // ya queda encima del enlace que cubre la tarjeta: los dos están
              // posicionados y este viene después en el HTML.
              <ListActionsMenu
                className="absolute -right-2 top-[calc(0.525em-1.375rem)] md:-right-4"
                etiqueta={t("lists.card.actionsLabel", { listName: nombre })}
                titulo={nombre}
                acciones={acciones}
              />
            )
          )}
          {!predeterminada && arrastre && (
            // Manija apilada justo debajo del ⋯, en la esquina: no le quita ancho
            // al nombre. Solo escritorio; en celular se arrastra con pulsación larga.
            <button
              ref={arrastre.refManija}
              type="button"
              data-drag-handle=""
              aria-label={t("common.lists.reorderLabel")}
              {...arrastre.atributos}
              className="absolute top-[calc(0.525em+1.375rem)] -right-4 z-10 hidden size-11 cursor-grab touch-none place-items-center rounded-full text-fg-3 hover:bg-raised-2 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring active:cursor-grabbing md:grid"
            >
              <GripVertical aria-hidden="true" className="size-5" />
            </button>
          )}
        </div>
        <p
          className={cn(
            "truncate text-[0.9375rem] whitespace-nowrap text-fg-2",
            // En escritorio la manija ocupa la esquina a la altura del conteo.
            !predeterminada && arrastre && "md:pr-8"
          )}
        >
          {t("lists.count.items", { count: lista.cantidad_items })}
          {lista.cantidad_items > 0 && (
            <>
              {" · "}
              {t("lists.count.movies", { count: lista.cantidad_peliculas })}
              {" · "}
              {t("lists.count.tvShows", { count: lista.cantidad_series })}
            </>
          )}
        </p>

        {posters.length > 0 ? (
          <div className="flex items-center" aria-hidden="true">
            {posters.map((ruta, indice) => (
              <Poster
                key={`${ruta}-${indice}`}
                ruta={ruta}
                className={cn(
                  "h-[4.125rem] w-11 flex-none rounded-md shadow-[0_0_0_2px_var(--raised)] md:h-24 md:w-16",
                  indice > 0 && "-ml-3 md:-ml-4",
                  indice >= POSTERS_CELULAR && "hidden md:block"
                )}
              />
            ))}
            {masAllaCelular > 0 && (
              <span className="ml-3 text-[0.8125rem] font-semibold text-fg-3 md:hidden">
                {t("lists.card.overflowCount", { count: formats.number(masAllaCelular) })}
              </span>
            )}
            {masAlla > 0 && (
              <span className="ml-3 hidden text-[0.8125rem] font-semibold text-fg-3 md:inline">
                {t("lists.card.overflowCount", { count: formats.number(masAlla) })}
              </span>
            )}
          </div>
        ) : (
          <div
            aria-hidden="true"
            className="h-[4.125rem] rounded-md border border-dashed border-line md:h-24"
          />
        )}
      </article>
    </li>
  );
}
