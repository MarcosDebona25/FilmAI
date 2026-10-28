"use client";

import Link from "next/link";
import { CircleAlert } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { CountrySelect } from "@/components/CountrySelect";
import { GoogleButton } from "@/components/GoogleButton";
import { AccessShell } from "@/components/access/AccessShell";
import { GoogleMark } from "@/components/access/GoogleMark";
import { AccessLogo } from "@/components/access/Logo";
import { FieldError, FieldOk, TextField, fieldClass } from "@/components/access/fields";
import type { AppLocale } from "@/i18n/config";
import enums from "@/i18n/enums.json";
import { fieldErrors, translateError, type CodedError } from "@/lib/errors";
import {
  completarRegistroGoogle,
  limpiarGooglePendiente,
  tieneGooglePendiente,
} from "@/lib/google-auth";
import { routes } from "@/lib/routes";
import { useUsernameAvailability } from "@/lib/use-username-availability";
import { useValidation } from "@/lib/use-validation";
import { maxFechaNacimiento } from "@/lib/validation";

type Campo = "nombre_usuario" | "pais" | "fecha_nacimiento" | "genero";
const CAMPOS: Campo[] = ["nombre_usuario", "pais", "fecha_nacimiento", "genero"];
const ERROR_DELAY_MS = 600;

/**
 * Alta con Google (canvas «Complete sign-up (Google)», A-06): una cuenta nueva
 * que tocó «Continue with Google» completa username, nacimiento, género y
 * términos, y confirma con el botón oficial de Google, inactivo hasta que el
 * formulario es válido. El id_token es de un solo uso: se pide uno fresco acá.
 */
export default function CompletarGooglePage() {
  const t = useTranslations("auth.completeSignUp");
  const signUp = useTranslations("auth.signUp");
  const common = useTranslations("common");
  const gender = useTranslations("enums.gender");
  const errors = useTranslations("errors.codes");
  const locale = useLocale() as AppLocale;
  const router = useRouter();
  const { validarFechaNacimiento, validarNombreUsuario } = useValidation();

  const [form, setForm] = useState<Record<Campo, string>>({
    nombre_usuario: "",
    pais: "",
    fecha_nacimiento: "",
    genero: "",
  });
  const [acepta, setAcepta] = useState(false);
  // «Sucio» = el usuario escribió o eligió algo; foco y blur no muestran errores.
  const [sucios, setSucios] = useState<Partial<Record<Campo, boolean>>>({});
  // El error del backend se guarda como código y se traduce al renderizar.
  const [fallo, setFallo] = useState<CodedError | null>(null);
  const [corregidos, setCorregidos] = useState<Partial<Record<string, boolean>>>({});
  const [diferido, setDiferido] = useState(form);
  const [loading, setLoading] = useState(false);
  const { estado: usernameEstado, marcarOcupado } = useUsernameAvailability(
    form.nombre_usuario,
    !validarNombreUsuario(form.nombre_usuario)
  );

  // Solo se llega acá tras «Continue with Google» en login o registro, que
  // marcan el flujo pendiente. Sin la marca no es un alta con Google válida.
  useEffect(() => {
    if (!tieneGooglePendiente()) router.replace(routes.login);
  }, [router]);

  useEffect(() => {
    const id = setTimeout(() => setDiferido(form), ERROR_DELAY_MS);
    return () => clearTimeout(id);
  }, [form]);

  // Errores de campo del backend que el usuario todavía no corrigió.
  const servidor = fallo ? fieldErrors(fallo, locale) : {};
  for (const campo of Object.keys(corregidos)) delete servidor[campo];
  const hayErroresDeCampo = Object.keys(servidor).length > 0;
  const mensajeGeneral =
    fallo && !hayErroresDeCampo
      ? translateError(fallo.errors?.find((entry) => !entry.field) ?? fallo, locale)
      : null;

  function validarCampo(campo: Campo, valor: string): string | null {
    if (campo === "nombre_usuario") return validarNombreUsuario(valor);
    if (campo === "fecha_nacimiento") return validarFechaNacimiento(valor);
    if (campo === "pais") return valor ? null : common("country.required");
    return valor ? null : errors("required");
  }

  function setField(campo: Campo, valor: string) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
    setSucios((prev) => ({ ...prev, [campo]: true }));
    setCorregidos((prev) => ({ ...prev, [campo]: true }));
  }

  /**
   * Error visible de un campo: solo si el usuario ya lo modificó. El texto del
   * username espera a una pausa; la fecha y el género aparecen al instante.
   */
  function mostrar(campo: Campo): string | undefined {
    if (servidor[campo]) return servidor[campo];
    if (!sucios[campo]) return undefined;
    const actual = validarCampo(campo, form[campo]);
    if (!actual) return undefined;
    if (campo !== "nombre_usuario") return actual;
    return validarCampo(campo, diferido[campo]) ? actual : undefined;
  }

  const formularioValido =
    acepta &&
    usernameEstado === "disponible" &&
    CAMPOS.every((campo) => !validarCampo(campo, form[campo]));

  async function onGoogle(idToken: string) {
    // El botón solo está activo con el formulario válido; esto es un resguardo
    // para no gastar el id_token (de un solo uso) con datos inválidos.
    if (loading || !formularioValido) return;
    setFallo(null);
    setLoading(true);
    try {
      const result = await completarRegistroGoogle(idToken, {
        nombre_usuario: form.nombre_usuario,
        pais: form.pais,
        fecha_nacimiento: form.fecha_nacimiento,
        genero: form.genero,
        acepta_terminos: true,
      });
      if (result.ok) {
        router.push(routes.explore);
        return;
      }
      setCorregidos({});
      setFallo(result.error);
      if (result.error.errors?.some((entry) => entry.field === "nombre_usuario")) marcarOcupado();
    } finally {
      setLoading(false);
    }
  }

  const usernameError = mostrar("nombre_usuario");
  const usernameStatus =
    usernameError || validarNombreUsuario(form.nombre_usuario) ? null : usernameEstado ===
      "disponible" ? (
      <FieldOk>{signUp("usernameAvailable")}</FieldOk>
    ) : usernameEstado === "ocupado" ? (
      <FieldError>{errors("username_already_used")}</FieldError>
    ) : usernameEstado === "reservado" ? (
      <FieldError>{errors("username_not_allowed")}</FieldError>
    ) : null;
  const terminosError = servidor.acepta_terminos;
  const activo = formularioValido && !loading;

  return (
    <AccessShell poster="band">
      <div className="flex w-full max-w-[480px] flex-col gap-5 lg:gap-[22px]">
        <div className="hidden lg:block">
          <AccessLogo className="self-start" />
        </div>
        <div className="flex flex-col gap-3.5">
          <p className="inline-flex h-9 items-center gap-2.5 self-start rounded-full bg-card pr-3.5 pl-1.5 text-sm font-semibold text-muted-foreground shadow-[inset_0_0_0_1px_var(--line)]">
            <GoogleMark />
            {t("badge")}
          </p>
          <div>
            <h1 className="mb-3 font-display text-[48px] leading-[0.95] lg:mb-[15px] lg:text-[60px]">
              {t("title")}
            </h1>
            <p className="text-pretty text-muted-foreground">{t("description")}</p>
          </div>
        </div>
        {hayErroresDeCampo && (
          <p
            role="alert"
            className="flex items-start gap-2.5 rounded-[10px] bg-destructive/12 px-3.5 py-3 text-[15px] leading-[1.45] text-foreground shadow-[inset_0_0_0_1px_var(--destructive)]"
          >
            <CircleAlert
              aria-hidden="true"
              className="mt-0.5 size-[15px] flex-none text-destructive"
            />
            {t("fixHighlighted")}
          </p>
        )}
        <form
          onSubmit={(event: FormEvent) => event.preventDefault()}
          noValidate
          className="flex flex-col gap-5 lg:gap-[22px]"
        >
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 sm:gap-4">
            <TextField
              label={common("fields.username")}
              name="nombre_usuario"
              autoComplete="username"
              prefix="@"
              value={form.nombre_usuario}
              onChange={(e) => setField("nombre_usuario", e.target.value)}
              error={usernameError}
              status={usernameStatus}
              help={signUp("usernameHelp")}
            />
            <CountrySelect
              value={form.pais}
              onChange={(code) => setField("pais", code)}
              onBlur={() => setSucios((prev) => ({ ...prev, pais: true }))}
              error={mostrar("pais")}
            />
          </div>
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 sm:gap-4">
            <TextField
              label={common("fields.birthDate")}
              name="fecha_nacimiento"
              type="date"
              lang={locale}
              max={maxFechaNacimiento()}
              value={form.fecha_nacimiento}
              onChange={(e) => setField("fecha_nacimiento", e.target.value)}
              error={mostrar("fecha_nacimiento")}
              help={signUp("minimumAgeHelp")}
            />
            <div className="flex flex-col gap-2">
              <label htmlFor="genero" className="text-sm font-semibold">
                {signUp("genderLabel")}
              </label>
              <select
                id="genero"
                name="genero"
                className={fieldClass}
                value={form.genero}
                onChange={(e) => setField("genero", e.target.value)}
                aria-invalid={mostrar("genero") ? true : undefined}
              >
                <option value="" disabled>
                  {t("genderPlaceholder")}
                </option>
                {enums.genderValues.map((value) => (
                  <option key={value} value={value}>
                    {gender(value as "masculino")}
                  </option>
                ))}
              </select>
              {mostrar("genero") && <FieldError>{mostrar("genero")}</FieldError>}
            </div>
          </div>
          <div className="flex flex-col gap-2">
            {/* Todo el recuadro es la etiqueta: sin zonas muertas alrededor de la casilla. */}
            <label
              htmlFor="terminos"
              className={`flex cursor-pointer items-start gap-3 rounded-[10px] px-3.5 py-3 ${terminosError ? "shadow-[inset_0_0_0_1px_var(--destructive)]" : "shadow-[inset_0_0_0_1px_var(--field-border)]"}`}
            >
              <input
                id="terminos"
                name="acepta_terminos"
                type="checkbox"
                checked={acepta}
                onChange={(e) => {
                  setAcepta(e.target.checked);
                  setCorregidos((prev) => ({ ...prev, acepta_terminos: true }));
                }}
                aria-invalid={terminosError ? true : undefined}
                aria-describedby="terminos-error"
                className="mt-0.5 size-5 flex-none cursor-pointer accent-primary"
              />
              <span className="flex-1 text-[15px] leading-[1.45] text-muted-foreground">
                {signUp.rich("termsAcceptance", {
                  terms: (chunks) => (
                    <Link
                      href={routes.terms}
                      target="_blank"
                      rel="noopener"
                      className="font-semibold text-foreground underline underline-offset-[3px]"
                    >
                      {chunks}
                      <span className="sr-only"> {signUp("termsNewTabHint")}</span>
                    </Link>
                  ),
                })}
              </span>
            </label>
            <div id="terminos-error">
              {terminosError && <FieldError>{terminosError}</FieldError>}
            </div>
          </div>
          {mensajeGeneral && <FieldError>{mensajeGeneral}</FieldError>}
          <div className="flex flex-col gap-2.5">
            {/* `inert`: sin el formulario válido el botón de Google no se puede usar. */}
            <div
              data-testid="google-confirm"
              inert={!activo}
              className={activo ? undefined : "opacity-40"}
            >
              <GoogleButton
                text="signup_with"
                theme="outline"
                fullWidth
                onSuccess={onGoogle}
                onError={() => setFallo({ code: "google_authentication_failed" })}
              />
            </div>
            {!formularioValido && (
              <p className="text-center text-[13px] text-fg-3">{signUp("submitPending")}</p>
            )}
          </div>
        </form>
        <p className="text-center">
          <Link
            href={routes.login}
            onClick={limpiarGooglePendiente}
            className="font-semibold text-foreground"
          >
            {t("cancel")}
          </Link>
        </p>
      </div>
    </AccessShell>
  );
}
