import { act, render, screen, waitFor } from "./render";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AccountProvider, useAccount } from "@/components/AccountProvider";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { apiFetch } from "@/lib/api";
import { localeCookie } from "@/i18n/config";

const router = vi.hoisted(() => ({ refresh: vi.fn(), replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => router, usePathname: () => "/settings" }));
vi.mock("@/lib/api", async (original) => ({
  ...(await original<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}));
function Probe() {
  const { perfil, preferencias } = useAccount();
  return (
    <>
      <output data-testid="account">
        {perfil?.idioma ?? "null"}:{preferencias?.idioma ?? "null"}
      </output>
      <LanguageSwitcher account />
    </>
  );
}
function setup(
  idioma: "en" | "es" | null,
  save: () => Promise<unknown> = async () => ({ idioma: "en" })
) {
  document.documentElement.lang = "es";
  document.cookie = `${localeCookie}=es`;
  vi.mocked(apiFetch).mockImplementation(async (path, options) => {
    if (options?.method === "PUT") return save();
    if (path === "/api/profile/") return { pk: 1, idioma };
    if (path === "/api/preferences/") return { idioma };
    return [];
  });
  render(
    <AccountProvider>
      <Probe />
    </AccountProvider>
  );
}
afterEach(() => {
  document.cookie = `${localeCookie}=; Max-Age=0`;
  vi.clearAllMocks();
});

describe("sincronización de cuenta y selector", () => {
  it("cuenta guardada prevalece sobre la cookie del dispositivo", async () => {
    setup("en");
    await waitFor(() => expect(screen.getByTestId("account")).toHaveTextContent("en:en"));
    expect(document.cookie).toContain(`${localeCookie}=en`);
    expect(router.refresh).toHaveBeenCalledOnce();
  });
  it("idioma nulo conserva la resolución vigente", async () => {
    setup(null);
    await waitFor(() => expect(apiFetch).toHaveBeenCalledWith("/api/preferences/"));
    expect(document.cookie).toContain(`${localeCookie}=es`);
    expect(router.refresh).not.toHaveBeenCalled();
  });
  it("espera confirmación del servidor antes de cambiar cuenta, cookie y render", async () => {
    let complete!: (value: unknown) => void;
    setup(
      "es",
      () =>
        new Promise((resolve) => {
          complete = resolve;
        })
    );
    await waitFor(() => expect(screen.getByTestId("account")).toHaveTextContent("es:es"));
    await userEvent.click(screen.getByRole("radio", { name: "English" }));
    expect(document.cookie).toContain(`${localeCookie}=es`);
    expect(screen.getByRole("radio", { name: "Español" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "English" })).toBeDisabled();
    await act(async () => complete({ idioma: "en" }));
    expect(document.cookie).toContain(`${localeCookie}=en`);
    expect(screen.getByTestId("account")).toHaveTextContent("en:en");
    expect(apiFetch).toHaveBeenCalledWith("/api/preferences/", {
      method: "PUT",
      body: { idioma: "en" },
    });
  });
  it("fallo al guardar conserva idioma anterior y ofrece recuperación", async () => {
    setup("es", async () => {
      throw new Error("network");
    });
    await waitFor(() => expect(screen.getByTestId("account")).toHaveTextContent("es:es"));
    await userEvent.click(screen.getByRole("radio", { name: "English" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("No pudimos guardar");
    expect(document.cookie).toContain(`${localeCookie}=es`);
    expect(screen.getByRole("radio", { name: "Español" })).toBeChecked();
    expect(router.refresh).not.toHaveBeenCalled();
  });
});
