export const routes = {
  home: "/",
  explore: "/home",
  search: "/search",
  login: "/login",
  register: "/register",
  profile: "/profile",
  settings: "/settings",
  language: "/settings#t-idioma",
  myReviews: "/my-reviews",
  lists: "/lists",
  // Provisoria: el chatbot aún no existe, así que hoy responde 404 (Not Found).
  // Sus enlaces van con `prefetch={false}` hasta que exista (22/10/2026).
  askFilmAI: "/chat",
  completeSignup: "/complete-signup",
  terms: "/terms",
  /**
   * Ficha de una película o serie (C-07). `from` es el origen para la miga de
   * pan: `home`, `search`, `reviews` o `list-{id}`.
   */
  title: (tipo: "movie" | "tv", id: number, from?: string) =>
    from ? `/${tipo}/${id}?from=${encodeURIComponent(from)}` : `/${tipo}/${id}`,
  /** Detalle de una lista (L-03, Marcos). */
  list: (id: number) => `/lists/${id}`,
  confirmEmail: (key: string) => `/confirm-email/${encodeURIComponent(key)}`,
  resetPassword: (uid: string, token: string) =>
    `/reset-password/${encodeURIComponent(uid)}/${encodeURIComponent(token)}`,
} as const;
/** Pantallas de acceso: ocupan toda la ventana, sin barra de navegación ni pie. */
export function isAccessPath(path: string): boolean {
  return (
    ([routes.home, routes.login, routes.register, routes.completeSignup] as string[]).includes(
      path
    ) || path.startsWith("/confirm-email/")
  );
}
export const protectedRoutes = [routes.profile, routes.settings, routes.myReviews, routes.lists];
