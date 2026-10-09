import { readFileSync, readdirSync } from "node:fs";
import { resolve, relative } from "node:path";
import ts from "typescript";
import { legacyFiles } from "./rules.mjs";

export function residues(root) {
  const violations = [];
  function walk(directory) {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const path = resolve(directory, entry.name);
      if (entry.isDirectory()) {
        if (entry.name !== "ui") walk(path);
        continue;
      }
      if (!/\.tsx?$/.test(path) || legacyFiles.includes(relative(root, path))) continue;
      const source = ts.createSourceFile(
        path,
        readFileSync(path, "utf8"),
        ts.ScriptTarget.Latest,
        true
      );
      function visit(node) {
        if (
          (ts.isStringLiteral(node) || ts.isJsxText(node)) &&
          (/[áéíóúñ¿¡]/i.test(node.text) ||
            (/\b(?:cuenta|correo|iniciar|guardar|cancelar|cargando|pudimos|letras|contraseña)\b/i.test(
              node.text
            ) &&
              !/^[a-z][a-z0-9_.:/-]*$/.test(node.text)))
        )
          violations.push(
            `${relative(root, path)}:${source.getLineAndCharacterOfPosition(node.getStart()).line + 1}: ${node.text.trim()}`
          );
        ts.forEachChild(node, visit);
      }
      visit(source);
    }
  }
  for (const directory of ["app", "components", "lib"]) walk(resolve(root, directory));
  return violations;
}
if (process.argv[1]?.endsWith("check.mjs")) {
  const found = residues(process.cwd());
  if (found.length) {
    process.stderr.write(`${found.join("\n")}\n`);
    process.exitCode = 1;
  } else process.stdout.write("Sin residuos fuera de las excepciones documentadas.\n");
}
