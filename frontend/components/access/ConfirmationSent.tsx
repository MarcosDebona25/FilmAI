"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { ApiError, apiFetch } from "@/lib/api";
import { translateError } from "@/lib/errors";
import { formatCountdown, RESEND_COOLDOWN_SECONDS } from "@/lib/pending-email";
import { routes } from "@/lib/routes";

import { AccessLogo } from "./Logo";
import { FieldError } from "./fields";

/** Estado «Revisá tu correo»: reenvío con espera de 60 s entre pedidos. */
export function ConfirmationSent({ email }: { email: string }) {
  const t = useTranslations("auth.confirmation");
  const common = useTranslations("common");
  const nav = useTranslations("nav.account");
  const [remaining, setRemaining] = useState(RESEND_COOLDOWN_SECONDS);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (remaining <= 0) return;
    const timer = setTimeout(() => setRemaining((value) => value - 1), 1000);
    return () => clearTimeout(timer);
  }, [remaining]);

  async function resend() {
    if (remaining > 0 || sending) return;
    setSending(true);
    setError(null);
    try {
      await apiFetch("/api/auth/registration/resend-email/", {
        method: "POST",
        body: { email },
      });
      setRemaining(RESEND_COOLDOWN_SECONDS);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : translateError({ code: "unknown" }));
    } finally {
      setSending(false);
    }
  }

  const waiting = remaining > 0;
  return (
    <div className="flex w-full max-w-[480px] flex-col items-center gap-[22px] text-center">
      <AccessLogo className="mb-6 self-start" />
      <h1 className="mb-[15px] font-display text-[44px] leading-[0.95] sm:text-[52px]">
        {t("inboxTitle")}
      </h1>
      <p className="text-balance text-muted-foreground">
        {t("sentDescription", { email })}
        <br />
        {t("spamHint")}
      </p>
      <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-3">
        <button
          type="button"
          aria-disabled={waiting || sending}
          onClick={() => void resend()}
          className={`h-12 rounded-[10px] bg-secondary px-5 text-base font-semibold text-foreground ${waiting || sending ? "cursor-not-allowed opacity-[0.55]" : "hover:brightness-110"}`}
        >
          {common("email.resendLink")}
        </button>
        {waiting && (
          <span
            aria-live="polite"
            className="text-sm text-fg-3 [font-variant-numeric:tabular-nums]"
          >
            {t("resendCountdown", { remainingTime: formatCountdown(remaining) })}
          </span>
        )}
      </div>
      {error && <FieldError>{error}</FieldError>}
      <p className="w-full border-t border-border pt-[22px] text-muted-foreground">
        {t("alreadyConfirmedPrompt")}{" "}
        <Link href={routes.login} className="font-semibold text-foreground">
          {nav("logIn")}
        </Link>
      </p>
    </div>
  );
}
