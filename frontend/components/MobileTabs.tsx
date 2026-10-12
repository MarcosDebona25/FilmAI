"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bookmark, House, Search } from "lucide-react";
import { useTranslations } from "next-intl";

import { useAccount } from "@/components/AccountProvider";
import { Avatar } from "@/components/Avatar";
import { isAccessPath, routes } from "@/lib/routes";

/** Barra inferior de celular (Home, Search, Lists, Profile); solo con sesión. */
export function MobileTabs() {
  const t = useTranslations("nav.main");
  const pathname = usePathname();
  const { perfil, avatares, cargando } = useAccount();

  if (cargando || !perfil || isAccessPath(pathname)) return null;

  const tabs = [
    {
      href: routes.explore,
      label: t("home"),
      icon: <House aria-hidden="true" className="size-[22px]" />,
    },
    {
      href: routes.search,
      label: t("search"),
      icon: <Search aria-hidden="true" className="size-[22px]" />,
    },
    {
      href: routes.lists,
      label: t("lists"),
      icon: <Bookmark aria-hidden="true" className="size-[22px]" />,
    },
    {
      href: routes.profile,
      label: t("profileShort"),
      icon: (
        <span aria-hidden="true">
          <Avatar perfil={perfil} avatares={avatares} size={24} />
        </span>
      ),
    },
  ];

  return (
    <>
      <div aria-hidden="true" className="h-[76px] md:hidden" />
      <nav
        aria-label={t("mainLabel")}
        className="fixed inset-x-0 bottom-0 z-30 grid h-[76px] grid-cols-4 bg-raised px-2 pb-1 shadow-[inset_0_1px_0_var(--line)] md:hidden"
      >
        {tabs.map((tab) => {
          const current = pathname === tab.href;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              aria-current={current ? "page" : undefined}
              className={`flex flex-col items-center justify-center gap-1 text-xs no-underline focus-visible:outline-2 focus-visible:outline-ring ${current ? "font-semibold text-foreground" : "font-medium text-fg-2"}`}
            >
              {tab.icon}
              {tab.label}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
