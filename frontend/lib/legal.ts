import { readFile } from "node:fs/promises";
import path from "node:path";

import type { AppLocale } from "@/i18n/config";

export type LegalBlock = { type: "p"; text: string } | { type: "ul"; items: string[] };
export type LegalSection = { id: string; heading: string; blocks: LegalBlock[] };
export type LegalDocument = {
  title: string;
  updated: string;
  intro: LegalBlock[];
  sections: LegalSection[];
};

/** Interpreta el subconjunto de Markdown de `content/legal` (títulos, párrafos y listas). */
export function parseLegalMarkdown(source: string): LegalDocument {
  let text = source.replace(/\r\n/g, "\n");
  let updated = "";
  const front = text.match(/^---\n([\s\S]*?)\n---\n/);
  if (front) {
    updated = front[1].match(/^updated:\s*(.+)$/m)?.[1].trim() ?? "";
    text = text.slice(front[0].length);
  }
  const doc: LegalDocument = { title: "", updated, intro: [], sections: [] };
  let target: LegalBlock[] = doc.intro;
  for (const chunk of text.split(/\n{2,}/)) {
    const block = chunk.trim();
    if (!block) continue;
    if (block.startsWith("## ")) {
      const heading = block.slice(3).trim();
      const section: LegalSection = { id: "", heading, blocks: [] };
      section.id = `s-${doc.sections.length + 1}`;
      doc.sections.push(section);
      target = section.blocks;
    } else if (block.startsWith("# ")) {
      doc.title = block.slice(2).trim();
    } else if (block.split("\n").every((line) => line.startsWith("- "))) {
      target.push({ type: "ul", items: block.split("\n").map((line) => line.slice(2).trim()) });
    } else {
      target.push({ type: "p", text: block.replace(/\n/g, " ") });
    }
  }
  return doc;
}

export async function loadTerms(locale: AppLocale): Promise<LegalDocument> {
  const file = path.join(process.cwd(), "content", "legal", `terms.${locale}.md`);
  return parseLegalMarkdown(await readFile(file, "utf8"));
}
