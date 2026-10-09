"use client";

import { LoaderCircle } from "lucide-react";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { useTranslations } from "next-intl";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { useAccount, type Preferencias } from "@/components/AccountProvider";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

import { mantenerFocoEnDialogo } from "@/lib/dialog-focus";

export default function PreferenciasPage() {
  const theme = useTranslations("enums.theme");
  const t = useTranslations("legacy.settings");
  const language = useTranslations("settings.language");
  const INTERRUPTORES: { campo: keyof Preferencias; titulo: string; descripcion: string }[] = [
    {
      campo: "perfil_publico",
      titulo: t("publicProfile"),
      descripcion: t("publicProfileHelp"),
    },
    {
      campo: "notif_recomendaciones",
      titulo: t("weeklyLabel"),
      descripcion: t("weeklyHelp"),
    },
    {
      campo: "notif_resenas",
      titulo: t("reviewsLabel"),
      descripcion: t("reviewsHelp"),
    },
    {
      campo: "notif_novedades",
      titulo: t("newsLabel"),
      descripcion: t("newsHelp"),
    },
  ];

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
      toast.error(t("saveError"));
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
      toast.success(t("deactivated"));
      router.replace("/");
    } catch {
      setErrorBaja(t("deactivateError"));
      setDandoBaja(false);
    }
  }

  return (
    <main id="contenido" className="mx-auto max-w-3xl px-6 py-10">
      <nav aria-label={t("breadcrumb")} className="mb-8 text-sm text-foreground/75">
        {t("heading")}
      </nav>
      <h1 className="mb-8 text-3xl font-bold text-foreground">{t("heading")}</h1>
      {cargando ? <p role="status">{t("loading")}</p> : null}
      {error ? (
        <div role="alert" className="mb-6 rounded-xl border border-destructive p-4">
          <p>{error}</p>
          <Button className="mt-3 min-h-11" variant="secondary" onClick={() => void recargar()}>
            {t("retry")}
          </Button>
        </div>
      ) : null}
      {preferencias ? (
        <div className="space-y-10">
          <section aria-labelledby="apariencia">
            <h2 id="apariencia" className="mb-4 text-xl font-semibold">
              {t("appearance")}
            </h2>
            <fieldset className="flex flex-wrap items-center justify-between gap-4 rounded-xl bg-card p-5">
              <legend className="sr-only">{t("themeLegend")}</legend>
              <span className="font-medium">{t("theme")}</span>
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
                    {theme(tema)}
                  </label>
                ))}
              </div>
            </fieldset>
          </section>

          <section aria-labelledby="t-idioma">
            <h2 id="t-idioma" className="mb-4 scroll-mt-24 text-xl font-semibold">
              {language("label")}
            </h2>
            <p className="mb-4 text-sm text-foreground/75">{language("description")}</p>
            <LanguageSwitcher account />
          </section>

          <section aria-labelledby="privacidad">
            <h2 id="privacidad" className="mb-4 text-xl font-semibold">
              {t("privacy")}
            </h2>
            <p
              className="mb-4 rounded-lg border border-border bg-muted p-4 text-sm text-foreground"
              role="note"
            >
              {t("futureFeatures")}
            </p>
            <div className="divide-y divide-border rounded-xl bg-card px-5">
              {INTERRUPTORES.slice(0, 1).map(({ campo, titulo, descripcion }) => (
                <label
                  key={campo}
                  className="flex min-h-18 cursor-pointer items-center justify-between gap-5 py-4"
                >
                  <span>
                    <span className="block font-medium">{titulo}</span>
                    <span className="block text-sm text-foreground/75">{descripcion}</span>
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
              {t("notifications")}
            </h2>
            <div className="divide-y divide-border rounded-xl bg-card px-5">
              {INTERRUPTORES.slice(1).map(({ campo, titulo, descripcion }) => (
                <label
                  key={campo}
                  className="flex min-h-18 cursor-pointer items-center justify-between gap-5 py-4"
                >
                  <span>
                    <span className="block font-medium">{titulo}</span>
                    <span className="block text-sm text-foreground/75">{descripcion}</span>
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
              {t("account")}
            </h2>
            <p className="mb-5 text-sm text-foreground/75">{t("deactivateWarning")}</p>
            <Button
              className="min-h-11"
              ref={bajaButtonRef}
              variant="destructive"
              onClick={() => setConfirmarBaja(true)}
            >
              {t("deactivateAccount")}
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
              {t("deactivateTitle")}
            </h2>
            <p className="mt-3 text-sm text-foreground/75">{t("deactivateConfirm")}</p>
            {errorBaja && (
              <p role="alert" className="mt-4 text-sm text-destructive">
                {errorBaja}
              </p>
            )}
            <div className="mt-6 flex justify-end gap-3">
              <Button
                className="min-h-11"
                ref={cancelarRef}
                variant="secondary"
                disabled={dandoBaja}
                onClick={cerrarBaja}
              >
                {t("cancel")}
              </Button>
              <Button
                className="min-h-11"
                variant="destructive"
                disabled={dandoBaja}
                onClick={() => void desactivarCuenta()}
              >
                {dandoBaja && (
                  <LoaderCircle className="size-4 motion-safe:animate-spin" aria-hidden="true" />
                )}
                {t("deactivate")}
              </Button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
