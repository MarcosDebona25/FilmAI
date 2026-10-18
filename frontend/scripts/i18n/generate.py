"""Siembra reproducible de los CSV aprobados, sin textos de correos en el cliente."""

import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def put(messages, key, value):
    parts = key.split(".")
    for part in parts[:-1]:
        messages = messages.setdefault(part, {})
    messages[parts[-1]] = value


def catalogs(locale):
    messages = {}
    for row in csv.DictReader((ROOT / "traducciones/claves.csv").open()):
        if row["estado"] in ("ok", "fragmento"):
            put(messages, row["clave"], row[f"{locale}_curado"])
    for row in csv.DictReader((ROOT / "traducciones/claves-extra.csv").open()):
        put(messages, row["clave"], row[locale])
    messages.pop("emails", None)
    # El texto legal vive en `frontend/content/legal/*.md` (revisión jurídica).
    messages.pop("legal", None)
    return {"common.json": messages}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    artifacts = {
        ROOT / "frontend/i18n/enums.json": json.loads(
            (ROOT / "contracts/enums.json").read_text()
        )
    }
    for locale in ("en", "es"):
        artifacts.update(
            {
                ROOT / "frontend/messages" / locale / name: messages
                for name, messages in catalogs(locale).items()
            }
        )
    for path, messages in artifacts.items():
        if args.check:
            if json.loads(path.read_text()) != messages:
                raise SystemExit(f"Catálogo desactualizado: {path.relative_to(ROOT)}")
        else:
            path.write_text(json.dumps(messages, ensure_ascii=False, indent=2) + "\n")
