"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bookmark, House, LogIn, Search } from "lucide-react";
import { useTranslations } from "next-intl";

import { useAccount } from "@/components/AccountProvider";
import { Avatar } from "@/components/Avatar";
import { isAccessPath, routes } from "@/lib/routes";

/**
 * Barra inferior de celular. Con sesión: Home, Search, Lists y Profile.
 * Sin sesión: Home, Search y Log in, así el buscador (público) también es
 * alcanzable en celular, donde el encabezado oculta la navegación.
 */
export function MobileTabs() {
  const t = useTranslations("nav.main");
  const account = useTranslations("nav.account");
  const pathname = usePathname();
  const { perfil, avatares, cargando } = useAccount();

  if (cargando || isAccessPath(pathname)) return null;

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
      icon: perfil && (
        <span aria-hidden="true">
          <Avatar perfil={perfil} avatares={avatares} size={24} />
        </span>
      ),
    },
  ];
  const visibles = perfil
    ? tabs
    : [
        tabs[0],
        tabs[1],
        {
          href: routes.login,
          label: account("logIn"),
          icon: <LogIn aria-hidden="true" className="size-[22px]" />,
        },
      ];

  return (
    <>
      <div aria-hidden="true" className="h-[76px] md:hidden" />
      <nav
        aria-label={t("mainLabel")}
        className={`fixed inset-x-0 bottom-0 z-30 grid h-[76px] ${perfil ? "grid-cols-4" : "grid-cols-3"} bg-raised px-2 pb-1 shadow-[inset_0_1px_0_var(--line)] md:hidden`}
      >
        {visibles.map((tab) => {
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
