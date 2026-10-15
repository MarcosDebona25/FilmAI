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
}: {
  value: ContentType;
  onChange: (value: ContentType) => void;
  className?: string;
  /** En celular comparte la fila con otro botón (Search): letra de 14 px y sin relleno lateral, como el canvas. */
  compact?: boolean;
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
              "h-10 cursor-pointer rounded-full transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring",
              compact ? "px-0 text-sm md:px-[18px] md:text-[15px]" : "px-[18px] text-[15px]",
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
