#!/usr/bin/env python3
"""
build.py

Builds a self-contained dist/ directory from index.html.
  - Resolves box art URLs via the Bulbagarden Archives MediaWiki API
  - Downloads Pokemon artwork from PokeAPI's GitHub
  - Copies index.html to dist/

Usage (run from the folder containing index.html):
    python3 build.py

Re-running is safe — already-downloaded files are skipped.
Requires: python3
"""

import json
import os
import re
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

SCRIPT_DIR  = Path(__file__).parent.resolve()
SRC_HTML    = SCRIPT_DIR / "index.html"
DIST_DIR    = SCRIPT_DIR / "dist"
BOXART_DIR  = DIST_DIR / "img" / "boxart"
POKEMON_DIR = DIST_DIR / "img" / "pokemon"
BULBA_API   = "https://archives.bulbagarden.net/w/api.php"
POKEAPI     = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork"
USER_AGENT  = "Mozilla/5.0 (compatible; build-dist/1.0)"

# ── Box art: (local filename, Bulbagarden archive filename) ───────────────────

BOXART = [
    ("red.png",              "Red_EN_boxart.png"),
    ("blue.png",             "Blue_EN_boxart.png"),
    ("yellow.png",           "Yellow_EN_boxart.png"),
    ("firered.png",          "FireRed_EN_boxart.png"),
    ("leafgreen.png",        "LeafGreen_EN_boxart.png"),
    ("letsgopikachu.png",    "Lets_Go_Pikachu_EN_boxart.png"),
    ("letsgoeevee.png",      "Lets_Go_Eevee_EN_boxart.png"),
    ("gold.png",             "Gold_EN_boxart.png"),
    ("silver.png",           "Silver_EN_boxart.png"),
    ("crystal.png",          "Crystal_EN_boxart.png"),
    ("heartgold.jpg",        "HeartGold_EN_boxart.jpg"),
    ("soulsilver.jpg",       "SoulSilver_EN_boxart.jpg"),
    ("ruby.png",             "Ruby_EN_boxart.png"),
    ("sapphire.png",         "Sapphire_EN_boxart.png"),
    ("emerald.jpg",          "Emerald_EN_boxart.jpg"),
    ("omegaruby.png",        "Omega_Ruby_EN_boxart.png"),
    ("alphasapphire.png",    "Alpha_Sapphire_EN_boxart.png"),
    ("diamond.jpg",          "Diamond_EN_boxart.jpg"),
    ("pearl.jpg",            "Pearl_EN_boxart.jpg"),
    ("platinum.png",         "Platinum_EN_boxart.png"),
    ("brilliantdiamond.png", "Brilliant_Diamond_EN_boxart.png"),
    ("shiningpearl.png",     "Shining_Pearl_EN_boxart.png"),
    ("legendsarceus.png",    "Legends_Arceus_EN_boxart.png"),
    ("black.png",            "Black_EN_boxart.png"),
    ("white.png",            "White_EN_boxart.png"),
    ("black2.png",           "Black_2_EN_boxart.png"),
    ("white2.png",           "White_2_EN_boxart.png"),
    ("x.png",                "X_EN_boxart.png"),
    ("y.png",                "Y_EN_boxart.png"),
    ("sun.png",              "Sun_EN_boxart.png"),
    ("moon.png",             "Moon_EN_boxart.png"),
    ("ultrasun.png",         "Ultra_Sun_EN_boxart.png"),
    ("ultramoon.png",        "Ultra_Moon_EN_boxart.png"),
    ("sword.png",            "Sword_EN_boxart.png"),
    ("shield.png",           "Shield_EN_boxart.png"),
    ("scarlet.png",          "Scarlet_EN_boxart.png"),
    ("violet.png",           "Violet_EN_boxart.png"),
]

# Mapping from alt text in the HTML -> local path under img/boxart/
ALT_TO_LOCAL = {
    "Pokemon Red":       "img/boxart/red.png",
    "Pokemon Blue":      "img/boxart/blue.png",
    "Pokemon Yellow":    "img/boxart/yellow.png",
    "FireRed":           "img/boxart/firered.png",
    "LeafGreen":         "img/boxart/leafgreen.png",
    "Let's Go Pikachu":  "img/boxart/letsgopikachu.png",
    "Let's Go Eevee":    "img/boxart/letsgoeevee.png",
    "Pokemon Gold":      "img/boxart/gold.png",
    "Pokemon Silver":    "img/boxart/silver.png",
    "Pokemon Crystal":   "img/boxart/crystal.png",
    "HeartGold":         "img/boxart/heartgold.png",
    "SoulSilver":        "img/boxart/soulsilver.png",
    "Ruby":              "img/boxart/ruby.png",
    "Sapphire":          "img/boxart/sapphire.png",
    "Emerald":           "img/boxart/emerald.png",
    "Omega Ruby":        "img/boxart/omegaruby.png",
    "Alpha Sapphire":    "img/boxart/alphasapphire.png",
    "Diamond":           "img/boxart/diamond.png",
    "Pearl":             "img/boxart/pearl.png",
    "Platinum":          "img/boxart/platinum.png",
    "Brilliant Diamond": "img/boxart/brilliantdiamond.png",
    "Shining Pearl":     "img/boxart/shiningpearl.png",
    "Legends Arceus":    "img/boxart/legendsarceus.png",
    "Pokemon Black":     "img/boxart/black.png",
    "Pokemon White":     "img/boxart/white.png",
    "Black 2 White 2":   "img/boxart/black2.png",
    "Pokemon X":         "img/boxart/x.png",
    "Pokemon Y":         "img/boxart/y.png",
    "Pokemon Sun":       "img/boxart/sun.png",
    "Pokemon Moon":      "img/boxart/moon.png",
    "Ultra Sun":         "img/boxart/ultrasun.png",
    "Ultra Moon":        "img/boxart/ultramoon.png",
    "Pokemon Sword":     "img/boxart/sword.png",
    "Pokemon Shield":    "img/boxart/shield.png",
    "Pokemon Scarlet":   "img/boxart/scarlet.png",
    "Pokemon Violet":    "img/boxart/violet.png",
}

POKEMON_IDS = [
    1, 4, 7,
    144, 145, 146, 150, 151,
    152, 155, 158,
    243, 244, 245, 249, 250, 251,
    252, 255, 258,
    377, 378, 379, 380, 381, 382, 383, 384, 385, 386,
    387, 390, 393,
    480, 481, 482, 483, 484, 485, 486, 487, 488, 491, 492, 493,
    495, 498, 501,
    638, 639, 640, 641, 642, 643, 644, 645, 646, 647, 648, 649,
    650, 653, 656,
    716, 717, 718, 719, 720, 721,
    722, 725, 728,
    785, 786, 787, 788, 789, 791, 792, 793, 800, 801, 802, 807,
    810, 813, 816,
    888, 889, 890, 891, 893, 894, 895, 896, 897, 898,
    906, 909, 912,
    1001, 1002, 1003, 1004, 1007, 1008, 1009, 1010, 1014, 1017, 1024, 1025,
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp:
        return resp.read()

def download(url: str, dest: Path) -> bool:
    """Download url to dest. Skip if dest already exists and is non-empty. Returns True on success."""
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  [skip]  {dest.name}")
        return True
    print(f"  [get]   {dest.name}")
    for attempt in range(1, 4):
        try:
            data = fetch(url)
            dest.write_bytes(data)
            return True
        except Exception as e:
            if attempt == 3:
                print(f"  [FAIL]  {url}: {e}", file=sys.stderr)
                if dest.exists():
                    dest.unlink()
                return False
            print(f"  [retry] attempt {attempt} failed for {dest.name}: {e}", file=sys.stderr)
    return False

# ── Step 1: Resolve box art URLs via Bulbagarden Archives API ─────────────────

def resolve_boxart_urls() -> dict[str, str]:
    """
    Query the Bulbagarden Archives MediaWiki API for all box art files.
    Returns a dict of {archive_filename_normalised -> direct_url}.
    Handles the API's underscore->space normalisation automatically.
    """
    titles = "|".join(f"File:{archive}" for _, archive in BOXART)
    params = urllib.parse.urlencode({
        "action": "query",
        "titles": titles,
        "prop": "imageinfo",
        "iiprop": "url",
        "format": "json",
    })
    url = f"{BULBA_API}?{params}"
    print(f"  Querying API for {len(BOXART)} files...")
    raw = fetch(url)
    data = json.loads(raw)

    # Build a normalisation map: spaces-version -> underscores-version
    # The API returns titles with spaces; our BOXART list uses underscores.
    # "normalized" entries tell us what got renamed; pages not in that list
    # were already in canonical form (spaces).  We want to map
    # canonical-title -> local-filename.
    norm_map: dict[str, str] = {}  # "File:Foo bar.png" -> "File:Foo_bar.png"
    for entry in data.get("query", {}).get("normalized", []):
        norm_map[entry["to"]] = entry["from"]  # spaces -> underscores original

    # Build canonical_title (with spaces) -> local filename
    canonical_to_local: dict[str, str] = {}
    for local, archive in BOXART:
        # The canonical title the API will use is "File:" + archive with _ -> space
        canonical = "File:" + archive.replace("_", " ")
        canonical_to_local[canonical] = local

    result: dict[str, str] = {}  # local_filename -> direct_url
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        canonical_title = page.get("title", "")
        local = canonical_to_local.get(canonical_title)
        if not local:
            print(f"  [WARN]  No local mapping for '{canonical_title}'", file=sys.stderr)
            continue
        imageinfo = page.get("imageinfo", [])
        if not imageinfo:
            print(f"  [WARN]  No imageinfo for '{canonical_title}'", file=sys.stderr)
            continue
        direct_url = imageinfo[0].get("url", "")
        if not direct_url:
            print(f"  [WARN]  Empty URL for '{canonical_title}'", file=sys.stderr)
            continue
        result[local] = direct_url

    return result

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not SRC_HTML.exists():
        sys.exit(f"ERROR: index.html not found at {SRC_HTML}")

    BOXART_DIR.mkdir(parents=True, exist_ok=True)
    POKEMON_DIR.mkdir(parents=True, exist_ok=True)

    # -- Box art --
    print("\n=== Box Art (Bulbagarden Archives) ===")
    url_map = resolve_boxart_urls()
    for local, _ in BOXART:
        direct_url = url_map.get(local)
        if not direct_url:
            print(f"  [SKIP]  {local} — no URL resolved", file=sys.stderr)
            continue
        download(direct_url, BOXART_DIR / local)

    # -- Pokemon artwork --
    print("\n=== Pokemon Artwork (PokeAPI GitHub) ===")
    for pid in POKEMON_IDS:
        url = f"{POKEAPI}/{pid}.png"
        download(url, POKEMON_DIR / f"{pid}.png")

    # -- Build dist/index.html --
    print("\n=== Building dist/index.html ===")
    html = SRC_HTML.read_text(encoding="utf-8")

    out = DIST_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    print("  HTML rewrite complete.")

    # -- Summary --
    boxart_count  = sum(1 for f in BOXART_DIR.iterdir()  if f.is_file())
    pokemon_count = sum(1 for f in POKEMON_DIR.iterdir() if f.is_file())
    print(f"""
============================================
  Done!
  Box art  : {boxart_count} / {len(BOXART)}
  Pokemon  : {pokemon_count} / {len(POKEMON_IDS)}
  Output   : {DIST_DIR / 'index.html'}

  Serve:  cd dist && python3 -m http.server 8080
============================================""")

if __name__ == "__main__":
    main()
