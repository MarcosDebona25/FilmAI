import { currentLocale } from "@/i18n/client";
import { translateError, fieldErrors, type FieldError, type ErrorParams } from "./errors";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export function apiUrl(path: string): string {
  const [pathname, query] = path.split("?", 2);
  const normalizedPath = pathname.endsWith("/") ? pathname : `${pathname}/`;
  return `${API_URL}${normalizedPath}${query ? `?${query}` : ""}`;
}

// ---------------------------------------------------------------------------
// Autenticación por cookie httpOnly: el backend (dj-rest-auth) setea las
// cookies `access` y `refresh` con JWT_AUTH_HTTPONLY=True. El frontend NO
// persiste tokens en localStorage (reduce la superficie de ataque XSS): las
// cookies viajan automáticamente con `credentials: "include"` y el backend
// autentica vía JWTCookieAuthentication.
//
// CSRF: con JWT_AUTH_COOKIE_USE_CSRF=True, las mutaciones autenticadas por
// cookie exigen el header `X-CSRFToken`. Django setea la cookie `csrftoken`
// (legible por JS) vía `GET /api/auth/csrf/`; acá se lee y se reenvía.
// ---------------------------------------------------------------------------

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

let csrfFetch: Promise<string> | null = null;

async function getCsrfToken(): Promise<string> {
  const existente = readCookie("csrftoken");
  if (existente) return existente;

  // La cookie aún no existe (primera mutación de la sesión): se pide al
  // backend, que la setea con `ensure_csrf_cookie`. Se deduplica con una única
  // promesa en vuelo para no disparar varias peticiones concurrentes.
  if (!csrfFetch) {
    csrfFetch = fetch(apiUrl("/api/auth/csrf/"), {
      credentials: "include",
      headers: { "Accept-Language": currentLocale() },
    })
      .then(() => {
        const token = readCookie("csrftoken");
        if (!token) throw new ApiError(0, { code: "unknown" });
        return token;
      })
      .finally(() => {
        csrfFetch = null;
      });
  }
  return csrfFetch;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly params: ErrorParams;
  readonly errors: FieldError[];

  constructor(status: number, data: unknown) {
    const envelope = data && typeof data === "object" ? (data as Record<string, unknown>) : {};
    const code = typeof envelope.code === "string" ? envelope.code : "unknown";
    const params =
      envelope.params && typeof envelope.params === "object"
        ? (envelope.params as ErrorParams)
        : {};
    const errors = Array.isArray(envelope.errors) ? (envelope.errors as FieldError[]) : [];
    super(translateError(errors.find((entry) => !entry.field) ?? { code, params }));
    this.status = status;
    this.code = code;
    this.params = params;
    this.errors = errors;
  }
}

export function extraerErroresPorCampo(error: ApiError): Record<string, string> {
  return fieldErrors(error);
}

interface ApiOptions {
  method?: string;
  body?: unknown;
}

// ---------------------------------------------------------------------------
// Renovación de la sesión (16/10/2026). La cookie `access` dura 8 horas y la
// `refresh`, 7 días. Cuando un pedido vuelve 401, se pide un `access` nuevo a
// `POST /api/auth/token/refresh/` (el backend lee la cookie `refresh`) y se
// repite el pedido una vez. Si tampoco así hay sesión, se avisa con el evento
// `SESION_VENCIDA` y `AccountProvider` decide si mostrar el aviso.
// ---------------------------------------------------------------------------

/** Evento de `window` cuando un 401 no se pudo resolver renovando la sesión. */
export const SESION_VENCIDA = "filmai:sesion-vencida";

let renovacion: Promise<boolean> | null = null;

/**
 * Pide un `access` nuevo con la cookie `refresh`. Varios 401 a la vez
 * comparten un único pedido: el backend rota la `refresh` (y anula la
 * anterior), así que un segundo pedido con la vieja fallaría.
 */
export function renovarSesion(): Promise<boolean> {
  if (!renovacion) {
    renovacion = (async () => {
      const csrf = await getCsrfToken().catch(() => null);
      const res = await fetch(apiUrl("/api/auth/token/refresh/"), {
        method: "POST",
        credentials: "include",
        headers: {
          "Accept-Language": currentLocale(),
          ...(csrf ? { "X-CSRFToken": csrf } : {}),
        },
      });
      return res.ok;
    })()
      .catch(() => false)
      .finally(() => {
        renovacion = null;
      });
  }
  return renovacion;
}

export async function apiFetch<T = unknown>(path: string, options: ApiOptions = {}): Promise<T> {
  const { method = "GET", body } = options;

  const headers: Record<string, string> = { "Accept-Language": currentLocale() };
  if (body !== undefined) headers["Content-Type"] = "application/json";

  // CSRF: solo las mutaciones requieren el header (los métodos seguros no
  // pasan por la verificación CSRF del backend).
  const metodo = method.toUpperCase();
  if (metodo !== "GET" && metodo !== "HEAD" && metodo !== "OPTIONS") {
    const csrf = await getCsrfToken();
    if (csrf) headers["X-CSRFToken"] = csrf;
  }

  // Si el pedido ni siquiera llega (sin conexión, servidor apagado, CORS),
  // `fetch` rechaza con un error del navegador («Failed to fetch» en inglés).
  // Se convierte en un error con código propio para que la pantalla muestre un
  // mensaje entendible y traducido (Q-03, 16/10/2026).
  const enviar = () =>
    fetch(apiUrl(path), {
      method,
      headers,
      credentials: "include",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }).catch(() => {
      throw new ApiError(0, { code: "network_error" });
    });

  let res = await enviar();
  // Las rutas de `auth/` (login, logout, la renovación misma) contestan 401
  // por sus propios motivos: renovar ahí no tiene sentido.
  if (res.status === 401 && !path.startsWith("/api/auth/")) {
    // Se repite aunque la renovación falle: otra pestaña pudo haber renovado
    // las cookies (compartidas) mientras tanto.
    await renovarSesion();
    res = await enviar();
    if (res.status === 401 && typeof window !== "undefined")
      window.dispatchEvent(new Event(SESION_VENCIDA));
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      // Non-JSON response body — leave data as null.
    }
  }

  if (!res.ok) {
    throw new ApiError(res.status, data);
  }

  return data as T;
}
