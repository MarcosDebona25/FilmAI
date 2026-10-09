import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("legacy.metadata");
  return { title: `${t("profile")} | FilmAI` };
}

export default function PerfilLayout({ children }: { children: React.ReactNode }) {
  return children;
}
