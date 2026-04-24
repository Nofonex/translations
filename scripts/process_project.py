#!/usr/bin/env python3
"""
process_project.py
Vult lege doelsegmenten in XLF-bronbestanden vanuit SDL-vertaalbestanden.
Slaat twee versies op: bijgewerkte SDL (.sdlxliff) en XLF-formaat.
"""

import os
import re
import glob
import shutil

PROJECT = 'GienTech_843369_HUAWEI_Digital-Power_20260423_TO202604000845_3L'
BASE    = f'/home/user/translations/{PROJECT}/files'
SRC_DIR = f'{BASE}/source'
NL_DIR  = f'{BASE}/translated/nl'

# ── Hardcoded vertalingen voor SDL-segmenten die leeg zijn in BEIDE bestanden ──

SDL_FIXES = {
    'en-us_topic_0000002523813602.xml.sdlxliff.xlf.sdlxliff': {
        '3': 'Als de laadtoestand de vooraf ingestelde eindlaaddrempelwaarde heeft bereikt (bijv. 90%), stopt het systeem met opladen om overopladen te voorkomen.',
        '4': 'In dat geval wordt het PV-vermogen aan het net geleverd of naar verbruikers gestuurd.',
    },
    'en-us_topic_0000002523813604.xml.sdlxliff.xlf.sdlxliff': {
        '7':  'SOC-limiet (energie)',
        '8':  '<g id="4">Beschermingsmechanisme back-upvermogen-SOC</g>:',
        '10': "Als de batterij-SOC 's nachts lager is dan deze drempelwaarde, voorkomt het systeem dat de batterij ontlaadt.",
        '11': '<g id="7">Einde-ontlaad-SOC</g>:',
        '12': 'Als de batterij-SOC daalt tot de einde-ontlaad-SOC (bijv. 10%), stopt het systeem geforceerd met ontladen om overontlading te voorkomen.',
        '16': '<g id="16"><x id="14" /> uitgeschakeld</g>:',
    },
    'en-us_topic_0000002554728695.xml.sdlxliff.xlf.sdlxliff': {
        '4':  '<g id="7">Intelligent planningsbeleid</g>:',
    },
    'en-us_topic_0000002554733493.xml.sdlxliff.xlf.sdlxliff': {
        '2':  'Beperkingen bedrijfsmodus',
        '6':  '<g id="7"><x id="5" /></g>:',
        '10': 'Status schakelaar',
        '12': 'De <x id="11" /> functie is standaard uitgeschakeld.',
        '13': 'U moet dit handmatig inschakelen om de batterij op te laden bij een lage elektriciteitsprijs.',
        '14': 'Instellingen systeemparameters',
        '16': 'De <x id="12" /> is te laag ingesteld (bijv. 80%).',
        '17': 'Wanneer de drempelwaarde is bereikt, stopt het opladen.',
        '18': 'Reserveer de <x id="13" /> voor piekbelastingafvlakking, waarbij het opladen van tevoren wordt gestopt.',
        '19': 'Vermogenslimiet',
        '23': 'Intelligent planningsbeleid',
    },
    'en-us_topic_0000002554815819.xml.sdlxliff.xlf.sdlxliff': {
        '12': '<g id="3">Type installatie</g>:',
        '13': "Deze functie is alleen van toepassing op residentiële installatiescenario's.",
        '15': '<x id="4" /> netwerk + Huawei-lader<g id="7">, PV&amp;ESS netwerk + Huawei-lader</g>',
        '16': '<g id="10">Gebruikersmachtiging</g>: alleen beschikbaar voor eigenaren.',
        '19': 'De <x id="12" /> functie moet zijn ingeschakeld.',
    },
    'en-us_topic_0000002554853535.xml.sdlxliff.xlf.sdlxliff': {
        '1': "Waarom levert de batterij 's nachts geen stroom?",
        '2': 'Intelligent planningsbeleid (economische optimalisatie)',
    },
    'en-us_topic_0000002554853537.xml.sdlxliff.xlf.sdlxliff': {
        '18': 'Intelligent planningsbeleid',
    },
    'en-us_topic_0000002561403103.xml.sdlxliff.xlf.sdlxliff': {
        '20': 'Steek de laadconnector volledig in de lader en het voertuig.',
    },
    'en-us_topic_0000002567052643.xml.sdlxliff.xlf.sdlxliff': {
        '2': 'Belastingsfluctuatie en afwijking van de voorspelling',
        '3': '<g id="2">Plotselinge belastingspiek</g>:',
        '4': 'Tijdens de ochtend- en avondspitsuren is het thuiselectriciteitsverbruik geconcentreerd (bijv. koken en opladen).',
        '5': 'Als de belasting plotseling boven het voorspelde bereik stijgt, reageert de batterij mogelijk niet.',
        '6': '<g id="5">Voorspellingsalgoritme-fout</g>:',
        '7': 'Het systeem plant energie op basis van historische verbruiksgegevens.',
        '8': "Als het werkelijke verbruikspatroon verandert (bijv. door toevoeging van energieverslindende apparaten), kan de energiereserve van de batterij onvoldoende zijn.",
    },
}


# ── Hulpfuncties ──────────────────────────────────────────────────────────────

def plain(text):
    """Verwijder alle XML-tags en geef puur tekst terug."""
    return re.sub(r'<[^>]+>', '', text).strip()


def get_sdl_segment_map(sdl_content):
    """
    Geeft dict: source_plain_text → (mid, sdl_target_inner_text)
    en ook dict: mid → sdl_target_inner_text
    """
    by_src  = {}
    by_mid  = {}
    for unit in re.findall(r'<trans-unit.*?</trans-unit>', sdl_content, re.DOTALL):
        tgt_m = re.search(r'<target>(.*?)</target>', unit, re.DOTALL)
        if not tgt_m:
            continue

        # mid ophalen – zoek in het hele unit, niet alleen in seg-source
        mid_m = re.search(r'<mrk mtype="seg" mid="(\d+)"', unit)
        mid   = mid_m.group(1) if mid_m else None

        # Brontekst ophalen (mrk kan vooraf gegaan worden door inline-elementen)
        src_mrk_m = re.search(r'<seg-source>.*?<mrk[^>]*>(.*?)</mrk>', unit, re.DOTALL)
        src_plain = plain(src_mrk_m.group(1)) if src_mrk_m else ''

        tgt_inner = tgt_m.group(1)
        mrk_m = re.search(r'<mrk[^>]*>(.*?)</mrk>', tgt_inner, re.DOTALL)
        tgt_text = mrk_m.group(1).strip() if mrk_m else ''

        if tgt_text and src_plain:
            by_src[src_plain] = (mid, tgt_text)
        if mid and tgt_text:
            by_mid[mid] = tgt_text
    return by_src, by_mid


def sdl_to_xlf_inline(sdl_text, xlf_src_str):
    """
    Converteert SDL inline-codes (<x/>, <g>) naar XLF inline-codes (<ph>, <bpt>/<ept>).
    Positie-gebaseerde mapping.
    """
    # Verzamel <ph> elementen uit XLF-bron (op volgorde van voorkomen)
    ph_list  = re.findall(r'<ph id="([^"]+)">(.*?)</ph>', xlf_src_str, re.DOTALL)
    bpt_list = re.findall(r'<bpt id="([^"]+)">(.*?)</bpt>', xlf_src_str, re.DOTALL)
    ept_list = re.findall(r'<ept id="([^"]+)">(.*?)</ept>', xlf_src_str, re.DOTALL)

    result   = sdl_text
    x_idx    = [0]
    g_idx    = [0]

    def repl_x(m):
        i = x_idx[0]; x_idx[0] += 1
        if i < len(ph_list):
            pid, pcont = ph_list[i]
            return f'<ph id="{pid}">{pcont}</ph>'
        return ''  # geen overeenkomst: verwijder placeholder

    def repl_g(m):
        i = g_idx[0]; g_idx[0] += 1
        inner = m.group(1)
        if i < len(bpt_list) and i < len(ept_list):
            bid, bcont = bpt_list[i]
            eid, econt = ept_list[i]
            return f'<bpt id="{bid}">{bcont}</bpt>{inner}<ept id="{eid}">{econt}</ept>'
        return inner  # strip g-tags

    result = re.sub(r'<x id="\d+" ?/>', repl_x, result)
    result = re.sub(r'<g id="\d+">(.*?)</g>', repl_g, result, flags=re.DOTALL)
    return result


# ── Stap 1: Bijwerken van SDL-bestanden ───────────────────────────────────────

def update_sdl_file(sdl_path, fixes):
    """Vul lege SDL-segmenten in met de opgegeven vertalingen."""
    with open(sdl_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    changed = 0

    def patch_unit(m):
        nonlocal changed
        unit = m.group(0)
        mid_m = re.search(r'mid="(\d+)"', unit)
        if not mid_m:
            return unit
        mid = mid_m.group(1)
        if mid not in fixes:
            return unit

        # Controleer of target al gevuld is
        tgt_m = re.search(r'<target>(.*?)</target>', unit, re.DOTALL)
        if tgt_m:
            tgt_inner = tgt_m.group(1)
            tgt_plain = plain(tgt_inner)
            if tgt_plain:
                return unit  # al vertaald, overslaan

            # Vervang lege <mrk .../> door <mrk ...>vertaling</mrk>
            translation = fixes[mid]
            new_tgt_inner = re.sub(
                r'<mrk (mtype="seg" mid="\d+")\s*/?>',
                lambda mm: f'<mrk {mm.group(1)}>{translation}</mrk>',
                tgt_inner,
                count=1
            )
            if new_tgt_inner == tgt_inner and '<mrk' in tgt_inner:
                # Probeer andere vorm
                new_tgt_inner = re.sub(
                    r'<mrk ([^>]+)></mrk>',
                    lambda mm: f'<mrk {mm.group(1)}>{translation}</mrk>',
                    tgt_inner,
                    count=1
                )
            new_unit = unit[:tgt_m.start(1)] + new_tgt_inner + unit[tgt_m.end(1):]
            changed += 1
            return new_unit
        return unit

    result = re.sub(r'<trans-unit.*?</trans-unit>', patch_unit, content, flags=re.DOTALL)

    # Zorg dat BOM niet verdubbeld wordt
    bom = '﻿'
    if result.startswith(bom):
        result = result[len(bom):]

    with open(sdl_path, 'w', encoding='utf-8') as f:
        f.write(result)

    return changed


# ── Stap 2: XLF-versie aanmaken ───────────────────────────────────────────────

def create_xlf_version(xlf_src_path, sdl_path, out_path):
    """
    Maak een XLF-uitvoerbestand gebaseerd op het bronbestand.
    Vult lege targets in vanuit het SDL-vertaalbestand.
    """
    with open(xlf_src_path, 'r', encoding='utf-8') as f:
        xlf_content = f.read()

    if not os.path.exists(sdl_path):
        shutil.copy2(xlf_src_path, out_path)
        return 0

    with open(sdl_path, 'r', encoding='utf-8-sig') as f:
        sdl_content = f.read()

    sdl_by_src, sdl_by_mid = get_sdl_segment_map(sdl_content)
    filled = [0]

    def patch_unit(m):
        unit = m.group(0)

        # Segment-ID in XLF (numeriek)
        uid_m = re.search(r'<trans-unit id="(\d+)"', unit)
        uid   = uid_m.group(1) if uid_m else None

        # Bronnelement
        src_m = re.search(r'<source>(.*?)</source>', unit, re.DOTALL)
        if not src_m:
            return unit
        src_inner = src_m.group(1)
        src_plain = plain(src_inner)

        # Huidig doelelement – zoek zowel self-closing als reguliere vorm
        tgt_self_m = re.search(r'<target([^>]*)/>', unit)
        tgt_full_m = re.search(r'<target([^>]*)>(.*?)</target>', unit, re.DOTALL)

        if tgt_full_m:
            tgt_attrs = tgt_full_m.group(1)
            tgt_inner = tgt_full_m.group(2)
            tgt_plain_txt = plain(tgt_inner)
            tgt_match = tgt_full_m
        elif tgt_self_m:
            tgt_attrs = tgt_self_m.group(1)
            tgt_plain_txt = ''
            tgt_match = tgt_self_m
        else:
            return unit

        if tgt_plain_txt:
            return unit  # Al vertaald – overslaan

        # Zoek vertaling: eerst op mid, dan op brontekst
        sdl_tgt = None
        if uid and uid in sdl_by_mid:
            sdl_tgt = sdl_by_mid[uid]
        elif src_plain and src_plain in sdl_by_src:
            sdl_tgt = sdl_by_src[src_plain][1]

        if not sdl_tgt:
            return unit  # Geen vertaling gevonden

        # Converteer SDL inline-codes naar XLF inline-codes
        xlf_tgt = sdl_to_xlf_inline(sdl_tgt, src_inner)

        # Stel ns:originTarget in
        xlf_tgt_plain = plain(xlf_tgt)
        unit = re.sub(
            r'ns:originTarget=""',
            f'ns:originTarget="{xlf_tgt_plain}"',
            unit, count=1
        )

        new_tgt = f'<target{tgt_attrs}>{xlf_tgt}</target>'
        # Herberekening positie na mogelijke wijziging van ns:originTarget
        if tgt_full_m:
            tgt_match2 = re.search(r'<target([^>]*)>(.*?)</target>', unit, re.DOTALL)
        else:
            tgt_match2 = re.search(r'<target([^>]*)/>', unit)
        if tgt_match2:
            new_unit = unit[:tgt_match2.start()] + new_tgt + unit[tgt_match2.end():]
        else:
            new_unit = unit
        filled[0] += 1
        return new_unit

    result = re.sub(r'<trans-unit.*?</trans-unit>', patch_unit, xlf_content, flags=re.DOTALL)

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(result)

    return filled[0]


# ── Hoofdprogramma ────────────────────────────────────────────────────────────

def main():
    print(f"Project: {PROJECT}")
    print("=" * 60)

    # Stap 1: Bijwerken SDL-bestanden met hardcoded vertalingen
    print("\n[Stap 1] SDL-bestanden bijwerken...")
    sdl_total = 0
    for sdl_fname, fixes in SDL_FIXES.items():
        sdl_path = os.path.join(NL_DIR, sdl_fname)
        if not os.path.exists(sdl_path):
            print(f"  ⚠  Niet gevonden: {sdl_fname}")
            continue
        n = update_sdl_file(sdl_path, fixes)
        sdl_total += n
        print(f"  ✓  {sdl_fname}: {n} segment(en) ingevuld")

    print(f"\n  Totaal SDL-fixes: {sdl_total} segment(en)")

    # Stap 2: XLF-versies aanmaken vanuit bronbestanden + SDL
    print("\n[Stap 2] XLF-versies aanmaken...")
    xlf_total = 0
    for xlf_src in sorted(glob.glob(os.path.join(SRC_DIR, '*.xlf'))):
        fname    = os.path.basename(xlf_src)
        sdl_path = os.path.join(NL_DIR, fname + '.sdlxliff')
        out_path = os.path.join(NL_DIR, fname)

        n = create_xlf_version(xlf_src, sdl_path, out_path)
        xlf_total += n
        status = f"{n} ingevuld" if n else "geen lege segmenten"
        print(f"  ✓  {fname}: {status}")

    print(f"\n  Totaal XLF-segmenten ingevuld: {xlf_total}")

    # Validatie
    print("\n[Validatie] Controleer resterende lege segmenten...")
    for xlf_out in sorted(glob.glob(os.path.join(NL_DIR, '*.xlf'))):
        fname = os.path.basename(xlf_out)
        with open(xlf_out, 'r', encoding='utf-8') as f:
            content = f.read()
        empty_count = len(re.findall(r'<target[^>]*/>|<target[^>]*></target>', content))
        if empty_count:
            print(f"  ⚠  {fname}: nog {empty_count} leeg")
        else:
            print(f"  ✓  {fname}: volledig vertaald")

    print("\nKlaar!")


if __name__ == '__main__':
    main()
