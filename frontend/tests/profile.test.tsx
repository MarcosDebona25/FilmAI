import { fireEvent, render, screen, waitFor, within } from "./render";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PerfilPage from "@/app/profile/page";
import PreferenciasPage from "@/app/settings/page";
import { NavigationGuard } from "@/components/NavigationGuard";
import { Avatar } from "@/components/Avatar";
import { apiFetch } from "@/lib/api";
const { account, router } = vi.hoisted(() => ({
  account: {
    perfil: {
      pk: 1,
      nombre: "Juan",
      apellido: "Pérez",
      nombre_usuario: "juanperez",
      avatar_id: 1,
      correo: "juan@example.com",
      fecha_nacimiento: "1992-04-10",
      fecha_registro: "2026-09-01",
      genero: "masculino",
      tiene_contrasena_local: true,
    },
    avatares: [
      { id: 1, src: "/one.png" },
      { id: 2, src: "/two.png" },
    ],
    preferencias: { tema: "oscuro", perfil_publico: true },
    cargando: false,
    error: null,
    recargar: vi.fn(),
    actualizarPerfil: vi.fn(),
    actualizarPreferencia: vi.fn(),
    limpiar: vi.fn(),
  },
  router: { push: vi.fn(), replace: vi.fn() },
}));
vi.mock("next/navigation", () => ({ useRouter: () => router }));
vi.mock("@/components/AccountProvider", () => ({ useAccount: () => account }));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}));
beforeEach(() => {
  vi.clearAllMocks();
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, json: async () => ({ disponible: true }) })
  );
});
it.each([
  ["en", "Your avatar"],
  ["es", "Tu avatar"],
] as const)("el avatar conserva su nombre accesible en %s si falla la imagen", (locale, label) => {
  render(<Avatar perfil={{ ...account.perfil, idioma: null }} avatares={account.avatares} />, {
    locale,
  });
  fireEvent.error(screen.getByRole("img", { name: label }));
  expect(screen.queryByRole("img")).not.toBeInTheDocument();
  expect(screen.getByLabelText(label)).toHaveTextContent("JP");
});
describe("edición de perfil", () => {
  it("solo ofrece cambiar avatar al editar, previsualiza y lo persiste al guardar", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ ...account.perfil, avatar_id: 2 });
    render(
      <NavigationGuard>
        <PerfilPage />
      </NavigationGuard>
    );
    expect(screen.queryByRole("button", { name: "Cambiar avatar" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Editar perfil" }));
    await userEvent.click(screen.getByRole("button", { name: "Cambiar avatar" }));
    await userEvent.click(screen.getByRole("radio", { name: "Avatar 2" }));
    expect(screen.getByRole("dialog")).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: /^Guardar$/ }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(apiFetch).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
    expect(apiFetch).toHaveBeenCalledWith(
      "/api/profile/",
      expect.objectContaining({ body: expect.objectContaining({ avatar_id: 2 }) })
    );
  });
  it("cancelar sin cambios es inmediato; con cambios requiere confirmación", async () => {
    render(
      <NavigationGuard>
        <PerfilPage />
      </NavigationGuard>
    );
    await userEvent.click(screen.getByRole("button", { name: "Editar perfil" }));
    await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Editar perfil" }));
    await userEvent.clear(screen.getByLabelText("Nombre", { exact: true }));
    await userEvent.type(screen.getByLabelText("Nombre", { exact: true }), "Pedro");
    await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    await userEvent.click(screen.getByRole("button", { name: "Seguir editando" }));
    expect(screen.getByLabelText("Nombre", { exact: true })).toHaveValue("Pedro");
    await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    await userEvent.click(screen.getByRole("button", { name: "Salir sin guardar" }));
    expect(screen.getByRole("button", { name: "Editar perfil" })).toBeVisible();
  });
  it("bloquea enlaces internos y ejecuta solo la salida confirmada", async () => {
    render(
      <NavigationGuard>
        <PerfilPage />
        <a href="/settings">Ir a preferencias</a>
      </NavigationGuard>
    );
    await userEvent.click(screen.getByRole("button", { name: "Editar perfil" }));
    fireEvent.change(screen.getByLabelText("Nombre", { exact: true }), {
      target: { value: "Otro" },
    });
    await userEvent.click(screen.getByRole("link", { name: "Ir a preferencias" }));
    expect(router.push).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Salir sin guardar" }));
    expect(router.push).toHaveBeenCalledWith("/settings");
  });
  it("muestra el resultado de disponibilidad en verde o rojo", async () => {
    render(
      <NavigationGuard>
        <PerfilPage />
      </NavigationGuard>
    );
    await userEvent.click(screen.getByRole("button", { name: "Editar perfil" }));
    fireEvent.change(screen.getByLabelText("Nombre de usuario", { exact: true }), {
      target: { value: "disponible" },
    });
    expect(await screen.findByText("Disponible", { exact: true })).toHaveClass("text-green-700");
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: async () => ({ disponible: false }),
    } as Response);
    fireEvent.change(screen.getByLabelText("Nombre de usuario", { exact: true }), {
      target: { value: "ocupado" },
    });
    await waitFor(() =>
      expect(screen.getByText("No disponible", { exact: true })).toHaveClass("text-red-700")
    );
  });
});
it("baja de cuenta: conserva cancelación y usa la advertencia aprobada", async () => {
  render(<PreferenciasPage />);
  await userEvent.click(screen.getByRole("button", { name: "Dar de baja cuenta" }));
  expect(screen.getByRole("dialog")).toHaveTextContent(
    "Asegurate de querer dar de baja la cuenta antes de continuar."
  );
  expect(screen.getByRole("dialog")).not.toHaveTextContent("se conservarán");
  await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
  expect(apiFetch).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole("button", { name: "Dar de baja cuenta" }));
  vi.mocked(apiFetch).mockResolvedValue({});
  await userEvent.click(screen.getByRole("button", { name: /^Dar de baja$/ }));
  expect(apiFetch).toHaveBeenCalledWith("/api/account/deactivate/", { method: "POST" });
});

it("ignora una respuesta de disponibilidad anterior al último nombre", async () => {
  let previous!: (value: Response) => void;
  vi.mocked(fetch)
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          previous = resolve;
        })
    )
    .mockResolvedValue({ ok: true, json: async () => ({ disponible: false }) } as Response);
  render(
    <NavigationGuard>
      <PerfilPage />
    </NavigationGuard>
  );
  await userEvent.click(screen.getByRole("button", { name: "Editar perfil" }));
  fireEvent.change(screen.getByLabelText("Nombre de usuario", { exact: true }), {
    target: { value: "primero" },
  });
  await waitFor(() => expect(fetch).toHaveBeenCalledOnce());
  fireEvent.change(screen.getByLabelText("Nombre de usuario", { exact: true }), {
    target: { value: "segundo" },
  });
  await screen.findByText("No disponible", { exact: true });
  previous({ ok: true, json: async () => ({ disponible: true }) } as Response);
  await waitFor(() => expect(screen.getByText("No disponible", { exact: true })).toBeVisible());
});
it("cerrar el selector sin elegir conserva avatar y un error de guardado conserva el borrador", async () => {
  vi.mocked(apiFetch).mockRejectedValue(new Error("network"));
  render(
    <NavigationGuard>
      <PerfilPage />
    </NavigationGuard>
  );
  await userEvent.click(screen.getByRole("button", { name: "Editar perfil" }));
  await userEvent.click(screen.getByRole("button", { name: "Cambiar avatar" }));
  await userEvent.click(
    within(screen.getByRole("dialog")).getByRole("button", { name: "Cancelar" })
  );
  fireEvent.change(screen.getByLabelText("Nombre", { exact: true }), {
    target: { value: "Pedro" },
  });
  await userEvent.click(screen.getByRole("button", { name: "Guardar cambios" }));
  await waitFor(() =>
    expect(screen.getByLabelText("Nombre", { exact: true })).toHaveValue("Pedro")
  );
  expect(apiFetch).toHaveBeenCalledWith(
    "/api/profile/",
    expect.objectContaining({ body: expect.objectContaining({ avatar_id: 1 }) })
  );
});

it("guardar el avatar vigente cierra el selector sin generar cambios", async () => {
  render(
    <NavigationGuard>
      <PerfilPage />
    </NavigationGuard>
  );
  await userEvent.click(screen.getByRole("button", { name: "Editar perfil" }));
  await userEvent.click(screen.getByRole("button", { name: "Cambiar avatar" }));
  await userEvent.click(screen.getByRole("radio", { name: "Avatar 1" }));
  await userEvent.click(screen.getByRole("button", { name: /^Guardar$/ }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});
