"use client";

import { useEffect, useId, useRef, useState } from "react";
import Image from "next/image";
import { ChevronDown } from "lucide-react";
import { useTranslations } from "next-intl";

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
  const caja = { width: size, height: size };
  return src ? (
    <Image
      src={src}
      alt={decorativo ? "" : plataforma.nombre}
      title={decorativo ? undefined : plataforma.nombre}
      {...caja}
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
 * opciones en el país, que abre un panel con los grupos Stream / Free / Rent /
 * Buy. TMDB no da enlaces directos por plataforma, así que los logos no son
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
  const panelId = useId();
  const raiz = useRef<HTMLDivElement>(null);
  const boton = useRef<HTMLButtonElement>(null);
  const [abierto, setAbierto] = useState(false);

  useEffect(() => {
    if (!abierto) return;
    const fuera = (event: PointerEvent) => {
      if (!raiz.current?.contains(event.target as Node)) setAbierto(false);
    };
    const escape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setAbierto(false);
      boton.current?.focus();
    };
    document.addEventListener("pointerdown", fuera);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("pointerdown", fuera);
      document.removeEventListener("keydown", escape);
    };
  }, [abierto]);

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
    <div ref={raiz} className={cn("flex flex-col gap-3", className)}>
      <button
        ref={boton}
        type="button"
        aria-expanded={abierto}
        aria-haspopup="dialog"
        aria-controls={abierto ? panelId : undefined}
        onClick={() => setAbierto((actual) => !actual)}
        className="flex min-h-11 cursor-pointer flex-wrap items-center gap-x-3 gap-y-1 self-start rounded-lg text-left text-sm text-fg-2 hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
      >
        <span className="font-semibold text-foreground">{t("lead")}</span>
        <span aria-hidden="true" className="flex gap-1.5">
          {[...unicas.values()].slice(0, EN_LINEA).map((p) => (
            <span key={p.id} className="block size-6 [&_img]:size-6">
              <Logo plataforma={p} size={24} decorativo />
            </span>
          ))}
        </span>
        <span className="inline-flex items-center gap-1">
          {t("options", { count: total, country: nombrePais })}
          <ChevronDown
            aria-hidden="true"
            className={cn("size-4 transition-transform", abierto && "rotate-180")}
          />
        </span>
      </button>
      {abierto && (
        <div
          id={panelId}
          role="dialog"
          aria-label={t("panelTitle")}
          className="flex flex-col gap-5 rounded-xl bg-raised p-4 shadow-[inset_0_0_0_1px_var(--line)] md:max-w-[720px] md:p-5"
        >
          {GRUPOS.filter(([clave]) => datos[clave].length > 0).map(([clave, grupo]) => (
            <section key={clave} aria-label={t(`groups.${grupo}`)} className="flex flex-col gap-2">
              <h3 className="text-[13px] font-semibold text-fg-3">{t(`groups.${grupo}`)}</h3>
              <ul className="flex flex-wrap gap-2">
                {datos[clave].map((p) => (
                  <li key={p.id}>
                    <Logo plataforma={p} size={40} />
                  </li>
                ))}
              </ul>
            </section>
          ))}
          <div className="flex flex-col gap-2 text-sm md:flex-row md:items-center md:justify-between">
            {datos.enlace && (
              <a
                href={datos.enlace}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex min-h-11 items-center font-semibold text-foreground underline underline-offset-[3px]"
              >
                {t("seeAll")}
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
        </div>
      )}
    </div>
  );
}
