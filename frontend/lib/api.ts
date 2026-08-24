const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function apiUrl(path: string): string {
  return `${API_URL}${path}`;
}

// ---------------------------------------------------------------------------
// Token: solo el access token se guarda en localStorage para el header
// Authorization. El refresh token viaja como cookie httpOnly (seteada por el
// backend con JWT_AUTH_HTTPONLY=True) y no es accesible desde JavaScript.
// ---------------------------------------------------------------------------
const ACCESS_KEY = "filmai_access";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_KEY);
}

export function storeTokens(access: string, _refresh?: string): void {
  window.localStorage.setItem(ACCESS_KEY, access);
}

export function clearTokens(): void {
  window.localStorage.removeItem(ACCESS_KEY);
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

/** Convierte errores DRF `{campo: [msgs]}` en un mapa `{campo: primerMensaje}`. */
export function extraerErroresPorCampo(details: unknown): Record<string, string> {
  const errores: Record<string, string> = {};
  if (!details || typeof details !== "object") return errores;
  for (const [campo, valor] of Object.entries(details as Record<string, unknown>)) {
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
  auth?: boolean;
}

export async function apiFetch<T = unknown>(path: string, options: ApiOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true } = options;

  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const token = getAccessToken();
  if (auth && token) headers["Authorization"] = `Bearer ${token}`;

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
