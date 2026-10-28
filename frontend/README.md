# FilmAI · Frontend

Aplicación web de FilmAI: Next.js 15 (App Router) con React 19, Tailwind CSS 4, componentes de shadcn/ui sobre Base UI y `next-intl` para el multiidioma (inglés y español). Habla con el backend Django por la API REST de `/api/`.

La documentación de dominio (requerimientos, UI, decisiones) está en `../docs/` y es la fuente de verdad. Este archivo solo cubre cómo trabajar dentro de `frontend/`. Para levantar todo el proyecto por primera vez (variables de entorno, cuentas de prueba, semilla), seguí el `README.md` de la raíz.

## Arranque

El camino habitual es con Docker, desde la raíz del repositorio:

```bash
docker compose up --build   # primera vez, o tras cambiar un Dockerfile
docker compose up           # las veces siguientes
docker compose logs -f frontend
```

El servicio `frontend` corre `next dev --turbopack` en http://localhost:3000, monta esta carpeta (hay hot-reload) y espera al backend en http://localhost:8000. El `.env` de la raíz define `NEXT_PUBLIC_API_URL` y `NEXT_PUBLIC_GOOGLE_CLIENT_ID` (ver `../.env.example`). Next.js solo expone al navegador las variables que empiezan con `NEXT_PUBLIC_`.

También se puede correr sin Docker (Node 22): `npm ci && npm run dev`, con el backend ya levantado.

## Scripts

| Comando                                   | Qué hace                                                      |
| ----------------------------------------- | ------------------------------------------------------------- |
| `npm run dev`                             | Servidor de desarrollo con Turbopack                          |
| `npm run build` / `npm start`             | Compilación de producción y servidor sobre ella               |
| `npm run lint`                            | ESLint (el CI lo corre con `--max-warnings=0`)                |
| `npm run format` / `npm run format:check` | Prettier: escribe o solo verifica                             |
| `npm run test:unit`                       | Vitest (`tests/`)                                             |
| `npm run test:e2e`                        | Playwright (`e2e/`)                                           |
| `npm run i18n:generate`                   | Genera `messages/{en,es}/` desde los CSV de `../traducciones` |
| `npm run i18n:check`                      | Verifica catálogos y reglas de texto visible                  |
| `npx tsc --noEmit`                        | Chequeo de tipos (también corre en el CI)                     |

`npm install` activa los hooks de Husky (`prepare`): el commit corre ESLint y Prettier sobre el frontend, así que un commit con archivos sin formatear falla.

## Tests

- **Unitarios** (`tests/`, Vitest + Testing Library, entorno jsdom): lógica de `lib/`, componentes y catálogos de traducción. `npm run test:unit`.
- **End to end** (`e2e/`, Playwright, Chromium, `es-AR`): recorren pantallas reales en el navegador. Playwright levanta su propio servidor de desarrollo en el puerto 3100 con `.next-e2e` como carpeta de compilación, y las pruebas **simulan la API** con `page.route`, así que no necesitan backend ni base de datos. `e2e/cuenta.ts` tiene el helper `prepararCuenta` para simular una sesión.
  - Primera vez: `npx playwright install chromium`.
  - Uno solo: `npx playwright test e2e/listas.spec.ts -g "nombre del test"`.
  - Estabilidad: `npx playwright test --workers=2 --repeat-each=5 e2e/archivo.spec.ts`.
- **Escribir e2e estables**: el servidor de desarrollo compila cada página la primera vez, y lo que se escribe o se clica antes de que la página hidrate se pierde. Para esos pasos, envolver la acción y su comprobación en `await expect(async () => { ... }).toPass({ timeout })`, con aserciones internas de timeout corto (un `timeout: 0` significa «sin límite» y evita que `toPass` reintente).
- La suite del backend se corre aparte (`python manage.py test`, ver la raíz).

El CI (`.github/workflows/ci.yml`) corre, en este orden: ESLint, Prettier, Vitest, `i18n:check`, `tsc`, `build` y Playwright. Es la única puerta automática antes de mergear: corré lo mismo en local antes.

## Multiidioma

Los textos visibles no se escriben en el código. La copia aprobada vive en `../traducciones/claves.csv` y `claves-extra.csv`; `npm run i18n:generate` produce `messages/en/` y `messages/es/`, que no se editan a mano. En componentes se usa `useTranslations("namespace")` (o `getTranslations` en servidor). Las reglas de ESLint de `scripts/i18n/rules.mjs` rechazan literales visibles. Los errores de la API se traducen por `code`, nunca por `detail` ni `debug`, y los formatos de fecha y número salen de `lib/format.ts`. La guía completa está en `../traducciones/guia.md`.

## Convenciones

- **Rutas visibles**: se declaran en `lib/routes.ts`; no se escriben a mano en los enlaces. Los enlaces de los correos y los del frontend se modifican juntos.
- **Estructura**: `app/` (rutas, App Router), `components/` (`ui/` es shadcn; `features/` y `access/` son de dominio), `lib/` (lógica sin UI: API, validaciones, formatos), `messages/` (generado), `i18n/` (configuración de `next-intl`), `public/` (estáticos).
- **Interfaz**: la app es solo oscura; los lineamientos están en `../docs/04_Lineamientos_UI.md`. Los controles táctiles miden 44 px o más.
- **Código**: TypeScript estricto, Prettier como único estilo y alias `@/` para importar desde la raíz de `frontend/`.
- **Decisiones**: todo cambio relevante se anota en `../docs/decisiones.md`, y las skills y reglas para agentes están en `../AGENTS.md`.
