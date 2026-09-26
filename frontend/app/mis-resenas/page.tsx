import Link from "next/link";

export const metadata = { title: "Mis reseñas | FilmAI" };

export default function MisResenasPage() {
  return (
    <main id="contenido" className="mx-auto max-w-5xl px-6 py-12">
      <nav aria-label="Ruta de navegación" className="mb-8 text-sm text-muted-foreground">
        Mis reseñas
      </nav>
      <h1 className="mb-6 text-3xl font-bold text-foreground">Mis reseñas</h1>
      <div className="max-w-xl rounded-xl border border-border bg-card p-8">
        <p className="text-lg font-semibold text-foreground">
          Esta sección todavía no está implementada.
        </p>
        <p className="mt-2 text-muted-foreground">
          Cuando esté disponible, vas a poder consultar y gestionar tus reseñas desde acá.
        </p>
        <Link
          href="/perfil"
          className="mt-6 inline-block text-primary underline underline-offset-4"
        >
          Volver a mi perfil
        </Link>
      </div>
    </main>
  );
}
