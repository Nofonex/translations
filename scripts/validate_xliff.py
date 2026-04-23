"""
validate_xliff.py
Controleert XLIFF- en SDL XLIFF-bestanden in de repo op ontbrekende vertalingen.
Gebruik: python validate_xliff.py <projectnaam>
         python validate_xliff.py  (controleert alle projecten)
"""

import os
import sys
import base64
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

REPO = "Nofonex/translations"
BASE_URL = f"https://api.github.com/repos/{REPO}/contents"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
SKIP = {"scripts", "translation-termbase-en-nl"}

# XML namespaces
NS_XLIFF = "urn:oasis:names:tc:xliff:document:1.2"
NS_SDL   = "http://sdl.com/FileTypes/SdlXliff/1.0"

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
    return [
        f for f in resp.json()
        if f["name"].endswith((".xlf", ".xliff", ".sdlxliff"))
    ]


def get_mrk_text(element):
    """Haal tekst op uit <mrk mtype='seg'> of direct uit element."""
    if element is None:
        return ""
    parts = []
    for mrk in element.findall(f"{{{NS_XLIFF}}}mrk") + element.findall("mrk"):
        if mrk.get("mtype") == "seg" and mrk.text:
            parts.append(mrk.text.strip())
    if parts:
        return " ".join(parts)
    return (element.text or "").strip()


def is_origin_source(trans_unit, seg_id):
    """Controleer of een segment origin='source' heeft (= niet vertaald in SDL)."""
    for seg in trans_unit.findall(f".//{{{NS_SDL}}}seg"):
        if seg.get("id") == str(seg_id) and seg.get("origin") == "source":
            return True
    return False


def validate_xliff(content, filename):
    issues = []
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        return [f"XML-fout: {e}"]

    units = (
        root.findall(f".//{{{NS_XLIFF}}}trans-unit")
        or root.findall(".//trans-unit")
    )

    for unit in units:
        uid = unit.get("id", "?")

        target = unit.find(f"{{{NS_XLIFF}}}target")
	if target is None:
	    target = unit.find("target")

        target_text = get_mrk_text(target)

        if not target_text:
            issues.append(f"  ⚠️  id='{uid}': doeltekst ontbreekt")
            continue

        # SDL: controleer of segment niet vertaald is (origin=source)
        seg_source = unit.find(f"{{{NS_XLIFF}}}seg-source")
	if seg_source is None:
	    seg_source = unit.find("seg-source")
        )
        if seg_source is not None:
            for mrk in (
                seg_source.findall(f"{{{NS_XLIFF}}}mrk")
                + seg_source.findall("mrk")
            ):
                mid = mrk.get("mid")
                if mid and is_origin_source(unit, mid):
                    issues.append(f"  ⚠️  id='{uid}': niet vertaald (origin=source)")
                    break

    return issues


def check_project(project_name):
    print(f"\n📁 Project: {project_name}")
    translated_path = f"{project_name}/files/translated"
    resp = requests.get(f"{BASE_URL}/{translated_path}", headers=headers)

    if resp.status_code != 200:
        print("   Geen 'translated' map gevonden.")
        return

    lang_dirs = [d for d in resp.json() if d["type"] == "dir"]
    if not lang_dirs:
        print("   Geen taalmappen gevonden in 'translated'.")
        return

    for lang_dir in lang_dirs:
        lang = lang_dir["name"]
        files = list_xliff_files(f"{translated_path}/{lang}")
        if not files:
            print(f"   [{lang}] Geen XLIFF-bestanden gevonden.")
            continue
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
            if i["type"] == "dir"
            and not i["name"].startswith((".", "_"))
            and i["name"] not in SKIP
        ]
        for p in projects:
            check_project(p)
