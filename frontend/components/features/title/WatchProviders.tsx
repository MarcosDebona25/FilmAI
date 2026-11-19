"use client";

import { useId, useRef, useState } from "react";
import Image from "next/image";
import { ChevronRight, ExternalLink, X } from "lucide-react";
import { useTranslations } from "next-intl";

import { DialogShell } from "@/components/features/title/DialogShell";
import { tmdbImage } from "@/lib/catalog";
import { useFormats } from "@/lib/format";
import type { Pedido } from "@/lib/use-catalog";
import type { Plataforma, Plataformas } from "@/lib/title";
import { cn } from "@/lib/utils";

const GRUPOS = [
  ["suscripcion", "stream"],
  ["gratis", "free"],
  ["alquiler", "rent"],
  ["compra", "buy"],
] as const;
/** Logos que se ven en la línea cerrada. */
const EN_LINEA = 4;
const JUSTWATCH = "https://www.justwatch.com";

function Logo({
  plataforma,
  size,
  decorativo = false,
}: {
  plataforma: Plataforma;
  size: number;
  decorativo?: boolean;
}) {
  const src = tmdbImage(plataforma.logo, "w92");
  // En rem: crece con la escala de la raíz en pantallas anchas (globals.css).
  const caja = { width: `${size / 16}rem`, height: `${size / 16}rem` };
  return src ? (
    <Image
      src={src}
      alt={decorativo ? "" : plataforma.nombre}
      title={decorativo ? undefined : plataforma.nombre}
      width={size}
      height={size}
      style={caja}
      unoptimized
      className="rounded-md bg-raised-2 object-cover"
    />
  ) : (
    // Sin logo: la inicial, para que la plataforma igual se distinga.
    <span
      role={decorativo ? undefined : "img"}
      aria-label={decorativo ? undefined : plataforma.nombre}
      title={decorativo ? undefined : plataforma.nombre}
      style={caja}
      className="grid place-items-center rounded-md bg-raised-2 text-xs font-semibold text-fg-2"
    >
      {plataforma.nombre.slice(0, 1)}
    </span>
  );
}

/**
 * «Dónde verla» en la ficha: una línea con los logos y la cantidad de
 * opciones en el país, que abre un diálogo (hoja desde abajo en celular) con
 * los grupos Stream / Free / Rent / Buy. TMDB no da enlaces directos por plataforma, así que los logos no son
 * enlaces: hay un solo enlace a TMDB. Cargando muestra un esqueleto; si el
 * pedido falla o no hay país, la sección no aparece (no es contenido crítico).
 */
export function WatchProviders({
  pedido,
  pais,
  className,
}: {
  pedido: Pedido<Plataformas>;
  pais: string | null;
  className?: string;
}) {
  const t = useTranslations("title.providers");
  const formats = useFormats();
  const tc = useTranslations("common.actions");
  const tituloId = useId();
  const [abierto, setAbierto] = useState(false);
  const linea = useRef<HTMLButtonElement>(null);

  if (!pais || pedido.status === "idle" || pedido.status === "error") return null;

  if (pedido.status === "loading") {
    return (
      <div role="status" className={cn("flex items-center gap-3", className)}>
        <span className="sr-only">{t("loading")}</span>
        <span aria-hidden="true" className="h-4 w-24 rounded bg-raised-2" />
        <span aria-hidden="true" className="flex gap-1.5">
          {[0, 1, 2].map((i) => (
            <span key={i} className="size-6 rounded-md bg-raised-2" />
          ))}
        </span>
      </div>
    );
  }

  if (pedido.status !== "ok") return null;
  const datos = pedido.data;
  const nombrePais = formats.country(datos.pais || pais);
  const unicas = new Map<number, Plataforma>();
  for (const [clave] of GRUPOS) for (const p of datos[clave]) unicas.set(p.id, p);
  const total = unicas.size;

  if (total === 0) {
    return (
      <p className={cn("text-sm text-fg-2", className)}>
        {t("unavailable", { country: nombrePais })}
      </p>
    );
  }

  return (
    <div className={cn("flex flex-col", className)}>
      <button
        ref={linea}
        type="button"
        aria-expanded={abierto}
        aria-haspopup="dialog"
        onClick={() => setAbierto(true)}
        className="group flex min-h-11 cursor-pointer flex-wrap items-center gap-x-3 gap-y-1 self-start rounded-lg pr-1.5 text-left text-sm text-fg-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      >
        <span className="font-semibold text-foreground">{t("lead")}</span>
        <span aria-hidden="true" className="flex gap-1.5">
          {[...unicas.values()].slice(0, EN_LINEA).map((p) => (
            <span key={p.id} className="block size-6 [&_img]:size-6">
              <Logo plataforma={p} size={24} decorativo />
            </span>
          ))}
        </span>
        <span className="inline-flex items-center gap-2">
          {t("options", { count: total, country: nombrePais })}
          <span
            aria-hidden="true"
            className="grid size-7 place-items-center rounded-full bg-raised-2 text-foreground group-hover:bg-selected group-hover:text-selected-foreground"
          >
            <ChevronRight className="size-4" strokeWidth={2.2} />
          </span>
        </span>
      </button>
      {abierto && (
        // Al desmontarse, `DialogShell` devuelve el foco a la línea (`returnFocus`:
        // en Safari un clic no la enfoca y `activeElement` sería el `body`).
        <DialogShell
          labelledBy={tituloId}
          onClose={() => setAbierto(false)}
          returnFocus={linea}
          cerrarConFondo
          ancho="md:w-[min(32.5rem,calc(100%-3rem))]"
          relleno="px-5 pt-2 pb-[max(1.5rem,env(safe-area-inset-bottom))] md:pb-5 md:shadow-[inset_0_0_0_1px_var(--line),0_24px_60px_rgb(0_0_0/0.5)]"
        >
          <div className="flex items-center justify-between py-3">
            <h2 id={tituloId} className="font-display text-[1.875rem] leading-none">
              {t("panelTitle")}
            </h2>
            <button
              type="button"
              aria-label={tc("close")}
              onClick={() => setAbierto(false)}
              className="grid size-11 cursor-pointer place-items-center rounded-full text-fg-2 hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
            >
              <X aria-hidden="true" className="size-[1.125rem]" />
            </button>
          </div>
          {GRUPOS.filter(([clave]) => datos[clave].length > 0).map(([clave, grupo]) => (
            <section
              key={clave}
              aria-label={t(`groups.${grupo}`)}
              className="flex flex-col gap-2.5 border-t border-line py-3.5"
            >
              <h3 className="text-[0.8125rem] font-semibold text-fg-3">{t(`groups.${grupo}`)}</h3>
              <ul className="flex flex-wrap gap-2">
                {datos[clave].map((p) => (
                  <li key={p.id}>
                    <Logo plataforma={p} size={40} />
                  </li>
                ))}
              </ul>
            </section>
          ))}
          <div className="flex flex-wrap items-center gap-x-5 gap-y-1 border-t border-line pt-1.5 text-sm">
            {datos.enlace && (
              <a
                href={datos.enlace}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex min-h-11 items-center gap-1.5 font-semibold text-foreground underline underline-offset-[3px]"
              >
                {t("seeAll")}
                <ExternalLink aria-hidden="true" className="size-3.5" />
                <span className="sr-only"> {t("newTabHint")}</span>
              </a>
            )}
            <p className="text-fg-3">
              {t.rich("attribution", {
                link: (chunks) => (
                  <a
                    href={JUSTWATCH}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline underline-offset-[3px] hover:text-foreground"
                  >
                    {chunks}
                  </a>
                ),
              })}
            </p>
          </div>
        </DialogShell>
      )}
    </div>
  );
}
