import { Suspense } from "react";
import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { HomeView } from "@/components/features/HomeView";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("nav.main");
  return { title: `${t("home")} | FilmAI` };
}

/** Home de descubrimiento (C-05). Pública: sin sesión no muestra Recomendado. */
export default function HomePage() {
  // `useSearchParams` (el selector vive en la URL) necesita un límite de Suspense.
  return (
    <Suspense fallback={null}>
      <HomeView />
    </Suspense>
  );
}
