"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Suspense, useRef, useState, type FormEvent } from "react";

import { useAccount } from "@/components/AccountProvider";
import { GoogleButton } from "@/components/GoogleButton";
import { Modal } from "@/components/Modal";
import { AccessLogo } from "@/components/access/Logo";
import { AccessShell } from "@/components/access/AccessShell";
import { FieldError, PasswordField, TextField } from "@/components/access/fields";
import { primaryButtonClass } from "@/components/access/styles";
import { synchronizeAccountLocale } from "@/lib/account-locale";
import { ApiError, apiFetch } from "@/lib/api";
import { translateError } from "@/lib/errors";
import { handleGoogleLogin } from "@/lib/google-auth";
import { routes } from "@/lib/routes";
import { useValidation } from "@/lib/use-validation";

function Divider({ children }: { children: string }) {
  return (
    <div aria-hidden="true" className="flex items-center gap-3.5 text-sm text-fg-3">
      <span className="h-px flex-1 bg-border" />
      {children}
      <span className="h-px flex-1 bg-border" />
    </div>
  );
}

function ResetPasswordDialog({ onClose }: { onClose: () => void }) {
  const t = useTranslations("auth.passwordReset");
  const common = useTranslations("common");
  const auth = useTranslations("auth");
  const { validarCorreo } = useValidation();
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const emailRef = useRef<HTMLInputElement>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const invalid = validarCorreo(email);
    if (invalid) {
      setError(invalid);
      return;
    }
    setError(null);
    setLoading(true);
    try {
      // El mensaje de éxito no revela si el correo tiene cuenta (CU-020).
      await apiFetch("/api/auth/password/reset/", { method: "POST", body: { email } });
      setSentTo(email);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : translateError({ code: "unknown" }));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal title={t("title")} onClose={onClose} busy={loading} initialFocusRef={emailRef}>
      {sentTo ? (
        <div className="mt-3 flex flex-col gap-5">
          <p role="status" className="text-muted-foreground">
            {t("sentDescription", { email: sentTo })}
          </p>
          <button type="button" onClick={onClose} className={primaryButtonClass}>
            {common("passwordReset.backToLogin")}
          </button>
        </div>
      ) : (
        <form onSubmit={onSubmit} noValidate className="mt-3 flex flex-col gap-5">
          <p className="text-muted-foreground">{t("description")}</p>
          <TextField
            ref={emailRef}
            label={common("fields.email")}
            type="email"
            autoComplete="email"
            value={email}
            error={error}
            onChange={(event) => {
              setEmail(event.target.value);
              if (error) setError(null);
            }}
          />
          <div className="flex flex-wrap justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="h-12 rounded-[10px] px-5 font-semibold text-foreground hover:bg-secondary"
            >
              {common("actions.cancel")}
            </button>
            <button
              type="submit"
              disabled={loading}
              className="h-12 rounded-[10px] bg-primary px-5 font-semibold text-primary-foreground disabled:opacity-70"
            >
              {common("passwordReset.sendLink")}
            </button>
          </div>
          <span className="sr-only">{auth("passwordReset.title")}</span>
        </form>
      )}
    </Modal>
  );
}

function ForgotPassword({ onClick }: { onClick: () => void }) {
  const t = useTranslations("auth.password");
  return (
    <button
      type="button"
      onClick={onClick}
      className="-my-3 min-h-11 text-sm font-semibold text-fg-2 underline underline-offset-[3px] hover:text-foreground"
    >
      {t("forgot")}
    </button>
  );
}

function LoginForm() {
  const t = useTranslations("auth");
  const nav = useTranslations("nav.account");
  const { recargar } = useAccount();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);

  const destination = (() => {
    const next = searchParams.get("next");
    return next && next.startsWith("/") ? next : routes.explore;
  })();

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await apiFetch("/api/auth/login/", {
        method: "POST",
        body: {
          password,
          ...(identifier.includes("@") ? { email: identifier } : { username: identifier }),
        },
      });
      await synchronizeAccountLocale();
      await recargar();
      router.refresh();
      router.push(destination);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.code === "invalid_credentials"
            ? t("login.invalidCredentials")
            : err.message
          : translateError({ code: "unknown" })
      );
    } finally {
      setLoading(false);
    }
  }

  async function onGoogle(idToken: string) {
    setError(null);
    setLoading(true);
    try {
      const result = await handleGoogleLogin(idToken);
      if (result.ok) {
        await recargar();
        router.refresh();
        router.push(destination);
      } else if (result.faltaCampos) {
        router.push(routes.completeSignup);
      } else {
        setError(result.error);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <AccessShell>
      <div className="flex w-full max-w-[400px] flex-col gap-[22px]">
        <AccessLogo className="mb-6 self-start" />
        <div>
          <h1 className="mb-3 font-display text-[48px] leading-[0.95] sm:text-[60px]">
            {nav("logIn")}
          </h1>
          <p className="hidden text-muted-foreground sm:block">{t("login.description")}</p>
        </div>
        <div className="flex justify-center">
          <GoogleButton text="signin_with" onSuccess={onGoogle} />
        </div>
        <Divider>{t("login.alternativeDivider")}</Divider>
        <form onSubmit={onSubmit} className="flex flex-col gap-[18px]">
          <TextField
            label={t("login.identifierLabel")}
            name="username"
            autoComplete="username"
            value={identifier}
            onChange={(event) => setIdentifier(event.target.value)}
            required
          />
          <PasswordField
            label={t("password.label")}
            name="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            labelAction={<ForgotPassword onClick={() => setResetOpen(true)} />}
          />
          {error && <FieldError>{error}</FieldError>}
          <button type="submit" disabled={loading} className={primaryButtonClass}>
            {nav("logIn")}
          </button>
        </form>
        <p className="text-center text-muted-foreground">
          {t("login.signUpPrompt")}{" "}
          <Link href={routes.register} className="font-semibold text-foreground">
            {nav("signUp")}
          </Link>
        </p>
      </div>
      {resetOpen && <ResetPasswordDialog onClose={() => setResetOpen(false)} />}
    </AccessShell>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}
