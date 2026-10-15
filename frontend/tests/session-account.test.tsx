import { beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

import { AccountProvider, useAccount } from "@/components/AccountProvider";
import { SESION_VENCIDA, apiFetch } from "@/lib/api";
import { render, screen, waitFor } from "./render";

const nav = vi.hoisted(() => ({
  pathname: "/profile",
  router: { refresh: vi.fn(), replace: vi.fn() },
}));
vi.mock("next/navigation", () => ({
  useRouter: () => nav.router,
  usePathname: () => nav.pathname,
}));
vi.mock("sonner", () => ({ toast: { info: vi.fn(), success: vi.fn(), error: vi.fn() } }));
vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}));

function Probe() {
  const { perfil, cargando } = useAccount();
  return (
    <output data-testid="cuenta">{cargando ? "cargando" : (perfil?.nombre ?? "sin sesión")}</output>
  );
}

describe("AccountProvider y el vencimiento", () => {
  beforeEach(() => {
    nav.pathname = "/profile";
    vi.mocked(toast.info).mockClear();
    nav.router.replace.mockClear();
  });

  it("sin cookies de sesión no pregunta por el perfil", async () => {
    nav.pathname = "/search";
    vi.mocked(apiFetch).mockClear();
    render(
      <AccountProvider sesionPosible={false}>
        <Probe />
      </AccountProvider>
    );
    expect(await screen.findByText("sin sesión")).toBeVisible();
    expect(apiFetch).not.toHaveBeenCalled();
  });

  it("si la sesión vence, avisa el motivo y lleva al login", async () => {
    vi.mocked(apiFetch).mockImplementation(async (path) => {
      if (path === "/api/profile/") return { pk: 1, nombre: "Juan" };
      return path === "/api/avatars/" ? [] : { tema: "oscuro" };
    });
    render(
      <AccountProvider>
        <Probe />
      </AccountProvider>
    );
    expect(await screen.findByText("Juan")).toBeVisible();
    window.dispatchEvent(new Event(SESION_VENCIDA));
    await waitFor(() =>
      expect(toast.info).toHaveBeenCalledWith("Tu sesión venció. Iniciá sesión de nuevo.")
    );
    expect(nav.router.replace).toHaveBeenCalledWith("/login?next=%2Fprofile");
    expect(screen.getByText("sin sesión")).toBeVisible();
  });

  it("a quien nunca inició sesión no le avisa nada", async () => {
    nav.pathname = "/search";
    render(
      <AccountProvider sesionPosible={false}>
        <Probe />
      </AccountProvider>
    );
    await screen.findByText("sin sesión");
    window.dispatchEvent(new Event(SESION_VENCIDA));
    expect(toast.info).not.toHaveBeenCalled();
  });
});
