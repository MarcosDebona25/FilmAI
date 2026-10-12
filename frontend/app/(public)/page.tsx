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
      <div className="flex flex-col items-center gap-9 text-center">
        <div className="flex items-center gap-4 sm:gap-[18px]">
          <TicketMark width={72} height={54} className="max-sm:h-[39px] max-sm:w-[52px]" />
          <h1
            translate="no"
            className="font-display text-[72px] leading-[0.9] tracking-[0.05em] sm:text-[104px]"
          >
            FilmAI
          </h1>
        </div>
        <p className="max-w-[460px] text-[19px] leading-[1.45] text-muted-foreground sm:text-[22px]">
          {t("description")}
        </p>
        <div className="flex w-full max-w-[380px] flex-col gap-3">
          <Link href="/inicio" className={`${primaryButtonClass} gap-2 text-[17px]`}>
            {t("explore")}
            <ChevronRight aria-hidden="true" className="size-[18px]" />
          </Link>
          <Link href={routes.register} className={`${secondaryButtonClass} text-[17px]`}>
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
          className="inline-flex min-h-11 items-center text-[13px] text-fg-3 underline underline-offset-[3px] max-sm:absolute max-sm:bottom-3 max-sm:left-1/2 max-sm:-translate-x-1/2"
        >
          {nav("main.terms")}
        </Link>
      </div>
    </AccessShell>
  );
}
