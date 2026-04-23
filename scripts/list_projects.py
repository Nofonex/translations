"""
list_projects.py
Haalt alle projecten op uit de Nofonex translations repo via de GitHub API.
Gebruik: python list_projects.py
"""

import requests
import json

REPO = "Nofonex/translations"
BASE_URL = f"https://api.github.com/repos/{REPO}/contents"
# Optioneel: zet je GitHub token hier voor hogere rate limits
import os
from dotenv import load_dotenv
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

headers = {}
if GITHUB_TOKEN:
    headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"


def get_projects():
    response = requests.get(BASE_URL, headers=headers)
    response.raise_for_status()
    items = response.json()

    projects = []
    for item in items:
        # Sla systeemmappen en bestanden over
        SKIP = {"scripts", "translation-termbase-en-nl"}
if item["type"] != "dir" or item["name"].startswith((".", "_")) or item["name"] in SKIP:
            continue

        project_info = {"name": item["name"], "url": item["html_url"]}

        # Probeer project.json te laden
        meta_url = f"{BASE_URL}/{item['name']}/project.json"
        meta_resp = requests.get(meta_url, headers=headers)
        if meta_resp.status_code == 200:
            import base64
            content = base64.b64decode(meta_resp.json()["content"]).decode("utf-8")
            project_info["meta"] = json.loads(content)

        projects.append(project_info)

    return projects


if __name__ == "__main__":
    projects = get_projects()
    if not projects:
        print("Geen projecten gevonden.")
    else:
        for p in projects:
            print(f"\n📁 {p['name']}")
            if "meta" in p:
                m = p["meta"]
                print(f"   Omschrijving : {m.get('description', '-')}")
                print(f"   Brontaal     : {m.get('source_language', '-')}")
                print(f"   Doeltalen    : {', '.join(m.get('target_languages', []))}")
                print(f"   Status       : {m.get('status', '-')}")
