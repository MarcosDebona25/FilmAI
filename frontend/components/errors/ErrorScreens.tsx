"use client";

import Link from "next/link";
import { RotateCw, Search } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { primaryButtonClass, secondaryButtonClass } from "@/components/access/styles";
import { routes } from "@/lib/routes";

const actionClass = "md:w-auto md:px-6";

/** Entrada de cine cortada al medio: ilustración de las pantallas de error. */
function TornTicket({ label }: { label: string }) {
  return (
    <svg
      viewBox="0 0 200 126"
      role="img"
      aria-label={label}
      className="h-auto w-[220px] flex-none md:w-[300px]"
    >
      <g transform="rotate(-9 46 63)">
        <path
          d="M0 12 H92 L84 24 L92 36 L84 48 L92 60 L84 72 L92 84 L84 96 L92 108 L88 114 H0 V73 A10 10 0 0 0 0 53 Z"
          className="fill-primary"
        />
      </g>
      <g transform="translate(18 8) rotate(11 150 63)">
        <path
          d="M100 12 H190 V53 A10 10 0 0 0 190 73 V114 H96 L104 108 L96 96 L104 84 L96 72 L104 60 L96 48 L104 36 L96 24 Z"
          className="fill-primary"
        />
        <polygon
          points="146 47 149.9 55.2 158.8 56.3 152.3 62.4 153.9 71.3 146 67 138.1 71.3 139.7 62.4 133.2 56.3 142.1 55.2"
          className="fill-on-accent"
        />
      </g>
    </svg>
  );
}

function ErrorLayout({
  code,
  title,
  description,
  children,
}: {
  code: string;
  title: string;
  description: string;
  children: ReactNode;
}) {
  const t = useTranslations("errors.pages");
  return (
    <main
      id="contenido"
      className="mx-auto flex w-full max-w-[1360px] flex-col gap-3.5 px-5 pt-10 pb-[120px] md:flex-row md:flex-wrap md:items-center md:justify-center md:gap-x-24 md:gap-y-12 md:px-10 md:pt-24"
    >
      <TornTicket label={t("ticketIllustrationAlt")} />
      <div className="flex max-w-[640px] flex-col gap-3.5 max-md:mt-7 md:flex-[1_1_520px] md:gap-4">
        <p className="text-sm font-semibold text-fg-3">{code}</p>
        <h1 className="font-display text-[60px] leading-[0.92] md:mb-[15px] md:text-[96px]">
          {title}
        </h1>
        <p className="text-[17px] text-fg-2 md:text-lg">{description}</p>
        <div className="mt-3.5 flex flex-col gap-2.5 md:mt-3 md:flex-row md:flex-wrap md:gap-3">
          {children}
        </div>
      </div>
    </main>
  );
}

/** 404 (Not Found): la ruta no existe. Ofrece volver al inicio o buscar. */
export function NotFoundScreen() {
  const t = useTranslations("errors.pages");
  const nav = useTranslations("nav.main");
  return (
    <ErrorLayout
      code={t("notFoundCode")}
      title={t("notFoundTitle")}
      description={t("notFoundDescription")}
    >
      <Link href={routes.explore} className={`${primaryButtonClass} ${actionClass}`}>
        {nav("backHome")}
      </Link>
      <Link href={routes.search} className={`${secondaryButtonClass} ${actionClass} gap-2`}>
        <Search aria-hidden="true" className="size-[18px]" />
        {nav("search")}
      </Link>
    </ErrorLayout>
  );
}

/** Error inesperado (500 (Internal Server Error) o fallo de render): permite reintentar. */
export function UnexpectedErrorScreen({ reset }: { reset: () => void }) {
  const t = useTranslations("errors.pages");
  const nav = useTranslations("nav.main");
  const common = useTranslations("common.actions");
  return (
    <ErrorLayout
      code={t("serverTitle")}
      title={t("unexpectedTitle")}
      description={t("unexpectedDescription")}
    >
      <button
        type="button"
        onClick={reset}
        className={`${primaryButtonClass} ${actionClass} cursor-pointer gap-2`}
      >
        <RotateCw aria-hidden="true" className="size-[18px]" />
        {common("retry")}
      </button>
      <Link href={routes.explore} className={`${secondaryButtonClass} ${actionClass}`}>
        {nav("backHome")}
      </Link>
    </ErrorLayout>
  );
}
