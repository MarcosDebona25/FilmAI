import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { MisResenas } from "@/components/MisResenas";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("legacy.metadata");
  return { title: `${t("myReviews")} | FilmAI` };
}

export default function MisResenasPage() {
  return <MisResenas />;
}
