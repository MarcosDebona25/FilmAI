"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { ApiError, apiFetch, storeTokens } from "@/lib/api";

const inputClass =
  "w-full rounded-lg border border-input bg-background px-3 py-2 text-sm text-foreground outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40";

const GENEROS = [
  { value: "masculino", label: "Masculino" },
  { value: "femenino", label: "Femenino" },
  { value: "no_especifica", label: "No especificar" },
];

export default function CompletarGooglePage() {
  const router = useRouter();
  const [idToken, setIdToken] = useState<string | null>(null);
  const [nombreUsuario, setNombreUsuario] = useState("");
  const [fechaNacimiento, setFechaNacimiento] = useState("");
  const [genero, setGenero] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = sessionStorage.getItem("google_id_token");
    if (!token) {
      router.replace("/login");
    } else {
      setIdToken(token);
    }
  }, [router]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!idToken) return;
    setError(null);
    setLoading(true);
    try {
      const data = await apiFetch<{ access: string; refresh: string }>("/api/auth/google/", {
        method: "POST",
        body: {
          id_token: idToken,
          nombre_usuario: nombreUsuario,
          fecha_nacimiento: fechaNacimiento,
          genero: genero,
        },
        auth: false,
      });
      storeTokens(data.access, data.refresh);
      sessionStorage.removeItem("google_id_token");
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo completar tu cuenta.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center p-6">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-card p-8">
        <h1 className="mb-1 text-2xl font-bold text-foreground">Completá tu cuenta</h1>
        <p className="mb-6 text-sm text-muted-foreground">
          Google ya nos dio tu nombre y correo. Falta completar estos datos.
        </p>

        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <div>
            <label className="mb-1 block text-sm text-muted-foreground">Nombre de usuario</label>
            <input
              className={inputClass}
              value={nombreUsuario}
              onChange={(e) => setNombreUsuario(e.target.value)}
              placeholder="5-25 caracteres alfanuméricos"
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted-foreground">Fecha de nacimiento</label>
            <input
              className={inputClass}
              type="date"
              value={fechaNacimiento}
              onChange={(e) => setFechaNacimiento(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-muted-foreground">Género</label>
            <select
              className={inputClass}
              value={genero}
              onChange={(e) => setGenero(e.target.value)}
              required
            >
              <option value="" disabled>
                Selecciona uno
              </option>
              {GENEROS.map((g) => (
                <option key={g.value} value={g.value}>
                  {g.label}
                </option>
              ))}
            </select>
          </div>

          {error && (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          )}

          <Button type="submit" disabled={loading} size="lg">
            {loading ? "Guardando…" : "Continuar"}
          </Button>
        </form>
      </div>
    </main>
  );
}
