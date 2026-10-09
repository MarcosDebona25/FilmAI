"use client";
import { routes } from "@/lib/routes";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { LoaderCircle } from "lucide-react";
import { toast } from "sonner";
import { ReviewCard } from "@/components/ReviewCard";
import { ReviewModal } from "@/components/ReviewModal";
import { Button } from "@/components/ui/button";
import { useAccount } from "@/components/AccountProvider";
import { apiFetch } from "@/lib/api";
import { combinarResenas, rutaPagina, type MiResena, type PaginaResenas } from "@/lib/reviews";

export function MisResenas() {
  const { perfil, cargando: accountLoading, error: accountError, recargar } = useAccount();
  const [items, setItems] = useState<MiResena[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<{
    item: MiResena;
    action: "edit" | "text" | "rating";
  } | null>(null);
  const inFlight = useRef(false);
  const sentinel = useRef<HTMLDivElement>(null);
  const alive = useRef(true);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);
  const load = useCallback(async (path = "/api/reviews/mias/", append = false) => {
    if (inFlight.current) return;
    inFlight.current = true;
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<PaginaResenas>(path);
      if (!alive.current) return;
      setItems((current) => (append ? combinarResenas(current, data.results) : data.results));
      setNext(data.next);
    } catch {
      if (alive.current) setError("No pudimos cargar tus reseñas. Intentá de nuevo.");
    } finally {
      inFlight.current = false;
      if (alive.current) setLoading(false);
    }
  }, []);
  useEffect(() => {
    if (perfil?.pk) void load();
  }, [perfil?.pk, load]);
  useEffect(() => {
    if (!next || loading || error || !sentinel.current) return;
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) void load(rutaPagina(next), true);
    });
    observer.observe(sentinel.current);
    return () => observer.disconnect();
  }, [next, loading, error, load]);

  return (
    <main id="contenido" className="mx-auto max-w-3xl px-6 py-10">
      <h1
        ref={heading}
        tabIndex={-1}
        className="mb-8 text-3xl font-bold focus-visible:outline-2 focus-visible:outline-ring"
      >
        Mis reseñas
      </h1>
      {accountError ? (
        <div role="alert">
          <p>{accountError}</p>
          <Button className="min-h-11" onClick={() => void recargar()}>
            Reintentar
          </Button>
        </div>
      ) : accountLoading || (loading && !items.length) ? (
        <div role="status" aria-label="Cargando reseñas" className="space-y-4">
          {[1, 2, 3].map((id) => (
            <div
              key={id}
              className="flex min-h-[280px] gap-4 rounded-xl bg-card p-5 motion-safe:animate-pulse"
            >
              <div className="h-[84px] w-14 rounded bg-secondary sm:h-[120px] sm:w-20" />
              <div className="flex-1 space-y-4">
                <div className="h-6 w-2/3 rounded bg-secondary" />
                <div className="h-16 rounded bg-secondary" />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <>
          {!items.length && !error && (
            <div className="rounded-xl bg-card p-6">
              <p>Todavía no calificaste ninguna producción ni escribiste reseñas.</p>
              <Link
                className="mt-4 inline-flex min-h-11 items-center text-primary underline"
                href={routes.profile}
              >
                Volver a mi perfil
              </Link>
            </div>
          )}
          <div className="space-y-4">
            {items.map((item) => (
              <ReviewCard
                key={item.id}
                item={item}
                onAction={(action) => setSelected({ item, action })}
              />
            ))}
          </div>
          {error && (
            <div role="alert" className="mt-5">
              <p>{error}</p>
              <Button
                className="mt-3 min-h-11"
                onClick={() =>
                  void load(
                    items.length && next ? rutaPagina(next) : undefined,
                    Boolean(items.length)
                  )
                }
              >
                Reintentar
              </Button>
            </div>
          )}
          {next && !error && (
            <div ref={sentinel} className="mt-6 flex justify-center">
              <Button
                className="min-h-11"
                variant="secondary"
                disabled={loading}
                onClick={() => void load(rutaPagina(next), true)}
              >
                {loading && (
                  <LoaderCircle aria-hidden="true" className="motion-safe:animate-spin" />
                )}
                Cargar más
              </Button>
            </div>
          )}
        </>
      )}
      {selected && (
        <ReviewModal
          item={selected.item}
          action={selected.action}
          onClose={() => setSelected(null)}
          onSuccess={(updated) => {
            setItems((current) =>
              updated
                ? current.map((item) => (item.id === updated.id ? updated : item))
                : current.filter((item) => item.id !== selected.item.id)
            );
            toast.success(
              selected.action === "text"
                ? "Reseña eliminada."
                : selected.action === "rating"
                  ? selected.item.texto
                    ? "Calificación y reseña eliminadas."
                    : "Calificación eliminada."
                  : updated?.valor !== selected.item.valor && updated?.texto !== selected.item.texto
                    ? "Calificación y reseña actualizadas."
                    : updated?.valor !== selected.item.valor
                      ? "Calificación actualizada."
                      : "Reseña actualizada."
            );
            setSelected(null);
            if (!updated) requestAnimationFrame(() => heading.current?.focus());
          }}
        />
      )}
    </main>
  );
}
