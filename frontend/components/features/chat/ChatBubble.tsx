import type { Tarjeta } from "@/lib/chat";

import { ChatMarkdown } from "./ChatMarkdown";
import { ChatTarjetas } from "./ChatTarjetas";

/** La pregunta del usuario: burbuja a la derecha (canvas, sección 10). */
export function BurbujaUsuario({ texto }: { texto: string }) {
  return (
    <p className="m-0 max-w-[84%] self-end rounded-[1rem_1rem_0.25rem_1rem] bg-raised-2 px-3.5 py-3 break-words whitespace-pre-wrap md:max-w-[80%] md:px-4">
      {texto}
    </p>
  );
}

/** La respuesta del asistente: texto suelto en Markdown seguro y sus tarjetas. */
export function RespuestaAsistente({ texto, tarjetas }: { texto: string; tarjetas: Tarjeta[] }) {
  return (
    <div className="flex max-w-full flex-col gap-2.5 md:max-w-[96%] md:gap-3">
      <ChatMarkdown texto={texto} />
      <ChatTarjetas tarjetas={tarjetas} />
    </div>
  );
}
