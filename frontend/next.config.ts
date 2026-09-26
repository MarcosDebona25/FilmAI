import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Las verificaciones usan otra carpeta para convivir con `next dev`.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
};

export default nextConfig;
