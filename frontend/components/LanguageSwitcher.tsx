"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useId, useState, useRef, useEffect } from "react";
import { useAccount } from "./AccountProvider";
import { persistLocale } from "@/i18n/client";
import { locales, type AppLocale } from "@/i18n/config";

/** Selector EN | ES. El nombre completo del idioma queda como etiqueta accesible. */
export function LanguageSwitcher({ account = false }: { account?: boolean }) {
  const locale = useLocale();
  const t = useTranslations("settings.language");
  const router = useRouter();
  const { actualizarPreferencia } = useAccount();
  const name = useId();
  const inputs = useRef<Partial<Record<AppLocale, HTMLInputElement>>>({});
  const restoreFocus = useRef<AppLocale | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!saving && restoreFocus.current) {
      inputs.current[restoreFocus.current]?.focus();
      restoreFocus.current = null;
    }
  }, [saving]);

  async function change(next: AppLocale) {
    if (saving || next === locale) return;
    restoreFocus.current = next;
    setSaving(true);
    setError(false);
    try {
      if (account) await actualizarPreferencia("idioma", next);
      else {
        persistLocale(next);
        router.refresh();
      }
    } catch {
      setError(true);
    } finally {
      setSaving(false);
    }
  }
  return (
    <div>
      <fieldset
        aria-busy={saving}
        className="inline-flex rounded-full border border-border bg-card p-0.5"
        role="radiogroup"
        aria-label={t("selectLabel")}
      >
        <legend className="sr-only">{t("selectLabel")}</legend>
        {locales.map((language) => (
          <label
            key={language}
            className={`relative flex min-h-11 min-w-11 touch-manipulation md:min-h-10 md:min-w-10 cursor-pointer items-center justify-center rounded-full px-3 text-sm font-semibold focus-within:ring-2 focus-within:ring-ring ${locale === language ? "bg-selected text-selected-foreground" : "text-foreground hover:bg-muted"} ${saving ? "cursor-wait opacity-70" : ""}`}
          >
            <input
              className="absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0"
              type="radio"
              name={name}
              ref={(element) => {
                if (element) inputs.current[language] = element;
              }}
              value={language}
              checked={locale === language}
              disabled={saving}
              onChange={() => void change(language)}
              aria-label={t(language === "en" ? "english" : "spanish")}
            />
            <span className="pointer-events-none" aria-hidden="true" lang={language}>
              {language.toUpperCase()}
            </span>
          </label>
        ))}
      </fieldset>
      <p role="status" className="mt-2 text-sm text-foreground/75">
        {saving ? t("changing") : ""}
      </p>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {t("saveError")}
        </p>
      )}
    </div>
  );
}
