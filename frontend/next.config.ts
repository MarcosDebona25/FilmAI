import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const nextConfig: NextConfig = {
  // Las verificaciones usan otra carpeta para convivir con `next dev`.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
};

const withNextIntl = createNextIntlPlugin({
  experimental: {
    createMessagesDeclaration: [
      "./messages/en/common.json",
      "./messages/es/common.json",
      "./messages/en/legal.json",
      "./messages/es/legal.json",
    ],
  },
});

export default withNextIntl(nextConfig);
