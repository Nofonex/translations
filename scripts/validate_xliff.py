"""
validate_xliff.py
Controleert XLIFF-bestanden in de repo op ontbrekende vertalingen.
Gebruik: python validate_xliff.py <projectnaam>
         python validate_xliff.py  (controleert alle projecten)
"""

import sys
import base64
import requests
import xml.etree.ElementTree as ET

REPO = "Nofonex/translations"
BASE_URL = f"https://api.github.com/repos/{REPO}/contents"
GITHUB_TOKEN = ""

NS = {"xliff": "urn:oasis:names:tc:xliff:document:1.2"}

headers = {}
if GITHUB_TOKEN:
    headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"


def fetch_file(path):
    resp = requests.get(f"{BASE_URL}/{path}", headers=headers)
    resp.raise_for_status()
    data = resp.json()
    return base64.b64decode(data["content"]).decode("utf-8")


def list_xliff_files(folder_path):
    resp = requests.get(f"{BASE_URL}/{folder_path}", headers=headers)
    if resp.status_code != 200:
        return []
    return [f for f in resp.json() if f["name"].endswith((".xlf", ".xliff"))]


def validate_xliff(content, filename):
    issues = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        return [f"XML-fout: {e}"]

    units = root.findall(".//xliff:trans-unit", NS) or root.findall(".//trans-unit")
    for unit in units:
        uid = unit.get("id", "?")
        target = unit.find("xliff:target", NS) or unit.find("target")
        if target is None or not (target.text or "").strip():
            issues.append(f"  ⚠️  trans-unit id='{uid}': doeltekst ontbreekt")

    return issues


def check_project(project_name):
    print(f"\n📁 Project: {project_name}")
    translated_path = f"{project_name}/files/translated"
    resp = requests.get(f"{BASE_URL}/{translated_path}", headers=headers)

    if resp.status_code != 200:
        print("   Geen 'translated' map gevonden.")
        return

    lang_dirs = [d for d in resp.json() if d["type"] == "dir"]
    for lang_dir in lang_dirs:
        lang = lang_dir["name"]
        files = list_xliff_files(f"{translated_path}/{lang}")
        for f in files:
            content = fetch_file(f"{translated_path}/{lang}/{f['name']}")
            issues = validate_xliff(content, f["name"])
            if issues:
                print(f"   [{lang}] {f['name']}: {len(issues)} probleem/problemen")
                for issue in issues:
                    print(issue)
            else:
                print(f"   [{lang}] {f['name']}: ✅ OK")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_project(sys.argv[1])
    else:
        resp = requests.get(BASE_URL, headers=headers)
        resp.raise_for_status()
        projects = [
            i["name"] for i in resp.json()
            if i["type"] == "dir" and not i["name"].startswith((".", "_"))
        ]
        for p in projects:
            check_project(p)
