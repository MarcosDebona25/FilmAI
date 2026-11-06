import { describe, expect, it } from "vitest";

import { ChatMarkdown } from "@/components/features/chat/ChatMarkdown";
import { render, screen } from "./render";

/**
 * La respuesta del modelo no es confiable: una sinopsis de TMDB puede traer
 * instrucciones escondidas que lo hagan escribir HTML o links (prompt
 * injection). Estos casos son los de la spec `chat-ui`, «Injected markup».
 */
describe("ChatMarkdown neutraliza lo que escribe el modelo", () => {
  it("no crea script, img ni atributos on* a partir de HTML crudo", () => {
    const { container } = render(
      <ChatMarkdown texto={'Hola <img src=x onerror="alert(1)"> y <script>alert(1)</script> fin'} />
    );
    expect(container.querySelector("script")).toBeNull();
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("[onerror]")).toBeNull();
    expect(container).toHaveTextContent("Hola");
  });

  it("un link Markdown queda como texto, sin href", () => {
    const { container } = render(
      <ChatMarkdown texto="Mirá [acá](javascript:alert(1)) o [esto](https://x.example)" />
    );
    expect(container.querySelector("a")).toBeNull();
    expect(container.querySelector("[href]")).toBeNull();
    expect(screen.getByText("acá")).toBeInTheDocument();
    expect(screen.getByText("esto")).toBeInTheDocument();
  });

  it("una imagen Markdown no crea un img (el navegador no pide la URL)", () => {
    const { container } = render(
      <ChatMarkdown texto="Mirá ![x](https://atacante.example/pixel?d=1) esto" />
    );
    expect(container.querySelector("img")).toBeNull();
    expect(container.innerHTML).not.toContain("atacante.example");
  });

  it("conserva el Markdown que sí sirve: párrafos, negrita y listas", () => {
    const { container } = render(<ChatMarkdown texto={"**Moon** (2009)\n\n- Una\n- Dos"} />);
    expect(container.querySelector("strong")).toHaveTextContent("Moon");
    expect(container.querySelectorAll("li")).toHaveLength(2);
  });
});
