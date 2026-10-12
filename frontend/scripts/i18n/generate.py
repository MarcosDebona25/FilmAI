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
    messages = {"common": {"brand": "FilmAI"}}
    for row in csv.DictReader(
        (ROOT / "docs/i18n/ot70-catalogo-transitorio.csv").open()
    ):
        put(messages, row["clave"], row["es_actual"] if locale == "es" else row["en"])
    for row in csv.DictReader((ROOT / "docs/i18n/claves.csv").open()):
        if row["estado"] in ("ok", "fragmento"):
            put(messages, row["clave"], row[f"{locale}_curado"])
    for row in csv.DictReader((ROOT / "docs/i18n/copia-propuesta.csv").open()):
        put(messages, row["clave"], row[f"{locale}_propuesto"])
    messages.pop("emails", None)
    # El texto legal vive en `frontend/content/legal/*.md` (revisión jurídica).
    messages.pop("legal", None)
    messages["legacy"]["reset"]["passwordHelp"] = messages["legacy"]["reset"][
        "passwordHelp"
    ].replace("@#$%&!", "@#$%&*!")
    if locale == "es":
        confirmation = messages["legacy"]["confirmation"]
        for key, value in confirmation.items():
            for old, new in [
                ("Confirmando su cuenta", "Confirmando tu cuenta"),
                (
                    "Su cuenta quedó activa. Ya puede",
                    "Tu cuenta quedó activa. Ya podés",
                ),
                ("Puede iniciar", "Podés iniciar"),
                ("Puede pedir", "Podés pedir"),
            ]:
                value = value.replace(old, new)
            confirmation[key] = value
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
