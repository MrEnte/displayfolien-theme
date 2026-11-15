# Displayfolien-Shop – Shopify-Theme & Store-Setup

## Projekt
Onlineshop für passgenaue Display-Schutzfolien für Auto-Infotainment- und Tachodisplays (Einzelfolie und Montage-Set).
Deutschsprachiger B2C-Shop für Deutschland, Preise in EUR inkl. MwSt. Launch geplant Q1 2027.
Aktuell: Meilenstein 1 – kostenloser, passwortgeschützter Prototyp.

- Store: `displayfolien-shop-b6zvvgf1.myshopify.com` (Shop zur Übertragung / Client-Transfer-Store im Partner-Konto)
- Theme: Shopify **Horizon** (Fork von github.com/Shopify/horizon, Remote `upstream`)
- Kommunikation, Texte im Shop und Commit-Messages: **Deutsch**

## Harte Regeln für diesen Store
Der Store wird später an den Inhaber übertragen und läuft dann im **Basic**-Tarif. Deshalb:
- **Keine** Entwurfs-/Custom-Apps installieren, **keine** Developer-Previews aktivieren.
- **Shopify Payments nicht aktivieren, auch nicht im Testmodus** (blockiert die Übertragung). Testzahlungen nur über das „Bogus Gateway“.
- Keine Funktionen nutzen, die es nur in Advanced/Plus gibt.
- Passwortschutz bleibt aktiv.
- Vor jeder Mutation gegen den Store kurz sagen, was geändert wird. Nichts löschen ohne Rückfrage.
- Passwörter und Tokens nie in Dateien schreiben oder committen.
  Einzige Ausnahme: das Store-Passwort in der lokalen `.env` (`DF_STORE_PW=…`, steht in `.gitignore` und
  `.shopifyignore`) für Screenshots der `theme dev`-Vorschau. Die Datei legt nur der Inhaber/Entwickler selbst an;
  Claude liest den Wert nur zur Laufzeit im Skript und gibt ihn nie aus.

## Werkzeuge
- Theme lokal: `shopify theme dev --store displayfolien-shop-b6zvvgf1.myshopify.com` (Store-Passwort fragt die CLI ab)
- Theme prüfen: `shopify theme check`
- Admin-API: `shopify store auth --store … --scopes …` einmalig (aktuelle Scopes: read/write_metaobject_definitions, read/write_metaobjects, read/write_products, read/write_themes, read/write_publications, read_locales), danach `shopify store execute --store … [--allow-mutations]`
- Vor dem Schreiben von GraphQL/Liquid die Shopify-AI-Toolkit-Skills nutzen (Doku durchsuchen, gegen Schema validieren).
- Hilfsskripte liegen in `scripts/` (stehen in `.shopifyignore`, werden nicht ins Theme hochgeladen).

## Fahrzeug-Datenmodell (Metaobjects)
Alle Definitionen mit Storefront-Zugriff `PUBLIC_READ`, Anzeigename = Feld `name`.

| Typ | Felder |
|---|---|
| `fahrzeug_marke` | name (Text, Pflicht), logo (Bild) |
| `fahrzeug_modell` | name (Pflicht), marke → fahrzeug_marke (Pflicht) |
| `fahrzeug_baureihe` | name (Pflicht), modell → fahrzeug_modell (Pflicht), baujahr_von (Ganzzahl, Pflicht), baujahr_bis (Ganzzahl, leer = bis heute) |
| `display_ausfuehrung` | name (Pflicht), baureihe → fahrzeug_baureihe (Pflicht), erkennungshinweis (mehrzeilig), bild (Bild), passform_bestaetigt (Boolean), produkt (Produkt-Referenz) |

Produkt-Metafeld: `custom.kompatible_displays` = Liste von `display_ausfuehrung` (angeheftet).

Im Shop nur Displayausführungen anzeigen, bei denen `passform_bestaetigt = true` ist.
Passformdaten müssen vom Inhaber bestätigt sein. Einträge mit „BEISPIELDATEN“ im Erkennungshinweis sind ungeprüfte Testdaten.

**Testwerte (nur zum Testen der Fahrzeugauswahl, vor dem Launch auf `false` zurücksetzen):**
Diese BEISPIELDATEN-Displays stehen seit 15.11.2026 vorübergehend auf `passform_bestaetigt = true`:
- `vw-golf-8-10-navi-discover-pro` (VW Golf 8, 10" Navi Discover Pro)
- `tesla-model-3-highland-15-4-zentraldisplay` (Tesla Model 3 Highland, 15,4" Zentraldisplay)

**Testprodukte** (angelegt mit `scripts/testprodukte_setup.py`, Tag `TESTPRODUKT`, Preise sind Platzhalter):
- `displayschutzfolie-vw-golf-8-10-navi-discover-pro` ↔ Display `vw-golf-8-10-navi-discover-pro`
- `displayschutzfolie-tesla-model-3-highland-15-4-zentraldisplay` ↔ Display `tesla-model-3-highland-15-4-zentraldisplay`
- Ein Produkt pro Displayausführung; Optionen „Oberfläche“ (Klar/Matt) × „Lieferumfang“ (Einzelfolie/Montage-Set),
  Lagerbestand nicht geführt (Fertigung auf Bestellung), SKU-Schema `DF-<FAHRZEUG>-<DISPLAY>-<KL|MT>-<EF|SET>`.

## Theme-Konventionen
- Eigene Übersetzungsschlüssel nur in `locales/de(.schema).json` und `locales/en.default(.schema).json`;
  die übrigen Locales bleiben identisch mit upstream. `MatchingTranslations` ist dafür in `.theme-check.yml` deaktiviert.
- Fahrzeugauswahl: `sections/vehicle-selector.liquid`, `snippets/vehicle-selector-data.liquid`, `assets/vehicle-selector.js`.
- Produktseite: Template `templates/product.displayfolie.json` (Produkte mit `templateSuffix = displayfolie`).
  Eigene Blöcke: `blocks/product-compatibility.liquid` (liest `custom.kompatible_displays`, nur bestätigte Passform),
  `blocks/product-delivery-scope.liquid` + `assets/product-delivery-scope.js` (Text je nach Variante Einzelfolie/Set).
  Lieferzeit, Montagehinweise und Video sind Horizon-Standardblöcke (Text, Akkordeon, Video) im Template.
  Weitere Blöcke: `product-fit-badge` (+ `assets/product-fit-badge.js`, zeigt „Passt zu deinem Fahrzeug“ anhand des
  localStorage-Eintrags der Fahrzeugauswahl) und `product-trust` (Vertrauensbox). Unter dem Produkt: Vorteilsleiste,
  Klar vs. Matt, Montage-Schritte, FAQ (Sections `feature-cards`/`faq`).
- Design „technisch & premium“: Palette Navy `#0B1222`, Akzent Elektroblau `#2F6BFF`, Hellblau `#E8EEFF`,
  Überschriften Space Grotesk, Text Inter (in `config/settings_data.json`).
- Eigene Sections: `feature-cards` (Layouts Leiste/Karten/Schritte, Hintergrund Standard/Weiß/Hellblau/Dunkel,
  Icons in `snippets/feature-icon.liquid`) und `faq`. Section-Hintergründe brauchen die Spezifität
  `.shopify-section:not(.header-section) .section-background.<klasse>`, sonst überschreibt Horizon die Farbe.

## Meilenstein 1 – Umfang
1. ✅ Partner-Konto, Client-Transfer-Store
2. ✅ Lokales Setup (CLI, Horizon, GitHub)
3. ✅ Startseite mit Fahrzeugauswahl im Kopfbereich (Marke → Modell → Baujahr → Display)
4. ✅ Fahrzeug-Datenmodell (siehe oben) + 3–5 Beispielmodelle
5. ✅ Fahrzeugauswahl (Eigenbau im Theme)
6. ✅ Produktseiten-Template: Bilder, Kompatibilität, Lieferumfang, Montagehinweise/Video, Lieferzeit
7. ✅ Varianten: matt/klar × Einzelfolie/Set (Testprodukte, siehe oben)
8. Testbestellung (Bogus Gateway), Bestellbestätigung, Übergabe an Produktion per Shopify Flow

## Offene Punkte
- Fahrzeugauswahl auf Kollektionsseiten: `snippets/vehicle-selector-data.liquid` nutzt `{% paginate %}`, das den
  URL-Parameter `?page=` mitliest. Auf Kollektionsseiten ab Seite 2 wäre die Fahrzeugliste deshalb leer/unvollständig.
  Vor dem Einsatz dort Daten anders laden (z. B. per JS über Section Rendering API oder Storefront API).
- Liquid liest max. 250 Displayausführungen (inkl. unbestätigter). Ab ca. 200 Einträgen auf Nachladen per JS umbauen.
- Kontaktseite `/pages/kontakt` im Admin anlegen (wird von der Fahrzeugauswahl verlinkt).
- Testwerte `passform_bestaetigt = true` und Testprodukte (siehe oben) vor dem Launch zurücksetzen bzw. ersetzen.
- Produktseite: Texte für Lieferzeit, Lieferumfang und Montage sind Platzhalter im Template. Die Testprodukte haben je
  6 generierte Platzhalterbilder (gelbes Label „PLATZHALTER“, Variantenbilder Klar/Matt) – vor dem Launch durch echte
  Fotos ersetzen. Montagevideo fehlt noch (Video-Block zeigt bis dahin einen Platzhalter).
- Navigationsmenüs (Main menu/Footer menu: „Home“, „Catalog“, „Contact“, „Search“) und Shop-Name sind noch englisch bzw.
  „displayfolien-shop“ – im Admin unter Inhalte → Menüs bzw. Einstellungen anpassen. Preisformat „€14,90“ → „14,90 €“
  unter Einstellungen → Allgemein → Währungsformat.
- `theme dev` mit `--theme-editor-sync` starten, sonst landen Editor-Änderungen nicht lokal.
