"use client";

import { ChevronRight, CircleAlert } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useSyncExternalStore, type FormEvent } from "react";

import { CountrySelect } from "@/components/CountrySelect";
import { GoogleButton } from "@/components/GoogleButton";
import { AccessShell } from "@/components/access/AccessShell";
import { GoogleMark } from "@/components/access/GoogleMark";
import { DateField } from "@/components/access/DateField";
import { AccessLogo } from "@/components/access/Logo";
import { SignupAvatarDialog } from "@/components/access/SignupAvatarDialog";
import { FieldError, FieldMessage, TextField, fieldClass } from "@/components/access/fields";
import {
  SignupAvatarField,
  SignupBackButton,
  SignupProgress,
  SignupTerms,
  celdaDePaso,
  useSignupAvatars,
} from "@/components/access/signup-steps";
import { primaryButtonClass } from "@/components/access/styles";
import type { AppLocale } from "@/i18n/config";
import enums from "@/i18n/enums.json";
import { fieldErrors, translateError, type CodedError } from "@/lib/errors";
import {
  completarRegistroGoogle,
  limpiarGooglePendiente,
  origenGooglePendiente,
} from "@/lib/google-auth";
import { routes } from "@/lib/routes";
import { useUsernameAvailability } from "@/lib/use-username-availability";
import { useValidation } from "@/lib/use-validation";
import { cn } from "@/lib/utils";

type Campo = "nombre_usuario" | "fecha_nacimiento" | "genero" | "pais";
/** El paso 1 fue «Continue with Google»: esta pantalla son el 2 y el 3. */
type Paso = 2 | 3;

/** Campos del paso 2, en el orden en que se ven. */
const CAMPOS: Campo[] = ["nombre_usuario", "fecha_nacimiento", "genero", "pais"];
const ERROR_DELAY_MS = 600;
const ID_ERROR_PASO_3 = "alta-google-error";

/** Selector del control que el usuario ve para un campo. */
function selectorDe(campo: Campo) {
  return campo === "pais" ? "#pais" : `[name="${campo}"]`;
}

/**
 * Dónde cae el foco al entrar a un paso: su primer campo. En el 3 gana el
 * primero que exista (sin catálogo de avatares no hay «Choose»).
 */
const PRIMER_CAMPO: Record<Paso, string> = {
  2: selectorDe("nombre_usuario"),
  3: '[data-elegir-avatar], [name="acepta_terminos"]',
};

const avisoClass =
  "flex items-start gap-2.5 rounded-[0.625rem] px-3.5 py-3 text-[0.9375rem] leading-[1.45]";

/**
 * Alta con Google (canvas, sección 16: «Complete sign-up (Google)»). Es el
 * mismo registro de 3 pasos que el del correo: «Continue with Google» fue el
 * paso 1, así que se llega acá en el 2 (usuario, nacimiento, género y país) y
 * el 3 es el avatar y los Términos. La última acción es el botón oficial de
 * Google, porque su id_token es de un solo uso y hay que pedir uno fresco.
 *
 * Como en `/register`, los dos pasos comparten una celda de la grilla: nada se
 * mueve al cambiar de paso ni al aparecer un error.
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
    fecha_nacimiento: "",
    genero: "",
    pais: "",
  });
  const [acepta, setAcepta] = useState(false);
  const { avatares, avatarId, setAvatarId } = useSignupAvatars();
  const [eligiendoAvatar, setEligiendoAvatar] = useState(false);
  const [paso, setPaso] = useState<Paso>(2);
  // Ya se apretó «Continue» con algo inválido: desde ahí los campos del paso 2
  // muestran el error aunque nadie los haya tocado.
  const [intentado, setIntentado] = useState(false);
  // Pedido de foco: el efecto lo cumple cuando el paso nuevo ya está en pantalla.
  const [foco, setFoco] = useState<{ selector: string } | null>(null);
  const formulario = useRef<HTMLFormElement>(null);
  // Falso en el HTML del servidor y hasta que React toma la página: antes de eso
  // «Continue» enviaría el formulario a la URL.
  const hidratado = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  );
  // De dónde se vino (Sign up o Log in): está en `sessionStorage`, así que en el
  // HTML del servidor todavía no se sabe.
  const origen = useSyncExternalStore(
    () => () => {},
    origenGooglePendiente,
    () => null
  );
  // «Sucio» = el usuario escribió o eligió algo; foco y blur no muestran errores.
  const [sucios, setSucios] = useState<Partial<Record<Campo, boolean>>>({});
  // El error del backend se guarda como código y se traduce al renderizar.
  const [fallo, setFallo] = useState<CodedError | null>(null);
  const [corregidos, setCorregidos] = useState<Partial<Record<string, boolean>>>({});
  const [diferido, setDiferido] = useState(form);
  const [loading, setLoading] = useState(false);
  // «Continue» apretado mientras se verificaba el usuario: el clic espera a que
  // la consulta termine y ahí se decide si avanza.
  const [continuarPendiente, setContinuarPendiente] = useState(false);
  const { estado: usernameEstado, marcarOcupado } = useUsernameAvailability(
    form.nombre_usuario,
    !validarNombreUsuario(form.nombre_usuario)
  );

  // Solo se llega acá tras «Continue with Google» en login o registro, que
  // marcan el flujo pendiente. Sin la marca no es un alta con Google válida.
  useEffect(() => {
    if (!origenGooglePendiente()) router.replace(routes.login);
  }, [router]);

  useEffect(() => {
    const id = setTimeout(() => setDiferido(form), ERROR_DELAY_MS);
    return () => clearTimeout(id);
  }, [form]);

  // Solo «en uso» y «reservado» bloquean. Si la consulta falló (red o 429
  // (Too Many Requests)) el estado es «idle» y se deja pasar: el backend valida
  // el usuario al confirmar y su error vuelve al paso 2.
  const usernameRechazado = usernameEstado === "ocupado" || usernameEstado === "reservado";

  // La consulta del usuario terminó con un «Continue» esperándola: disponible
  // (o sin respuesta) avanza; en uso o reservado se queda y muestra los errores.
  useEffect(() => {
    if (!continuarPendiente || usernameEstado === "checking") return;
    setContinuarPendiente(false);
    if (usernameRechazado) {
      setIntentado(true);
      return;
    }
    setPaso(3);
    setFoco({ selector: PRIMER_CAMPO[3] });
  }, [continuarPendiente, usernameEstado, usernameRechazado]);

  useEffect(() => {
    if (!foco) return;
    formulario.current?.querySelector<HTMLElement>(foco.selector)?.focus();
  }, [foco]);

  // Errores de campo del backend que el usuario todavía no corrigió.
  const servidor = fallo ? fieldErrors(fallo, locale) : {};
  for (const campo of Object.keys(corregidos)) delete servidor[campo];
  // El aviso acompaña a los errores del paso 2: hay que volver a tocar el botón
  // de Google, que quedó en el paso 3.
  const avisoVisible = CAMPOS.some((campo) => servidor[campo]);
  const errorTerminos = servidor.acepta_terminos;
  // Un fallo que no apunta a nada de lo que se ve (correo ya registrado, Google
  // caído) se muestra entero en el paso 3.
  const sinCampoVisible =
    fallo !== null &&
    ![...CAMPOS, "acepta_terminos", "avatar_id"].some((campo) =>
      fallo.errors?.some((entry) => entry.field === campo)
    );
  const errorPaso3 = sinCampoVisible
    ? translateError(fallo.errors?.find((entry) => !entry.field) ?? fallo, locale)
    : servidor.avatar_id;

  function validarCampo(campo: Campo, valor: string): string | null {
    if (campo === "nombre_usuario") return validarNombreUsuario(valor);
    if (campo === "fecha_nacimiento") return validarFechaNacimiento(valor);
    if (campo === "pais") return valor ? null : common("country.required");
    return valor ? null : errors("required");
  }

  const paso2Valido =
    !usernameRechazado && CAMPOS.every((campo) => !validarCampo(campo, form[campo]));

  /** Cambia de paso y lleva el foco a su primer campo (o al que se pida). */
  function irA(destino: Paso, selector = PRIMER_CAMPO[destino]) {
    setContinuarPendiente(false);
    setPaso(destino);
    setFoco({ selector });
  }

  function setField(campo: Campo, valor: string) {
    setForm((prev) => ({ ...prev, [campo]: valor }));
    setSucios((prev) => ({ ...prev, [campo]: true }));
    setCorregidos((prev) => ({ ...prev, [campo]: true }));
    // Editar el paso cancela el «Continue» que esperaba la consulta del usuario.
    setContinuarPendiente(false);
  }

  /**
   * Error visible de un campo: solo si el usuario ya lo modificó y el valor
   * sigue siendo inválido. El texto del username espera a una pausa; selección
   * y fecha (`inmediato`) aparecen al instante. Tras un «Continue» inválido el
   * error se ve aunque el campo esté sin tocar.
   */
  function mostrar(campo: Campo, inmediato = false): string | undefined {
    if (servidor[campo]) return servidor[campo];
    if (!sucios[campo] && !intentado) return undefined;
    const actual = validarCampo(campo, form[campo]);
    if (!actual) return undefined;
    if (inmediato || intentado) return actual;
    return validarCampo(campo, diferido[campo]) ? actual : undefined;
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    // En el paso 3 la acción es el botón de Google; Enter no la reemplaza.
    if (paso !== 2 || continuarPendiente) return;
    // Un paso inválido se queda donde está y muestra los errores de sus campos.
    if (!paso2Valido) {
      setIntentado(true);
      return;
    }
    // Todavía no se sabe si el usuario está libre: el clic queda pendiente.
    if (usernameEstado === "checking") {
      setContinuarPendiente(true);
      return;
    }
    irA(3);
  }

  function onBack() {
    if (paso === 3) {
      irA(2);
      return;
    }
    // En el paso 2 se abandona el alta: se vuelve a la pantalla de origen.
    const destino = origenGooglePendiente() === "register" ? routes.register : routes.login;
    limpiarGooglePendiente();
    router.push(destino);
  }

  async function onGoogle(idToken: string) {
    // El botón solo está activo con los Términos aceptados; esto es un resguardo
    // para no gastar el id_token (de un solo uso) con datos inválidos.
    if (loading || !acepta) return;
    if (!paso2Valido) {
      setIntentado(true);
      irA(2);
      return;
    }
    setFallo(null);
    setLoading(true);
    try {
      const result = await completarRegistroGoogle(idToken, {
        nombre_usuario: form.nombre_usuario,
        pais: form.pais,
        fecha_nacimiento: form.fecha_nacimiento,
        genero: form.genero,
        acepta_terminos: true,
        ...(avatarId !== null && { avatar_id: avatarId }),
      });
      if (result.ok) {
        router.push(routes.explore);
        return;
      }
      setCorregidos({});
      setFallo(result.error);
      const rechazados = result.error.errors?.map((entry) => entry.field) ?? [];
      if (rechazados.includes("nombre_usuario")) marcarOcupado();
      // Un error de un campo del paso 2 vuelve a ese paso, con el foco en el
      // campo. Los de Términos, avatar y los generales se quedan en el 3.
      const primero = CAMPOS.find((campo) => rechazados.includes(campo));
      if (primero) irA(2, selectorDe(primero));
    } finally {
      setLoading(false);
    }
  }

  const usernameValido = !validarNombreUsuario(form.nombre_usuario);
  // Igual que en el registro: «en uso» y «reservado» son errores del campo y
  // «disponible» es el ✓ dentro del campo.
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
      ? signUp("usernameAvailable")
      : null;
  const avatarElegido = avatares.find((avatar) => avatar.id === avatarId);
  const googleActivo = acepta && !loading;
  const aviso = (
    <>
      <CircleAlert aria-hidden="true" className="mt-0.5 size-[0.9375rem] flex-none" />
      {t("fixHighlighted")}
    </>
  );

  return (
    <AccessShell>
      <form
        ref={formulario}
        onSubmit={onSubmit}
        noValidate
        className="flex w-full max-w-[30rem] flex-col gap-[1.375rem]"
      >
        <AccessLogo className="self-start" />
        <SignupProgress paso={paso} desde={1} />
        <div>
          <h1 className="mb-3 font-display text-[2.75rem] leading-[0.95] sm:text-[3.75rem]">
            {signUp("title")}
          </h1>
          <p className="flex items-start gap-2.5 text-muted-foreground sm:items-center">
            <GoogleMark />
            {t("googleLine")}
          </p>
        </div>
        {/* Los dos pasos están siempre montados y comparten la misma celda de la
            grilla: la celda mide lo que el paso más alto, en cualquier idioma y
            ancho, así la acción y «Back» no se mueven al cambiar de paso.
            Sin `overflow`: el calendario y la lista de países se abren por fuera. */}
        <div className="grid grid-cols-[minmax(0,1fr)]">
          <div {...celdaDePaso(2, paso)}>
            <div className="flex flex-col gap-5">
              {/* El aviso del servidor tiene su lugar desde el principio, así no
                  empuja el formulario al aparecer. La copia invisible guarda el
                  alto; la región `role="alert"` existe siempre y recibe el texto
                  cuando hay error, que es cuando los lectores la anuncian. */}
              <div className="grid [&>*]:col-start-1 [&>*]:row-start-1">
                <p aria-hidden="true" className={cn(avisoClass, "invisible")}>
                  {aviso}
                </p>
                <p
                  role="alert"
                  data-aviso-servidor
                  className={cn(
                    avisoVisible &&
                      `${avisoClass} bg-destructive/12 text-foreground shadow-[inset_0_0_0_1px_var(--destructive)] [&>svg]:text-destructive`
                  )}
                >
                  {avisoVisible ? aviso : null}
                </p>
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
                help={signUp("usernameHelp")}
              />
              <div className="grid grid-cols-2 items-start gap-4">
                <DateField
                  label={common("fields.birthDate")}
                  name="fecha_nacimiento"
                  required
                  value={form.fecha_nacimiento}
                  onChange={(iso) => setField("fecha_nacimiento", iso)}
                  error={mostrar("fecha_nacimiento", true)}
                  help={signUp("minimumAgeHelp")}
                />
                <div className="flex flex-col gap-2">
                  <label htmlFor="genero" className="text-sm font-semibold">
                    {signUp("genderLabel")}
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
          <div {...celdaDePaso(3, paso)}>
            <div className="flex flex-col gap-[1.375rem]">
              {avatarId !== null && avatarElegido && (
                <SignupAvatarField
                  avatar={avatarElegido}
                  onChoose={() => setEligiendoAvatar(true)}
                  describedBy={servidor.avatar_id ? ID_ERROR_PASO_3 : undefined}
                />
              )}
              <SignupTerms
                checked={acepta}
                onChange={(marcado) => {
                  setAcepta(marcado);
                  setCorregidos((prev) => ({ ...prev, acepta_terminos: true }));
                }}
                error={errorTerminos}
                hint={t("termsPending")}
                hintVisible={!acepta}
              />
              {/* Renglón reservado: es lo último del paso, así que un error del
                  servidor (general o del avatar) no empuja nada al aparecer. */}
              <div id={ID_ERROR_PASO_3} className="min-h-[1lh] text-[0.8125rem]">
                {errorPaso3 && <FieldError>{errorPaso3}</FieldError>}
              </div>
            </div>
          </div>
        </div>
        <div className="flex flex-col gap-2.5">
          {paso === 2 ? (
            // `type="submit"`: Enter en cualquier campo hace lo mismo que el botón.
            <button
              type="submit"
              data-accion
              disabled={!hidratado || continuarPendiente}
              aria-busy={continuarPendiente || undefined}
              className={`${primaryButtonClass} gap-2.5`}
            >
              {signUp("continue")}
              <ChevronRight aria-hidden="true" className="size-5" />
            </button>
          ) : (
            // Fila del alto de «Continue» (52 px): el botón de Google mide 40 px
            // y, centrado acá, deja «Back» a la misma altura en los dos pasos.
            <div data-accion className="flex h-[3.25rem] flex-col justify-center">
              {/* `inert`: sin los Términos el botón de Google no se puede usar. */}
              <div
                data-testid="google-confirm"
                inert={!googleActivo}
                className={googleActivo ? undefined : "opacity-40"}
              >
                <GoogleButton
                  text="signup_with"
                  theme="outline"
                  fullWidth
                  onSuccess={onGoogle}
                  onError={() => setFallo({ code: "google_authentication_failed" })}
                />
              </div>
            </div>
          )}
          <div className="flex min-h-11 items-center justify-between gap-3">
            <SignupBackButton
              label={
                paso === 3
                  ? signUp("backToStep", { step: "2" })
                  : t(origen === "register" ? "backToSignUp" : "backToLogIn")
              }
              onClick={onBack}
            />
          </div>
        </div>
      </form>
      {eligiendoAvatar && avatarId !== null && (
        <SignupAvatarDialog
          avatares={avatares}
          avatarId={avatarId}
          onUse={(id) => {
            setAvatarId(id);
            setCorregidos((prev) => ({ ...prev, avatar_id: true }));
            setEligiendoAvatar(false);
          }}
          onClose={() => setEligiendoAvatar(false)}
        />
      )}
    </AccessShell>
  );
}
