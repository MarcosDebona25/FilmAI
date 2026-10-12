"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Check, Circle } from "lucide-react";

import { AccessShell } from "@/components/access/AccessShell";
import { ConfirmationSent } from "@/components/access/ConfirmationSent";
import { AccessLogo } from "@/components/access/Logo";
import {
  FieldError,
  FieldOk,
  PasswordField,
  TextField,
  fieldClass,
  primaryButtonClass,
  secondaryButtonClass,
} from "@/components/access/fields";
import enums from "@/i18n/enums.json";
import { currentLocale } from "@/i18n/client";
import { ApiError, apiFetch, apiUrl, extraerErroresPorCampo } from "@/lib/api";
import { translateError } from "@/lib/errors";
import { marcarGooglePendiente } from "@/lib/google-auth";
import { savePendingEmail } from "@/lib/pending-email";
import { passwordRules } from "@/lib/password-rules";
import { routes } from "@/lib/routes";
import { useValidation } from "@/lib/use-validation";

type Campo =
  | "nombre"
  | "apellido"
  | "nombre_usuario"
  | "correo"
  | "fecha_nacimiento"
  | "genero"
  | "password1"
  | "password2"
  | "acepta_terminos";

type Errores = Partial<Record<Campo, string>>;

/** Fecha máxima para el selector: hoy −13 años (el backend es quien valida). */
function maxFechaNacimiento(): string {
  const d = new Date();
  d.setFullYear(d.getFullYear() - 13);
  return d.toISOString().slice(0, 10);
}

export default function RegisterPage() {
  const t = useTranslations("auth");
  const common = useTranslations("common");
  const nav = useTranslations("nav.account");
  const gender = useTranslations("enums.gender");
  const errors = useTranslations("errors.codes");
  const router = useRouter();
  const {
    validarApellido,
    validarConfirmacion,
    validarCorreo,
    validarFechaNacimiento,
    validarNombre,
    validarNombreUsuario,
    validarPassword,
  } = useValidation();

  const [form, setForm] = useState<Record<Exclude<Campo, "acepta_terminos">, string>>({
    nombre: "",
    apellido: "",
    nombre_usuario: "",
    correo: "",
    fecha_nacimiento: "",
    genero: "",
    password1: "",
    password2: "",
  });
  const [acepta, setAcepta] = useState(false);
  const [errores, setErrores] = useState<Errores>({});
  const [tocados, setTocados] = useState<Partial<Record<Campo, boolean>>>({});
  const [usernameEstado, setUsernameEstado] = useState<
    "idle" | "checking" | "disponible" | "ocupado"
  >("idle");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [enviadoA, setEnviadoA] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const validadores: Record<
    Exclude<Campo, "acepta_terminos">,
    (valor: string, actual: typeof form) => string | null
  > = {
    nombre: (v) => validarNombre(v),
    apellido: (v) => validarApellido(v),
    nombre_usuario: (v) => validarNombreUsuario(v),
    correo: (v) => validarCorreo(v),
    fecha_nacimiento: (v) => validarFechaNacimiento(v),
    genero: (v) => (v ? null : errors("required")),
    password1: (v) => validarPassword(v),
    password2: (v, actual) => validarConfirmacion(actual.password1, v),
  };

  function setField(campo: keyof typeof form, valor: string) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
  }

  function onBlurCampo(campo: keyof typeof form) {
    setTocados((prev) => ({ ...prev, [campo]: true }));
    setErrores((prev) => ({
      ...prev,
      [campo]: validadores[campo](form[campo], form) ?? undefined,
    }));
  }

  function mostrar(campo: Campo): string | undefined {
    return tocados[campo] ? errores[campo] : undefined;
  }

  // Disponibilidad del nombre de usuario en vivo, con debounce.
  useEffect(() => {
    const valor = form.nombre_usuario.trim();
    clearTimeout(debounceRef.current);
    if (!valor || validarNombreUsuario(valor)) {
      setUsernameEstado("idle");
      return;
    }
    setUsernameEstado("checking");
    const controller = new AbortController();
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await fetch(
          apiUrl(`/api/auth/username-available/?username=${encodeURIComponent(valor)}`),
          { signal: controller.signal, headers: { "Accept-Language": currentLocale() } }
        );
        if (!res.ok) {
          // Un error (p. ej. 429 (Too Many Requests)) no significa «ocupado».
          setUsernameEstado("idle");
          return;
        }
        const data: { disponible?: boolean } = await res.json();
        setUsernameEstado(data.disponible ? "disponible" : "ocupado");
      } catch {
        if (!controller.signal.aborted) setUsernameEstado("idle");
      }
    }, 400);
    return () => {
      clearTimeout(debounceRef.current);
      controller.abort();
    };
  }, [form.nombre_usuario, validarNombreUsuario]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    const nuevos: Errores = {};
    for (const campo of Object.keys(validadores) as (keyof typeof form)[]) {
      const mensaje = validadores[campo](form[campo], form);
      if (mensaje) nuevos[campo] = mensaje;
    }
    if (!acepta) nuevos.acepta_terminos = t("signUp.termsRequiredError");
    if (Object.keys(nuevos).length > 0) {
      setErrores(nuevos);
      setTocados(Object.fromEntries(Object.keys(nuevos).map((c) => [c, true])));
      return;
    }

    setLoading(true);
    try {
      await apiFetch("/api/auth/registration/", {
        method: "POST",
        body: {
          correo: form.correo,
          nombre_usuario: form.nombre_usuario,
          nombre: form.nombre.trim(),
          apellido: form.apellido.trim(),
          fecha_nacimiento: form.fecha_nacimiento,
          genero: form.genero,
          password1: form.password1,
          password2: form.password2,
          acepta_terminos: true,
        },
      });
      savePendingEmail(form.correo);
      setEnviadoA(form.correo);
    } catch (err) {
      if (err instanceof ApiError) {
        const porCampo = extraerErroresPorCampo(err);
        const mapeados: Errores = {};
        for (const campo of [...Object.keys(validadores), "acepta_terminos"] as Campo[]) {
          if (porCampo[campo]) mapeados[campo] = porCampo[campo];
        }
        if (Object.keys(mapeados).length > 0) {
          setErrores((prev) => ({ ...prev, ...mapeados }));
          setTocados((prev) => ({
            ...prev,
            ...Object.fromEntries(Object.keys(mapeados).map((c) => [c, true])),
          }));
          if ("nombre_usuario" in mapeados) setUsernameEstado("ocupado");
        } else {
          setError(err.message);
        }
      } else {
        setError(translateError({ code: "unknown" }));
      }
    } finally {
      setLoading(false);
    }
  }

  function onGoogle() {
    marcarGooglePendiente();
    router.push(routes.completeSignup);
  }

  if (enviadoA) {
    return (
      <AccessShell>
        <ConfirmationSent email={enviadoA} />
      </AccessShell>
    );
  }

  const reglas = passwordRules(form.password1);
  const reglaTextos = {
    length: t("password.lengthRule"),
    case: t("password.caseRule"),
    number: t("password.numberRule"),
    symbol: t("password.symbolRule"),
  } as const;
  const usernameValido = !validarNombreUsuario(form.nombre_usuario);
  const usernameError = mostrar("nombre_usuario");
  const usernameStatus =
    usernameError || !usernameValido ? null : usernameEstado === "disponible" ? (
      <FieldOk id="usuario-estado">{t("signUp.usernameAvailable")}</FieldOk>
    ) : usernameEstado === "ocupado" ? (
      <FieldError>{errors("username_already_used")}</FieldError>
    ) : null;

  return (
    <AccessShell>
      <div className="flex w-full max-w-[480px] flex-col gap-[22px]">
        <AccessLogo className="mb-3 self-start" />
        <div>
          <h1 className="mb-3 font-display text-[48px] leading-[0.95] sm:text-[60px]">
            {nav("signUp")}
          </h1>
          <p className="text-muted-foreground">{t("signUp.description")}</p>
        </div>
        <button type="button" onClick={onGoogle} className={secondaryButtonClass}>
          <span aria-hidden="true" className="grid size-6 place-items-center rounded-full bg-white">
            <svg className="size-4" viewBox="0 0 48 48">
              <path
                fill="#EA4335"
                d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
              />
              <path
                fill="#4285F4"
                d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
              />
              <path
                fill="#FBBC05"
                d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
              />
              <path
                fill="#34A853"
                d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
              />
            </svg>
          </span>
          {t("google.continue")}
        </button>
        <div aria-hidden="true" className="flex items-center gap-3.5 text-sm text-fg-3">
          <span className="h-px flex-1 bg-border" />
          {t("signUp.alternativeDivider")}
          <span className="h-px flex-1 bg-border" />
        </div>
        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-5">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <TextField
              label={common("fields.firstName")}
              name="nombre"
              autoComplete="given-name"
              maxLength={50}
              value={form.nombre}
              onChange={(e) => setField("nombre", e.target.value)}
              onBlur={() => onBlurCampo("nombre")}
              error={mostrar("nombre")}
              help={t("signUp.nameHelp")}
            />
            <TextField
              label={common("fields.lastName")}
              name="apellido"
              autoComplete="family-name"
              maxLength={50}
              value={form.apellido}
              onChange={(e) => setField("apellido", e.target.value)}
              onBlur={() => onBlurCampo("apellido")}
              error={mostrar("apellido")}
              help={t("signUp.nameHelp")}
            />
          </div>
          <TextField
            label={common("fields.username")}
            name="nombre_usuario"
            autoComplete="username"
            prefix="@"
            value={form.nombre_usuario}
            onChange={(e) => setField("nombre_usuario", e.target.value)}
            onBlur={() => onBlurCampo("nombre_usuario")}
            error={usernameError}
            status={usernameStatus}
            help={t("signUp.usernameHelp")}
          />
          <TextField
            label={common("fields.email")}
            name="correo"
            type="email"
            autoComplete="email"
            value={form.correo}
            onChange={(e) => setField("correo", e.target.value)}
            onBlur={() => onBlurCampo("correo")}
            error={mostrar("correo")}
          />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <TextField
              label={common("fields.birthDate")}
              name="fecha_nacimiento"
              type="date"
              max={maxFechaNacimiento()}
              value={form.fecha_nacimiento}
              onChange={(e) => setField("fecha_nacimiento", e.target.value)}
              onBlur={() => onBlurCampo("fecha_nacimiento")}
              error={mostrar("fecha_nacimiento")}
              help={t("signUp.minimumAgeHelp")}
            />
            <div className="flex flex-col gap-2">
              <label htmlFor="genero" className="text-sm font-semibold">
                {t("signUp.genderLabel")}
              </label>
              <select
                id="genero"
                name="genero"
                className={fieldClass}
                value={form.genero}
                onChange={(e) => setField("genero", e.target.value)}
                onBlur={() => onBlurCampo("genero")}
                aria-invalid={mostrar("genero") ? true : undefined}
              >
                <option value="" disabled />
                {enums.genderValues.map((value) => (
                  <option key={value} value={value}>
                    {gender(value as "masculino")}
                  </option>
                ))}
              </select>
              {mostrar("genero") && <FieldError>{mostrar("genero")}</FieldError>}
            </div>
          </div>
          <PasswordField
            label={t("password.label")}
            name="password1"
            autoComplete="new-password"
            value={form.password1}
            onChange={(e) => setField("password1", e.target.value)}
            onBlur={() => onBlurCampo("password1")}
            error={mostrar("password1")}
          >
            <ul className="flex flex-col gap-1.5 text-sm" aria-label={t("password.label")}>
              {(Object.keys(reglas) as (keyof typeof reglas)[]).map((regla) => (
                <li key={regla} className="flex items-center gap-2">
                  {reglas[regla] ? (
                    <Check aria-hidden="true" className="size-[15px] flex-none text-ok" />
                  ) : (
                    <Circle aria-hidden="true" className="size-[15px] flex-none text-fg-3" />
                  )}
                  <span className={reglas[regla] ? "text-muted-foreground" : "text-foreground"}>
                    {reglaTextos[regla]}
                    <span className="sr-only">
                      {" "}
                      {reglas[regla]
                        ? t("password.ruleSatisfiedLabel")
                        : t("password.ruleMissingLabel")}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          </PasswordField>
          <PasswordField
            label={common("fields.passwordConfirm")}
            name="password2"
            autoComplete="new-password"
            value={form.password2}
            onChange={(e) => setField("password2", e.target.value)}
            onBlur={() => onBlurCampo("password2")}
            error={
              mostrar("password2") ??
              (tocados.password2 && form.password2 && form.password2 !== form.password1
                ? t("password.confirmMismatch")
                : undefined)
            }
          />
          <div className="flex flex-col gap-2">
            <div
              className={`flex items-start gap-3 rounded-[10px] px-3.5 py-3 shadow-[inset_0_0_0_1px_var(--line)] ${mostrar("acepta_terminos") ? "shadow-[inset_0_0_0_1px_var(--destructive)]" : ""}`}
            >
              <input
                id="terminos"
                name="acepta_terminos"
                type="checkbox"
                checked={acepta}
                onChange={(e) => {
                  setAcepta(e.target.checked);
                  setErrores((prev) => ({ ...prev, acepta_terminos: undefined }));
                }}
                aria-invalid={mostrar("acepta_terminos") ? true : undefined}
                aria-describedby="terminos-error"
                className="mt-0.5 size-5 flex-none cursor-pointer accent-primary"
              />
              <label
                htmlFor="terminos"
                className="flex-1 cursor-pointer text-[15px] leading-[1.45] text-muted-foreground"
              >
                {t.rich("signUp.termsAcceptance", {
                  terms: (chunks) => (
                    <Link
                      href={routes.terms}
                      target="_blank"
                      rel="noopener"
                      className="font-semibold text-foreground underline underline-offset-[3px]"
                    >
                      {chunks}
                      <span className="sr-only"> {t("signUp.termsNewTabHint")}</span>
                    </Link>
                  ),
                })}
              </label>
            </div>
            <div id="terminos-error">
              {mostrar("acepta_terminos") && <FieldError>{mostrar("acepta_terminos")}</FieldError>}
            </div>
          </div>
          {error && <FieldError>{error}</FieldError>}
          <button
            type="submit"
            aria-disabled={!acepta || loading}
            className={`${primaryButtonClass} ${!acepta ? "opacity-60" : ""}`}
          >
            {nav("signUp")}
          </button>
        </form>
        <p className="border-t border-border pt-[22px] text-center text-muted-foreground">
          {t("landing.loginPrompt")}{" "}
          <Link href={routes.login} className="font-semibold text-foreground">
            {nav("logIn")}
          </Link>
        </p>
      </div>
    </AccessShell>
  );
}
