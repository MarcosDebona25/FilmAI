import { render, waitFor } from "./render";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, expect, it, vi } from "vitest";
import { GoogleButton } from "@/components/GoogleButton";
import en from "@/messages/en/common.json";
import es from "@/messages/es/common.json";

afterEach(() => {
  vi.unstubAllEnvs();
  delete window.google;
  document.getElementById("google-identity-services")?.remove();
});
it("el botón oficial recibe el idioma activo y se vuelve a renderizar al cambiarlo", () => {
  vi.stubEnv("NEXT_PUBLIC_GOOGLE_CLIENT_ID", "test");
  const renderButton = vi.fn();
  window.google = { accounts: { id: { initialize: vi.fn(), renderButton } } };
  const view = render(
    <NextIntlClientProvider locale="en" messages={en}>
      <GoogleButton onSuccess={vi.fn()} />
    </NextIntlClientProvider>
  );
  expect(renderButton).toHaveBeenLastCalledWith(
    expect.any(HTMLDivElement),
    expect.objectContaining({ locale: "en" })
  );
  view.rerender(
    <NextIntlClientProvider locale="es" messages={es}>
      <GoogleButton onSuccess={vi.fn()} />
    </NextIntlClientProvider>
  );
  expect(renderButton).toHaveBeenLastCalledWith(
    expect.any(HTMLDivElement),
    expect.objectContaining({ locale: "es" })
  );
});
it("una carga tardía del SDK usa el idioma nuevo y no deja escuchas del componente desmontado", async () => {
  vi.stubEnv("NEXT_PUBLIC_GOOGLE_CLIENT_ID", "test");
  const renderButton = vi.fn();
  const view = render(
    <NextIntlClientProvider locale="en" messages={en}>
      <GoogleButton onSuccess={vi.fn()} />
    </NextIntlClientProvider>
  );
  const script = document.getElementById("google-identity-services")!;
  expect(script).toHaveAttribute("src", "https://accounts.google.com/gsi/client?hl=en");
  view.rerender(
    <NextIntlClientProvider locale="es" messages={es}>
      <GoogleButton onSuccess={vi.fn()} />
    </NextIntlClientProvider>
  );
  window.google = { accounts: { id: { initialize: vi.fn(), renderButton } } };
  script.dispatchEvent(new Event("load"));
  await waitFor(() => expect(renderButton).toHaveBeenCalledOnce());
  expect(renderButton).toHaveBeenCalledWith(
    expect.any(HTMLDivElement),
    expect.objectContaining({ locale: "es" })
  );
  view.unmount();
  script.dispatchEvent(new Event("load"));
  expect(renderButton).toHaveBeenCalledOnce();
});
