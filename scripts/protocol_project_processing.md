# Protocol: Vertaalproject verwerken

## Doel
Lege segmenten vertalen en twee versies opslaan, zonder reeds vertaalde segmenten aan te raken.

## Mappenstructuur
```
{project}/
  files/
    source/          ← bronbestanden (.xlf)
    translated/
      nl/            ← doelbestanden
```

## Stappen

### 1. Analyse
Controleer welke segmenten leeg zijn in de bronbestanden (`.xlf`) en welke al een vertaling hebben.
- **Al vertaald** → overslaan
- **Leeg in XLF, wel aanwezig in SDL** → overnemen uit SDL
- **Leeg in beide** → handmatig vertalen

### 2. SDL-bestanden bijwerken
Vul lege segmenten in de SDL-bestanden (`.sdlxliff`) in met de ontbrekende Nederlandse vertalingen.
- Inline SDL-codes (`<x/>`, `<g>`) meenemen in de vertaling
- Zelfsluitende `<mrk ... />` vervangen door `<mrk ...>vertaling</mrk>`

### 3. XLF-versie aanmaken
Maak per bronbestand een volledig vertaald XLF-bestand aan in `translated/nl/`.
- Dezelfde bestandsnaam als het bronbestand
- Zelfde structuur, titel, ID's en attributen als het bronbestand
- Lege targets invullen vanuit het SDL-bestand:
  - Matching op segment-ID (`mid`) of brontekst
  - SDL-codes omzetten naar XLF-codes: `<x id="N"/>` → `<ph id="fN">…</ph>`, `<g id="N">…</g>` → `<bpt id="gN">…</bpt>…<ept id="gN">…</ept>`

### 4. Resultaat
| Versie | Bestandstype | Locatie |
|--------|-------------|---------|
| SDL (huidig formaat) | `.sdlxliff` | `translated/nl/` |
| XLF | `.xlf` | `translated/nl/` |

> **Let op:** geen hernoeming van bestaande bestanden nodig.

## Script
`scripts/process_project.py` — uitvoeren vanuit de root van de repo:
```bash
python3 scripts/process_project.py
```
