import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("legacy.metadata");
  return { title: `${t("settings")} | FilmAI` };
}

export default function PreferenciasLayout({ children }: { children: React.ReactNode }) {
  return children;
}
