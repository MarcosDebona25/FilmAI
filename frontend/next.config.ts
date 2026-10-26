import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

/**
 * Cabeceras básicas de seguridad (revisión del 26/10/2026). La CSP queda para el
 * despliegue: Next, Google Sign-In y las imágenes de TMDB necesitan excepciones.
 */
const CABECERAS = [
  // El navegador no adivina el tipo de un archivo distinto al declarado.
  { key: "X-Content-Type-Options", value: "nosniff" },
  // A otros sitios solo les llega el origen, nunca la ruta completa.
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
];
/** Estas rutas llevan un token en el path: no lo mandan a nadie. */
const SIN_REFERRER = [{ key: "Referrer-Policy", value: "no-referrer" }];

const nextConfig: NextConfig = {
  // Las verificaciones usan otra carpeta para convivir con `next dev`.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  async headers() {
    return [
      { source: "/:path*", headers: CABECERAS },
      { source: "/reset-password/:path*", headers: SIN_REFERRER },
      { source: "/confirm-email/:path*", headers: SIN_REFERRER },
    ];
  },
};

const withNextIntl = createNextIntlPlugin({
  experimental: {
    createMessagesDeclaration: ["./messages/en/common.json", "./messages/es/common.json"],
  },
});

export default withNextIntl(nextConfig);
