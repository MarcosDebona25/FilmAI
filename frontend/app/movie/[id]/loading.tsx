import { TitleSkeleton } from "@/components/features/title/TitleSkeleton";

/**
 * Next muestra este archivo en el instante del clic, mientras el servidor
 * resuelve la página (en Java sería la pantalla de «cargando» que se pinta
 * antes de que llegue la respuesta). Es el mismo esqueleto que `TitleView`.
 */
export default function Loading() {
  return <TitleSkeleton />;
}
