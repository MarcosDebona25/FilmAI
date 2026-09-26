"""Sincroniza el catálogo de avatares con las imágenes individuales de Next.js.

Los IDs existentes no se reutilizan: cambiar un archivo nunca debe cambiar el
avatar que eligió un usuario en la base de datos.
"""

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "frontend/public/avatars/recortados"
CATALOG = ROOT / "backend/usuarios/avatar_catalog.json"
EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def main():
    old = json.loads(CATALOG.read_text(encoding="utf-8")) if CATALOG.exists() else []
    existing = {item["filename"]: item["id"] for item in old}
    next_id = max((item["id"] for item in old), default=0) + 1
    images = sorted(
        (file for file in IMAGES.iterdir() if file.is_file() and file.suffix.lower() in EXTENSIONS),
        key=lambda file: file.name.casefold(),
    )
    catalog = []
    for file in images:
        avatar_id = existing.get(file.name)
        if avatar_id is None:
            numbered = re.fullmatch(r"avatar \((\d+)\)\.[^.]+", file.name)
            suggested = int(numbered.group(1)) if numbered else None
            used_ids = {item["id"] for item in catalog} | set(existing.values())
            if suggested is not None and suggested not in used_ids:
                avatar_id = suggested
            else:
                while next_id in used_ids:
                    next_id += 1
                avatar_id = next_id
                next_id += 1
        catalog.append({"id": avatar_id, "filename": file.name, "active": True})
    present = {item["filename"] for item in catalog}
    catalog.extend(
        {**item, "active": False} for item in old if item["filename"] not in present
    )
    catalog.sort(key=lambda item: item["id"])
    if not any(item["id"] == 1 and item["active"] for item in catalog):
        raise SystemExit("Falta el avatar predeterminado (ID 1).")
    contenido = json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
    if "--check" in sys.argv:
        if not CATALOG.exists() or CATALOG.read_text(encoding="utf-8") != contenido:
            raise SystemExit("Catálogo desactualizado: ejecutá python3 scripts/sync_avatars.py")
        print(f"Catálogo actualizado: {sum(item['active'] for item in catalog)} avatares")
        return
    CATALOG.write_text(contenido, encoding="utf-8")
    print(f"{sum(item['active'] for item in catalog)} avatares sincronizados en {CATALOG.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
