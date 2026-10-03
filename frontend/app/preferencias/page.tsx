"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { useAccount, type Preferencias } from "@/components/AccountProvider";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";
import { ADVERTENCIA_BAJA } from "@/lib/profile-draft";
import { mantenerFocoEnDialogo } from "@/lib/dialog-focus";

const INTERRUPTORES: { campo: keyof Preferencias; titulo: string; descripcion: string }[] = [
  {
    campo: "perfil_publico",
    titulo: "Perfil público",
    descripcion: "Preferencia de visibilidad para futuras vistas públicas.",
  },
  {
    campo: "notif_recomendaciones",
    titulo: "Recomendaciones semanales",
    descripcion: "Preferencia para futuros correos de sugerencias.",
  },
  {
    campo: "notif_resenas",
    titulo: "Reseñas en tus listas",
    descripcion: "Preferencia para futuros avisos sobre reseñas.",
  },
  {
    campo: "notif_novedades",
    titulo: "Novedades de FilmAI",
    descripcion: "Preferencia para futuros correos de novedades.",
  },
];

export default function PreferenciasPage() {
  const router = useRouter();
  const { preferencias, cargando, error, recargar, actualizarPreferencia, limpiar } = useAccount();
  const [guardando, setGuardando] = useState<string | null>(null);
  const [confirmarBaja, setConfirmarBaja] = useState(false);
  const [dandoBaja, setDandoBaja] = useState(false);
  const [errorBaja, setErrorBaja] = useState<string | null>(null);
  const cancelarRef = useRef<HTMLButtonElement>(null);
  const bajaButtonRef = useRef<HTMLButtonElement>(null);
  const bajaDialogRef = useRef<HTMLDivElement>(null);

  function cerrarBaja() {
    setConfirmarBaja(false);
    bajaButtonRef.current?.focus();
  }

  useEffect(() => {
    if (!confirmarBaja) return;
    cancelarRef.current?.focus();
    function onEscape(event: KeyboardEvent) {
      if (event.key === "Escape" && !dandoBaja) cerrarBaja();
      mantenerFocoEnDialogo(event, bajaDialogRef.current);
    }
    window.addEventListener("keydown", onEscape);
    return () => window.removeEventListener("keydown", onEscape);
  }, [confirmarBaja, dandoBaja]);

  async function cambiar<K extends keyof Preferencias>(campo: K, valor: Preferencias[K]) {
    setGuardando(campo);
    try {
      await actualizarPreferencia(campo, valor);
    } catch {
      toast.error("No pudimos guardar la preferencia. Intentá de nuevo.");
    } finally {
      setGuardando(null);
    }
  }

  async function desactivarCuenta() {
    setErrorBaja(null);
    setDandoBaja(true);
    try {
      await apiFetch("/api/account/deactivate/", { method: "POST" });
      limpiar();
      toast.success("Tu cuenta fue dada de baja.");
      router.replace("/");
    } catch {
      setErrorBaja("No pudimos dar de baja tu cuenta. Sigue activa; intentá de nuevo.");
      setDandoBaja(false);
    }
  }

  return (
    <main id="contenido" className="mx-auto max-w-3xl px-6 py-10">
      <nav aria-label="Ruta de navegación" className="mb-8 text-sm text-muted-foreground">
        Preferencias
      </nav>
      <h1 className="mb-8 text-3xl font-bold text-foreground">Preferencias</h1>
      {cargando ? <p role="status">Cargando preferencias…</p> : null}
      {error ? (
        <div role="alert" className="mb-6 rounded-xl border border-destructive p-4">
          <p>{error}</p>
          <Button className="mt-3" variant="secondary" onClick={() => void recargar()}>
            Reintentar
          </Button>
        </div>
      ) : null}
      {preferencias ? (
        <div className="space-y-10">
          <section aria-labelledby="apariencia">
            <h2 id="apariencia" className="mb-4 text-xl font-semibold">
              Apariencia
            </h2>
            <fieldset className="flex flex-wrap items-center justify-between gap-4 rounded-xl bg-card p-5">
              <legend className="sr-only">Tema de la interfaz</legend>
              <span className="font-medium">Tema</span>
              <div className="flex gap-4">
                {(["oscuro", "claro"] as const).map((tema) => (
                  <label key={tema} className="flex min-h-11 cursor-pointer items-center gap-2">
                    <input
                      type="radio"
                      name="tema"
                      value={tema}
                      checked={preferencias.tema === tema}
                      disabled={guardando !== null}
                      onChange={() => void cambiar("tema", tema)}
                      className="accent-primary"
                    />
                    {tema === "oscuro" ? "Oscuro" : "Claro"}
                  </label>
                ))}
              </div>
            </fieldset>
          </section>

          <section aria-labelledby="privacidad">
            <h2 id="privacidad" className="mb-4 text-xl font-semibold">
              Privacidad
            </h2>
            <p
              className="mb-4 rounded-lg border border-border bg-muted p-4 text-sm text-foreground"
              role="note"
            >
              Estas preferencias se guardan, pero todavía no cambian la visibilidad de reseñas o
              listas ni activan correos.
            </p>
            <div className="divide-y divide-border rounded-xl bg-card px-5">
              {INTERRUPTORES.slice(0, 1).map(({ campo, titulo, descripcion }) => (
                <label
                  key={campo}
                  className="flex min-h-18 cursor-pointer items-center justify-between gap-5 py-4"
                >
                  <span>
                    <span className="block font-medium">{titulo}</span>
                    <span className="block text-sm text-muted-foreground">{descripcion}</span>
                  </span>
                  <input
                    type="checkbox"
                    name={campo}
                    checked={Boolean(preferencias[campo])}
                    disabled={guardando !== null}
                    onChange={(event) => void cambiar(campo, event.target.checked)}
                    className="size-5 shrink-0 accent-primary"
                  />
                </label>
              ))}
            </div>
          </section>

          <section aria-labelledby="notificaciones">
            <h2 id="notificaciones" className="mb-4 text-xl font-semibold">
              Notificaciones
            </h2>
            <div className="divide-y divide-border rounded-xl bg-card px-5">
              {INTERRUPTORES.slice(1).map(({ campo, titulo, descripcion }) => (
                <label
                  key={campo}
                  className="flex min-h-18 cursor-pointer items-center justify-between gap-5 py-4"
                >
                  <span>
                    <span className="block font-medium">{titulo}</span>
                    <span className="block text-sm text-muted-foreground">{descripcion}</span>
                  </span>
                  <input
                    type="checkbox"
                    name={campo}
                    checked={Boolean(preferencias[campo])}
                    disabled={guardando !== null}
                    onChange={(event) => void cambiar(campo, event.target.checked)}
                    className="size-5 shrink-0 accent-primary"
                  />
                </label>
              ))}
            </div>
          </section>

          <section aria-labelledby="cuenta" className="border-t border-border pt-8">
            <h2 id="cuenta" className="mb-3 text-xl font-semibold">
              Cuenta
            </h2>
            <p className="mb-5 text-sm text-muted-foreground">
              La baja de la cuenta es irreversible. No podrás volver a iniciar sesión ni
              reactivarla.
            </p>
            <Button
              ref={bajaButtonRef}
              variant="destructive"
              onClick={() => setConfirmarBaja(true)}
            >
              Dar de baja cuenta
            </Button>
          </section>
        </div>
      ) : null}

      {confirmarBaja && (
        <div
          ref={bajaDialogRef}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="baja-titulo"
        >
          <div className="w-full max-w-lg rounded-xl bg-card p-6 shadow-xl">
            <h2 id="baja-titulo" className="text-xl font-semibold">
              ¿Dar de baja tu cuenta?
            </h2>
            <p className="mt-3 text-sm text-muted-foreground">{ADVERTENCIA_BAJA}</p>
            {errorBaja && (
              <p role="alert" className="mt-4 text-sm text-destructive">
                {errorBaja}
              </p>
            )}
            <div className="mt-6 flex justify-end gap-3">
              <Button
                ref={cancelarRef}
                variant="secondary"
                disabled={dandoBaja}
                onClick={cerrarBaja}
              >
                Cancelar
              </Button>
              <Button
                variant="destructive"
                disabled={dandoBaja}
                onClick={() => void desactivarCuenta()}
              >
                {dandoBaja ? "Dando de baja…" : "Dar de baja"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
