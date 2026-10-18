"use client";

import { Check, CircleAlert } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useState, type FormEvent } from "react";

import { AccessShell } from "@/components/access/AccessShell";
import { ConfirmationSent } from "@/components/access/ConfirmationSent";
import { AccessLogo } from "@/components/access/Logo";
import { FieldError, TextField } from "@/components/access/fields";
import { primaryButtonClass } from "@/components/access/styles";
import { ApiError, apiFetch } from "@/lib/api";
import { translateError } from "@/lib/errors";
import { clearPendingEmail, readPendingEmail } from "@/lib/pending-email";
import { routes } from "@/lib/routes";
import { useValidation } from "@/lib/use-validation";

type Estado = "cargando" | "ok" | "vencido";

function ExpiredLink() {
  const t = useTranslations("auth.confirmation");
  const common = useTranslations("common");
  const { validarCorreo } = useValidation();
  const [email, setEmail] = useState("");
  const [askEmail, setAskEmail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sentTo, setSentTo] = useState<string | null>(null);

  async function resend(target: string) {
    setLoading(true);
    setError(null);
    try {
      await apiFetch("/api/auth/registration/resend-email/", {
        method: "POST",
        body: { email: target },
      });
      setSentTo(target);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : translateError({ code: "unknown" }));
    } finally {
      setLoading(false);
    }
  }

  function onResend() {
    // La clave del enlace no trae el correo: se usa el de este navegador y, si
    // no está, se lo pide.
    const stored = readPendingEmail();
    if (stored) void resend(stored);
    else setAskEmail(true);
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const invalid = validarCorreo(email);
    if (invalid) setError(invalid);
    else void resend(email);
  }

  if (sentTo) return <ConfirmationSent email={sentTo} />;

  return (
    <div className="flex w-full max-w-[480px] flex-col gap-[22px]">
      <AccessLogo className="mb-6 self-start" />
      <div className="mb-[15px] flex items-center gap-4">
        <span
          aria-hidden="true"
          className="grid size-[52px] flex-none place-items-center rounded-full bg-secondary text-destructive"
        >
          <CircleAlert className="size-6" />
        </span>
        <h1 className="font-display text-[40px] leading-[0.95] sm:text-[52px]">
          {t("invalidTitle")}
        </h1>
      </div>
      <p className="text-balance text-muted-foreground">{t("invalidDescription")}</p>
      {askEmail ? (
        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
          <TextField
            label={common("fields.email")}
            type="email"
            autoComplete="email"
            value={email}
            error={error}
            onChange={(event) => {
              setEmail(event.target.value);
              setError(null);
            }}
          />
          <button type="submit" disabled={loading} className={primaryButtonClass}>
            {common("email.resendLink")}
          </button>
        </form>
      ) : (
        <>
          {error && <FieldError>{error}</FieldError>}
          <button
            type="button"
            disabled={loading}
            onClick={onResend}
            className={primaryButtonClass}
          >
            {common("email.resendLink")}
          </button>
        </>
      )}
    </div>
  );
}

export default function ConfirmarCorreoPage() {
  const t = useTranslations("auth.confirmation");
  const nav = useTranslations("nav.account");
  const params = useParams<{ key: string }>();
  const [estado, setEstado] = useState<Estado>("cargando");

  useEffect(() => {
    const rawKey = params?.key;
    if (!rawKey) {
      setEstado("vencido");
      return;
    }
    // useParams() devuelve valores URL-encoded; la clave contiene ":" que
    // llega como "%3A" y rompe la verificación del backend.
    let key: string;
    try {
      key = decodeURIComponent(rawKey);
    } catch {
      setEstado("vencido");
      return;
    }
    apiFetch("/api/auth/registration/verify-email/", { method: "POST", body: { key } })
      .then(() => {
        clearPendingEmail();
        setEstado("ok");
      })
      .catch((err: unknown) => {
        // «Ya confirmada» es, para quien llega, una cuenta confirmada.
        if (err instanceof ApiError && err.code === "already_confirmed") setEstado("ok");
        else setEstado("vencido");
      });
  }, [params]);

  return (
    <AccessShell>
      {estado === "cargando" && (
        <p role="status" className="text-muted-foreground">
          {t("loading")}
        </p>
      )}
      {estado === "ok" && (
        <div className="flex w-full max-w-[480px] flex-col gap-[22px]">
          <AccessLogo className="mb-6 self-start" />
          <div className="mb-[15px] flex items-center gap-4">
            <span
              aria-hidden="true"
              className="grid size-[52px] flex-none place-items-center rounded-full bg-secondary text-ok"
            >
              <Check className="size-6" strokeWidth={2.2} />
            </span>
            <h1 className="font-display text-[40px] leading-[0.95] sm:text-[52px]">
              {t("successTitle")}
            </h1>
          </div>
          <p className="text-balance text-muted-foreground">{t("successDescription")}</p>
          <Link href={routes.login} className={primaryButtonClass}>
            {nav("logIn")}
          </Link>
        </div>
      )}
      {estado === "vencido" && <ExpiredLink />}
    </AccessShell>
  );
}
