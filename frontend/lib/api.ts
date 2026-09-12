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
    csrfFetch = fetch(apiUrl("/api/auth/csrf/"), { credentials: "include" })
      .then(() => {
        const token = readCookie("csrftoken");
        if (!token) throw new Error("No se pudo obtener el token CSRF.");
        return token;
      })
      .finally(() => {
        csrfFetch = null;
      });
  }
  return csrfFetch;
}

export class ApiError extends Error {
  status: number;
  details: unknown;

  constructor(status: number, message: string, details: unknown) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

function extractError(data: unknown): string | null {
  if (!data || typeof data !== "object") return null;
  const obj = data as Record<string, unknown>;
  if (typeof obj.detail === "string") return obj.detail;
  const nonField = obj.non_field_errors;
  if (Array.isArray(nonField) && nonField.length) return String(nonField[0]);
  for (const key of Object.keys(obj)) {
    const value = obj[key];
    if (Array.isArray(value) && value.length) return `${key}: ${value[0]}`;
    if (typeof value === "string") return `${key}: ${value}`;
  }
  return null;
}

/**
 * Convierte errores DRF `{campo: [msgs]}` en un mapa `{campo: primerMensaje}`.
 *
 * Los errores globales del serializer (`non_field_errors`) y el detalle
 * genérico (`detail`) NO son campos: excluirlos evita que una pantalla
 * muestre "corregí los campos marcados" sin ningún campo resaltado. Esos
 * mensajes se presentan aparte vía `extractError`.
 */
export function extraerErroresPorCampo(details: unknown): Record<string, string> {
  const CLAVES_NO_CAMPO = new Set(["non_field_errors", "detail"]);
  const errores: Record<string, string> = {};
  if (!details || typeof details !== "object") return errores;
  for (const [campo, valor] of Object.entries(details as Record<string, unknown>)) {
    if (CLAVES_NO_CAMPO.has(campo)) continue;
    if (Array.isArray(valor) && typeof valor[0] === "string") {
      errores[campo] = valor[0];
    } else if (typeof valor === "string") {
      errores[campo] = valor;
    }
  }
  return errores;
}

interface ApiOptions {
  method?: string;
  body?: unknown;
}

export async function apiFetch<T = unknown>(path: string, options: ApiOptions = {}): Promise<T> {
  const { method = "GET", body } = options;

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";

  // CSRF: solo las mutaciones requieren el header (los métodos seguros no
  // pasan por la verificación CSRF del backend).
  const metodo = method.toUpperCase();
  if (metodo !== "GET" && metodo !== "HEAD" && metodo !== "OPTIONS") {
    const csrf = await getCsrfToken();
    if (csrf) headers["X-CSRFToken"] = csrf;
  }

  const res = await fetch(apiUrl(path), {
    method,
    headers,
    credentials: "include",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

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
    throw new ApiError(res.status, extractError(data) ?? `Error ${res.status}`, data);
  }

  return data as T;
}
