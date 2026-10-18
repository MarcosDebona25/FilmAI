"use client";

import { useId, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { useAccount, type Preferencias } from "@/components/AccountProvider";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { ConfirmDialog } from "@/components/features/title/ConfirmDialog";
import { ErrorRetry } from "@/components/ui/ErrorRetry";
import { Switch } from "@/components/ui/switch";
import { apiFetch } from "@/lib/api";
import { routes } from "@/lib/routes";

type Interruptor = "perfil_publico" | "notif_recomendaciones" | "notif_resenas" | "notif_novedades";

/**
 * Settings según el canvas («Settings · desktop / mobile»). Sin selector de
 * tema: la app es solo oscura. «Perfil público» queda
 * aunque el canvas no lo tiene, por decisión del usuario, con el aviso de que
 * todavía no cambia nada.
 */
export default function SettingsPage() {
  const t = useTranslations();
  const legacy = useTranslations("legacy.settings");
  const router = useRouter();
  const { preferencias, cargando, error, recargar, actualizarPreferencia, limpiar } = useAccount();
  const [guardando, setGuardando] = useState<Interruptor | null>(null);
  const [confirmarBaja, setConfirmarBaja] = useState(false);
  const idioma = useId();

  async function cambiar(campo: Interruptor, valor: boolean) {
    setGuardando(campo);
    try {
      await actualizarPreferencia(campo, valor as Preferencias[typeof campo]);
    } catch {
      toast.error(legacy("saveError"));
    } finally {
      setGuardando(null);
    }
  }

  async function desactivarCuenta() {
    try {
      await apiFetch("/api/account/deactivate/", { method: "POST" });
    } catch {
      // `ConfirmDialog` muestra el mensaje del error que se lanza.
      throw new Error(legacy("deactivateError"));
    }
    limpiar();
    toast.success(legacy("deactivated"));
    router.replace(routes.home);
  }

  // Una fila del canvas: texto a la izquierda y el control a la derecha.
  function fila(campo: Interruptor, titulo: string, detalle: string) {
    const etiqueta = `${idioma}-${campo}`;
    return (
      <div
        key={campo}
        className="flex items-center gap-4 border-t border-line py-4 md:gap-6 md:py-[18px]"
      >
        <span className="flex flex-1 flex-col">
          <span id={etiqueta} className="font-semibold">
            {titulo}
          </span>
          <span className="text-sm text-fg-3">{detalle}</span>
        </span>
        <Switch
          checked={Boolean(preferencias?.[campo])}
          onChange={(valor) => void cambiar(campo, valor)}
          labelledBy={etiqueta}
          disabled={guardando !== null}
        />
      </div>
    );
  }

  const titulo2 = "font-display text-[30px] leading-none md:text-[34px]";

  return (
    <main
      id="contenido"
      className="mx-auto flex max-w-[760px] flex-col gap-9 px-5 pt-4 pb-[120px] md:gap-14 md:px-10 md:pt-12 md:pb-24"
    >
      <div className="flex flex-col gap-2.5 md:gap-3.5">
        <Link
          href={routes.profile}
          className="-ml-2.5 inline-flex h-11 items-center gap-1 self-start px-2.5 text-[15px] font-medium text-fg-2 no-underline md:hidden"
        >
          <ChevronLeft aria-hidden="true" className="size-5" />
          {t("nav.main.profileShort")}
        </Link>
        <nav
          aria-label={t("nav.main.breadcrumbLabel")}
          className="hidden text-sm text-fg-2 md:block"
        >
          <ol className="flex flex-wrap items-center gap-2">
            <li>
              <Link href={routes.profile} className="text-fg-2 hover:text-foreground">
                {t("nav.main.profileShort")}
              </Link>
            </li>
            <li aria-hidden="true">›</li>
            <li aria-current="page" className="font-semibold text-foreground">
              {t("nav.main.settings")}
            </li>
          </ol>
        </nav>
        <h1 className="font-display text-[48px] leading-none md:mb-[15px] md:text-[72px] md:leading-[0.95]">
          {t("nav.main.settings")}
        </h1>
      </div>

      {cargando && !preferencias && (
        <p role="status" className="text-fg-2">
          {legacy("loading")}
        </p>
      )}
      {error && <ErrorRetry mensaje={error} onReintentar={() => void recargar()} />}

      {preferencias && (
        <>
          {/* Id fijo: el footer lleva a `routes.language` (`/settings#t-idioma`). */}
          <section aria-labelledby="t-idioma" className="flex flex-col gap-3.5 md:gap-2">
            <h2 id="t-idioma" className={`${titulo2} scroll-mt-24 md:mb-2`}>
              {t("settings.language.label")}
            </h2>
            <div className="flex flex-col gap-3 border-y border-line py-4 md:flex-row md:items-center md:gap-6 md:py-[18px]">
              <span className="flex flex-1 flex-col">
                <span className="font-semibold">{t("settings.language.interfaceLabel")}</span>
                <span className="text-sm text-fg-3">{t("settings.language.interfaceHelp")}</span>
              </span>
              <LanguageSwitcher account />
            </div>
          </section>

          <section aria-labelledby={`${idioma}-privacidad`} className="flex flex-col gap-2">
            <h2 id={`${idioma}-privacidad`} className={`${titulo2} mb-1.5 md:mb-2`}>
              {legacy("privacy")}
            </h2>
            <p role="note" className="mb-2 text-sm text-fg-2">
              {legacy("futureFeatures")}
            </p>
            <div className="border-b border-line">
              {fila("perfil_publico", legacy("publicProfile"), legacy("publicProfileHelp"))}
            </div>
          </section>

          <section aria-labelledby={`${idioma}-notificaciones`} className="flex flex-col gap-2">
            <h2 id={`${idioma}-notificaciones`} className={`${titulo2} mb-1.5 md:mb-2`}>
              {t("settings.notifications.heading")}
            </h2>
            {/* Las descripciones dicen «para futuros correos»: hoy no se manda ninguno. */}
            <div className="border-b border-line">
              {fila(
                "notif_recomendaciones",
                t("settings.notifications.weeklyLabel"),
                legacy("weeklyHelp")
              )}
              {fila(
                "notif_resenas",
                t("settings.notifications.reviewsLabel"),
                legacy("reviewsHelp")
              )}
              {fila("notif_novedades", t("settings.notifications.newsLabel"), legacy("newsHelp"))}
            </div>
          </section>

          <section aria-labelledby={`${idioma}-legal`} className="flex flex-col gap-2">
            <h2 id={`${idioma}-legal`} className={`${titulo2} mb-1.5 md:mb-2`}>
              {t("settings.legal.heading")}
            </h2>
            <Link
              href={routes.terms}
              className="flex items-center gap-4 border-y border-line py-4 text-foreground no-underline focus-visible:outline-2 focus-visible:outline-ring md:gap-6 md:py-[18px]"
            >
              <span className="flex flex-1 flex-col">
                <span className="font-semibold">{t("nav.main.terms")}</span>
                <span className="text-sm text-fg-3">{t("settings.legal.description")}</span>
              </span>
              <ChevronRight aria-hidden="true" className="size-5 shrink-0 text-fg-3" />
            </Link>
          </section>

          <section aria-labelledby={`${idioma}-cuenta`} className="flex flex-col gap-3">
            <h2 id={`${idioma}-cuenta`} className={titulo2}>
              {t("settings.account.heading")}
            </h2>
            <p className="text-[15px] text-fg-2 md:text-base">
              {t("settings.account.deactivateWarning")}
            </p>
            <button
              type="button"
              onClick={() => setConfirmarBaja(true)}
              className="h-[52px] cursor-pointer rounded-[10px] px-[18px] font-semibold text-destructive shadow-[inset_0_0_0_1px_var(--line)] focus-visible:outline-2 focus-visible:outline-ring md:h-12 md:self-start"
            >
              {legacy("deactivateAccount")}
            </button>
          </section>
        </>
      )}

      {confirmarBaja && (
        <ConfirmDialog
          titulo={legacy("deactivateTitle")}
          // El texto aprobado (docs/decisiones.md), más largo que el del canvas.
          descripcion={legacy("deactivateConfirm")}
          confirmar={legacy("deactivate")}
          onConfirm={desactivarCuenta}
          onCancel={() => setConfirmarBaja(false)}
        />
      )}
    </main>
  );
}
