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
  confirmEmail: (key: string) => `/confirm-email/${encodeURIComponent(key)}`,
  resetPassword: (uid: string, token: string) =>
    `/reset-password/${encodeURIComponent(uid)}/${encodeURIComponent(token)}`,
} as const;
export const protectedRoutes = [routes.profile, routes.settings, routes.myReviews, routes.lists];
