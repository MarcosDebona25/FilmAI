"use client";

import { LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { toast } from "sonner";

import { useAccount, type Perfil } from "@/components/AccountProvider";
import { AvatarSelector } from "@/components/AvatarSelector";
import { useNavigationGuard } from "@/components/NavigationGuard";
import { tieneCambios, colorDisponibilidad, type Borrador } from "@/lib/profile-draft";
import { Avatar } from "@/components/Avatar";
import { Button } from "@/components/ui/button";
import { ApiError, apiFetch, apiUrl, extraerErroresPorCampo } from "@/lib/api";
import {
  normalizarNombre,
  validarApellido,
  validarNombre,
  validarNombreUsuario,
  validarPassword,
  validarConfirmacion,
} from "@/lib/validation";

type Campo = "nombre" | "apellido" | "nombre_usuario";
const INPUT =
  "mt-1 w-full rounded-lg border border-input bg-background px-3 py-2.5 text-base text-foreground focus-visible:outline-2 focus-visible:outline-ring";

function fechaVisible(fecha: string) {
  return new Intl.DateTimeFormat("es-AR", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${fecha}T00:00:00Z`));
}

function generoVisible(genero: string) {
  return (
    (
      { masculino: "Masculino", femenino: "Femenino", no_especifica: "No especificado" } as Record<
        string,
        string
      >
    )[genero] ?? genero
  );
}

export default function PerfilPage() {
  const router = useRouter();
  const { setDirty, requestExit } = useNavigationGuard();
  const { perfil, avatares, cargando, error, recargar, actualizarPerfil } = useAccount();
  const [editando, setEditando] = useState(false);
  const [borrador, setBorrador] = useState<Borrador | null>(null);
  const [selectorAbierto, setSelectorAbierto] = useState(false);
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [disponibilidad, setDisponibilidad] = useState<"idle" | "checking" | "available" | "taken">(
    "idle"
  );
  const [guardando, setGuardando] = useState(false);
  const [oldPassword, setOldPassword] = useState("");
  const [password1, setPassword1] = useState("");
  const [password2, setPassword2] = useState("");
  const [cambiandoPassword, setCambiandoPassword] = useState(false);
  const [enviandoEnlace, setEnviandoEnlace] = useState(false);
  const campoRefs = useRef<Record<Campo, HTMLInputElement | null>>({
    nombre: null,
    apellido: null,
    nombre_usuario: null,
  });

  useEffect(() => {
    setDirty(editando && tieneCambios(borrador, perfil));
    return () => setDirty(false);
  }, [editando, borrador, perfil, setDirty]);

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
          { signal: controller.signal }
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
  }, [borrador?.nombre_usuario, editando, perfil, borrador]);

  function iniciarEdicion() {
    if (!perfil) return;
    setBorrador({
      nombre: perfil.nombre,
      apellido: perfil.apellido,
      nombre_usuario: perfil.nombre_usuario,
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
      nombre: validarNombre(limpio.nombre) ?? "",
      apellido: validarApellido(limpio.apellido) ?? "",
      nombre_usuario:
        validarNombreUsuario(limpio.nombre_usuario) ??
        (disponibilidad === "taken" ? "Este usuario ya está en uso." : ""),
    };
    if (Object.values(nuevosErrores).some(Boolean)) {
      setErrores(nuevosErrores);
      const primerCampo = (Object.keys(nuevosErrores) as Campo[]).find(
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
      toast.success("Perfil actualizado.");
    } catch (err) {
      if (err instanceof ApiError) {
        const campos = extraerErroresPorCampo(err.details);
        setErrores(
          err.status === 409 ? { nombre_usuario: "Este usuario ya está en uso." } : campos
        );
      }
      toast.error("No pudimos guardar el perfil. Revisá los datos e intentá de nuevo.");
    } finally {
      setGuardando(false);
    }
  }

  async function cambiarContrasena(event: FormEvent) {
    event.preventDefault();
    const nuevosErrores = {
      old_password: oldPassword ? "" : "Ingresá tu contraseña actual.",
      password1: validarPassword(password1) ?? "",
      password2: validarConfirmacion(password1, password2) ?? "",
    };
    if (Object.values(nuevosErrores).some(Boolean)) {
      setErrores(nuevosErrores);
      return;
    }
    if (
      !window.confirm(
        "Se cerrarán tus sesiones en todos los dispositivos. Tendrás que iniciar sesión nuevamente. ¿Continuar?"
      )
    )
      return;
    setCambiandoPassword(true);
    try {
      await apiFetch("/api/profile/change-password/", {
        method: "POST",
        body: { old_password: oldPassword, password1, password2 },
      });
      toast.success("Contraseña actualizada. Iniciá sesión nuevamente.");
      router.replace("/login");
    } catch (err) {
      if (err instanceof ApiError) setErrores(extraerErroresPorCampo(err.details));
      toast.error("No pudimos cambiar la contraseña.");
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
      toast.success("Te enviamos un enlace para establecer tu contraseña.");
    } catch {
      toast.error("No pudimos enviar el enlace. Intentá más tarde.");
    } finally {
      setEnviandoEnlace(false);
    }
  }

  const vista = editando && borrador && perfil ? { ...perfil, ...borrador } : perfil;
  return (
    <main id="contenido" className="mx-auto max-w-3xl px-6 py-10">
      <nav aria-label="Ruta de navegación" className="mb-8 text-sm text-muted-foreground">
        Perfil
      </nav>
      <h1 className="mb-8 text-3xl font-bold text-foreground">Mi perfil</h1>
      {cargando && <p role="status">Cargando perfil…</p>}
      {error && (
        <div role="alert">
          <p>{error}</p>
          <Button onClick={() => void recargar()}>Reintentar</Button>
        </div>
      )}
      {vista && (
        <div className="space-y-10">
          <section className="rounded-xl bg-card p-6 sm:p-8">
            <div className="flex flex-col items-center text-center">
              {editando ? (
                <button
                  type="button"
                  onClick={() => setSelectorAbierto(true)}
                  className="relative cursor-pointer rounded-full focus-visible:outline-2 focus-visible:outline-ring"
                  aria-label="Cambiar avatar"
                  aria-haspopup="dialog"
                >
                  <Avatar perfil={vista} avatares={avatares} size={96} />
                  <span className="absolute inset-0 flex items-center justify-center rounded-full bg-black/65 px-2 text-sm font-semibold text-white">
                    Cambiar avatar
                  </span>
                </button>
              ) : (
                <Avatar perfil={vista} avatares={avatares} size={96} />
              )}
              <h2 className="mt-4 text-2xl font-semibold">
                {vista.nombre} {vista.apellido}
              </h2>
              <p className="text-primary">@{vista.nombre_usuario}</p>
              <p className="mt-1 text-sm text-muted-foreground">{vista.correo}</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Miembro desde {fechaVisible(vista.fecha_registro)}
              </p>
              {!editando && (
                <Button className="mt-5 min-h-11" onClick={iniciarEdicion}>
                  Editar perfil
                </Button>
              )}
            </div>
            {!editando ? (
              <dl className="mt-8 grid gap-4 border-t border-border pt-6 sm:grid-cols-2">
                <div>
                  <dt className="text-sm text-muted-foreground">Nombre</dt>
                  <dd>{perfil?.nombre}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">Apellido</dt>
                  <dd>{perfil?.apellido}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">Fecha de nacimiento</dt>
                  <dd>{fechaVisible(vista.fecha_nacimiento)}</dd>
                </div>
                <div>
                  <dt className="text-sm text-muted-foreground">Género</dt>
                  <dd>{generoVisible(vista.genero)}</dd>
                </div>
              </dl>
            ) : borrador ? (
              <form
                onSubmit={(event) => void guardar(event)}
                className="mt-8 space-y-5 border-t border-border pt-6"
                noValidate
              >
                {(["nombre", "apellido", "nombre_usuario"] as const).map((campo) => (
                  <div key={campo}>
                    <label htmlFor={campo} className="block text-sm font-medium">
                      {campo === "nombre_usuario"
                        ? "Nombre de usuario"
                        : campo === "nombre"
                          ? "Nombre"
                          : "Apellido"}
                    </label>
                    <input
                      id={campo}
                      ref={(element) => {
                        campoRefs.current[campo] = element;
                      }}
                      name={campo}
                      value={borrador[campo]}
                      onChange={(event) => cambiarCampo(campo, event.target.value)}
                      onBlur={(event) =>
                        campo !== "nombre_usuario" &&
                        cambiarCampo(campo, normalizarNombre(event.target.value))
                      }
                      autoComplete={
                        campo === "nombre"
                          ? "given-name"
                          : campo === "apellido"
                            ? "family-name"
                            : "username"
                      }
                      aria-invalid={Boolean(errores[campo])}
                      aria-describedby={`${campo}-ayuda ${campo}-error`}
                      className={INPUT}
                    />
                    <p id={`${campo}-ayuda`} className="mt-1 text-xs text-muted-foreground">
                      {campo === "nombre_usuario"
                        ? "5 a 25 caracteres, solo letras y números; debe ser único."
                        : "Solo letras y espacios entre palabras; máximo 50 caracteres."}
                    </p>
                    {campo === "nombre_usuario" &&
                      borrador.nombre_usuario !== perfil?.nombre_usuario &&
                      !errores[campo] && (
                        <p
                          className={`mt-1 text-xs ${colorDisponibilidad(disponibilidad)}`}
                          aria-live="polite"
                        >
                          {disponibilidad === "checking"
                            ? "Comprobando disponibilidad…"
                            : disponibilidad === "available"
                              ? "Disponible"
                              : disponibilidad === "taken"
                                ? "No disponible"
                                : ""}
                        </p>
                      )}
                    {errores[campo] && (
                      <p
                        id={`${campo}-error`}
                        role="alert"
                        className="mt-1 text-sm text-destructive"
                      >
                        {errores[campo]}
                      </p>
                    )}
                  </div>
                ))}
                <div className="flex flex-wrap justify-end gap-3">
                  <Button
                    type="button"
                    className="min-h-11"
                    variant="secondary"
                    disabled={guardando}
                    onClick={cancelar}
                  >
                    Cancelar
                  </Button>
                  <Button type="submit" disabled={guardando} className="min-h-11">
                    {guardando && (
                      <LoaderCircle aria-hidden="true" className="motion-safe:animate-spin" />
                    )}
                    Guardar cambios
                  </Button>
                </div>
              </form>
            ) : null}
          </section>

          <section className="rounded-xl bg-card p-6 sm:p-8">
            <h2 className="text-xl font-semibold">Contraseña</h2>
            {perfil?.tiene_contrasena_local ? (
              <details className="mt-4">
                <summary className="cursor-pointer text-primary">Cambiar contraseña</summary>
                <form
                  onSubmit={(event) => void cambiarContrasena(event)}
                  className="mt-5 space-y-4"
                  noValidate
                >
                  {(
                    [
                      ["old_password", "Contraseña actual", oldPassword, setOldPassword],
                      ["password1", "Contraseña nueva", password1, setPassword1],
                      ["password2", "Repetir contraseña nueva", password2, setPassword2],
                    ] as const
                  ).map(([id, label, value, setValue]) => (
                    <div key={id}>
                      <label htmlFor={id} className="block text-sm font-medium">
                        {label}
                      </label>
                      <input
                        id={id}
                        name={id}
                        type="password"
                        autoComplete={id === "old_password" ? "current-password" : "new-password"}
                        value={value}
                        onChange={(event) => setValue(event.target.value)}
                        aria-invalid={Boolean(errores[id])}
                        className={INPUT}
                      />
                      {errores[id] && (
                        <p role="alert" className="mt-1 text-sm text-destructive">
                          {errores[id]}
                        </p>
                      )}
                    </div>
                  ))}
                  <p className="text-xs text-muted-foreground">
                    8-20 caracteres, con al menos una mayúscula, una minúscula, un dígito y un
                    carácter especial @#$%&*!
                  </p>
                  <p className="text-sm text-muted-foreground">
                    Al confirmar se cerrarán tus sesiones en todos los dispositivos.
                  </p>
                  <Button type="submit" disabled={cambiandoPassword}>
                    {cambiandoPassword ? "Cambiando…" : "Cambiar contraseña"}
                  </Button>
                </form>
              </details>
            ) : (
              <div className="mt-3">
                <p className="text-sm text-muted-foreground">
                  Tu cuenta usa Google y todavía no tiene contraseña local. Podés establecerla con
                  un enlace enviado a tu correo.
                </p>
                <Button
                  className="mt-4"
                  variant="secondary"
                  disabled={enviandoEnlace}
                  onClick={() => void enviarEnlace()}
                >
                  {enviandoEnlace ? "Enviando…" : "Enviar enlace por correo"}
                </Button>
              </div>
            )}
          </section>
        </div>
      )}
      {selectorAbierto && borrador && (
        <AvatarSelector
          avatares={avatares}
          avatarId={borrador.avatar_id}
          onClose={() => setSelectorAbierto(false)}
          onSave={(avatar_id) => {
            setBorrador({ ...borrador, avatar_id });
            setSelectorAbierto(false);
          }}
        />
      )}
    </main>
  );
}
