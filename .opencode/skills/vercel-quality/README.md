# vercel-quality

## Qué hace

Skill de validación post-implementación con reglas MUST/SHOULD/NEVER. Audita interacciones (keyboard, touch, forms), animaciones (compositor, easing, reduced-motion), layout (alignment, safe-areas), accesibilidad, performance (CLS, virtualization, reflows), dark mode, y diseño (contrast, shadows, radii).

## Cuándo usarla

**Solo después de que la implementación está completa.** Es el último paso del pipeline. Activarla para:
- Validar que el output cumple estándares de producción
- Detectar regresiones de accesibilidad
- Auditar performance y CLS
- Revisar edge cases (contenido largo, estados vacíos, dark mode)

## Flujo

1. Recibe el código implementado
2. Audita contra cada categoría de reglas
3. Reporta: Category | Rule | Severity | File:Line | Issue | Fix
4. Los MUST son bloqueantes, los SHOULD son warnings

## Dónde encaja

```
design-discovery → Design Brief → frontend-design → emil-design-eng → vercel-quality
                                                                           ↑
                                                                   último paso
```

## Instalación

```bash
npx skills add <repo-url> --skill "vercel-quality"
```

O copiar `skills/vercel-quality/SKILL.md` a `.opencode/skills/vercel-quality/` del proyecto.
