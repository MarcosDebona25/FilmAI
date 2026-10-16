"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { Check, Circle } from "lucide-react";

import { AccessShell } from "@/components/access/AccessShell";
import { ConfirmationSent } from "@/components/access/ConfirmationSent";
import { GoogleMark } from "@/components/access/GoogleMark";
import { AccessLogo } from "@/components/access/Logo";
import {
  FieldError,
  FieldOk,
  PasswordField,
  TextField,
  fieldClass,
} from "@/components/access/fields";
import { primaryButtonClass, secondaryButtonClass } from "@/components/access/styles";
import enums from "@/i18n/enums.json";
import { ApiError, apiFetch, extraerErroresPorCampo } from "@/lib/api";
import { translateError } from "@/lib/errors";
import { marcarGooglePendiente } from "@/lib/google-auth";
import { savePendingEmail } from "@/lib/pending-email";
import { passwordRules } from "@/lib/password-rules";
import { routes } from "@/lib/routes";
import { useUsernameAvailability } from "@/lib/use-username-availability";
import { useValidation } from "@/lib/use-validation";
import { maxFechaNacimiento } from "@/lib/validation";

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

const ERROR_DELAY_MS = 600;

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
  // «Sucio» = el usuario escribió o eligió algo en el campo; foco y blur no cuentan.
  const [sucios, setSucios] = useState<Partial<Record<Campo, boolean>>>({});
  const [erroresServidor, setErroresServidor] = useState<Errores>({});
  // Copia con retardo: el error de un campo de texto aparece cuando el usuario
  // hace una pausa, no en cada pulsación.
  const [diferido, setDiferido] = useState(form);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [enviadoA, setEnviadoA] = useState<string | null>(null);
  const { estado: usernameEstado, marcarOcupado } = useUsernameAvailability(
    form.nombre_usuario,
    !validarNombreUsuario(form.nombre_usuario)
  );

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

  const formularioValido =
    acepta &&
    usernameEstado === "disponible" &&
    (Object.keys(validadores) as (keyof typeof form)[]).every(
      (campo) => !validadores[campo](form[campo], form)
    );

  useEffect(() => {
    const id = setTimeout(() => setDiferido(form), ERROR_DELAY_MS);
    return () => clearTimeout(id);
  }, [form]);

  function setField(campo: keyof typeof form, valor: string) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
    setSucios((prev) => ({ ...prev, [campo]: true }));
    setErroresServidor((prev) => ({ ...prev, [campo]: undefined }));
  }

  /**
   * Error visible de un campo: solo si el usuario ya lo modificó y el valor
   * actual sigue siendo inválido. En texto espera a que haga una pausa;
   * en selección y fecha (`inmediato`) aparece al instante.
   */
  function mostrar(campo: Campo, inmediato = false): string | undefined {
    if (erroresServidor[campo]) return erroresServidor[campo];
    if (campo === "acepta_terminos" || !sucios[campo]) return undefined;
    const actual = validadores[campo](form[campo], form);
    if (!actual) return undefined;
    if (inmediato) return actual;
    return validadores[campo](diferido[campo], diferido) ? actual : undefined;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (!formularioValido) return;

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
          setErroresServidor((prev) => ({ ...prev, ...mapeados }));
          if ("nombre_usuario" in mapeados) marcarOcupado();
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
          <GoogleMark />
          {t("google.continue")}
        </button>
        <div aria-hidden="true" className="flex items-center gap-3.5 text-sm text-fg-3">
          <span className="h-px flex-1 bg-border" />
          {t("signUp.alternativeDivider")}
          <span className="h-px flex-1 bg-border" />
        </div>
        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-5">
          <div className="grid grid-cols-2 gap-4">
            <TextField
              label={common("fields.firstName")}
              name="nombre"
              autoComplete="given-name"
              maxLength={50}
              value={form.nombre}
              onChange={(e) => setField("nombre", e.target.value)}
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
              error={mostrar("fecha_nacimiento", true)}
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
                aria-invalid={mostrar("genero", true) ? true : undefined}
              >
                <option value="" disabled />
                {enums.genderValues.map((value) => (
                  <option key={value} value={value}>
                    {gender(value as "masculino")}
                  </option>
                ))}
              </select>
              {mostrar("genero", true) && <FieldError>{mostrar("genero", true)}</FieldError>}
            </div>
          </div>
          <PasswordField
            label={t("password.label")}
            name="password1"
            autoComplete="new-password"
            value={form.password1}
            onChange={(e) => setField("password1", e.target.value)}
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
            error={mostrar("password2")}
          />
          <div className="flex flex-col gap-2">
            {/* Todo el recuadro es la etiqueta: sin zonas muertas alrededor de la casilla. */}
            <label
              htmlFor="terminos"
              className={`flex cursor-pointer items-start gap-3 rounded-[10px] px-3.5 py-3 shadow-[inset_0_0_0_1px_var(--line)] ${mostrar("acepta_terminos") ? "shadow-[inset_0_0_0_1px_var(--destructive)]" : ""}`}
            >
              <input
                id="terminos"
                name="acepta_terminos"
                type="checkbox"
                checked={acepta}
                onChange={(e) => {
                  setAcepta(e.target.checked);
                  setErroresServidor((prev) => ({ ...prev, acepta_terminos: undefined }));
                }}
                aria-invalid={mostrar("acepta_terminos") ? true : undefined}
                aria-describedby="terminos-error"
                className="mt-0.5 size-5 flex-none cursor-pointer accent-primary"
              />
              <span className="flex-1 text-[15px] leading-[1.45] text-muted-foreground">
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
              </span>
            </label>
            <div id="terminos-error">
              {mostrar("acepta_terminos") && <FieldError>{mostrar("acepta_terminos")}</FieldError>}
            </div>
          </div>
          {error && <FieldError>{error}</FieldError>}
          <button
            type="submit"
            disabled={!formularioValido || loading}
            aria-describedby={formularioValido ? undefined : "registro-pendiente"}
            // Deshabilitado por formulario incompleto: bloqueado. Mientras envía: espera
            // (`primaryButtonClass` ya trae `disabled:cursor-wait`, por eso el `!`).
            className={`${primaryButtonClass} disabled:opacity-60 ${loading ? "" : "disabled:cursor-not-allowed!"}`}
          >
            {nav("signUp")}
          </button>
          {!formularioValido && (
            <p id="registro-pendiente" className="-mt-2 text-center text-[13px] text-fg-3">
              {t("signUp.submitPending")}
            </p>
          )}
        </form>
        <p className="text-center text-muted-foreground">
          {t("landing.loginPrompt")}{" "}
          <Link href={routes.login} className="font-semibold text-foreground">
            {nav("logIn")}
          </Link>
        </p>
      </div>
    </AccessShell>
  );
}
