export const routes = {
  home: "/",
  login: "/login",
  register: "/register",
  profile: "/profile",
  settings: "/settings",
  language: "/settings#t-idioma",
  myReviews: "/my-reviews",
  lists: "/lists",
  completeSignup: "/complete-signup",
  terms: "/terms",
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
