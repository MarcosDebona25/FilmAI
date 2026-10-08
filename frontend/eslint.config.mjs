import { legacyFiles, rules } from "./scripts/i18n/rules.mjs";
import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";
import eslintConfigPrettier from "eslint-config-prettier";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    files: ["app/**/*.{ts,tsx}", "components/**/*.{ts,tsx}", "lib/**/*.{ts,tsx}"],
    plugins: { i18n: { rules } },
    rules: { "i18n/no-debug": "error", "i18n/centralized-formats": "error" },
  },
  { files: ["lib/format.ts"], rules: { "i18n/centralized-formats": "off" } },
  {
    files: ["app/**/*.{ts,tsx}", "components/**/*.{ts,tsx}"],
    ignores: [...legacyFiles, "components/ui/**"],
    rules: { "i18n/no-visible-literals": "error" },
  },
  // Desactiva las reglas de ESLint que chocan con Prettier (debe ir al final).
  eslintConfigPrettier,
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      // Directorios de salida de builds de comprobación y de Playwright
      // (ver decisión del 26/09/2026): son artefactos generados, no código
      // fuente, y al no ignorarlos un `eslint .` local reporta miles de
      // problemas ajenos. En CI no existen porque el checkout es limpio.
      ".next-build/**",
      ".next-e2e/**",
      "out/**",
      "build/**",
      "next-env.d.ts",
    ],
  },
];

export default eslintConfig;
