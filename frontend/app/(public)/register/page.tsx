"use client";

import Image from "next/image";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useSyncExternalStore, type FormEvent } from "react";
import { Check, ChevronLeft, ChevronRight, Circle } from "lucide-react";

import type { AvatarOption } from "@/components/AccountProvider";
import { AccessShell } from "@/components/access/AccessShell";
import { CountrySelect } from "@/components/CountrySelect";
import { ConfirmationSent } from "@/components/access/ConfirmationSent";
import { GoogleMark } from "@/components/access/GoogleMark";
import { SignupAvatarDialog } from "@/components/access/SignupAvatarDialog";
import { DateField } from "@/components/access/DateField";
import { AccessLogo } from "@/components/access/Logo";
import {
  FieldError,
  FieldMessage,
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
import { cn } from "@/lib/utils";

type Campo =
  | "nombre"
  | "apellido"
  | "nombre_usuario"
  | "pais"
  | "correo"
  | "fecha_nacimiento"
  | "genero"
  | "password1"
  | "password2"
  | "acepta_terminos";

type CampoTexto = Exclude<Campo, "acepta_terminos">;
// El avatar no se valida en el cliente, pero el servidor puede rechazarlo.
type Errores = Partial<Record<Campo | "avatar_id", string>>;
type Paso = 1 | 2 | 3;

const ERROR_DELAY_MS = 600;
const TOTAL_PASOS = 3;

/** Campos de cada paso, en el orden en que se ven (canvas, sección 16). */
const CAMPOS_POR_PASO: Record<Paso, (Campo | "avatar_id")[]> = {
  1: ["correo", "password1", "password2"],
  2: ["nombre", "apellido", "nombre_usuario", "fecha_nacimiento", "genero", "pais"],
  3: ["avatar_id", "acepta_terminos"],
};
const PASOS: Paso[] = [1, 2, 3];

/** Selector del control que el usuario ve para un campo. */
function selectorDe(campo: Campo | "avatar_id") {
  if (campo === "pais") return "#pais";
  if (campo === "avatar_id") return "[data-elegir-avatar]";
  return `[name="${campo}"]`;
}

/**
 * Dónde cae el foco al entrar a un paso: su primer campo. Se piden todos los del
 * paso y gana el primero que exista (sin catálogo de avatares no hay «Choose»).
 */
function primerCampoDe(paso: Paso) {
  return CAMPOS_POR_PASO[paso].map(selectorDe).join(", ");
}

function pasoDe(campo: Campo | "avatar_id"): Paso {
  return PASOS.find((paso) => CAMPOS_POR_PASO[paso].includes(campo)) ?? 3;
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

  const [form, setForm] = useState<Record<CampoTexto, string>>({
    nombre: "",
    apellido: "",
    nombre_usuario: "",
    pais: "",
    correo: "",
    fecha_nacimiento: "",
    genero: "",
    password1: "",
    password2: "",
  });
  const [acepta, setAcepta] = useState(false);
  // Catálogo público de avatares y el elegido. Arranca en el primero del catálogo
  // (el mismo que el backend asigna si el alta no trae `avatar_id`). Si el
  // catálogo no carga, el selector no aparece y el alta sigue sin ese campo.
  const [avatares, setAvatares] = useState<AvatarOption[]>([]);
  const [avatarId, setAvatarId] = useState<number | null>(null);
  const [eligiendoAvatar, setEligiendoAvatar] = useState(false);
  const [paso, setPaso] = useState<Paso>(1);
  // Pasos en los que ya se apretó el botón principal con algo inválido: desde
  // ahí sus campos muestran el error aunque nadie los haya tocado.
  const [intentados, setIntentados] = useState<Partial<Record<Paso, boolean>>>({});
  // Pedido de foco: el efecto lo cumple cuando el paso nuevo ya está en pantalla.
  const [foco, setFoco] = useState<{ selector: string } | null>(null);
  const formulario = useRef<HTMLFormElement>(null);
  // Falso en el HTML del servidor y hasta que React toma la página: antes de eso
  // el botón principal enviaría el formulario a la URL, contraseña incluida.
  const hidratado = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );
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

  const validadores: Record<CampoTexto, (valor: string, actual: typeof form) => string | null> = {
    nombre: (v) => validarNombre(v),
    apellido: (v) => validarApellido(v),
    nombre_usuario: (v) => validarNombreUsuario(v),
    pais: (v) => (v ? null : common("country.required")),
    correo: (v) => validarCorreo(v),
    fecha_nacimiento: (v) => validarFechaNacimiento(v),
    genero: (v) => (v ? null : errors("required")),
    password1: (v) => validarPassword(v),
    password2: (v, actual) => validarConfirmacion(actual.password1, v),
  };

  function pasoValido(cual: Paso) {
    if (cual === 3) return acepta;
    const camposValidos = (CAMPOS_POR_PASO[cual] as CampoTexto[]).every(
      (campo) => !validadores[campo](form[campo], form)
    );
    return cual === 2 ? camposValidos && usernameEstado === "disponible" : camposValidos;
  }

  useEffect(() => {
    let activo = true;
    apiFetch<AvatarOption[]>("/api/avatars/")
      .then((lista) => {
        if (!activo || lista.length === 0) return;
        setAvatares(lista);
        setAvatarId((actual) => actual ?? lista[0].id);
      })
      .catch(() => {});
    return () => {
      activo = false;
    };
  }, []);

  useEffect(() => {
    const id = setTimeout(() => setDiferido(form), ERROR_DELAY_MS);
    return () => clearTimeout(id);
  }, [form]);

  useEffect(() => {
    if (!foco) return;
    formulario.current?.querySelector<HTMLElement>(foco.selector)?.focus();
  }, [foco]);

  /** Cambia de paso y lleva el foco a su primer campo (o al que se pida). */
  function irA(destino: Paso, selector = primerCampoDe(destino)) {
    setPaso(destino);
    setError(null);
    setFoco({ selector });
  }

  function setField(campo: keyof typeof form, valor: string) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
    setSucios((prev) => ({ ...prev, [campo]: true }));
    setErroresServidor((prev) => ({ ...prev, [campo]: undefined }));
  }

  /**
   * Error visible de un campo: solo si el usuario ya lo modificó y el valor
   * actual sigue siendo inválido. En texto espera a que haga una pausa;
   * en selección y fecha (`inmediato`) aparece al instante. Si ya se intentó
   * pasar de ese paso, el error se ve aunque el campo esté sin tocar.
   */
  function mostrar(campo: Campo, inmediato = false): string | undefined {
    if (erroresServidor[campo]) return erroresServidor[campo];
    if (campo === "acepta_terminos")
      return intentados[3] && !acepta ? errors("terms_not_accepted") : undefined;
    const intentado = intentados[pasoDe(campo)];
    if (!sucios[campo] && !intentado) return undefined;
    const actual = validadores[campo](form[campo], form);
    if (!actual) return undefined;
    if (inmediato || intentado) return actual;
    return validadores[campo](diferido[campo], diferido) ? actual : undefined;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (loading) return;

    // Un paso inválido se queda donde está y muestra los errores de sus campos.
    if (!pasoValido(paso)) {
      setIntentados((prev) => ({ ...prev, [paso]: true }));
      return;
    }
    if (paso < TOTAL_PASOS) {
      irA((paso + 1) as Paso);
      return;
    }

    setLoading(true);
    try {
      await apiFetch("/api/auth/registration/", {
        method: "POST",
        body: {
          correo: form.correo,
          nombre_usuario: form.nombre_usuario,
          pais: form.pais,
          nombre: form.nombre.trim(),
          apellido: form.apellido.trim(),
          fecha_nacimiento: form.fecha_nacimiento,
          genero: form.genero,
          password1: form.password1,
          password2: form.password2,
          acepta_terminos: true,
          ...(avatarId !== null && { avatar_id: avatarId }),
        },
      });
      savePendingEmail(form.correo);
      setEnviadoA(form.correo);
    } catch (err) {
      if (err instanceof ApiError) {
        const porCampo = extraerErroresPorCampo(err);
        const mapeados: Errores = {};
        // En el orden de los pasos: el primero con error decide a cuál se vuelve.
        const enOrden = PASOS.flatMap((cual) => CAMPOS_POR_PASO[cual]);
        for (const campo of enOrden) {
          if (porCampo[campo]) mapeados[campo] = porCampo[campo];
        }
        const primero = enOrden.find((campo) => mapeados[campo]);
        if (primero) {
          setErroresServidor((prev) => ({ ...prev, ...mapeados }));
          if ("nombre_usuario" in mapeados) marcarOcupado();
          // Decisión del 15/11/2026: la página vuelve al paso del primer campo
          // con error y lo deja enfocado, con el mensaje en ese campo.
          irA(pasoDe(primero), selectorDe(primero));
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
  // «En uso» y «reservado» son errores del campo (reemplazan la ayuda);
  // «disponible» es el ✓ dentro del campo, y la ayuda sigue a la vista.
  const usernameError =
    mostrar("nombre_usuario") ??
    (!usernameValido
      ? undefined
      : usernameEstado === "ocupado"
        ? errors("username_already_used")
        : usernameEstado === "reservado"
          ? errors("username_not_allowed")
          : undefined);
  const usernameOk =
    usernameValido && !usernameError && usernameEstado === "disponible"
      ? t("signUp.usernameAvailable")
      : null;

  /**
   * Celda de un paso. El que no está activo conserva su tamaño (`invisible` es
   * `visibility: hidden`) pero queda fuera del teclado y de los lectores de
   * pantalla: `inert` saca todo su contenido del foco y del árbol de accesibilidad.
   */
  const celda = (cual: Paso) => ({
    "data-paso": cual,
    inert: paso !== cual,
    "aria-hidden": paso !== cual || undefined,
    className: cn("[grid-area:1/1]", paso !== cual && "invisible"),
  });

  const avatarElegido = avatares.find((avatar) => avatar.id === avatarId);
  const errorTerminos = mostrar("acepta_terminos");

  return (
    <AccessShell>
      <form
        ref={formulario}
        onSubmit={onSubmit}
        noValidate
        className="flex w-full max-w-[30rem] flex-col gap-[1.375rem]"
      >
        <AccessLogo className="self-start" />
        <div
          role="progressbar"
          aria-label={t("signUp.progressLabel")}
          aria-valuemin={0}
          aria-valuemax={TOTAL_PASOS}
          aria-valuenow={paso}
          aria-valuetext={t("signUp.stepOf", { step: String(paso), total: String(TOTAL_PASOS) })}
          className="relative mt-0.5 h-1 overflow-hidden rounded-full bg-raised-2"
        >
          <span
            aria-hidden="true"
            style={{ width: paso === TOTAL_PASOS ? "100%" : `${((paso * 100) / 3).toFixed(2)}%` }}
            className="absolute inset-y-0 left-0 rounded-full bg-primary transition-[width] duration-[400ms] ease-[cubic-bezier(.2,.7,.2,1)] motion-reduce:transition-none"
          />
        </div>
        <div>
          <h1 className="mb-3 font-display text-[2.75rem] leading-[0.95] sm:text-[3.75rem]">
            {t("signUp.title")}
          </h1>
          <p className="text-muted-foreground">{t("signUp.subtitle")}</p>
        </div>
        {/* Los tres pasos están siempre montados y comparten la misma celda de la
            grilla: la celda mide lo que el paso más alto, en cualquier idioma y
            ancho, así el botón principal y «Back» no se mueven al cambiar de paso.
            Sin `overflow`: el calendario y la lista de países se abren por fuera. */}
        <div className="grid grid-cols-[minmax(0,1fr)]">
          <div {...celda(1)}>
            <div className="flex flex-col gap-5">
              <button type="button" onClick={onGoogle} className={secondaryButtonClass}>
                <GoogleMark />
                {t("google.continue")}
              </button>
              <div aria-hidden="true" className="flex items-center gap-3.5 text-sm text-fg-3">
                <span className="h-px flex-1 bg-border" />
                {t("signUp.alternativeDivider")}
                <span className="h-px flex-1 bg-border" />
              </div>
              <TextField
                label={common("fields.email")}
                name="correo"
                required
                type="email"
                autoComplete="email"
                value={form.correo}
                onChange={(e) => setField("correo", e.target.value)}
                error={mostrar("correo")}
                reserveMessage
              />
              <PasswordField
                label={t("password.label")}
                name="password1"
                required
                autoComplete="new-password"
                value={form.password1}
                onChange={(e) => setField("password1", e.target.value)}
                error={mostrar("password1")}
                reserveMessage
              >
                <ul
                  className="grid grid-cols-1 gap-x-4 gap-y-1.5 text-[0.8125rem] sm:grid-cols-2"
                  aria-label={t("password.label")}
                >
                  {(Object.keys(reglas) as (keyof typeof reglas)[]).map((regla) => (
                    <li key={regla} className="flex items-center gap-1.5">
                      {reglas[regla] ? (
                        <Check aria-hidden="true" className="size-[0.9375rem] flex-none text-ok" />
                      ) : (
                        <Circle
                          aria-hidden="true"
                          className="size-[0.9375rem] flex-none text-fg-3"
                        />
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
                required
                autoComplete="new-password"
                value={form.password2}
                onChange={(e) => setField("password2", e.target.value)}
                error={mostrar("password2")}
                reserveMessage
              />
            </div>
          </div>
          <div {...celda(2)}>
            <div className="flex flex-col gap-5">
              <div className="grid grid-cols-2 items-start gap-4">
                <TextField
                  label={common("fields.firstName")}
                  name="nombre"
                  required
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
                  required
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
                required
                autoComplete="username"
                prefix="@"
                value={form.nombre_usuario}
                onChange={(e) => setField("nombre_usuario", e.target.value)}
                error={usernameError}
                ok={usernameOk}
                help={t("signUp.usernameHelp")}
              />
              <div className="grid grid-cols-2 items-start gap-4">
                <DateField
                  label={common("fields.birthDate")}
                  name="fecha_nacimiento"
                  required
                  value={form.fecha_nacimiento}
                  onChange={(iso) => setField("fecha_nacimiento", iso)}
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
                    required
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
                  <FieldMessage error={mostrar("genero", true)} reserve />
                </div>
              </div>
              <CountrySelect
                id="pais"
                value={form.pais}
                onChange={(code) => setField("pais", code)}
                onBlur={() => setSucios((prev) => ({ ...prev, pais: true }))}
                error={mostrar("pais", true)}
                required
                reserveMessage
              />
            </div>
          </div>
          <div {...celda(3)}>
            <div className="flex flex-col gap-[1.375rem]">
              {avatarId !== null && avatarElegido && (
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-4 rounded-[0.625rem] px-3.5 py-3 shadow-[inset_0_0_0_1px_var(--line)]">
                    <span className="relative size-14 flex-none overflow-hidden rounded-full bg-raised-2">
                      <Image
                        src={avatarElegido.src}
                        alt=""
                        fill
                        sizes="56px"
                        className="object-cover"
                      />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold">
                        {t.rich("signUp.avatarOptional", {
                          hint: (chunks) => <span className="font-medium text-fg-3">{chunks}</span>,
                        })}
                      </p>
                      <p className="text-[0.8125rem] text-fg-3">{t("signUp.avatarLaterHelp")}</p>
                    </div>
                    <button
                      type="button"
                      data-elegir-avatar
                      aria-haspopup="dialog"
                      onClick={() => setEligiendoAvatar(true)}
                      className="h-11 flex-none cursor-pointer rounded-[0.625rem] bg-secondary px-[1.125rem] font-semibold text-foreground hover:bg-line focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                    >
                      {t("signUp.avatarChoose")}
                    </button>
                  </div>
                  {erroresServidor.avatar_id && (
                    <FieldError>{erroresServidor.avatar_id}</FieldError>
                  )}
                </div>
              )}
              <div className="flex flex-col gap-2">
                {/* Todo el recuadro es la etiqueta: sin zonas muertas alrededor de la casilla. */}
                <label
                  htmlFor="terminos"
                  className={`flex cursor-pointer items-start gap-3 rounded-[0.625rem] px-3.5 py-3 ${errorTerminos ? "shadow-[inset_0_0_0_1px_var(--destructive)]" : "shadow-[inset_0_0_0_1px_var(--field-border)]"}`}
                >
                  <input
                    id="terminos"
                    name="acepta_terminos"
                    required
                    type="checkbox"
                    checked={acepta}
                    onChange={(e) => {
                      setAcepta(e.target.checked);
                      setErroresServidor((prev) => ({ ...prev, acepta_terminos: undefined }));
                    }}
                    aria-invalid={errorTerminos ? true : undefined}
                    aria-describedby="terminos-error"
                    className="mt-0.5 size-5 flex-none cursor-pointer accent-primary"
                  />
                  <span className="flex-1 text-[0.9375rem] leading-[1.45] text-muted-foreground">
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
                {/* Renglón reservado: el error no empuja lo que sigue al aparecer. */}
                <div id="terminos-error" className="min-h-[1lh] text-[0.8125rem]">
                  {errorTerminos && <FieldError>{errorTerminos}</FieldError>}
                </div>
              </div>
              {error && <FieldError>{error}</FieldError>}
            </div>
          </div>
        </div>
        <div className="flex flex-col gap-2.5">
          {/* `type="submit"`: Enter en cualquier campo hace lo mismo que el botón. */}
          <button
            type="submit"
            disabled={!hidratado || loading}
            className={`${primaryButtonClass} gap-2.5`}
          >
            {paso < TOTAL_PASOS ? (
              <>
                {t("signUp.continue")}
                <ChevronRight aria-hidden="true" className="size-5" />
              </>
            ) : (
              t("signUp.createAccount")
            )}
          </button>
          <div className="flex min-h-11 items-center justify-between gap-3">
            {/* En el paso 1 no se ve ni se puede usar, pero guarda su lugar. */}
            <button
              type="button"
              onClick={() => irA(Math.max(1, paso - 1) as Paso)}
              aria-label={t("signUp.backToStep", { step: String(Math.max(1, paso - 1)) })}
              style={{ visibility: paso > 1 ? "visible" : "hidden" }}
              className="-ml-1 inline-flex h-11 cursor-pointer items-center gap-1.5 rounded-lg pr-2.5 pl-1 text-[0.9375rem] font-semibold text-fg-2 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
            >
              <ChevronLeft aria-hidden="true" className="size-[1.125rem]" />
              {t("signUp.back")}
            </button>
            <p className="text-[0.9375rem] text-muted-foreground">
              {t("landing.loginPrompt")}{" "}
              <Link href={routes.login} className="font-semibold text-foreground">
                {nav("logIn")}
              </Link>
            </p>
          </div>
        </div>
      </form>
      {eligiendoAvatar && avatarId !== null && (
        <SignupAvatarDialog
          avatares={avatares}
          avatarId={avatarId}
          onUse={(id) => {
            setAvatarId(id);
            setErroresServidor((prev) => ({ ...prev, avatar_id: undefined }));
            setEligiendoAvatar(false);
          }}
          onClose={() => setEligiendoAvatar(false)}
        />
      )}
    </AccessShell>
  );
}
