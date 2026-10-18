import { beforeEach, describe, expect, it, vi } from "vitest";
import { toast } from "sonner";

import { AccountProvider, useAccount } from "@/components/AccountProvider";
import { ApiError, SESION_VENCIDA, apiFetch } from "@/lib/api";
import { translateError } from "@/lib/errors";
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

function ProbeError() {
  const { error } = useAccount();
  return <output data-testid="error">{error ?? "sin error"}</output>;
}

describe("AccountProvider cuando la cuenta no carga", () => {
  it("muestra el mensaje del error y no el genérico de «la acción»", async () => {
    // Q-03: antes cualquier falla decía «No pudimos completar la acción».
    nav.pathname = "/profile";
    vi.mocked(apiFetch).mockRejectedValue(
      new ApiError(500, { code: "server_error", params: {}, errors: [] })
    );
    render(
      <AccountProvider>
        <ProbeError />
      </AccountProvider>
    );

    // El mensaje sale del propio error (servidor), no del código «unknown».
    expect(await screen.findByText(translateError({ code: "server_error" }))).toBeVisible();
    expect(screen.queryByText(translateError({ code: "unknown" }))).not.toBeInTheDocument();
  });
});

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
      return path === "/api/avatars/" ? [] : {};
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
