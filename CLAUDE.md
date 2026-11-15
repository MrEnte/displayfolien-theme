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

## Werkzeuge
- Theme lokal: `shopify theme dev --store displayfolien-shop-b6zvvgf1.myshopify.com` (Store-Passwort fragt die CLI ab)
- Theme prüfen: `shopify theme check`
- Admin-API: `shopify store auth --store … --scopes …` einmalig, danach `shopify store execute --store … [--allow-mutations]`
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

## Meilenstein 1 – Umfang
1. ✅ Partner-Konto, Client-Transfer-Store
2. ✅ Lokales Setup (CLI, Horizon, GitHub)
3. Startseite mit Fahrzeugauswahl im Kopfbereich (Marke → Modell → Baujahr → Display)
4. Fahrzeug-Datenmodell (siehe oben) + 3–5 Beispielmodelle
5. Fahrzeugauswahl (Eigenbau im Theme)
6. Produktseiten-Template: Bilder, Kompatibilität, Lieferumfang, Montagehinweise/Video, Lieferzeit
7. Varianten: matt/klar × Einzelfolie/Set
8. Testbestellung (Bogus Gateway), Bestellbestätigung, Übergabe an Produktion per Shopify Flow
