"use client";

import Image from "next/image";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { LanguageSwitcher } from "@/components/LanguageSwitcher";

/**
 * Marco de las pantallas de acceso (canvas «Access»): collage de pósters a la
 * izquierda (detrás del contenido en celular), contenido a la derecha y el
 * selector EN|ES sin sesión arriba a la derecha.
 */
export function AccessShell({
  children,
  poster = "side",
  weights = "grid-cols-1 lg:grid-cols-[5fr_6fr]",
}: {
  children: ReactNode;
  poster?: "side" | "background";
  weights?: string;
}) {
  const t = useTranslations("auth.landing");
  return (
    <div className="relative min-h-screen bg-background tracking-normal text-foreground">
      <div className="absolute top-4 right-4 z-20 lg:top-6 lg:right-8">
        <LanguageSwitcher compact />
      </div>
      <div
        className={`grid min-h-screen ${poster === "side" ? weights : "grid-cols-1 lg:grid-cols-[5fr_6fr]"}`}
      >
        <div
          className={`relative overflow-hidden ${poster === "side" ? "hidden lg:block" : "absolute inset-0 lg:static"}`}
        >
          <Image
            src="/collage-posters/Opcion 1.jpg"
            alt={poster === "background" ? "" : t("posterCollageAlt")}
            fill
            priority
            sizes="(max-width: 1023px) 100vw, 45vw"
            className="object-cover"
          />
          <div
            aria-hidden="true"
            className="absolute inset-0 bg-linear-to-r from-[rgb(var(--scrim)/0.1)] via-[rgb(var(--scrim)/0.3)] to-[rgb(var(--scrim))] max-lg:bg-[rgb(var(--scrim)/0.82)] max-lg:bg-none"
          />
        </div>
        <main className="relative z-10 flex items-center justify-center px-5 pt-[104px] pb-10 lg:p-12">
          {children}
        </main>
      </div>
    </div>
  );
}
