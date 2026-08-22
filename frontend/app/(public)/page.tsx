"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";

// Poster lateral intercambiable: cambiá el array (o el orden) para rotar.
const POSTERS = [
  { src: "/collage-posters/Opcion 1.jpg", label: "Opción 1" },
  { src: "/collage-posters/Opcion 2.jpg", label: "Opción 2" },
  { src: "/collage-posters/Opcion 3.jpg", label: "Opción 3" },
];

export default function PublicHome() {
  const router = useRouter();
  const [poster, setPoster] = useState(POSTERS[0].src);

  return (
    <main className="flex min-h-screen flex-col md:flex-row">
      {/* Poster lateral (oculto en pantallas chicas) */}
      <aside className="relative hidden md:block md:w-1/2">
        <Image
          src={poster}
          alt="Collage de posters de películas"
          fill
          priority
          sizes="(max-width: 767px) 0px, 50vw"
          className="object-cover"
        />
        {process.env.NODE_ENV === "development" && (
          <select
            value={poster}
            onChange={(e) => setPoster(e.target.value)}
            aria-label="Elegir poster"
            className="absolute bottom-4 left-4 rounded-lg border border-border bg-card/80 px-3 py-2 text-sm text-foreground backdrop-blur"
          >
            {POSTERS.map((p) => (
              <option key={p.src} value={p.src}>
                {p.label}
              </option>
            ))}
          </select>
        )}
      </aside>

      {/* Contenido centrado */}
      <section className="flex flex-1 flex-col items-center justify-center gap-6 px-8 py-16 text-center">
        <h1 className="font-heading text-4xl font-bold tracking-normal text-foreground md:text-5xl">
          FilmAI
        </h1>
        <p className="max-w-md text-lg text-muted-foreground">
          Plataforma de reseñas cinematográficas con recomendaciones inteligentes.
        </p>
        <div className="flex w-full max-w-xs flex-col gap-3">
          <Button size="lg" className="w-full" onClick={() => router.push("/catalogo")}>
            Explorar catálogo
          </Button>
          <Button
            size="lg"
            variant="secondary"
            className="w-full"
            onClick={() => router.push("/register")}
          >
            Registrarse
          </Button>
          <Button
            size="lg"
            variant="secondary"
            className="w-full"
            onClick={() => router.push("/login")}
          >
            Iniciar sesión
          </Button>
        </div>
      </section>
    </main>
  );
}
