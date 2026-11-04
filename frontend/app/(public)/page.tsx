import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { AccessShell } from "@/components/access/AccessShell";
import { TicketMark } from "@/components/access/Logo";
import { primaryButtonClass, secondaryButtonClass } from "@/components/access/styles";
import { routes } from "@/lib/routes";

export default async function LandingPage() {
  const t = await getTranslations("auth.landing");
  const nav = await getTranslations("nav");
  return (
    <AccessShell>
      <div className="flex flex-col items-center gap-9 text-center lg:pt-[4.6875rem]">
        <div className="flex items-center gap-4 sm:gap-[1.125rem]">
          <TicketMark width={72} height={54} className="max-sm:h-[2.4375rem] max-sm:w-[3.25rem]" />
          <h1
            translate="no"
            className="font-display text-[4.5rem] leading-[0.9] tracking-[0.05em] sm:text-[6.5rem]"
          >
            FilmAI
          </h1>
        </div>
        <p className="max-w-[28.75rem] text-[1.1875rem] leading-[1.45] text-muted-foreground sm:text-[1.375rem]">
          {t("description")}
        </p>
        <div className="flex w-full max-w-[23.75rem] flex-col gap-3">
          <Link href={routes.explore} className={`${primaryButtonClass} gap-2 text-[1.0625rem]`}>
            {t("explore")}
            <ChevronRight aria-hidden="true" className="size-[1.125rem]" />
          </Link>
          <Link href={routes.register} className={`${secondaryButtonClass} text-[1.0625rem]`}>
            {nav("account.signUp")}
          </Link>
          <p className="mt-1.5 text-center text-muted-foreground">
            {t("loginPrompt")}{" "}
            <Link href={routes.login} className="font-semibold text-foreground">
              {nav("account.logIn")}
            </Link>
          </p>
        </div>
        <Link
          href={routes.terms}
          className="inline-flex min-h-11 items-center text-[0.8125rem] text-fg-3 underline underline-offset-[3px] max-sm:absolute max-sm:bottom-3 max-sm:left-1/2 max-sm:-translate-x-1/2"
        >
          {nav("main.terms")}
        </Link>
      </div>
    </AccessShell>
  );
}
