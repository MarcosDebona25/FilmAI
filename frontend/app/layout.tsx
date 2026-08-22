import type { Metadata } from "next";
import { Roboto } from "next/font/google";
import { Navbar } from "@/components/Navbar";
import "./globals.css";

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

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className="dark">
      <body className={`${roboto.variable} antialiased`}>
        <Navbar />
        {children}
      </body>
    </html>
  );
}
