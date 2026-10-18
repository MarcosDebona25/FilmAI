"use client";

import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Camera,
  Check,
  ChevronDown,
  ChevronRight,
  FileText,
  Info,
  Lock,
  LogOut,
  Pencil,
  SlidersHorizontal,
  Star,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { useAccount, type Perfil } from "@/components/AccountProvider";
import { CountrySelect } from "@/components/CountrySelect";
import { Avatar } from "@/components/Avatar";
import { useNavigationGuard } from "@/components/NavigationGuard";
import { AvatarDialog } from "@/components/features/profile/AvatarDialog";
import { ConfirmDialog } from "@/components/features/title/ConfirmDialog";
import { ErrorRetry } from "@/components/ui/ErrorRetry";
import { currentLocale } from "@/i18n/client";
import { ApiError, apiFetch, apiUrl, extraerErroresPorCampo } from "@/lib/api";
import { translateError } from "@/lib/errors";
import { useFormats } from "@/lib/format";
import { tieneCambios, type Borrador } from "@/lib/profile-draft";
import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";
import { useValidation } from "@/lib/use-validation";
import { normalizarNombre } from "@/lib/validation";

type Campo = "nombre" | "apellido" | "nombre_usuario";
type Disponibilidad = "idle" | "checking" | "available" | "taken";

const CAMPO =
  "h-[52px] w-full rounded-[10px] border-0 bg-raised px-4 text-base text-foreground shadow-[inset_0_0_0_1px_var(--line)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring aria-[invalid=true]:shadow-[inset_0_0_0_1px_var(--destructive)]";
const ETIQUETA = "text-sm font-semibold";
const AYUDA = "text-[13px] text-fg-3";
const TITULO_2 = "font-display text-[30px] leading-none md:text-[36px]";
const BOTON_SECUNDARIO =
  "h-[52px] cursor-pointer rounded-[10px] px-4 font-semibold text-fg-2 shadow-[inset_0_0_0_1px_var(--line)] focus-visible:outline-2 focus-visible:outline-ring disabled:cursor-wait md:h-12 md:font-medium md:shadow-none";

/**
 * Mi perfil según el canvas («My profile · desktop / mobile»). Conserva la
 * lógica de antes: borrador con aviso de cambios sin guardar, disponibilidad
 * del usuario mientras se escribe, cambio de contraseña (o el enlace para
 * crearla en cuentas de Google) y el avatar, que se guarda con el resto.
 */
export default function PerfilPage() {
  const t = useTranslations();
  const {
    validarApellido,
    validarNombre,
    validarNombreUsuario,
    validarPassword,
    validarConfirmacion,
  } = useValidation();
  const formats = useFormats();
  const router = useRouter();
  const { setDirty, requestExit } = useNavigationGuard();
  const { perfil, avatares, cargando, error, recargar, actualizarPerfil, limpiar } = useAccount();
  const ids = useId();
  const [editando, setEditando] = useState(false);
  const [borrador, setBorrador] = useState<Borrador | null>(null);
  const [selectorAbierto, setSelectorAbierto] = useState(false);
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [disponibilidad, setDisponibilidad] = useState<Disponibilidad>("idle");
  const [guardando, setGuardando] = useState(false);
  const [claveAbierta, setClaveAbierta] = useState(false);
  const [oldPassword, setOldPassword] = useState("");
  const [password1, setPassword1] = useState("");
  const [password2, setPassword2] = useState("");
  const [cambiandoPassword, setCambiandoPassword] = useState(false);
  const [enviandoEnlace, setEnviandoEnlace] = useState(false);
  const [confirmarSalida, setConfirmarSalida] = useState(false);
  const campoRefs = useRef<Record<Campo, HTMLInputElement | null>>({
    nombre: null,
    apellido: null,
    nombre_usuario: null,
  });

  const generos = useTranslations("enums.gender");
  const generoVisible = (value: string) =>
    generos.has(value as "masculino") ? generos(value as "masculino") : value;
  const fechaVisible = (value: string) => formats.date(value, "long");

  useEffect(() => {
    setDirty(editando && tieneCambios(borrador, perfil));
    return () => setDirty(false);
  }, [editando, borrador, perfil, setDirty]);

  // Disponibilidad del usuario, 400 ms después de la última tecla.
  useEffect(() => {
    if (
      !editando ||
      !borrador ||
      !perfil ||
      borrador.nombre_usuario === perfil.nombre_usuario ||
      validarNombreUsuario(borrador.nombre_usuario)
    ) {
      setDisponibilidad("idle");
      return;
    }
    setDisponibilidad("checking");
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(
          apiUrl(
            `/api/auth/username-available/?username=${encodeURIComponent(borrador.nombre_usuario)}`
          ),
          { signal: controller.signal, headers: { "Accept-Language": currentLocale() } }
        );
        if (!res.ok) throw new Error("availability");
        const data: { disponible: boolean } = await res.json();
        if (!controller.signal.aborted) setDisponibilidad(data.disponible ? "available" : "taken");
      } catch {
        if (!controller.signal.aborted) setDisponibilidad("idle");
      }
    }, 400);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [borrador?.nombre_usuario, editando, perfil, borrador, validarNombreUsuario]);

  function iniciarEdicion() {
    if (!perfil) return;
    setBorrador({
      nombre: perfil.nombre,
      apellido: perfil.apellido,
      nombre_usuario: perfil.nombre_usuario,
      pais: perfil.pais,
      avatar_id: perfil.avatar_id,
    });
    setErrores({});
    setSelectorAbierto(false);
    setEditando(true);
  }

  function cancelar() {
    requestExit(() => {
      setEditando(false);
      setBorrador(null);
      setErrores({});
      setSelectorAbierto(false);
    });
  }

  function cambiarCampo(campo: Campo, valor: string) {
    setBorrador((actual) => (actual ? { ...actual, [campo]: valor } : actual));
    setErrores((actual) => ({ ...actual, [campo]: "" }));
  }

  async function guardar(event: FormEvent) {
    event.preventDefault();
    if (!borrador || !perfil) return;
    const limpio = {
      ...borrador,
      nombre: normalizarNombre(borrador.nombre),
      apellido: normalizarNombre(borrador.apellido),
    };
    const nuevosErrores = {
      pais: limpio.pais ? "" : t("common.country.required"),
      nombre: validarNombre(limpio.nombre) ?? "",
      apellido: validarApellido(limpio.apellido) ?? "",
      nombre_usuario:
        validarNombreUsuario(limpio.nombre_usuario) ??
        (disponibilidad === "taken" ? translateError({ code: "username_already_used" }) : ""),
    };
    if (Object.values(nuevosErrores).some(Boolean)) {
      setErrores(nuevosErrores);
      const primerCampo = (["nombre", "apellido", "nombre_usuario"] as Campo[]).find(
        (campo) => nuevosErrores[campo]
      );
      if (primerCampo) campoRefs.current[primerCampo]?.focus();
      return;
    }
    setGuardando(true);
    setErrores({});
    try {
      const actualizado = await apiFetch<Perfil>("/api/profile/", { method: "PUT", body: limpio });
      actualizarPerfil(actualizado);
      setEditando(false);
      setBorrador(null);
      toast.success(t("profile.feedback.updated"));
    } catch (err) {
      if (err instanceof ApiError) {
        const campos = extraerErroresPorCampo(err);
        setErrores(err.code === "username_already_used" ? { nombre_usuario: err.message } : campos);
      }
      toast.error(err instanceof ApiError ? err.message : translateError({ code: "unknown" }));
    } finally {
      setGuardando(false);
    }
  }

  function cerrarClave() {
    setClaveAbierta(false);
    setOldPassword("");
    setPassword1("");
    setPassword2("");
    setErrores({});
  }

  async function cambiarContrasena(event: FormEvent) {
    event.preventDefault();
    const nuevosErrores = {
      old_password: oldPassword ? "" : t("profile.password.currentRequired"),
      password1: validarPassword(password1) ?? "",
      password2: validarConfirmacion(password1, password2) ?? "",
    };
    if (Object.values(nuevosErrores).some(Boolean)) {
      setErrores(nuevosErrores);
      return;
    }
    // Sin confirmación aparte: el aviso de que se cierran todas las sesiones
    // está a la vista arriba del formulario (canvas).
    setCambiandoPassword(true);
    try {
      await apiFetch("/api/profile/change-password/", {
        method: "POST",
        body: { old_password: oldPassword, password1, password2 },
      });
      toast.success(t("profile.feedback.passwordChanged"));
      router.replace(routes.login);
    } catch (err) {
      if (err instanceof ApiError) setErrores(extraerErroresPorCampo(err));
      toast.error(err instanceof ApiError ? err.message : translateError({ code: "unknown" }));
      setCambiandoPassword(false);
    }
  }

  async function enviarEnlace() {
    if (!perfil) return;
    setEnviandoEnlace(true);
    try {
      await apiFetch("/api/auth/password/reset/", {
        method: "POST",
        body: { email: perfil.correo },
      });
      toast.success(t("profile.password.linkSent"));
    } catch {
      toast.error(t("profile.password.linkError"));
    } finally {
      setEnviandoEnlace(false);
    }
  }

  async function salir() {
    // La misma salida que el menú de la cuenta; si falla, `ConfirmDialog` lo muestra.
    await apiFetch("/api/auth/logout/", { method: "POST" });
    limpiar();
    router.push(routes.home);
  }

  const vista = editando && borrador && perfil ? { ...perfil, ...borrador } : perfil;

  // Un campo del formulario de edición, con su ayuda y su error.
  function campoEditable(campo: Campo, etiqueta: string, ayuda: string, autoComplete: string) {
    const id = `${ids}-${campo}`;
    return (
      <div key={campo} className="flex flex-col gap-1.5">
        <label htmlFor={id} className={ETIQUETA}>
          {etiqueta}
        </label>
        <div className="relative">
          {campo === "nombre_usuario" && (
            <span aria-hidden="true" className="absolute top-[15px] left-4 text-fg-3">
              @
            </span>
          )}
          <input
            id={id}
            ref={(element) => {
              campoRefs.current[campo] = element;
            }}
            name={campo}
            value={borrador?.[campo] ?? ""}
            maxLength={campo === "nombre_usuario" ? 25 : 50}
            onChange={(event) => cambiarCampo(campo, event.target.value)}
            onBlur={(event) =>
              campo !== "nombre_usuario" &&
              cambiarCampo(campo, normalizarNombre(event.target.value))
            }
            autoComplete={autoComplete}
            aria-invalid={Boolean(errores[campo])}
            aria-describedby={`${id}-ayuda ${id}-estado ${id}-error`}
            className={cn(CAMPO, campo === "nombre_usuario" && "pl-9")}
          />
        </div>
        {campo === "nombre_usuario" &&
          borrador?.nombre_usuario !== perfil?.nombre_usuario &&
          !errores[campo] && (
            <p
              id={`${id}-estado`}
              aria-live="polite"
              className={cn(
                "flex items-center gap-1.5 text-[13px] font-semibold",
                disponibilidad === "available"
                  ? "text-ok"
                  : disponibilidad === "taken"
                    ? "text-destructive"
                    : "font-normal text-fg-3"
              )}
            >
              {disponibilidad === "available" && <Check aria-hidden="true" className="size-4" />}
              {disponibilidad === "checking"
                ? t("profile.username.checking")
                : disponibilidad === "available"
                  ? t("auth.signUp.usernameAvailable")
                  : disponibilidad === "taken"
                    ? t("profile.username.taken")
                    : ""}
            </p>
          )}
        <p id={`${id}-ayuda`} className={AYUDA}>
          {ayuda}
        </p>
        {errores[campo] && (
          <p id={`${id}-error`} role="alert" className="text-sm text-destructive">
            {errores[campo]}
          </p>
        )}
      </div>
    );
  }

  function campoDeLectura(id: string, etiqueta: string, valor: string) {
    return (
      <div key={id} className="flex flex-col gap-1.5">
        <label htmlFor={`${ids}-${id}`} className={ETIQUETA}>
          {etiqueta}
        </label>
        <div className="relative">
          <input
            id={`${ids}-${id}`}
            readOnly
            value={valor}
            aria-describedby={`${ids}-lectura`}
            className={cn(CAMPO, "cursor-not-allowed bg-transparent pr-11 text-fg-2")}
          />
          <Lock aria-hidden="true" className="absolute top-[17px] right-4 size-[18px] text-fg-3" />
        </div>
      </div>
    );
  }

  return (
    <main
      id="contenido"
      className="mx-auto flex max-w-[920px] flex-col gap-9 px-5 pt-7 pb-[120px] md:gap-14 md:px-10 md:pt-12 md:pb-24"
    >
      {cargando && !perfil && (
        <p role="status" className="text-fg-2">
          {t("profile.loading")}
        </p>
      )}
      {error && <ErrorRetry mensaje={error} onReintentar={() => void recargar()} />}

      {vista && perfil && (
        <>
          <section
            aria-labelledby={`${ids}-titulo`}
            className="flex flex-col gap-[18px] md:flex-row md:flex-wrap md:items-center md:gap-7"
          >
            <div className="flex items-center gap-5 md:contents">
              <div className="relative size-[88px] shrink-0 md:size-[120px] [&>span]:!size-full [&>img]:!size-full">
                <Avatar perfil={vista} avatares={avatares} size={120} />
                {editando && (
                  <button
                    type="button"
                    onClick={() => setSelectorAbierto(true)}
                    aria-haspopup="dialog"
                    aria-label={t("common.avatar.change")}
                    className="absolute -right-1 -bottom-1 grid size-11 cursor-pointer place-items-center rounded-full bg-primary text-primary-foreground shadow-[0_0_0_3px_var(--background)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring md:inset-0 md:size-auto md:flex md:flex-col md:gap-1 md:bg-black/55 md:text-sm md:font-semibold md:text-white md:shadow-none"
                  >
                    <Camera aria-hidden="true" className="size-5" />
                    <span aria-hidden="true" className="hidden md:inline">
                      {t("common.avatar.change")}
                    </span>
                  </button>
                )}
              </div>
              <div className="flex min-w-0 flex-col md:flex-1">
                <h1
                  id={`${ids}-titulo`}
                  className="mb-2 font-display text-[44px] leading-[0.95] break-words md:mb-[15px] md:text-[72px]"
                >
                  {vista.nombre} {vista.apellido}
                </h1>
                <p className="font-semibold text-primary md:text-[17px]">@{vista.nombre_usuario}</p>
                <p className="hidden text-fg-3 md:block">
                  {t("profile.header.memberEmail", {
                    email: vista.correo,
                    date: fechaVisible(vista.fecha_registro),
                  })}
                </p>
              </div>
            </div>
            <p className="text-sm text-fg-3 md:hidden">
              {vista.correo}
              <br />
              {t("profile.header.memberSince", { date: fechaVisible(vista.fecha_registro) })}
            </p>
            {!editando && (
              <button
                type="button"
                onClick={iniciarEdicion}
                className="flex h-[52px] cursor-pointer items-center justify-center gap-2 rounded-[10px] bg-raised-2 px-[18px] font-semibold focus-visible:outline-2 focus-visible:outline-ring md:h-12"
              >
                <Pencil aria-hidden="true" className="size-[18px]" />
                {t("profile.editor.title")}
              </button>
            )}
          </section>

          {!editando ? (
            <section aria-labelledby={`${ids}-datos`} className="flex flex-col gap-1 md:gap-2">
              <h2 id={`${ids}-datos`} className={cn(TITULO_2, "mb-2")}>
                {t("profile.personal.heading")}
              </h2>
              <dl className="grid grid-cols-2 gap-x-4 md:flex md:flex-col">
                {(
                  [
                    [t("common.fields.firstName"), perfil.nombre],
                    [t("common.fields.lastName"), perfil.apellido],
                    [t("common.fields.birthDate"), fechaVisible(perfil.fecha_nacimiento)],
                    [t("auth.signUp.genderLabel"), generoVisible(perfil.genero)],
                    [t("common.fields.country"), formats.country(perfil.pais)],
                  ] as const
                ).map(([etiqueta, valor]) => (
                  <div
                    key={etiqueta}
                    className="flex flex-col gap-0.5 border-t border-line py-3.5 md:grid md:grid-cols-[220px_minmax(0,1fr)] md:gap-6 md:border-t-0 md:border-b md:py-[18px]"
                  >
                    <dt className="text-[13px] text-fg-3 md:text-base">{etiqueta}</dt>
                    <dd className="font-semibold">{valor}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ) : (
            borrador && (
              <form
                aria-labelledby={`${ids}-editar`}
                onSubmit={(event) => void guardar(event)}
                noValidate
                className="flex flex-col gap-5 md:gap-[22px]"
              >
                <h2 id={`${ids}-editar`} className={TITULO_2}>
                  {t("profile.personal.edit")}
                </h2>
                <div className="grid gap-5 md:grid-cols-2">
                  {campoEditable(
                    "nombre",
                    t("common.fields.firstName"),
                    t("auth.signUp.nameHelp"),
                    "given-name"
                  )}
                  {campoEditable(
                    "apellido",
                    t("common.fields.lastName"),
                    t("auth.signUp.nameHelp"),
                    "family-name"
                  )}
                </div>
                <div className="grid items-start gap-5 md:grid-cols-2">
                  {campoEditable(
                    "nombre_usuario",
                    t("common.fields.username"),
                    t("auth.signUp.usernameHelp"),
                    "username"
                  )}
                  <CountrySelect
                    id={`${ids}-pais`}
                    value={borrador.pais}
                    onChange={(pais) => {
                      setBorrador((actual) => (actual ? { ...actual, pais } : actual));
                      setErrores((actual) => ({ ...actual, pais: "" }));
                    }}
                    error={errores.pais}
                    className="gap-1.5"
                    selectClassName={CAMPO}
                  />
                </div>
                <div className="flex flex-col gap-3">
                  <p
                    id={`${ids}-lectura`}
                    className="flex items-center gap-2 text-[13px] text-fg-2"
                  >
                    <Info aria-hidden="true" className="size-4 shrink-0" />
                    {t("profile.personal.readOnlyFieldsHint")}
                  </p>
                  <div className="grid gap-5 md:grid-cols-3">
                    {campoDeLectura("correo", t("common.fields.email"), perfil.correo)}
                    {campoDeLectura(
                      "nacimiento",
                      t("common.fields.birthDate"),
                      fechaVisible(perfil.fecha_nacimiento)
                    )}
                    {campoDeLectura(
                      "genero",
                      t("auth.signUp.genderLabel"),
                      generoVisible(perfil.genero)
                    )}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2.5 md:flex md:justify-end">
                  <button
                    type="button"
                    disabled={guardando}
                    onClick={cancelar}
                    className={BOTON_SECUNDARIO}
                  >
                    {t("common.actions.cancel")}
                  </button>
                  <button
                    type="submit"
                    disabled={guardando}
                    className="h-[52px] cursor-pointer rounded-[10px] bg-primary px-6 font-semibold text-primary-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:cursor-wait disabled:opacity-60 md:h-12"
                  >
                    {t("common.actions.saveChanges")}
                  </button>
                </div>
              </form>
            )
          )}

          <section aria-labelledby={`${ids}-clave`} className="flex flex-col gap-2.5 md:gap-3.5">
            <h2 id={`${ids}-clave`} className={TITULO_2}>
              {t("auth.password.label")}
            </h2>
            {perfil.tiene_contrasena_local ? (
              <>
                <button
                  type="button"
                  aria-expanded={claveAbierta}
                  aria-controls={`${ids}-form-clave`}
                  onClick={() => (claveAbierta ? cerrarClave() : setClaveAbierta(true))}
                  className="inline-flex h-11 cursor-pointer items-center gap-2 self-start font-semibold focus-visible:outline-2 focus-visible:outline-ring"
                >
                  {t("profile.password.heading")}
                  <ChevronDown
                    aria-hidden="true"
                    className={cn("size-5 transition-transform", claveAbierta && "rotate-180")}
                  />
                </button>
                {claveAbierta && (
                  <form
                    id={`${ids}-form-clave`}
                    onSubmit={(event) => void cambiarContrasena(event)}
                    noValidate
                    className="flex flex-col gap-4 md:max-w-[480px]"
                  >
                    <p className="flex gap-2.5 text-[15px] text-fg-2 md:text-base">
                      <Info aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
                      <span>{t("profile.password.logoutWarning")}</span>
                    </p>
                    {(
                      [
                        [
                          "old_password",
                          t("common.password.currentLabel"),
                          oldPassword,
                          setOldPassword,
                        ],
                        ["password1", t("common.password.newLabel"), password1, setPassword1],
                        ["password2", t("common.password.repeatNewLabel"), password2, setPassword2],
                      ] as const
                    ).map(([campo, etiqueta, valor, setValor]) => (
                      <div key={campo} className="flex flex-col gap-1.5">
                        <label htmlFor={`${ids}-${campo}`} className={ETIQUETA}>
                          {etiqueta}
                        </label>
                        <input
                          id={`${ids}-${campo}`}
                          name={campo}
                          type="password"
                          autoComplete={
                            campo === "old_password" ? "current-password" : "new-password"
                          }
                          value={valor}
                          onChange={(event) => setValor(event.target.value)}
                          aria-invalid={Boolean(errores[campo])}
                          aria-describedby={campo === "password1" ? `${ids}-requisitos` : undefined}
                          className={CAMPO}
                        />
                        {campo === "password1" && (
                          <p id={`${ids}-requisitos`} className={AYUDA}>
                            {t("profile.password.requirements")}
                          </p>
                        )}
                        {errores[campo] && (
                          <p role="alert" className="text-sm text-destructive">
                            {errores[campo]}
                          </p>
                        )}
                      </div>
                    ))}
                    <div className="grid grid-cols-2 gap-2.5 md:flex md:justify-end">
                      <button
                        type="button"
                        disabled={cambiandoPassword}
                        onClick={cerrarClave}
                        className={BOTON_SECUNDARIO}
                      >
                        {t("common.actions.cancel")}
                      </button>
                      <button
                        type="submit"
                        disabled={cambiandoPassword}
                        className="h-[52px] cursor-pointer rounded-[10px] bg-raised-2 px-5 font-semibold focus-visible:outline-2 focus-visible:outline-ring disabled:cursor-wait disabled:opacity-60 md:h-12"
                      >
                        {t("profile.password.heading")}
                      </button>
                    </div>
                  </form>
                )}
              </>
            ) : (
              <div className="flex flex-col items-start gap-3">
                <p className="text-fg-2">{t("profile.password.googleDescription")}</p>
                <button
                  type="button"
                  disabled={enviandoEnlace}
                  onClick={() => void enviarEnlace()}
                  className="h-12 cursor-pointer rounded-[10px] bg-raised-2 px-5 font-semibold focus-visible:outline-2 focus-visible:outline-ring disabled:cursor-wait disabled:opacity-60"
                >
                  {t("profile.password.sendLink")}
                </button>
              </div>
            )}
          </section>

          {/* En celular no hay menú de la cuenta en la barra: estos accesos lo reemplazan. */}
          <nav aria-labelledby={`${ids}-cuenta`} className="flex flex-col md:hidden">
            <h2 id={`${ids}-cuenta`} className={cn(TITULO_2, "mb-1")}>
              {t("profile.account.heading")}
            </h2>
            <ul className="flex flex-col">
              {(
                [
                  [routes.myReviews, t("nav.main.ratingsReviews"), Star],
                  [routes.settings, t("nav.main.settings"), SlidersHorizontal],
                  [routes.terms, t("nav.main.terms"), FileText],
                ] as const
              ).map(([href, etiqueta, Icono]) => (
                <li key={href}>
                  <Link
                    href={href}
                    className="flex h-14 items-center gap-3.5 border-b border-line font-semibold text-foreground no-underline"
                  >
                    <Icono aria-hidden="true" className="size-5 text-fg-2" />
                    <span className="flex-1">{etiqueta}</span>
                    <ChevronRight aria-hidden="true" className="size-5 text-fg-3" />
                  </Link>
                </li>
              ))}
              <li>
                <button
                  type="button"
                  onClick={() => setConfirmarSalida(true)}
                  className="flex h-14 w-full cursor-pointer items-center gap-3.5 border-b border-line text-left font-semibold text-destructive"
                >
                  <LogOut aria-hidden="true" className="size-5" />
                  {t("nav.account.logOut")}
                </button>
              </li>
            </ul>
          </nav>
        </>
      )}

      {selectorAbierto && borrador && (
        <AvatarDialog
          avatares={avatares}
          avatarId={borrador.avatar_id}
          onClose={() => setSelectorAbierto(false)}
          onSave={(avatar_id) => {
            setBorrador({ ...borrador, avatar_id });
            setSelectorAbierto(false);
          }}
        />
      )}
      {confirmarSalida && (
        <ConfirmDialog
          titulo={t("nav.account.logoutConfirmTitle")}
          descripcion={t("nav.account.logoutConfirmDescription")}
          confirmar={t("nav.account.logOut")}
          onConfirm={salir}
          onCancel={() => setConfirmarSalida(false)}
        />
      )}
    </main>
  );
}
