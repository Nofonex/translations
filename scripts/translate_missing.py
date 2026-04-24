"""
translate_missing.py
Vertaalt ontbrekende doelteksten in SDL XLIFF-bestanden via de DeepL tekst-API
en pusht de bijgewerkte bestanden automatisch naar GitHub.

Gebruik: python translate_missing.py <projectnaam>
         python translate_missing.py  (alle projecten)

Vereisten in .env:
  GITHUB_TOKEN=...
  DEEPL_API_KEY=...
"""

import os
import sys
import json
import time
import base64
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

REPO         = "Nofonex/translations"
BASE_URL     = f"https://api.github.com/repos/{REPO}/contents"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
DEEPL_KEY    = os.getenv("DEEPL_API_KEY", "")
DEEPL_TEXT   = "https://api.deepl.com/v2/translate"
SKIP         = {"scripts", "translation-termbase-en-nl"}
EXTENSIONS   = (".xlf", ".xliff", ".sdlxliff")
BATCH_SIZE   = 50  # max segmenten per DeepL-aanroep

NS_XLIFF = "urn:oasis:names:tc:xliff:document:1.2"
NS_SDL   = "http://sdl.com/FileTypes/SdlXliff/1.0"

ET.register_namespace("",    NS_XLIFF)
ET.register_namespace("sdl", NS_SDL)

gh_headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}


# ── GitHub helpers ────────────────────────────────────────────────────────────

def gh_get_file(path):
    resp = requests.get(f"{BASE_URL}/{path}", headers=gh_headers)
    resp.raise_for_status()
    data = resp.json()
    return base64.b64decode(data["content"]), data["sha"]


def gh_put_file(path, content_bytes, sha, message):
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "sha":     sha,
    }
    resp = requests.put(f"{BASE_URL}/{path}", headers=gh_headers, json=payload)
    resp.raise_for_status()


def list_xliff_files(folder_path):
    resp = requests.get(f"{BASE_URL}/{folder_path}", headers=gh_headers)
    if resp.status_code != 200:
        return []
    return [f for f in resp.json() if f["name"].endswith(EXTENSIONS)]


def list_projects():
    resp = requests.get(BASE_URL, headers=gh_headers)
    resp.raise_for_status()
    return [
        i["name"] for i in resp.json()
        if i["type"] == "dir"
        and not i["name"].startswith((".", "_"))
        and i["name"] not in SKIP
    ]


# ── DeepL tekst-API ───────────────────────────────────────────────────────────

def deepl_translate_batch(texts, source_lang, target_lang):
    """Vertaalt een lijst teksten via de DeepL tekst-API."""
    resp = requests.post(
        DEEPL_TEXT,
        headers={"Authorization": f"DeepL-Auth-Key {DEEPL_KEY}"},
        json={
            "text":        texts,
            "source_lang": source_lang.upper().split("-")[0],
            "target_lang": target_lang.upper(),
            "tag_handling": "xml",
            "formality":   "default",
        },
    )
    if resp.status_code != 200:
        raise Exception(f"DeepL fout: {resp.status_code} {resp.text}")
    return [t["text"] for t in resp.json()["translations"]]


# ── XML verwerking ────────────────────────────────────────────────────────────

def get_mrk_text(element):
    """Haal tekst op uit <mrk mtype='seg'> of direct uit element."""
    if element is None:
        return ""
    for mrk in element.findall(f"{{{NS_XLIFF}}}mrk") + element.findall("mrk"):
        if mrk.get("mtype") == "seg" and mrk.text:
            return mrk.text.strip()
    return (element.text or "").strip()


def set_mrk_text(element, text):
    """Zet tekst in <mrk mtype='seg'> of direct in element."""
    mrks = element.findall(f"{{{NS_XLIFF}}}mrk") + element.findall("mrk")
    if mrks:
        for mrk in mrks:
            if mrk.get("mtype") == "seg":
                mrk.text = text
    else:
        element.text = text


def find_missing_targets(root):
    """
    Geeft lijst van (trans_unit_element, target_element) terug
    waarbij de doeltekst ontbreekt.
    """
    missing = []
    units = (
        root.findall(f".//{{{NS_XLIFF}}}trans-unit")
        or root.findall(".//trans-unit")
    )
    for unit in units:
        target = unit.find(f"{{{NS_XLIFF}}}target")
        if target is None:
            target = unit.find("target")
        if not get_mrk_text(target):
            missing.append((unit, target))
    return missing


def translate_file(content_bytes, source_lang, target_lang):
    """
    Verwerkt één XLIFF-bestand: vertaalt ontbrekende targets en geeft
    de bijgewerkte XML terug als bytes. Geeft None als er niets te doen was.
    """
    xml_str = content_bytes.decode("utf-8")
    # Bewaar BOM als aanwezig
    bom = "\ufeff" if xml_str.startswith("\ufeff") else ""
    if bom:
        xml_str = xml_str[1:]

    root = ET.fromstring(xml_str)
    missing = find_missing_targets(root)

    if not missing:
        return None  # niets te doen

    # Haal bronsegmenten op
    sources = []
    for unit, target in missing:
        src_el = unit.find(f"{{{NS_XLIFF}}}source")
        if src_el is None:
            src_el = unit.find("source")
        sources.append(get_mrk_text(src_el) or "")

    # Vertaal in batches
    translations = []
    for i in range(0, len(sources), BATCH_SIZE):
        batch = sources[i:i + BATCH_SIZE]
        translations.extend(deepl_translate_batch(batch, source_lang, target_lang))
        if i + BATCH_SIZE < len(sources):
            time.sleep(1)

    # Schrijf vertalingen terug
    for (unit, target), translation in zip(missing, translations):
        if target is None:
            # Maak nieuw target-element aan
            target = ET.SubElement(unit, f"{{{NS_XLIFF}}}target")
        set_mrk_text(target, translation)

    # Serialiseer terug naar bytes
    ET.indent(root, space="")
    updated = ET.tostring(root, encoding="unicode", xml_declaration=False)
    header = '<?xml version="1.0" encoding="utf-8"?>'
    result = bom + header + updated
    return result.encode("utf-8")


# ── Hoofdlogica ───────────────────────────────────────────────────────────────

def process_project(project_name):
    print(f"\n📁 Project: {project_name}")
    translated_path = f"{project_name}/files/translated"

    resp = requests.get(f"{BASE_URL}/{translated_path}", headers=gh_headers)
    if resp.status_code != 200:
        print("   Geen 'translated' map gevonden.")
        return

    lang_dirs = [d for d in resp.json() if d["type"] == "dir"]
    if not lang_dirs:
        print("   Geen taalmappen gevonden.")
        return

    source_lang = "EN"
    meta_resp = requests.get(f"{BASE_URL}/{project_name}/project.json", headers=gh_headers)
    if meta_resp.status_code == 200:
        meta = json.loads(base64.b64decode(meta_resp.json()["content"]).decode("utf-8"))
        source_lang = meta.get("source_language", "en").upper()

    for lang_dir in lang_dirs:
        target_lang = lang_dir["name"].upper()
        files = list_xliff_files(f"{translated_path}/{lang_dir['name']}")

        if not files:
            print(f"   [{target_lang}] Geen bestanden gevonden.")
            continue

        for f in files:
            file_path = f"{translated_path}/{lang_dir['name']}/{f['name']}"
            print(f"   [{target_lang}] {f['name']} — verwerken...", end=" ", flush=True)

            try:
                content_bytes, sha = gh_get_file(file_path)
                updated = translate_file(content_bytes, source_lang, target_lang)

                if updated is None:
                    print("⏭  niets te vertalen")
                    continue

                gh_put_file(
                    file_path,
                    updated,
                    sha,
                    f"Vertaling: {f['name']} ({target_lang})",
                )
                print("✅ vertaald en gepusht")
                time.sleep(2)

            except Exception as e:
                print(f"❌ fout: {e}")


if __name__ == "__main__":
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN ontbreekt in .env")
        sys.exit(1)
    if not DEEPL_KEY:
        print("❌ DEEPL_API_KEY ontbreekt in .env")
        sys.exit(1)

    if len(sys.argv) > 1:
        process_project(sys.argv[1])
    else:
        for project in list_projects():
            process_project(project)
