"use client";

import { useTranslations } from "next-intl";

import { cn } from "@/lib/utils";

export type ContentType = "all" | "movie" | "tv";

/**
 * Selector `All · Movies · TV shows` del canvas (Home, y después Search).
 * Grilla de tres en celular; en escritorio se ajusta al contenido. Quien lo usa
 * puede cambiar el fondo con `className` (sobre el Hero va semitransparente).
 */
export function TypeSelector({
  value,
  onChange,
  className,
  compact = false,
  apretado = false,
}: {
  value: ContentType;
  onChange: (value: ContentType) => void;
  className?: string;
  /** En celular comparte la fila con otro botón (Search): letra de 14 px y sin relleno lateral, como el canvas. */
  compact?: boolean;
  /** Entre 768 y 1280 px los botones llevan 14 px de relleno en vez de 18 (Search, para que la fila entre en una línea). */
  apretado?: boolean;
}) {
  const t = useTranslations("common.content");
  const options: { id: ContentType; label: string }[] = [
    { id: "all", label: t("all") },
    { id: "movie", label: t("movies") },
    { id: "tv", label: t("tvShows") },
  ];

  return (
    <div
      role="group"
      aria-label={t("typeLabel")}
      className={cn(
        "grid grid-cols-3 gap-1 rounded-full bg-raised p-1 shadow-[inset_0_0_0_1px_var(--line)] md:inline-flex",
        className
      )}
    >
      {options.map((option) => {
        const active = option.id === value;
        return (
          <button
            key={option.id}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(option.id)}
            className={cn(
              "h-11 cursor-pointer rounded-full transition-colors md:h-10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
              compact
                ? cn(
                    "px-0 text-sm md:text-[0.9375rem]",
                    apretado ? "md:px-3.5 xl:px-[1.125rem]" : "md:px-[1.125rem]"
                  )
                : "px-[1.125rem] text-[0.9375rem]",
              active
                ? "bg-selected font-semibold text-selected-foreground"
                : "font-medium text-fg-2 hover:text-foreground"
            )}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
