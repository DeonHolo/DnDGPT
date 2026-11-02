"""Offline-first public 2024 references, with explicit source and edition scope.

Source labelling, exact-name preference, verified endpoint filters and inherited
species resolution follow the approach in heffrey78/dnd-mcp (see NOTICE).
The hosted Python service performs these lookups directly, without a Node child
process or another model/tool round trip. Complete official SRD text stays local.
"""
import copy
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

from .engine import fail

ROOT = Path(__file__).resolve().parent.parent / "rules/dnd2024"
SOURCE = "srd-2024"
KINDS = {"classes", "species", "backgrounds", "feats", "weapons", "armor", "spells", "creatures", "items"}


@lru_cache(maxsize=1)
def catalog():
    data = json.loads((ROOT / "open5e-srd-2024.json").read_text(encoding="utf-8"))
    for kind in KINDS:
        if any(row.get("document", {}).get("key") != SOURCE for row in data[kind]):
            raise ValueError("Bundled D&D reference includes an unexpected source")
    return data


@lru_cache(maxsize=1)
def srd():
    return json.loads((ROOT / "srd-5.2.1.json").read_text(encoding="utf-8"))


def parent_key(value):
    return value.get("key") if isinstance(value, dict) else value


def class_features(classes):
    output = []
    for chosen in classes:
        base = next((row for row in catalog()["classes"] if row["name"] == chosen["name"] and not row.get("subclass_of")), None)
        if base is None:
            continue
        sources = [base] + [row for row in catalog()["classes"] if row["name"] == chosen.get("subclass") and parent_key(row.get("subclass_of")) == base["key"]]
        for row in sources:
            for feature in row.get("features", []):
                gained = feature.get("gained_at", [])
                levels = [at["level"] for at in gained if type(at.get("level")) is int]
                if levels and min(levels) > chosen["level"]:
                    continue
                if not levels:
                    continue
                desc = feature.get("desc", "")
                progression = [{"level": at["level"], "name": feature["name"], "description": at["detail"]}
                               for at in gained if at.get("detail") and type(at.get("level")) is int]
                tables = [f for f in row.get("features", []) if f.get("feature_type") == "CLASS_TABLE_DATA" and f["name"] == feature["name"]]
                for table in tables:
                    previous = None
                    for at in sorted(table.get("data_for_class_table", []), key=lambda x: x["level"]):
                        if at["column_value"] != previous:
                            progression.append({"level": at["level"], "name": feature["name"], "description": at["column_value"]})
                            previous = at["column_value"]
                output.append({"id": feature["key"], "name": feature["name"], "description": desc,
                               "summary": desc.split("\n\n")[0][:360], "source": row["name"], "source_key": row["key"],
                               "level_acquired": min(levels), "advancement": [],
                               "level_progression": sorted(progression, key=lambda x: x["level"]) if len(progression) > 1 else []})
    return output


def resolve_species(row):
    result = copy.deepcopy(row)
    parent = parent_key(row.get("subspecies_of"))
    if parent:
        base = next((item for item in catalog()["species"] if item["key"] == parent), None)
        if base:
            result["traits"] = [*copy.deepcopy(base.get("traits", [])), *result.get("traits", [])]
            result["parent_species"] = base["name"]
    return result


def lookup(kind="spells", query="", key=None, filters=None, detail=False, offset=0, limit=12):
    from .adventure_library import SETTING_RESOURCES
    if kind == "setting":
        return copy.deepcopy(SETTING_RESOURCES)
    if type(query) is not str or len(query) > 200 or type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 30:
        fail(422, "invalid_reference_query", "Use a short query, valid offset and limit from 1 to 30")
    if kind == "rules":
        words = [word.casefold() for word in re.findall(r"[\w'-]+", query)]
        pages = srd()["pages"]
        matches = [p for p in pages if not words or all(word in p["text"].casefold() for word in words)]
        if key:
            matches = [p for p in pages if str(p["page"]) == str(key)]
        if detail and matches:
            page = matches[0]
            text = page["text"]
            end = min(len(text), offset + 8000)
            return {"source": "Official SRD 5.2.1", "source_url": srd()["source_url"], "page": page["page"],
                    "pdf_sha256": srd()["pdf_sha256"], "content": text[offset:end],
                    "next_offset": end if end < len(text) else None, "total_characters": len(text)}
        return {"source": "Official SRD 5.2.1", "count": len(matches),
                "results": [{"page": p["page"], "preview": p["text"].strip()[:220]} for p in matches[offset:offset+limit]],
                "next_offset": offset+limit if len(matches) > offset+limit else None}
    if kind not in KINDS:
        fail(422, "invalid_reference_kind", "Choose rules, setting, classes, species, backgrounds, feats, weapons, armor, spells, creatures or items")
    filters = filters or {}
    permitted = {"level", "max_level", "class_name", "min_cr", "max_cr", "type", "environment", "rarity"}
    if type(filters) is not dict or filters.keys() - permitted:
        fail(422, "invalid_reference_filter", "Unknown reference filter; filters never silently broaden a search")
    applicable = {"spells": {"level", "max_level", "class_name"}, "creatures": {"min_cr", "max_cr", "type", "environment"},
                  "items": {"rarity"}, "classes": {"level"}}.get(kind, set())
    if filters.keys() - applicable:
        fail(422, "invalid_reference_filter", "This filter does not apply to the selected content type")
    for field in {"level", "max_level", "min_cr", "max_cr"} & filters.keys():
        if type(filters[field]) not in (int, float) or not 0 <= filters[field] <= 30:
            fail(422, "invalid_reference_filter", "Level and challenge filters must be numbers from 0 to 30")
    needle = query.strip().casefold()
    rows = [copy.deepcopy(row) for row in catalog()[kind] if (not key or row["key"] == key)
            and (not needle or needle in row["name"].casefold())]
    if kind == "spells":
        rows = [r for r in rows if ("level" not in filters or r["level"] == filters["level"])
                and ("max_level" not in filters or r["level"] <= filters["max_level"])
                and ("class_name" not in filters or any(filters["class_name"].casefold() == str(c.get("name", "") if isinstance(c, dict) else c).casefold() for c in r.get("classes", [])))]
    elif kind == "creatures":
        rows = [r for r in rows if ("min_cr" not in filters or r["challenge_rating"] >= filters["min_cr"])
                and ("max_cr" not in filters or r["challenge_rating"] <= filters["max_cr"])
                and ("type" not in filters or filters["type"].casefold() in {str(r.get("type", {}).get(x, "")).casefold() for x in ("name", "key")})
                and ("environment" not in filters or any(filters["environment"].casefold() in str(e).casefold() for e in r.get("environments", [])))]
    elif kind == "items" and "rarity" in filters:
        rows = [r for r in rows if str(filters["rarity"]).casefold() in str(r.get("rarity", "")).casefold()]
    rows.sort(key=lambda row: (row["name"].casefold() != needle, len(row["name"]), row["name"]))
    provenance = copy.deepcopy(catalog()["_provenance"])
    if detail and rows:
        row = resolve_species(rows[0]) if kind == "species" else rows[0]
        if kind == "classes" and "level" in filters:
            row["features"] = [f for f in row.get("features", []) if not f.get("gained_at") or
                               any(g.get("level", 99) <= filters["level"] for g in f["gained_at"])]
        content = json.dumps(row, ensure_ascii=False)
        if offset > len(content):
            fail(422, "invalid_reference_offset", "Offset is outside the reference entry")
        end = min(len(content), offset+12000)
        return {"key": row["key"], "name": row["name"], "content_json": content[offset:end],
                "next_offset": end if end < len(content) else None, "total_characters": len(content), "source": provenance}
    results = [{k: row[k] for k in ("key", "name", "level", "challenge_rating", "caster_type", "subclass_of") if k in row}
               for row in rows[offset:offset+limit]]
    return {"kind": kind, "source": provenance, "count": len(rows), "results": results,
            "next_offset": offset+limit if len(rows) > offset+limit else None}


def rules_source(document):
    path = ROOT / ("hardener.txt" if document == "hardener" else "gm-guide.txt")
    data = path.read_bytes()
    return {"content": data.decode("utf-8"), "source_sha256": hashlib.sha256(data).hexdigest(),
            "base_sha256": srd()["pdf_sha256"], "replacements": []}


def guidance_sections(text):
    headings = list(re.finditer(r"^## ([a-z-]+): (.+)$", text, re.M))
    return {match[1]: {"title": match[2], "start": match.start(),
                       "end": headings[i+1].start() if i+1 < len(headings) else len(text)} for i, match in enumerate(headings)}
