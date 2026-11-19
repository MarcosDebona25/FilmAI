"use client";

import { Fragment, useId, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import type { MediaType } from "@/lib/catalog";
import { urlDePersona, type RolPersona } from "@/lib/search";
import type { Creditos, PersonaDeCreditos } from "@/lib/title";
import { cn } from "@/lib/utils";

const VISIBLES = 10;

/**
 * El nombre de una persona como enlace a Buscar con su chip (el mismo destino
 * que su fila en la lupa de la navbar). Sin `id` de TMDB queda como texto.
 */
function Nombre({ persona, rol }: { persona: PersonaDeCreditos; rol: RolPersona }) {
  if (persona.id === null) return <span className="font-semibold">{persona.nombre}</span>;
  return (
    <Link
      href={urlDePersona(persona.id, rol)}
      className="rounded-sm font-semibold text-foreground underline decoration-fg-3/40 underline-offset-[3px] hover:decoration-current focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
    >
      {persona.nombre}
    </Link>
  );
}

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
      <h2 id={tituloId} className="font-display text-[2.125rem] leading-none md:text-[2.75rem]">
        {hayDirectores ? t("heading") : t("cast")}
      </h2>
      {/* Sin director (muchas series y animes) el reparto ocupa todo el ancho:
          con la columna de 240 px quedaba apretado en esa columna. */}
      <div
        className={cn(
          "grid gap-x-14 gap-y-6",
          hayDirectores && "md:grid-cols-[15rem_minmax(0,1fr)]"
        )}
      >
        {hayDirectores && (
          <div className="flex flex-col gap-1">
            <span className="text-[0.8125rem] font-semibold text-fg-3">
              {tipo === "tv" ? t("creators") : t("directors")}
            </span>
            {/* Los creadores de una serie también van como «director»: es el rol
                con el que Buscar arma su filmografía. */}
            <span>
              {creditos.directores.map((persona, i) => (
                <Fragment key={`${persona.id}-${persona.nombre}`}>
                  {i > 0 && <span className="font-semibold">, </span>}
                  <Nombre persona={persona} rol="director" />
                </Fragment>
              ))}
            </span>
          </div>
        )}
        {creditos.reparto.length > 0 && (
          <div className="flex flex-col gap-3">
            {/* Sin director el título ya dice «Reparto». */}
            {hayDirectores && (
              <span className="text-[0.8125rem] font-semibold text-fg-3">{t("cast")}</span>
            )}
            <ul
              className={cn(
                "grid grid-cols-1 gap-x-8 gap-y-3 sm:grid-cols-2 lg:grid-cols-3",
                !hayDirectores && "xl:grid-cols-4"
              )}
            >
              {reparto.map((persona) => (
                <li
                  key={`${persona.nombre}-${persona.personaje}`}
                  className="flex flex-col items-start"
                >
                  <Nombre persona={persona} rol="actor" />
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
