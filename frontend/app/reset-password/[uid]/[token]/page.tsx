"use client";
import { routes } from "@/lib/routes";

import { useLocale, useTranslations } from "next-intl";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, useRef, type FormEvent } from "react";

import { Eye, EyeOff, LoaderCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError, apiFetch } from "@/lib/api";
import { validarPassword, validarConfirmacion } from "@/lib/validation";
import { validationError } from "@/lib/validation-error";
import { translateError, type CodedError } from "@/lib/errors";

const inputClass =
  "w-full rounded-lg border border-field-border bg-background px-3 py-2 text-base text-foreground outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40";

class EnlaceInvalido extends Error {}

// decodeURIComponent lanza URIError ante secuencias inválidas (p.ej. "%" suelto
// en el enlace): eso es un enlace malformado, no un fallo de contraseña.
function decodificarParametro(valor?: string): string | undefined {
  try {
    return valor ? decodeURIComponent(valor) : undefined;
  } catch {
    throw new EnlaceInvalido();
  }
}

type Estado = "formulario" | "ok" | "enlace_invalido";

export default function RestablecerContrasenaPage() {
  const t = useTranslations("auth.newPassword");
  const common = useTranslations("common");

  const locale = useLocale();

  const params = useParams<{ uid: string; token: string }>();
  const [estado, setEstado] = useState<Estado>("formulario");

  const [password, setPassword] = useState("");
  const [confirmacion, setConfirmacion] = useState("");
  const [mostrarPassword, setMostrarPassword] = useState(false);
  const [mostrarConfirmacion, setMostrarConfirmacion] = useState(false);
  const [errorPassword, setErrorPassword] = useState<CodedError | null>(null);
  const [errorConfirmacion, setErrorConfirmacion] = useState<CodedError | null>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const confirmationRef = useRef<HTMLInputElement>(null);
  const [loading, setLoading] = useState(false);

  function validarEnBlur(
    valor: string,
    set: (msg: CodedError | null) => void,
    validador: () => string | null
  ) {
    set(valor ? validationError(validador()) : null);
  }

  // CU-020: el enlace es válido durante 1 hora. Si el backend responde
  // `codigo: invalido` (token vencido o manipulado), se muestra la pantalla
  // de enlace inválido en lugar del formulario.
  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const errPass = validarPassword(password);
    const errConf = validarConfirmacion(password, confirmacion);
    if (errPass || errConf) {
      setErrorPassword(validationError(errPass));
      setErrorConfirmacion(validationError(errConf));
      (errPass ? passwordRef : confirmationRef).current?.focus();
      return;
    }
    setErrorPassword(null);
    setErrorConfirmacion(null);
    setLoading(true);
    try {
      await apiFetch("/api/auth/password/reset/confirm/", {
        method: "POST",
        body: {
          uid: decodificarParametro(params?.uid),
          token: decodificarParametro(params?.token),
          password1: password,
          password2: confirmacion,
        },
      });
      setEstado("ok");
    } catch (err) {
      if (err instanceof EnlaceInvalido) {
        setEstado("enlace_invalido");
        return;
      }
      if (err instanceof ApiError && err.status === 400) {
        if (err.code === "link_invalid" || err.code === "link_expired") {
          setEstado("enlace_invalido");
          return;
        }
        const passwordError = err.errors.find((entry) =>
          ["password1", "new_password1"].includes(entry.field ?? "")
        );
        const confirmationError = err.errors.find((entry) =>
          ["password2", "new_password2"].includes(entry.field ?? "")
        );
        setErrorPassword(passwordError ?? null);
        setErrorConfirmacion(confirmationError ?? (!passwordError ? err : null));
        (passwordError ? passwordRef : confirmationRef).current?.focus();
      } else {
        setErrorConfirmacion(err instanceof ApiError ? err : { code: "unknown" });
      }
    } finally {
      setLoading(false);
    }
  }

  if (estado === "ok") {
    return (
      <main id="contenido" className="flex min-h-screen items-center justify-center p-6">
        <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 text-center">
          <p className="mb-4 text-2xl font-bold text-foreground">FilmAI</p>
          <h1 className="mb-3 text-2xl font-bold text-foreground">{t("successTitle")}</h1>
          <p className="mb-6 text-sm text-foreground/75">{t("successDescription")}</p>
          <Link href={routes.login} className="text-primary hover:underline">
            {t("goToLogin")}
          </Link>
        </div>
      </main>
    );
  }

  if (estado === "enlace_invalido") {
    return (
      <main id="contenido" className="flex min-h-screen items-center justify-center p-6">
        <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8 text-center">
          <p className="mb-4 text-2xl font-bold text-foreground">FilmAI</p>
          <h1 className="mb-3 text-2xl font-bold text-foreground">{t("invalidTitle")}</h1>
          <p className="mb-6 text-sm text-foreground/75">{t("invalidDescription")}</p>
          <Link href={routes.login} className="text-primary hover:underline">
            {common("passwordReset.backToLogin")}
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main id="contenido" className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8">
        <p className="mb-4 text-center text-2xl font-bold text-foreground">FilmAI</p>
        <h1 className="mb-1 text-2xl font-bold text-foreground">{t("title")}</h1>
        <p className="mb-6 text-sm text-foreground/75">{t("description")}</p>

        <form noValidate onSubmit={onSubmit} className="flex flex-col gap-4">
          <div>
            <label htmlFor="nueva-password" className="mb-1 block text-sm text-foreground/75">
              {common("password.newLabel")}
            </label>
            <div className="relative">
              <input
                id="nueva-password"
                ref={passwordRef}
                className={`${inputClass} pr-12`}
                type={mostrarPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onBlur={() =>
                  validarEnBlur(password, setErrorPassword, () => validarPassword(password))
                }
                autoComplete="new-password"
                aria-invalid={Boolean(errorPassword)}
                required
              />
              <button
                type="button"
                onClick={() => setMostrarPassword((v) => !v)}
                className="absolute inset-y-0 right-0 flex w-11 items-center justify-center text-foreground/75 focus-visible:outline-2 focus-visible:outline-ring"
                aria-label={t("togglePasswordLabel")}
              >
                {mostrarPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
            <p className="mt-1 text-xs text-foreground/75">{t("passwordHelp")}</p>
            {errorPassword && (
              <p className="mt-1 text-sm text-destructive" role="alert">
                {translateError(errorPassword, locale, "password1")}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="confirmar-password" className="mb-1 block text-sm text-foreground/75">
              {common("fields.passwordConfirm")}
            </label>
            <div className="relative">
              <input
                id="confirmar-password"
                ref={confirmationRef}
                aria-invalid={Boolean(errorConfirmacion)}
                className={`${inputClass} pr-12`}
                type={mostrarConfirmacion ? "text" : "password"}
                value={confirmacion}
                onChange={(e) => setConfirmacion(e.target.value)}
                onBlur={() =>
                  validarEnBlur(confirmacion, setErrorConfirmacion, () =>
                    validarConfirmacion(password, confirmacion)
                  )
                }
                autoComplete="new-password"
                required
              />
              <button
                type="button"
                onClick={() => setMostrarConfirmacion((v) => !v)}
                className="absolute inset-y-0 right-0 flex w-11 items-center justify-center text-foreground/75 focus-visible:outline-2 focus-visible:outline-ring"
                aria-label={t("toggleConfirmationLabel")}
              >
                {mostrarConfirmacion ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
              </button>
            </div>
            {errorConfirmacion && (
              <p className="mt-1 text-sm text-destructive" role="alert">
                {translateError(errorConfirmacion, locale, "password2")}
              </p>
            )}
          </div>

          <Button
            className="min-h-11"
            type="submit"
            aria-busy={loading}
            disabled={loading}
            size="lg"
          >
            {loading && (
              <LoaderCircle className="size-4 motion-safe:animate-spin" aria-hidden="true" />
            )}
            {t("save")}
          </Button>
        </form>
      </div>
    </main>
  );
}
