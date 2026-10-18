import { Suspense } from "react";
import type { Metadata, Viewport } from "next";
import { Big_Shoulders, Hanken_Grotesk } from "next/font/google";
import { cookies } from "next/headers";
import { Toaster } from "sonner";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getTranslations } from "next-intl/server";

import { Footer } from "@/components/Footer";
import { MobileTabs } from "@/components/MobileTabs";
import { Navbar } from "@/components/Navbar";
import { AccountProvider } from "@/components/AccountProvider";
import { NavigationGuard } from "@/components/NavigationGuard";
import { NavigationProgress } from "@/components/NavigationProgress";
import "./globals.css";

const hanken = Hanken_Grotesk({
  variable: "--font-hanken",
  subsets: ["latin"],
});

const bigShoulders = Big_Shoulders({
  variable: "--font-big-shoulders",
  subsets: ["latin"],
  weight: ["800"],
});

// La app es solo oscura (15/10/2026): se declara desde el servidor para que los
// controles nativos y el scroll no se pinten claros antes de que cargue JS, y
// la barra del navegador en celular tome el fondo de la app.
export const viewport: Viewport = { themeColor: "#0d0d14", colorScheme: "dark" };

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("legacy.metadata");
  return {
    title: "FilmAI",
    description: t("description"),
    icons: {
      icon: [{ url: "/favicon.svg", type: "image/svg+xml" }],
      apple: "/favicon.jpeg",
    },
  };
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale();
  // Sin ninguna de las dos cookies de sesión, el front ni pregunta por el perfil.
  const almacen = await cookies();
  const sesionPosible = almacen.has("access") || almacen.has("refresh");
  return (
    <html lang={locale} className="dark" suppressHydrationWarning>
      <body className={`${hanken.variable} ${bigShoulders.variable} antialiased`}>
        {/* `useSearchParams` (detecta el fin de la navegación) necesita Suspense. */}
        <Suspense fallback={null}>
          <NavigationProgress />
        </Suspense>
        <NextIntlClientProvider>
          <AccountProvider sesionPosible={sesionPosible}>
            <NavigationGuard>
              <Navbar />
              {children}
              <Footer />
              <MobileTabs />
            </NavigationGuard>
          </AccountProvider>
          <Toaster position="top-center" />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
