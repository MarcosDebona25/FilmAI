import type { Metadata } from "next";
import { Big_Shoulders, Hanken_Grotesk } from "next/font/google";
import { Toaster } from "sonner";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getTranslations } from "next-intl/server";

import { Footer } from "@/components/LocaleControls";
import { MobileTabs } from "@/components/MobileTabs";
import { Navbar } from "@/components/Navbar";
import { AccountProvider } from "@/components/AccountProvider";
import { NavigationGuard } from "@/components/NavigationGuard";
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

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("legacy.metadata");
  return {
    title: "FilmAI",
    description: t("description"),
    icons: { icon: "/icons8-movies-32.png" },
  };
}

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const locale = await getLocale();
  return (
    <html lang={locale} className="dark" suppressHydrationWarning>
      <body className={`${hanken.variable} ${bigShoulders.variable} antialiased`}>
        <NextIntlClientProvider>
          <AccountProvider>
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
