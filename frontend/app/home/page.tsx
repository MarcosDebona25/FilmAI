import { Suspense } from "react";
import type { Metadata } from "next";
import { getLocale, getTranslations } from "next-intl/server";

import { HomeView } from "@/components/features/HomeView";
import { pedirVarias } from "@/lib/catalogo-servidor";
import { rutasHeroPara, tipoDesdeUrl } from "@/lib/home";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("nav.main");
  return { title: `${t("home")} | FilmAI` };
}

/**
 * Home de descubrimiento (C-05). Pública: sin sesión no muestra Recomendado.
 *
 * Lo que necesita el Hero (tendencias y géneros) se pide acá, en el servidor:
 * el HTML ya trae el título y la imagen de fondo, y el navegador pide esa
 * imagen (el LCP) sin esperar a que el JavaScript pida tendencias (24/10/2026).
 * Si el backend no responde a tiempo, `HomeView` lo pide como antes.
 */
export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<{ type?: string | string[] }>;
}) {
  const { type } = await searchParams;
  const tipo = tipoDesdeUrl(typeof type === "string" ? type : null);
  const idioma = await getLocale();
  const datos = await pedirVarias(rutasHeroPara(tipo), idioma);

  // `useSearchParams` (el selector vive en la URL) necesita un límite de Suspense.
  return (
    <Suspense fallback={null}>
      <HomeView inicial={{ idioma, datos }} />
    </Suspense>
  );
}
