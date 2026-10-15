"use client";

import { useId, useState } from "react";
import { useTranslations } from "next-intl";

import type { MediaType } from "@/lib/catalog";
import type { Creditos } from "@/lib/title";
import { cn } from "@/lib/utils";

const VISIBLES = 10;

/**
 * «Director and cast» (canvas). En series no hay director a nivel serie y se
 * muestran los creadores («Created by»). El reparto se pliega pasados los 10.
 */
export function CreditsSection({ creditos, tipo }: { creditos: Creditos; tipo: MediaType }) {
  const t = useTranslations("title.credits");
  const tc = useTranslations("common.disclosure");
  const tituloId = useId();
  const [todo, setTodo] = useState(false);
  if (!creditos.directores.length && !creditos.reparto.length) return null;
  const reparto = todo ? creditos.reparto : creditos.reparto.slice(0, VISIBLES);
  const ocultos = creditos.reparto.length - VISIBLES;
  const hayDirectores = creditos.directores.length > 0;

  return (
    <section aria-labelledby={tituloId} className="flex flex-col gap-6">
      <h2 id={tituloId} className="font-display text-[34px] leading-none md:text-[44px]">
        {t("heading")}
      </h2>
      {/* Sin director (muchas series y animes) el reparto ocupa todo el ancho:
          con la columna de 240 px quedaba apretado en esa columna. */}
      <div
        className={cn(
          "grid gap-x-14 gap-y-6",
          hayDirectores && "md:grid-cols-[240px_minmax(0,1fr)]"
        )}
      >
        {hayDirectores && (
          <div className="flex flex-col gap-1">
            <span className="text-[13px] font-semibold text-fg-3">
              {tipo === "tv" ? t("creators") : t("directors")}
            </span>
            <span className="font-semibold">{creditos.directores.join(", ")}</span>
          </div>
        )}
        {creditos.reparto.length > 0 && (
          <div className="flex flex-col gap-3">
            <span className="text-[13px] font-semibold text-fg-3">{t("cast")}</span>
            <ul
              className={cn(
                "grid grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2 lg:grid-cols-3",
                !hayDirectores && "xl:grid-cols-4"
              )}
            >
              {reparto.map((persona) => (
                <li key={`${persona.nombre}-${persona.personaje}`} className="flex flex-col">
                  <span className="font-semibold">{persona.nombre}</span>
                  {persona.personaje && (
                    <span className="text-sm text-fg-3">{persona.personaje}</span>
                  )}
                </li>
              ))}
            </ul>
            {ocultos > 0 && (
              <button
                type="button"
                aria-expanded={todo}
                onClick={() => setTodo(!todo)}
                className="h-11 cursor-pointer self-start font-semibold text-fg-2 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
              >
                {todo ? tc("showLess") : tc("showMore", { count: String(ocultos) })}
              </button>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
