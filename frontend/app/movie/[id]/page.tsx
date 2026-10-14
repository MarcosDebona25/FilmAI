import { Suspense } from "react";
import { notFound } from "next/navigation";

import { TitleView } from "@/components/features/title/TitleView";

/** Ficha de una película (C-07). Pública: sin sesión no muestra las acciones. */
export default async function MoviePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  // Un id que no es número no es una ficha: 404 (Not Found) sin pedir nada.
  if (!/^\d+$/.test(id)) notFound();
  // `useSearchParams` (el origen de la miga) necesita un límite de Suspense.
  return (
    <Suspense fallback={null}>
      <TitleView tipo="movie" id={Number(id)} />
    </Suspense>
  );
}
