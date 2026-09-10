"""Phase 5 -- generate the report layout from the visual catalogue.

The output shape is copied from a real sample: Power BI Desktop 2.157.1354.0 was
asked to build one visual of each archetype against this model, and the layout it
wrote back was read to learn the role names, the query structure and the type
codes. Nothing here is inferred from documentation.

One cache Desktop maintains itself is deliberately NOT written:

* `query` -- the sample's slicer carries none at all, which shows Desktop
  rebuilds it. `config.singleVisual.prototypeQuery` is the authoritative copy.

`filters` IS written, and stays an empty list for every visual that declares
none. The one visual that declares a filter -- the technology slicer -- follows
a shape read back out of the report Desktop saved, not one invented here.

`dataTransforms` IS written, because it carries the format string and the display
name, and those are ours to control rather than Desktop's to guess.

Run:  python python\\05_build_report.py
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import phase5_contract as K  # noqa: E402
from config import POWERBI  # noqa: E402


def _load(module_name: str, file_name: str):
    spec = importlib.util.spec_from_file_location(
        module_name, Path(__file__).resolve().parent / file_name
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


_measures_module = _load("phase5_measures", "05_measures.py")
_visuals_module = _load("phase5_visuals", "05_visuals.py")

MEASURES = {m["name"]: m for m in _measures_module.MEASURES}
VISUALS = _visuals_module.VISUALS
COLUMNS = _visuals_module.COLUMNS
CANVAS_W = _visuals_module.CANVAS_W
CANVAS_H = _visuals_module.CANVAS_H

REPORT_DIR = POWERBI / f"{K.MODEL_NAME}.Report"
REPORT_PATH = REPORT_DIR / "report.json"

PAGES = _load("phase5_builder", "05_build_pbip.py").PAGES

# Two different type vocabularies live in one file, both read off the sample.
# `selects[].type.underlyingType`: 259 decimal, 260 whole number, 1 text.
# `queryMetadata.Select[].Type`:     1 measure, 3 whole number, 2048 text.
MEASURE_TYPE_CODE = 259
META_TYPE_BY_UNDERLYING = {259: 1, 260: 3, 1: 2048}

# Desktop marks the first projection of the category role active; that is what
# drives drill and the "expand" affordance. Everything else stays inactive.
ACTIVE_ROLE = "Category"


def visual_name(visual_id: str) -> str:
    """Stable 20-hex-character id, the shape Desktop uses for visual names."""
    return hashlib.sha1(f"phase5:visual:{visual_id}".encode()).hexdigest()[:20]


def filter_literal(value: Any) -> str:
    """One filter value in the form the layout stores it.

    Text is single-quoted, which is what the sampled technology filter carries
    for `'generation'`. A whole number takes an `L` suffix instead: quoting an
    int64 column's value compares a number against a string and matches nothing,
    so the slicer would silently show every row again.

    The suffix is the one detail in this function NOT round-tripped through
    Desktop -- the sample only ever covered a text column. Criterion D3 in
    `docs/Phase5_Review.md` confirms it against a rendered slicer, and a country
    slicer still listing 256 entities is the symptom if it turns out wrong.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return f"'{value}'"
    return f"{value}L"


def visual_filters(visual: dict[str, Any]) -> list[dict[str, Any]]:
    """Visual-level categorical filters, in the shape Desktop wrote for them.

    Also a sample rather than a guess: the technology slicer was restricted by
    hand in Desktop and the JSON it saved is what this reproduces, down to
    `howCreated: 1` and the single-entity alias.

    The filter earns its place on the technology slicer. `technology_label`
    resolves seven labels, and three of them -- Renewables total, Biofuel,
    Geothermal -- have no generation metric behind them, so picking one blanks
    the whole page without a word of explanation.

    The country slicer earns one for the same reason on the opposite side:
    `entity_label` resolves all 256 entities, so the list offered World, Africa
    and USSR beside the ten countries any visual can actually draw.
    """
    items = []
    for entity, prop, values in visual.get("filters", ()):
        alias = entity[0].lower()
        items.append(
            {
                "name": hashlib.sha1(
                    f"phase5:filter:{visual['visual_id']}:{entity}.{prop}".encode()
                ).hexdigest()[:20],
                "expression": {
                    "Column": {
                        "Expression": {"SourceRef": {"Entity": entity}},
                        "Property": prop,
                    }
                },
                "filter": {
                    "Version": 2,
                    "From": [{"Name": alias, "Entity": entity, "Type": 0}],
                    "Where": [
                        {
                            "Condition": {
                                "In": {
                                    "Expressions": [
                                        {
                                            "Column": {
                                                "Expression": {
                                                    "SourceRef": {"Source": alias}
                                                },
                                                "Property": prop,
                                            }
                                        }
                                    ],
                                    "Values": [
                                        [{"Literal": {"Value": filter_literal(value)}}]
                                        for value in values
                                    ],
                                }
                            }
                        }
                    ],
                },
                "type": "Categorical",
                "howCreated": 1,
                "objects": {},
            }
        )
    return items


def page_name(page_id: str) -> str:
    return hashlib.sha1(f"phase5:page:{page_id}".encode()).hexdigest()[:20]


def field_spec(query_ref: str) -> dict[str, Any]:
    """Resolve a catalogue reference into everything the layout needs.

    A measure and a column are encoded differently -- `Measure` versus `Column`
    in the query, and different type codes -- so the two cases are kept apart
    rather than guessed from the name.
    """
    if query_ref in COLUMNS:
        column = COLUMNS[query_ref]
        return {
            "kind": "Column",
            "entity": column["entity"],
            "property": column["property"],
            "type": column["type"],
            "format": column.get("format"),
            "display": column["property"],
        }
    entity, _, name = query_ref.partition(".")
    if entity != "KPI_Measures" or name not in MEASURES:
        raise KeyError(f"unknown field reference {query_ref!r}")
    return {
        "kind": "Measure",
        "entity": entity,
        "property": name,
        "type": MEASURE_TYPE_CODE,
        "format": MEASURES[name]["format_string"] or None,
        "display": name,
    }


def build_from(entities: list[str]) -> dict[str, str]:
    """Alias table for the query `From` clause.

    Desktop's convention, observed in the sample: the entity's first letter in
    lower case, with a numeric suffix when two entities collide (DimYear -> "d",
    DimMetric -> "d1").
    """
    aliases: dict[str, str] = {}
    used: dict[str, int] = {}
    for entity in entities:
        stem = entity[0].lower()
        count = used.get(stem, 0)
        aliases[entity] = stem if count == 0 else f"{stem}{count}"
        used[stem] = count + 1
    return aliases


def ordered_refs(visual: dict[str, Any]) -> list[tuple[str, str]]:
    """(role, query_ref) in projection order."""
    return [(role, ref) for role, refs in visual["roles"].items() for ref in refs]


def prototype_query(visual: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    refs = ordered_refs(visual)
    entities: list[str] = []
    for _, ref in refs:
        entity = field_spec(ref)["entity"]
        if entity not in entities:
            entities.append(entity)
    aliases = build_from(entities)

    select = []
    for _, ref in refs:
        spec = field_spec(ref)
        select.append(
            {
                spec["kind"]: {
                    "Expression": {"SourceRef": {"Source": aliases[spec["entity"]]}},
                    "Property": spec["property"],
                },
                "Name": ref,
                "NativeReferenceName": spec["display"],
            }
        )
    return (
        {
            "Version": 2,
            "From": [
                {"Name": alias, "Entity": entity, "Type": 0}
                for entity, alias in aliases.items()
            ],
            "Select": select,
        },
        aliases,
    )


def title_objects(title: str) -> dict[str, Any]:
    """Visual title, which belongs under `vcObjects` and NOT under `objects`.

    The two are different layers: `objects` formats what is inside the plot
    (legend, axes, data points), `vcObjects` formats the container chrome
    (title, background, border). A title written into `objects` is accepted
    silently and simply never appears -- the first attempt here did exactly
    that, and every visual fell back to its auto-generated caption.

    Power BI stores literals single-quoted inside the string value.
    """
    escaped = title.replace("'", "''")
    return {
        "title": [
            {
                "properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "text": {"expr": {"Literal": {"Value": f"'{escaped}'"}}},
                }
            }
        ]
    }


def data_transforms(visual: dict[str, Any]) -> dict[str, Any]:
    """All five keys Desktop writes, in the shapes the sample showed.

    Emitting only a subset was tempting, but `queryMetadata` and `visualElements`
    are what tell the renderer which field feeds which well; a partial block is
    the kind of thing that renders blank without raising anything.
    """
    refs = ordered_refs(visual)
    selects: list[dict[str, Any]] = []
    ordering: dict[str, list[int]] = {}
    metadata: list[dict[str, Any]] = []
    roles: list[dict[str, Any]] = []
    active_items: dict[str, list[dict[str, Any]]] = {}

    for index, (role, ref) in enumerate(refs):
        spec = field_spec(ref)
        entry: dict[str, Any] = {
            "displayName": spec["display"],
            "queryName": ref,
            "roles": {role: True},
            "type": {"category": None, "underlyingType": spec["type"]},
            "expr": {
                spec["kind"]: {
                    "Expression": {"SourceRef": {"Entity": spec["entity"]}},
                    "Property": spec["property"],
                }
            },
        }
        meta: dict[str, Any] = {
            "Restatement": spec["display"],
            "Name": ref,
            "Type": META_TYPE_BY_UNDERLYING[spec["type"]],
        }
        if spec["format"]:
            entry["format"] = spec["format"]
            meta["Format"] = spec["format"]

        # `Projection` is the index into `selects`, not the slot within the role.
        # The sample proves it: a line chart with one field per role wrote
        # Category 0, Y 1, Series 2 rather than 0, 0, 0.
        is_active = role == ACTIVE_ROLE and not ordering.get(role)
        if is_active:
            active_items[role] = [{"queryRef": ref, "suppressConcat": False}]

        selects.append(entry)
        metadata.append(meta)
        roles.append({"Name": role, "Projection": index, "isActive": is_active})
        ordering.setdefault(role, []).append(index)

    transforms: dict[str, Any] = {
        "selects": selects,
        "projectionOrdering": ordering,
        "queryMetadata": {"Select": metadata},
        "visualElements": [{"DataRoles": roles}],
    }
    if active_items:
        transforms["projectionActiveItems"] = active_items
    return transforms


def render_visual(visual: dict[str, Any]) -> dict[str, Any]:
    proto, _ = prototype_query(visual)
    position = {
        "x": visual["x"],
        "y": visual["y"],
        "z": 0,
        "width": visual["width"],
        "height": visual["height"],
    }
    projections: dict[str, list[dict[str, Any]]] = {}
    for role, refs in visual["roles"].items():
        items = []
        for slot, ref in enumerate(refs):
            item: dict[str, Any] = {"queryRef": ref}
            if role == ACTIVE_ROLE and slot == 0:
                item["active"] = True
            items.append(item)
        projections[role] = items

    single: dict[str, Any] = {
        "visualType": visual["visual_type"],
        "projections": projections,
        "prototypeQuery": proto,
        "drillFilterOtherVisuals": True,
    }
    if visual["title"]:
        single["vcObjects"] = title_objects(visual["title"])

    config = {
        "name": visual_name(visual["visual_id"]),
        "layouts": [{"id": 0, "position": position}],
        "singleVisual": single,
    }
    return {
        **position,
        "config": json.dumps(config, ensure_ascii=False),
        "filters": json.dumps(visual_filters(visual), ensure_ascii=False),
        "dataTransforms": json.dumps(data_transforms(visual), ensure_ascii=False),
    }


def render_report() -> dict[str, Any]:
    sections = []
    for ordinal, (page_id, display_name) in enumerate(PAGES):
        containers = [render_visual(v) for v in VISUALS if v["page"] == page_id]
        sections.append(
            {
                "name": page_name(page_id),
                "displayName": display_name,
                "ordinal": ordinal,
                "width": CANVAS_W,
                "height": CANVAS_H,
                "displayOption": 1,
                "config": json.dumps(
                    {"visibility": 0, "defaultLayout": {"displayOption": 1}},
                    ensure_ascii=False,
                ),
                "filters": "[]",
                "visualContainers": containers,
            }
        )
    return {
        "config": json.dumps(
            {
                "version": "5.55",
                "themeCollection": {"baseTheme": {"name": "CY24SU10"}},
                "activeSectionIndex": 0,
                "defaultDrillFilterOtherVisuals": True,
                "settings": {
                    "useStylableVisualContainerHeader": True,
                    "defaultFilterActionIsDataFilter": True,
                },
            },
            ensure_ascii=False,
        ),
        "layoutOptimization": 0,
        "resourcePackages": [
            {
                "resourcePackage": {
                    "disabled": False,
                    "items": [
                        {"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json", "type": 202}
                    ],
                    "name": "SharedResources",
                    "type": 2,
                }
            }
        ],
        "sections": sections,
    }


def main() -> int:
    # Every field must resolve before anything is written: an unknown reference
    # here becomes a visual that renders blank with no error in Desktop.
    for visual in VISUALS:
        for _, ref in ordered_refs(visual):
            field_spec(ref)

    payload = render_report()
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if not text.isascii():
        offenders = sorted({c for c in text if not c.isascii()})
        raise ValueError(f"report layout must stay ASCII, found {''.join(offenders)!r}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(text, encoding="utf-8", newline="\r\n")

    per_page = {
        page_id: sum(1 for v in VISUALS if v["page"] == page_id) for page_id, _ in PAGES
    }
    print(
        f"PHASE 5 REPORT BUILD: PASS | visuals={len(VISUALS)} | "
        f"pages={per_page} | types={sorted({v['visual_type'] for v in VISUALS})}"
    )
    print(f"  -> {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
