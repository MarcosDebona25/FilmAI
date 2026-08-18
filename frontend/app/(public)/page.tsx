import { Button } from "@/components/ui/button";

export default function PublicHome() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <h1 className="font-heading text-4xl font-bold tracking-tight text-foreground">FilmAI</h1>
      <p className="max-w-md text-center text-muted-foreground text">
        Plataforma de reseñas cinematográficas con recomendaciones inteligentes.
      </p>
      <div className="flex gap-3">
        <Button>Explorar catálogo</Button>
        <Button variant="outline">Iniciar sesión</Button>
      </div>
    </main>
  );
}
