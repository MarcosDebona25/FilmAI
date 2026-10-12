import Link from "next/link";
import { useTranslations } from "next-intl";

import { routes } from "@/lib/routes";

export function TicketMark({ width = 32, height = 24 }: { width?: number; height?: number }) {
  return (
    <svg width={width} height={height} viewBox="0 0 32 24" aria-hidden="true" className="flex-none">
      <path
        d="M4 0h24a4 4 0 0 1 4 4v5a3 3 0 0 0 0 6v5a4 4 0 0 1-4 4H4a4 4 0 0 1-4-4v-5a3 3 0 0 0 0-6V4a4 4 0 0 1 4-4Z"
        className="fill-primary"
      />
      <polygon
        points="16 6.8 17.29 10.22 20.95 10.39 18.09 12.68 19.06 16.21 16 14.2 12.94 16.21 13.91 12.68 11.05 10.39 14.71 10.22"
        className="fill-on-accent"
      />
    </svg>
  );
}

/** Marca de las pantallas de acceso: lleva siempre a la landing. */
export function AccessLogo({ className = "" }: { className?: string }) {
  const t = useTranslations("nav.main");
  return (
    <Link
      href={routes.home}
      aria-label={t("brandLandingLabel")}
      className={`flex items-center gap-2.5 text-foreground no-underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring ${className}`}
    >
      <TicketMark />
      <span translate="no" className="font-display text-[30px] leading-none tracking-[0.05em]">
        FilmAI
      </span>
    </Link>
  );
}
