# Nofonex – Translations Repository

Central opslag voor alle vertaalbestanden, georganiseerd per project.

## Mapstructuur

```
translations/
├── README.md
├── _template/               ← Kopieer dit voor elk nieuw project
│   ├── project.json
│   └── files/
│       ├── source/
│       └── translated/
│
├── project-naam/            ← Één map per project
│   ├── project.json         ← Metadata over het project
│   └── files/
│       ├── source/          ← Originele bestanden (brontaal)
│       │   └── *.xlf
│       └── translated/      ← Vertaalde bestanden, per taal
│           ├── nl/
│           ├── de/
│           └── fr/
│
└── scripts/
    ├── list_projects.py     ← Overzicht van alle projecten
    └── validate_xliff.py    ← Validatie van XLIFF-bestanden
```

## Naamgeving

- **Projectmap**: gebruik kebab-case, bijv. `mijn-app-2024`
- **Bestandsnamen**: beschrijvend en consistent, bijv. `ui-labels.xlf`, `emails.xlf`
- **Taalcodes**: gebruik ISO 639-1 (bijv. `nl`, `de`, `fr`, `en`)

## Nieuw project toevoegen

1. Kopieer de map `_template/` naar een nieuwe map met de projectnaam
2. Vul `project.json` in met de projectgegevens
3. Zet de bronbestanden in `files/source/`
4. Zet vertaalde bestanden in `files/translated/{taalcode}/`
5. Commit en push

## Toegang via script (GitHub API)

```python
import requests

REPO = "Nofonex/translations"
BASE = f"https://api.github.com/repos/{REPO}/contents"

# Alle projecten ophalen
projects = requests.get(BASE).json()

# Bestanden van een project ophalen
files = requests.get(f"{BASE}/mijn-project/files/source").json()
```

## Toegang via dit Claude-project

Upload bestanden uit de repo direct in dit Claude-project voor AI-verwerking
(vertalen, reviewen, samenvatten, converteren).
