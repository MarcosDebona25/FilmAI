import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import en from "@/messages/en/common.json";
import { render, screen } from "./render";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), refresh: vi.fn() }),
}));
vi.mock("@/lib/google-auth", async (original) => ({
  ...(await original<typeof import("@/lib/google-auth")>()),
  tieneGooglePendiente: () => true,
}));
vi.mock("@/components/GoogleButton", () => ({
  GoogleButton: () => <button type="button">google</button>,
}));

import CompletarGooglePage from "@/app/complete-signup/page";

afterEach(() => vi.clearAllMocks());

describe("completar registro con Google", () => {
  it("recorrer los campos no muestra errores y el botón de Google está inerte", async () => {
    const user = userEvent.setup();
    const { container } = render(<CompletarGooglePage />, { locale: "en" });
    await user.click(screen.getByRole("textbox"));
    await user.tab();
    await user.tab();
    await user.tab();
    expect(screen.queryAllByRole("alert")).toHaveLength(0);
    expect(container.querySelector("[inert]")).not.toBeNull();
    expect(screen.getByText(en.auth.signUp.submitPending)).toBeInTheDocument();
  });

  it("con los datos válidos y los términos aceptados el botón de Google se activa", async () => {
    const user = userEvent.setup();
    const { container } = render(<CompletarGooglePage />, { locale: "en" });
    await user.type(screen.getByRole("textbox"), "juanperez");
    await user.type(container.querySelector('input[type="date"]')!, "1992-04-10");
    await user.selectOptions(screen.getByRole("combobox"), "masculino");
    await user.click(screen.getByRole("checkbox"));
    expect(container.querySelector("[inert]")).toBeNull();
  });
});
