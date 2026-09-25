"""Export a pinned FireRed town-map grid and southern map connections.

Reference tooling only: this neither compiles a ROM nor unlocks travel. The pret
decompilation is a community reconstruction, not an official source publication.
No coastline, global coordinates, or edges are inferred from decorative artwork.
"""
import argparse
import hashlib
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REV = "c75f352304d529f6ba92d4f74b9cf8b5c3810788"
BASE = f"https://raw.githubusercontent.com/pret/pokefirered/{REV}/"
OUT = ROOT / "research/geography/kanto-reference.json"
CACHE = ROOT / ".cache/geography" / REV
LAYOUT = "src/data/region_map/region_map_layout_kanto.h"
MAPS = ["PalletTown", "Route21_North", "Route21_South", "CinnabarIsland",
        "Route20", "SeafoamIslands_1F", "Route19", "FuchsiaCity"]
LABELS = {
    "PALLET_TOWN": "真新镇", "VIRIDIAN_CITY": "常青市", "PEWTER_CITY": "深灰市",
    "CERULEAN_CITY": "华蓝市", "LAVENDER_TOWN": "紫苑镇", "VERMILION_CITY": "枯叶市",
    "CELADON_CITY": "玉虹市", "SAFFRON_CITY": "金黄市", "FUCHSIA_CITY": "浅红市",
    "CINNABAR_ISLAND": "红莲岛", "INDIGO_PLATEAU": "石英高原",
    "SEAFOAM_ISLANDS": "双子岛",
}


def read_source(path, expected):
    cached = CACHE / path
    data = cached.read_bytes() if cached.exists() else urllib.request.urlopen(BASE + path, timeout=30).read()
    sha = hashlib.sha256(data).hexdigest()
    if path in expected and sha != expected[path]:
        raise ValueError(f"Source hash changed: {path}")
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(data)
    return path, data, {"path": path, "url": BASE + path, "sha256": sha}


def parse_layers(text):
    result = {}
    for name in ("MAP", "DUNGEON"):
        part = text.split(f"[LAYER_{name}] =", 1)[1].split("[LAYER_", 1)[0]
        rows = re.findall(r"\{\s*(MAPSEC_[^{}]+)\}", part)
        grid = [re.findall(r"MAPSEC_[A-Z0-9_]+", row) for row in rows]
        if len(grid) != 15 or any(len(row) != 22 for row in grid):
            raise ValueError(f"Unexpected {name} grid shape")
        result[name.lower()] = grid
    return result


def render_svg(layers):
    # This is a literal town-map cell diagram, not a new illustrated geography.
    step, ox, oy = 44, 72, 116
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1112" height="900" viewBox="0 0 1112 900">',
             '<rect width="1112" height="900" fill="#f4f1e8"/>',
             '<g font-family="Microsoft YaHei, sans-serif" fill="#243c46">',
             '<text x="72" y="48" font-size="27" font-weight="bold">关都 · 原作地图坐标核对</text>',
             '<text x="72" y="79" font-size="15">火红 22 × 15 城镇地图格 · 格位直接取自固定版本数据 · 非美术成品</text>']
    for y, row in enumerate(layers["map"]):
        for x, section in enumerate(row):
            color = "#ece8dd" if section == "MAPSEC_NONE" else "#bacdb1"
            parts.append(f'<rect x="{ox+x*step}" y="{oy+y*step}" width="{step-1}" height="{step-1}" fill="{color}"/>')
    for layer, color in (("map", "#35677c"), ("dungeon", "#a36440")):
        groups = {}
        for y, row in enumerate(layers[layer]):
            for x, section in enumerate(row):
                if section != "MAPSEC_NONE":
                    groups.setdefault(section.removeprefix("MAPSEC_"), []).append((x,y))
        for key, cells in groups.items():
            if key not in LABELS:
                continue
            x = ox + (sum(c[0] for c in cells)/len(cells)+.5)*step
            y = oy + (sum(c[1] for c in cells)/len(cells)+.5)*step
            parts.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{color}"/>')
            # Town labels sit above their coordinate; dungeon labels below.
            dy = 27 if layer == "dungeon" else -14
            parts.append(f'<text x="{x}" y="{y+dy}" text-anchor="middle" font-size="16" font-weight="bold">{escape(LABELS[key])}</text>')
    parts.extend(['<text x="72" y="810" font-size="16">浅绿：原作城镇／道路格位　蓝点：城镇　棕点：双子岛洞窟标记</text>',
                  '<text x="72" y="840" font-size="15">留白格不代表海洋；接近的格位不自动构成可通行边。无世界经纬度、无原创遗迹坐标。</text>',
                  '<text x="72" y="867" font-size="13">来源：pret/pokefirered 社区反编译 · c75f352304d529f6ba92d4f74b9cf8b5c3810788</text>',
                  '</g></svg>'])
    return "\n".join(parts)+"\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Verify committed outputs without rewriting them")
    args = parser.parse_args()
    expected = {}
    if OUT.exists():
        expected = {r["path"]: r["sha256"] for r in json.loads(OUT.read_text(encoding="utf-8"))["sources"]}
    paths = [LAYOUT] + [f"data/maps/{m}/map.json" for m in MAPS]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda p: read_source(p, expected), paths))
    sources = {path: data for path, data, _ in results}
    layers = parse_layers(sources[LAYOUT].decode())
    records = []
    for name in MAPS:
        raw = json.loads(sources[f"data/maps/{name}/map.json"])
        records.append({"source_name": name, "id": raw["id"], "region_map_section": raw["region_map_section"],
                        "connections": raw.get("connections") or [], "warp_events": raw.get("warp_events") or []})
    data = {"schema_version": 1, "status": "source_reference_not_playable_maps",
            "source_repository": "https://github.com/pret/pokefirered", "source_commit": REV,
            "evidence_level": "community_decompilation_of_game_data",
            "coordinate_system": "FireRed town-map cells; x east, y south; NOT world coordinates",
            "scope": "Complete Kanto overview grid; only eight southern map metadata records; NOT full traversal graph",
            "sources": [r for _, _, r in results], "layers": layers, "southern_maps": records}
    positions = {key: [(x,y) for y,row in enumerate(layers["map"]) for x,v in enumerate(row) if v == "MAPSEC_"+key] for key in ("PALLET_TOWN", "CINNABAR_ISLAND")}
    assert positions["PALLET_TOWN"][0][0] == positions["CINNABAR_ISLAND"][0][0]
    assert positions["PALLET_TOWN"][0][1] < positions["CINNABAR_ISLAND"][0][1]
    by_name = {m["source_name"]: m for m in records}
    assert any(c["map"] == "MAP_ROUTE21_NORTH" and c["direction"] == "down" for c in by_name["PalletTown"]["connections"])
    assert any(c["map"] == "MAP_ROUTE20" and c["direction"] == "right" for c in by_name["CinnabarIsland"]["connections"])
    outputs = {OUT: json.dumps(data, ensure_ascii=False, indent=2)+"\n",
               ROOT/"research/geography/kanto-grid-reference.svg": render_svg(layers)}
    for path, content in outputs.items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                raise ValueError(f"Reference differs: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print(f"PASS: two 22x15 layers; {len(records)} southern map records; {len(results)} source hashes; {'checked' if args.check else 'exported'}")


if __name__ == "__main__":
    main()
