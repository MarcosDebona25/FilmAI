import ReactMarkdown, { type Components } from "react-markdown";
import rehypeSanitize from "rehype-sanitize";

/**
 * Links e imágenes del modelo se muestran como texto (28/10/2026). Un link
 * podría llevar a un sitio elegido por prompt injection, y una imagen haría
 * que el navegador pida sola una URL del atacante (filtra la IP y lo que vaya
 * en la query). Los links a fichas los arma el front en `ChatTarjetas`.
 */
const componentes: Components = {
  a: ({ children }) => <span>{children}</span>,
  img: ({ alt }) => (alt ? <span>{alt}</span> : null),
};

/**
 * Respuesta del asistente en Markdown, sin HTML: `react-markdown` arma
 * elementos de React (nunca `innerHTML`) y escapa el HTML crudo; sin
 * `rehype-raw` ese HTML nunca llega al DOM. `rehype-sanitize` es la segunda
 * red: solo deja pasar etiquetas y atributos de una lista blanca.
 */
export function ChatMarkdown({ texto }: { texto: string }) {
  return (
    <div className="flex flex-col gap-3 leading-[1.6] break-words [&_ol]:list-decimal [&_ol]:pl-5 [&_ul]:list-disc [&_ul]:pl-5">
      <ReactMarkdown rehypePlugins={[rehypeSanitize]} components={componentes}>
        {texto}
      </ReactMarkdown>
    </div>
  );
}
