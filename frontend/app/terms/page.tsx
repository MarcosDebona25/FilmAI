import { ChevronDown } from "lucide-react";
import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";

import { TicketMark } from "@/components/access/Logo";
import { TermsBackLink } from "@/components/TermsBackLink";
import type { AppLocale } from "@/i18n/config";
import { formatDate } from "@/lib/format";
import { loadTerms } from "@/lib/legal";
import { routes } from "@/lib/routes";

export async function generateMetadata() {
  const locale = (await getLocale()) as AppLocale;
  const doc = await loadTerms(locale);
  return { title: `${doc.title} · FilmAI` };
}

// Celular según el canvas «Terms · mobile». El escritorio sigue pendiente de rehacerse.
export default async function TermsPage() {
  const locale = (await getLocale()) as AppLocale;
  const doc = await loadTerms(locale);
  const nav = await getTranslations("nav.main");
  const date = formatDate(doc.updated, locale, "long");
  return (
    <main
      id="contenido"
      className="mx-auto flex max-w-[1120px] flex-col gap-5 px-5 pt-4 pb-12 sm:px-10 md:gap-10 md:pt-8 md:pb-24"
    >
      <div className="flex flex-col gap-2.5 md:gap-3">
        <TermsBackLink />
        <Link
          href={routes.home}
          className="hidden min-h-11 items-center gap-2 self-start text-sm font-semibold text-muted-foreground md:inline-flex"
        >
          <TicketMark width={24} height={18} />
          {nav("backLanding")}
        </Link>
        <h1 className="mb-1.5 font-display text-[48px] leading-[0.95] sm:text-[72px] md:mb-0">
          {doc.title}
        </h1>
        <p className="text-sm text-fg-3">{nav("termsUpdated", { date })}</p>
        {doc.intro.map((block, index) =>
          block.type === "p" ? (
            <p key={index} className="max-w-[80ch] leading-[1.7] text-muted-foreground">
              {block.text}
            </p>
          ) : null
        )}
      </div>
      <div className="grid gap-5 md:grid-cols-[240px_minmax(0,1fr)] md:gap-16">
        <details className="group rounded-[14px] bg-card md:hidden">
          <summary className="flex min-h-[52px] cursor-pointer list-none items-center justify-between gap-3 px-4 font-semibold [&::-webkit-details-marker]:hidden">
            {nav("termsOnPage")}
            <ChevronDown
              aria-hidden="true"
              className="size-[18px] transition-transform group-open:rotate-180"
            />
          </summary>
          <nav aria-label={nav("termsOnPage")} className="px-1 pb-2.5">
            <ol className="flex flex-col gap-0.5">
              {doc.sections.map((section) => (
                <li key={section.id}>
                  <a
                    href={`#${section.id}`}
                    className="flex min-h-10 items-center rounded-lg px-3 text-[15px] leading-[1.35] text-muted-foreground"
                  >
                    {section.heading}
                  </a>
                </li>
              ))}
            </ol>
          </nav>
        </details>
        <nav
          aria-label={nav("termsOnPage")}
          className="hidden md:sticky md:top-6 md:block md:self-start"
        >
          <p className="mb-2 px-3 text-xs text-fg-3">{nav("termsOnPage")}</p>
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
              className="flex flex-col gap-3 border-t border-border py-7 md:py-8"
            >
              <h2
                id={section.id}
                className="scroll-mt-6 font-display text-[28px] leading-[1.05] md:text-[30px]"
              >
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
