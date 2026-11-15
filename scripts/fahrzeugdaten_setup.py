#!/usr/bin/env python3
"""
Legt das Fahrzeug-Datenmodell (Metaobjects + Produkt-Metafeld) im Shopify-Shop an
und befüllt es optional mit Beispieldaten.

Voraussetzungen (einmalig, im WSL-Terminal):
    shopify store auth --store <shop>.myshopify.com \
        --scopes read_metaobject_definitions,write_metaobject_definitions,read_metaobjects,write_metaobjects,read_products,write_products

Aufruf:
    python3 scripts/fahrzeugdaten_setup.py <shop>.myshopify.com              # Definitionen + Beispieldaten
    python3 scripts/fahrzeugdaten_setup.py <shop>.myshopify.com --ohne-testdaten

Das Skript ist idempotent: Bestehende Definitionen werden übersprungen,
Einträge werden per Handle aktualisiert statt doppelt angelegt.
"""
import json
import re
import subprocess
import sys

if len(sys.argv) < 2 or not sys.argv[1].endswith(".myshopify.com"):
    sys.exit("Aufruf: python3 fahrzeugdaten_setup.py <shop>.myshopify.com [--ohne-testdaten]")

STORE = sys.argv[1]
MIT_TESTDATEN = "--ohne-testdaten" not in sys.argv


# --------------------------------------------------------------------------- #
# GraphQL über die Shopify CLI
# --------------------------------------------------------------------------- #
def gql(query, variables=None, mutation=False):
    cmd = ["shopify", "store", "execute", "--store", STORE, "--json", "--query", query]
    if variables is not None:
        cmd += ["--variables", json.dumps(variables)]
    if mutation:
        cmd.append("--allow-mutations")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr, file=sys.stderr)
        sys.exit("Fehler beim Aufruf der Shopify CLI (siehe oben).")
    out = r.stdout
    start = out.find("{")
    if start == -1:
        sys.exit(f"Unerwartete Ausgabe der CLI:\n{out}")
    data = json.loads(out[start:])
    if "errors" in data and data["errors"]:
        sys.exit(f"GraphQL-Fehler: {json.dumps(data['errors'], indent=2, ensure_ascii=False)}")
    return data.get("data", data)


def check_user_errors(payload, was):
    if payload is None:
        sys.exit(f"Fehler bei {was}: leere Antwort (fehlende Berechtigung/Scope?)")
    errs = payload.get("userErrors") or []
    if errs:
        sys.exit(f"Fehler bei {was}: {json.dumps(errs, indent=2, ensure_ascii=False)}")


# --------------------------------------------------------------------------- #
# 1) Metaobject-Definitionen
# --------------------------------------------------------------------------- #
# (key, Name, Typ, Pflicht, Referenz-Ziel bzw. Validierung)
DEFINITIONEN = [
    ("fahrzeug_marke", "Fahrzeug: Marke", [
        ("name", "Name", "single_line_text_field", True, None),
        ("logo", "Logo", "file_reference", False, "image"),
    ]),
    ("fahrzeug_modell", "Fahrzeug: Modell", [
        ("name", "Name", "single_line_text_field", True, None),
        ("marke", "Marke", "metaobject_reference", True, "fahrzeug_marke"),
    ]),
    ("fahrzeug_baureihe", "Fahrzeug: Baureihe", [
        ("name", "Name", "single_line_text_field", True, None),
        ("modell", "Modell", "metaobject_reference", True, "fahrzeug_modell"),
        ("baujahr_von", "Baujahr von", "number_integer", True, None),
        ("baujahr_bis", "Baujahr bis (leer = bis heute)", "number_integer", False, None),
    ]),
    ("display_ausfuehrung", "Fahrzeug: Displayausführung", [
        ("name", "Name", "single_line_text_field", True, None),
        ("baureihe", "Baureihe", "metaobject_reference", True, "fahrzeug_baureihe"),
        ("erkennungshinweis", "So erkennst du dein Display", "multi_line_text_field", False, None),
        ("bild", "Bild", "file_reference", False, "image"),
        ("passform_bestaetigt", "Passform bestätigt", "boolean", False, None),
        ("produkt", "Produkt", "product_reference", False, None),
    ]),
]

Q_DEF_BY_TYPE = """
query($type: String!) { metaobjectDefinitionByType(type: $type) { id } }
"""

M_DEF_CREATE = """
mutation($definition: MetaobjectDefinitionCreateInput!) {
  metaobjectDefinitionCreate(definition: $definition) {
    metaobjectDefinition { id type }
    userErrors { field message code }
  }
}
"""


def ensure_definition(typ, name, felder, def_ids):
    found = gql(Q_DEF_BY_TYPE, {"type": typ})["metaobjectDefinitionByType"]
    if found:
        print(f"  = {typ} existiert bereits")
        return found["id"]

    field_defs = []
    for key, fname, ftype, required, extra in felder:
        fd = {"key": key, "name": fname, "type": ftype, "required": required}
        if ftype == "metaobject_reference":
            fd["validations"] = [{"name": "metaobject_definition_id", "value": def_ids[extra]}]
        elif ftype == "file_reference" and extra == "image":
            fd["validations"] = [{"name": "file_type_options", "value": json.dumps(["Image"])}]
        field_defs.append(fd)

    payload = gql(M_DEF_CREATE, {"definition": {
        "type": typ,
        "name": name,
        "displayNameKey": "name",
        "access": {"storefront": "PUBLIC_READ"},
        "fieldDefinitions": field_defs,
    }}, mutation=True)["metaobjectDefinitionCreate"]
    check_user_errors(payload, f"Definition {typ}")
    print(f"  + {typ} angelegt")
    return payload["metaobjectDefinition"]["id"]


# --------------------------------------------------------------------------- #
# 2) Produkt-Metafeld custom.kompatible_displays
# --------------------------------------------------------------------------- #
Q_MF_DEF = """
query {
  metafieldDefinitions(first: 1, ownerType: PRODUCT, namespace: "custom", key: "kompatible_displays") {
    nodes { id }
  }
}
"""

M_MF_DEF_CREATE = """
mutation($definition: MetafieldDefinitionInput!) {
  metafieldDefinitionCreate(definition: $definition) {
    createdDefinition { id }
    userErrors { field message code }
  }
}
"""


def ensure_produkt_metafeld(display_def_id):
    if gql(Q_MF_DEF)["metafieldDefinitions"]["nodes"]:
        print("  = Produkt-Metafeld custom.kompatible_displays existiert bereits")
        return
    payload = gql(M_MF_DEF_CREATE, {"definition": {
        "name": "Kompatible Displays",
        "namespace": "custom",
        "key": "kompatible_displays",
        "description": "Fahrzeug-Displays, auf die diese Folie passt",
        "type": "list.metaobject_reference",
        "ownerType": "PRODUCT",
        "pin": True,
        "access": {"storefront": "PUBLIC_READ"},
        "validations": [{"name": "metaobject_definition_id", "value": display_def_id}],
    }}, mutation=True)["metafieldDefinitionCreate"]
    check_user_errors(payload, "Produkt-Metafeld")
    print("  + Produkt-Metafeld custom.kompatible_displays angelegt")


# --------------------------------------------------------------------------- #
# 3) Beispieldaten (NICHT geprüft – nur zum Testen der Fahrzeugauswahl)
# --------------------------------------------------------------------------- #
# Marke -> Modell -> [(Baureihe, von, bis, [Displayausführungen])]
TESTDATEN = {
    "VW": {
        "Golf": [
            ("Golf 8", 2019, None, ["10\" Navi Discover Pro", "8,25\" Composition Media"]),
        ],
    },
    "Tesla": {
        "Model 3": [
            ("Model 3 (2017–2023)", 2017, 2023, ["15\" Zentraldisplay"]),
            ("Model 3 Highland", 2023, None, ["15,4\" Zentraldisplay"]),
        ],
    },
    "BMW": {
        "3er": [
            ("3er G20", 2019, 2022, ["10,25\" Zentraldisplay"]),
            ("3er G20 LCI", 2022, None, ["14,9\" Curved Display"]),
        ],
    },
}

M_UPSERT = """
mutation($handle: MetaobjectHandleInput!, $metaobject: MetaobjectUpsertInput!) {
  metaobjectUpsert(handle: $handle, metaobject: $metaobject) {
    metaobject { id handle }
    userErrors { field message code }
  }
}
"""


def slug(*teile):
    s = "-".join(teile).lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"), (",", "-")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def upsert(typ, handle, felder):
    payload = gql(M_UPSERT, {
        "handle": {"type": typ, "handle": handle},
        "metaobject": {"fields": [{"key": k, "value": v} for k, v in felder.items()]},
    }, mutation=True)["metaobjectUpsert"]
    check_user_errors(payload, f"{typ}/{handle}")
    print(f"  ~ {typ}/{handle}")
    return payload["metaobject"]["id"]


def testdaten_anlegen():
    for marke, modelle in TESTDATEN.items():
        marke_id = upsert("fahrzeug_marke", slug(marke), {"name": marke})
        for modell, baureihen in modelle.items():
            modell_id = upsert("fahrzeug_modell", slug(marke, modell),
                               {"name": modell, "marke": marke_id})
            for br_name, von, bis, displays in baureihen:
                br_felder = {"name": br_name, "modell": modell_id, "baujahr_von": str(von)}
                if bis:
                    br_felder["baujahr_bis"] = str(bis)
                br_id = upsert("fahrzeug_baureihe", slug(marke, br_name), br_felder)
                for disp in displays:
                    upsert("display_ausfuehrung", slug(marke, br_name, disp), {
                        "name": disp,
                        "baureihe": br_id,
                        "erkennungshinweis": "BEISPIELDATEN – Passform und Angaben nicht geprüft.",
                        "passform_bestaetigt": "false",  # Beispieldaten: erst nach Bestätigung durch Inhaber auf true
                    })


# --------------------------------------------------------------------------- #
def main():
    print(f"Shop: {STORE}\n\n1) Metaobject-Definitionen")
    def_ids = {}
    for typ, name, felder in DEFINITIONEN:
        def_ids[typ] = ensure_definition(typ, name, felder, def_ids)

    print("\n2) Produkt-Metafeld")
    ensure_produkt_metafeld(def_ids["display_ausfuehrung"])

    if MIT_TESTDATEN:
        print("\n3) Beispieldaten")
        testdaten_anlegen()

    print("\nFertig. Prüfen im Admin unter Inhalte → Metaobjekte "
          "bzw. Einstellungen → Benutzerdefinierte Daten.")


if __name__ == "__main__":
    main()
