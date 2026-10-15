import { Suspense } from "react";
import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { SearchView } from "@/components/features/SearchView";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("nav.main");
  return { title: `${t("search")} | FilmAI` };
}

/** Buscar (C-06). Pública, como el Home y la ficha. */
export default function SearchPage() {
  // `useSearchParams` (la búsqueda vive en la URL) necesita un límite de Suspense.
  return (
    <Suspense fallback={null}>
      <SearchView />
    </Suspense>
  );
}
