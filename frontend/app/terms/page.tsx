import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";

import { TicketMark } from "@/components/access/Logo";
import type { AppLocale } from "@/i18n/config";
import { formatDate } from "@/lib/format";
import { loadTerms } from "@/lib/legal";
import { routes } from "@/lib/routes";

export async function generateMetadata() {
  const locale = (await getLocale()) as AppLocale;
  const doc = await loadTerms(locale);
  return { title: `${doc.title} · FilmAI` };
}

// Versión mínima; el punto 9 del plan la refina (con/sin sesión, escritorio/celular).
export default async function TermsPage() {
  const locale = (await getLocale()) as AppLocale;
  const doc = await loadTerms(locale);
  const nav = await getTranslations("nav.main");
  const date = formatDate(doc.updated, locale, "long");
  return (
    <main
      id="contenido"
      className="mx-auto flex max-w-[1120px] flex-col gap-10 px-5 pt-8 pb-24 sm:px-10"
    >
      <div className="flex flex-col gap-3">
        <Link
          href={routes.home}
          className="inline-flex min-h-11 items-center gap-2 self-start text-sm font-semibold text-muted-foreground"
        >
          <TicketMark width={24} height={18} />
          {nav("backLanding")}
        </Link>
        <h1 className="font-display text-[48px] leading-[0.95] sm:text-[72px]">{doc.title}</h1>
        <p className="text-sm text-fg-3">{date}</p>
        {doc.intro.map((block, index) =>
          block.type === "p" ? (
            <p key={index} className="max-w-[80ch] leading-[1.7] text-muted-foreground">
              {block.text}
            </p>
          ) : null
        )}
      </div>
      <div className="grid gap-6 md:grid-cols-[240px_minmax(0,1fr)] md:gap-16">
        <nav aria-label={nav("mainLabel")} className="md:sticky md:top-6 md:self-start">
          <ol className="flex flex-col gap-0.5">
            {doc.sections.map((section) => (
              <li key={section.id}>
                <a
                  href={`#${section.id}`}
                  className="block rounded-lg px-3 py-1.5 text-sm text-muted-foreground hover:bg-card hover:text-foreground"
                >
                  {section.heading}
                </a>
              </li>
            ))}
          </ol>
        </nav>
        <div>
          {doc.sections.map((section) => (
            <section
              key={section.id}
              aria-labelledby={section.id}
              className="flex flex-col gap-3 border-t border-border py-8"
            >
              <h2 id={section.id} className="scroll-mt-6 font-display text-[30px] leading-[1.05]">
                {section.heading}
              </h2>
              {section.blocks.map((block, index) =>
                block.type === "p" ? (
                  <p key={index} className="max-w-[68ch] leading-[1.7] text-muted-foreground">
                    {block.text}
                  </p>
                ) : (
                  <ul
                    key={index}
                    className="flex max-w-[68ch] list-disc flex-col gap-1.5 pl-[22px]"
                  >
                    {block.items.map((item) => (
                      <li key={item} className="leading-[1.7] text-muted-foreground">
                        {item}
                      </li>
                    ))}
                  </ul>
                )
              )}
            </section>
          ))}
        </div>
      </div>
    </main>
  );
}
