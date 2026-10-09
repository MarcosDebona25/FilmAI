import { NextResponse, type NextRequest } from "next/server";

// Rutas protegidas (docs/05 — A-09). Se redirigen a /login si no hay sesión.
import { protectedRoutes } from "@/lib/routes";

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const protegida = protectedRoutes.some((p) => pathname.startsWith(p));

  if (!protegida) return NextResponse.next();

  // El backend setea la cookie httpOnly `access` al iniciar sesión. La
  // verificación real del token la hace el backend en cada request; aquí solo
  // se hace una comprobación liviana de presencia para la UX del redirect.
  const access = request.cookies.get("access")?.value;
  if (!access) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    url.searchParams.set("next", pathname);
    return NextResponse.redirect(url);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/profile/:path*", "/lists/:path*", "/my-reviews/:path*", "/settings/:path*"],
};
