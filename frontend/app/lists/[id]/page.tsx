import { Suspense } from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";

import { ListDetailView } from "@/components/features/lists/ListDetailView";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("lists.detail");
  return { title: `${t("pageTitle")} | FilmAI` };
}

/** Detalle de una lista (L-03). Privada: el middleware pide sesión. */
export default async function ListaPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  // Un id que no es número no es una lista: 404 (Not Found) sin pedir nada.
  if (!/^\d+$/.test(id)) notFound();
  // `useSearchParams` (los filtros viven en la URL) necesita un límite de Suspense.
  return (
    <Suspense fallback={null}>
      <ListDetailView id={Number(id)} />
    </Suspense>
  );
}
