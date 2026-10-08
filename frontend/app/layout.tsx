import type { Metadata } from "next";
import { Inter, Roboto } from "next/font/google";
import { Toaster } from "sonner";
import { NextIntlClientProvider } from "next-intl";
import { getLocale } from "next-intl/server";

import { Navbar } from "@/components/Navbar";
import { AccountProvider } from "@/components/AccountProvider";
import { NavigationGuard } from "@/components/NavigationGuard";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const roboto = Roboto({
  variable: "--font-roboto",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "FilmAI",
  description: "Plataforma de reseñas cinematográficas con recomendaciones inteligentes.",
  icons: {
    icon: "/icons8-movies-32.png",
  },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale();
  return (
    <html lang={locale} className="dark" suppressHydrationWarning>
      <body className={`${inter.variable} ${roboto.variable} antialiased`}>
        <NextIntlClientProvider>
          <AccountProvider>
            <NavigationGuard>
              <Navbar />
              {children}
            </NavigationGuard>
          </AccountProvider>
          <Toaster position="top-center" />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
