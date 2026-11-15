#!/usr/bin/env python3
"""
Legt Testprodukte (ein Produkt pro Displayausführung) mit den Varianten
Oberfläche (Klar/Matt) × Lieferumfang (Einzelfolie/Montage-Set) an, veröffentlicht sie
im Onlineshop und verknüpft sie mit den Displayausführungen:
  - display_ausfuehrung.produkt          → Produkt
  - Produkt custom.kompatible_displays   → [Displayausführung]

Voraussetzungen (einmalig):
    shopify store auth --store <shop>.myshopify.com --scopes \
        read_metaobject_definitions,write_metaobject_definitions,read_metaobjects,write_metaobjects,\
        read_products,write_products,read_themes,write_themes,read_publications,write_publications,read_locales

Aufruf:
    python3 scripts/testprodukte_setup.py <shop>.myshopify.com

Idempotent: Produkte werden per Handle über productSet angelegt bzw. aktualisiert.
Alle Produkte sind als TESTPRODUKT gekennzeichnet (Titel-Tag, Beschreibung, Tag).
"""
import json
import subprocess
import sys

if len(sys.argv) < 2 or not sys.argv[1].endswith(".myshopify.com"):
    sys.exit("Aufruf: python3 testprodukte_setup.py <shop>.myshopify.com")

STORE = sys.argv[1]
# Name des Kanals hängt von der Admin-Sprache ab
ONLINE_STORE_PUBLICATIONS = ("Onlineshop", "Online Store")


# --------------------------------------------------------------------------- #
# GraphQL über die Shopify CLI
# --------------------------------------------------------------------------- #
def gql(query, variables=None, mutation=False):
    cmd = ["shopify", "store", "execute", "--store", STORE, "--json", "--no-input", "--query", query]
    if variables is not None:
        cmd += ["--variables", json.dumps(variables)]
    if mutation:
        cmd.append("--allow-mutations")
    r = subprocess.run(cmd, capture_output=True, text=True)
    out = r.stdout
    start = out.find("{")
    data = json.loads(out[start:]) if start != -1 else None
    if r.returncode != 0 or data is None or data.get("errors") or "error" in data:
        print(out)
        print(r.stderr, file=sys.stderr)
        sys.exit("Fehler beim Aufruf der Shopify CLI (siehe oben).")
    return data.get("data", data)


def check_user_errors(payload, was):
    if payload is None:
        sys.exit(f"Fehler bei {was}: leere Antwort (fehlende Berechtigung/Scope?)")
    errs = payload.get("userErrors") or []
    if errs:
        sys.exit(f"Fehler bei {was}: {json.dumps(errs, indent=2, ensure_ascii=False)}")


# --------------------------------------------------------------------------- #
# Testprodukte – Preise sind Platzhalter für den Prototyp (EUR inkl. MwSt.)
# --------------------------------------------------------------------------- #
# Preise: (Klar/Einzelfolie, Matt/Einzelfolie, Klar/Montage-Set, Matt/Montage-Set)
PRODUKTE = [
    {
        "display": "vw-golf-8-10-navi-discover-pro",
        "handle": "displayschutzfolie-vw-golf-8-10-navi-discover-pro",
        "title": 'Displayschutzfolie VW Golf 8 – 10" Navi Discover Pro',
        "sku": "DF-VWG8-NDP10",
        "tags": ["TESTPRODUKT", "VW", "Golf 8"],
        "preise": ("14.90", "16.90", "24.90", "26.90"),
    },
    {
        "display": "tesla-model-3-highland-15-4-zentraldisplay",
        "handle": "displayschutzfolie-tesla-model-3-highland-15-4-zentraldisplay",
        "title": 'Displayschutzfolie Tesla Model 3 Highland – 15,4" Zentraldisplay',
        "sku": "DF-TM3H-ZD154",
        "tags": ["TESTPRODUKT", "Tesla", "Model 3 Highland"],
        "preise": ("19.90", "21.90", "29.90", "31.90"),
    },
]

OBERFLAECHEN = [("Klar", "KL"), ("Matt", "MT")]
UMFAENGE = [("Einzelfolie", "EF", 0.05), ("Montage-Set", "SET", 0.15)]  # Gewicht in kg

BESCHREIBUNG = """<p><strong>TESTPRODUKT – Angaben, Preise und Passform sind nicht geprüft.</strong></p>
<p>Passgenaue Displayschutzfolie für {display}.</p>
<ul>
<li><strong>Klar:</strong> brillante Darstellung, nahezu unsichtbar</li>
<li><strong>Matt:</strong> reduziert Spiegelungen und Fingerabdrücke</li>
<li><strong>Montage-Set:</strong> Folie plus Reinigungstuch, Staubentferner und Rakel</li>
</ul>"""


Q_DISPLAY = """
query($handle: MetaobjectHandleInput!) {
  metaobjectByHandle(handle: $handle) { id displayName }
}
"""

M_PRODUCT_SET = """
mutation($identifier: ProductSetIdentifiers, $input: ProductSetInput!) {
  productSet(identifier: $identifier, input: $input, synchronous: true) {
    product { id handle title variants(first: 10) { nodes { sku price } } }
    userErrors { field message code }
  }
}
"""

Q_PUBLICATIONS = """
query { publications(first: 20) { nodes { id name } } }
"""

M_PUBLISH = """
mutation($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) {
    userErrors { field message }
  }
}
"""

M_DISPLAY_UPSERT = """
mutation($handle: MetaobjectHandleInput!, $metaobject: MetaobjectUpsertInput!) {
  metaobjectUpsert(handle: $handle, metaobject: $metaobject) {
    metaobject { handle }
    userErrors { field message code }
  }
}
"""


def varianten(p):
    out = []
    preise = iter(p["preise"])
    for umfang, umfang_code, gewicht in UMFAENGE:
        for oberflaeche, ob_code in OBERFLAECHEN:
            sku = f"{p['sku']}-{ob_code}-{umfang_code}"
            out.append({
                "optionValues": [
                    {"optionName": "Oberfläche", "name": oberflaeche},
                    {"optionName": "Lieferumfang", "name": umfang},
                ],
                "price": next(preise),
                "sku": sku,
                "taxable": True,
                "inventoryPolicy": "CONTINUE",
                "inventoryItem": {
                    "sku": sku,
                    "tracked": False,  # wird auf Bestellung gefertigt
                    "requiresShipping": True,
                    "measurement": {"weight": {"value": gewicht, "unit": "KILOGRAMS"}},
                },
            })
    return out


def online_store_publication_id():
    pubs = gql(Q_PUBLICATIONS)["publications"]["nodes"]
    for pub in pubs:
        if pub["name"] in ONLINE_STORE_PUBLICATIONS:
            return pub["id"]
    sys.exit(f"Vertriebskanal {ONLINE_STORE_PUBLICATIONS} nicht gefunden: {[p['name'] for p in pubs]}")


def main():
    print(f"Shop: {STORE}\n")
    publication_id = online_store_publication_id()

    for p in PRODUKTE:
        display = gql(Q_DISPLAY, {"handle": {"type": "display_ausfuehrung", "handle": p["display"]}})[
            "metaobjectByHandle"
        ]
        if not display:
            sys.exit(f"Displayausführung {p['display']} nicht gefunden – erst fahrzeugdaten_setup.py ausführen.")

        payload = gql(M_PRODUCT_SET, {
            "identifier": {"handle": p["handle"]},
            "input": {
                "handle": p["handle"],
                "title": p["title"],
                "descriptionHtml": BESCHREIBUNG.format(display=display["displayName"]),
                "vendor": "Displayfolien",
                "productType": "Displayschutzfolie",
                "tags": p["tags"],
                "status": "ACTIVE",
                "productOptions": [
                    {"name": "Oberfläche", "position": 1, "values": [{"name": n} for n, _ in OBERFLAECHEN]},
                    {"name": "Lieferumfang", "position": 2, "values": [{"name": n} for n, _, _ in UMFAENGE]},
                ],
                "variants": varianten(p),
                "metafields": [{
                    "namespace": "custom",
                    "key": "kompatible_displays",
                    "type": "list.metaobject_reference",
                    "value": json.dumps([display["id"]]),
                }],
            },
        }, mutation=True)["productSet"]
        check_user_errors(payload, f"Produkt {p['handle']}")
        product = payload["product"]
        print(f"  ~ Produkt {product['handle']}")
        for v in product["variants"]["nodes"]:
            print(f"      {v['sku']:<28} {v['price']} EUR")

        pub = gql(M_PUBLISH, {"id": product["id"], "input": [{"publicationId": publication_id}]},
                  mutation=True)["publishablePublish"]
        check_user_errors(pub, f"Veröffentlichung {p['handle']}")
        print("      veröffentlicht im Onlineshop")

        link = gql(M_DISPLAY_UPSERT, {
            "handle": {"type": "display_ausfuehrung", "handle": p["display"]},
            "metaobject": {"fields": [{"key": "produkt", "value": product["id"]}]},
        }, mutation=True)["metaobjectUpsert"]
        check_user_errors(link, f"Verknüpfung {p['display']}")
        print(f"      verknüpft mit display_ausfuehrung/{p['display']}")

    print("\nFertig.")


if __name__ == "__main__":
    main()
