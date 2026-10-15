import { Suspense } from "react";
import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { MyReviewsView } from "@/components/features/reviews/MyReviewsView";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("nav.main");
  return { title: `${t("ratingsReviews")} | FilmAI` };
}

export default function MisResenasPage() {
  // `useSearchParams` (los filtros viven en la URL) necesita un límite de Suspense.
  return (
    <Suspense fallback={null}>
      <MyReviewsView />
    </Suspense>
  );
}
