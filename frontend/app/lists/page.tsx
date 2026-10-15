import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { ListsView } from "@/components/features/lists/ListsView";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("nav.main");
  return { title: `${t("lists")} | FilmAI` };
}

export default function ListasPage() {
  return <ListsView />;
}
