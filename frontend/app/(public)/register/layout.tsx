import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("nav.account");
  return { title: `${t("signUp")} | FilmAI` };
}

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
