import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import en from "@/messages/en/common.json";
import { render, screen, within } from "./render";

vi.mock("next/image", () => ({
  // eslint-disable-next-line @next/next/no-img-element
  default: ({ alt }: { alt: string }) => <img alt={alt} />,
}));

import { SignupAvatarDialog } from "@/components/access/SignupAvatarDialog";

const signUp = en.auth.signUp;
// El catálogo real trae 26 avatares: 2 páginas de 18 en escritorio, 3 de 12 en celular.
const avatares = Array.from({ length: 26 }, (_, i) => ({ id: i + 1, src: `/a${i + 1}.png` }));

/** jsdom no trae `matchMedia`: simula el corte `md:` de escritorio o celular. */
function pantalla(escritorio: boolean) {
  vi.stubGlobal("matchMedia", (consulta: string) => ({
    matches: escritorio,
    media: consulta,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
}

function abrir(avatarId = 1) {
  const onUse = vi.fn();
  const onClose = vi.fn();
  render(
    <SignupAvatarDialog avatares={avatares} avatarId={avatarId} onUse={onUse} onClose={onClose} />,
    { locale: "en" }
  );
  return { onUse, onClose, user: userEvent.setup() };
}

const radios = () => within(screen.getByRole("radiogroup")).getAllByRole("radio");
const radio = (n: number) => screen.getByRole("radio", { name: `Avatar ${n}` });
const anterior = () => screen.getByRole("button", { name: signUp.avatarPrevious });
const siguiente = () => screen.getByRole("button", { name: signUp.avatarMore });
const pagina = (n: number, total: number) => screen.getByText(`${n} of ${total}`);

afterEach(() => vi.unstubAllGlobals());

describe("paginado del diálogo de avatar del registro", () => {
  it("en escritorio muestra 18 por página: 26 avatares son 2 páginas", async () => {
    pantalla(true);
    const { user } = abrir();
    expect(radios()).toHaveLength(18);
    expect(pagina(1, 2)).toHaveAttribute("aria-live", "polite");

    await user.click(siguiente());
    // La última página es corta y la numeración sigue la del catálogo.
    expect(radios()).toHaveLength(8);
    expect(radio(19)).toBeInTheDocument();
    expect(radio(26)).toBeInTheDocument();
    expect(pagina(2, 2)).toBeInTheDocument();
  });

  it("en celular muestra 12 por página: 26 avatares son 3 páginas", async () => {
    pantalla(false);
    const { user } = abrir();
    expect(radios()).toHaveLength(12);
    expect(pagina(1, 3)).toBeInTheDocument();

    await user.click(siguiente());
    expect(radios()).toHaveLength(12);
    expect(radio(13)).toBeInTheDocument();
    await user.click(siguiente());
    expect(radios()).toHaveLength(2);
    expect(pagina(3, 3)).toBeInTheDocument();
  });

  it("abre en la página del avatar actual, con el foco en él", () => {
    pantalla(true);
    abrir(20);
    expect(pagina(2, 2)).toBeInTheDocument();
    expect(radio(20)).toHaveAttribute("aria-checked", "true");
    expect(radio(20)).toHaveFocus();
  });

  it("en los extremos la flecha queda inerte, a la vista y sin perder el foco", async () => {
    pantalla(true);
    const { user } = abrir();
    expect(anterior()).toHaveAttribute("aria-disabled", "true");
    expect(siguiente()).toHaveAttribute("aria-disabled", "false");
    // Inerte: el clic no cambia de página.
    await user.click(anterior());
    expect(pagina(1, 2)).toBeInTheDocument();

    await user.click(siguiente());
    expect(siguiente()).toHaveAttribute("aria-disabled", "true");
    expect(anterior()).toHaveAttribute("aria-disabled", "false");
    // La flecha que se usó conserva el foco aunque haya quedado inerte.
    expect(siguiente()).toHaveFocus();
    await user.click(siguiente());
    expect(pagina(2, 2)).toBeInTheDocument();
  });

  it("cambiar de página conserva la elección", async () => {
    pantalla(true);
    const { user, onUse } = abrir();
    await user.click(radio(3));
    await user.click(siguiente());
    // En la otra página no hay ninguno marcado, pero el grupo sigue entrando con Tab.
    expect(radios().filter((r) => r.getAttribute("aria-checked") === "true")).toHaveLength(0);
    expect(radios().filter((r) => r.tabIndex === 0)).toHaveLength(1);
    await user.click(anterior());
    expect(radio(3)).toHaveAttribute("aria-checked", "true");

    await user.click(screen.getByRole("button", { name: signUp.avatarUse }));
    expect(onUse).toHaveBeenCalledWith(3);
  });

  it("las flechas del teclado se mueven dentro de la página visible", async () => {
    pantalla(true);
    const { user } = abrir(18);
    expect(radio(18)).toHaveFocus();
    // Desde el último de la página, → vuelve al primero de esa misma página.
    await user.keyboard("{ArrowRight}");
    expect(radio(1)).toHaveFocus();
    expect(radio(1)).toHaveAttribute("aria-checked", "true");
    expect(pagina(1, 2)).toBeInTheDocument();
  });

  it("«Use this avatar» aplica un avatar de la página 2", async () => {
    pantalla(true);
    const { user, onUse } = abrir();
    await user.click(siguiente());
    await user.click(radio(23));
    expect(radio(23)).toHaveAttribute("aria-checked", "true");
    await user.click(screen.getByRole("button", { name: signUp.avatarUse }));
    expect(onUse).toHaveBeenCalledWith(23);
  });
});
