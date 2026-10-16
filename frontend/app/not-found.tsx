import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { NotFoundScreen } from "@/components/errors/ErrorScreens";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("errors.pages");
  return { title: `${t("notFoundTitle")} | FilmAI` };
}

export default function NotFound() {
  return <NotFoundScreen />;
}
