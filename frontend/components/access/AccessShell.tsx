"use client";

import Image from "next/image";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { AccessLogo } from "@/components/access/Logo";

/**
 * Marco de las pantallas de acceso (canvas «Access»): collage de pósters a la
 * izquierda (detrás del contenido en celular), contenido a la derecha y el
 * selector EN|ES sin sesión arriba a la derecha.
 *
 * `poster="band"` (alta con Google): en celular el collage es una franja de
 * 160 px arriba, con el logo encima; en escritorio, la columna de siempre.
 */
export function AccessShell({
  children,
  poster = "side",
  weights = "grid-cols-1 lg:grid-cols-[5fr_6fr]",
}: {
  children: ReactNode;
  poster?: "side" | "background" | "band";
  weights?: string;
}) {
  const t = useTranslations("auth.landing");
  return (
    <div className="relative min-h-screen bg-background tracking-normal text-foreground">
      {/* Landmarks: todo el contenido queda en `header`, `aside` o `main`. */}
      <header className="absolute top-4 right-4 z-20 lg:top-6 lg:right-8">
        <LanguageSwitcher />
      </header>
      <div
        className={`grid min-h-screen ${
          poster === "side"
            ? weights
            : poster === "band"
              ? "grid-cols-1 grid-rows-[auto_1fr] lg:grid-cols-[5fr_6fr] lg:grid-rows-1"
              : "grid-cols-1 lg:grid-cols-[5fr_6fr]"
        }`}
      >
        <aside
          className={`relative overflow-hidden ${
            poster === "side"
              ? "hidden lg:block"
              : poster === "band"
                ? "h-40 lg:h-auto"
                : "absolute inset-0 lg:static"
          }`}
        >
          <Image
            src="/collage-posters/Opcion 1.jpg"
            alt={poster === "background" ? "" : t("posterCollageAlt")}
            fill
            priority
            sizes="(max-width: 1023px) 100vw, 45vw"
            className={`object-cover ${poster === "band" ? "object-[50%_20%] lg:object-center" : ""}`}
          />
          {poster === "band" ? (
            <>
              <div
                aria-hidden="true"
                className="absolute inset-0 bg-linear-to-t from-[rgb(var(--scrim))] to-[rgb(var(--scrim)/0.2)] to-70% lg:hidden"
              />
              <div
                aria-hidden="true"
                className="absolute inset-0 hidden bg-linear-to-r from-[rgb(var(--scrim)/0.1)] via-[rgb(var(--scrim)/0.3)] to-[rgb(var(--scrim))] lg:block"
              />
              <AccessLogo compact className="absolute bottom-4 left-5 lg:hidden" />
            </>
          ) : (
            <div
              aria-hidden="true"
              className="absolute inset-0 bg-linear-to-r from-[rgb(var(--scrim)/0.1)] via-[rgb(var(--scrim)/0.3)] to-[rgb(var(--scrim))] max-lg:bg-[rgb(var(--scrim)/0.82)] max-lg:bg-none"
            />
          )}
        </aside>
        <main
          className={`relative z-10 flex justify-center lg:items-center lg:p-12 ${
            poster === "band" ? "px-5 pt-5 pb-10" : "items-center px-5 pt-[104px] pb-10"
          }`}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
