"""Emit JSON-RPC requests that load the Phase 5 model into an open blank PBIX.

The script does not contact Power BI itself. It renders deterministic requests
for the local Power BI Modeling MCP server, using the same table and measure
catalogues as ``05_build_pbip.py``. The caller replaces ``__CONNECTION__`` with
the connection selected after listing local Power BI Desktop instances.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import phase5_contract as K  # noqa: E402
from config import CLEAN  # noqa: E402

_builder_spec = importlib.util.spec_from_file_location(
    "phase5_builder", Path(__file__).resolve().parent / "05_build_pbip.py"
)
_builder = importlib.util.module_from_spec(_builder_spec)
assert _builder_spec.loader is not None
_builder_spec.loader.exec_module(_builder)

TABLES = _builder.TABLES
MEASURES = _builder.MEASURES
CONNECTION = "__CONNECTION__"
MEASURE_TABLE = "KPI_Measures"


def rpc(request_id: int, tool: str, request: dict[str, Any]) -> None:
    request["connectionName"] = CONNECTION
    print(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": tool, "arguments": {"request": request}},
            },
            # ASCII escapes keep Vietnamese metadata intact even when a Windows
            # console is running with a legacy code page.
            ensure_ascii=True,
        )
    )


def inline_m_expression(table_name: str, spec: dict[str, Any]) -> str:
    transforms = ", ".join(
        f'{{"{name}", {m_type}}}' for name, _, m_type in spec["columns"]
    )
    source_path = str(CLEAN / spec["source"])
    return f'''let
    Source = Csv.Document(
        File.Contents("{source_path}"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(
        Promoted,
        {{{transforms}}},
        "en-US"
    )
in
    Typed'''


def source_table_definition(name: str, spec: dict[str, Any]) -> dict[str, Any]:
    type_map = {"string": "String", "int64": "Int64", "double": "Double"}
    columns = []
    for ordinal, (column, data_type, _) in enumerate(spec["columns"]):
        definition: dict[str, Any] = {
            "name": column,
            "dataType": type_map[data_type],
            "sourceColumn": column,
            "ordinal": ordinal,
            "summarizeBy": "None",
            "lineageTag": _builder.tag("column", name, column),
        }
        if data_type == "int64":
            definition["formatString"] = "0"
        if column in spec["hidden_columns"]:
            definition["isHidden"] = True
        columns.append(definition)
    return {
        "name": name,
        "mode": "Import",
        "partitionName": name,
        "mExpression": inline_m_expression(name, spec),
        "columns": columns,
        "lineageTag": _builder.tag("table", name),
    }


def main() -> None:
    rpc(
        100,
        "model_operations",
        {
            "operation": "Update",
            "definition": {
                "sourceQueryCulture": "en-US",
                "defaultPowerBIDataSourceVersion": "PowerBI_V3",
                "discourageImplicitMeasures": True,
            },
        },
    )

    source_tables = [source_table_definition(name, spec) for name, spec in TABLES.items()]
    calculated_tables = [
        {
            "name": "SelReportYear",
            "daxExpression": (
                f'SELECTCOLUMNS(GENERATESERIES({K.YEAR_START}, {K.YEAR_END}, 1), '
                '"year", [Value])'
            ),
            "lineageTag": _builder.tag("table", "SelReportYear"),
        },
        {
            "name": "SelBaseYear",
            "daxExpression": (
                f'SELECTCOLUMNS(GENERATESERIES({K.YEAR_START}, {K.YEAR_END}, 1), '
                '"year", [Value])'
            ),
            "lineageTag": _builder.tag("table", "SelBaseYear"),
        },
        {
            "name": "SelMode",
            "daxExpression": (
                'DATATABLE("mode_key", STRING, "mode_label", STRING, '
                '"sort_order", INTEGER, {'
                '{"RENEWABLE_TOTAL", "Tổng NLTT (thủy điện + gió + mặt trời + NLTT khác)", 1},'
                '{"MODERN_WIND_SOLAR", "Chỉ NLTT hiện đại (gió + mặt trời)", 2}})'
            ),
            "lineageTag": _builder.tag("table", "SelMode"),
        },
        {
            "name": MEASURE_TABLE,
            "daxExpression": 'ROW("_placeholder", "")',
            "isHidden": True,
            "lineageTag": _builder.tag("table", "Measures"),
        },
    ]
    rpc(
        101,
        "table_operations",
        {
            "operation": "Create",
            "definitions": source_tables + calculated_tables,
            "options": {"continueOnError": False, "useTransaction": True},
        },
    )

    rpc(
        102,
        "column_operations",
        {
            "operation": "Create",
            "definitions": [
                {
                    "tableName": "DimEntity",
                    "name": "entity_vi",
                    "expression": _builder.switch_expression(
                        "DimEntity[entity]", _builder.ENTITY_VI
                    ),
                    "dataType": "String",
                    "summarizeBy": "None",
                    "lineageTag": _builder.tag("column", "DimEntity", "entity_vi"),
                },
                {
                    "tableName": "DimMetric",
                    "name": "technology_vi",
                    "expression": _builder.switch_expression(
                        "DimMetric[technology]", _builder.TECHNOLOGY_VI
                    ),
                    "dataType": "String",
                    "summarizeBy": "None",
                    "lineageTag": _builder.tag("column", "DimMetric", "technology_vi"),
                },
                {
                    "tableName": "DimMetric",
                    "name": "technology_sort",
                    "expression": _builder.switch_expression(
                        "DimMetric[technology]", _builder.TECHNOLOGY_SORT, quote=False
                    ),
                    "dataType": "Int64",
                    "formatString": "0",
                    "summarizeBy": "None",
                    "isHidden": True,
                    "lineageTag": _builder.tag("column", "DimMetric", "technology_sort"),
                },
            ],
            "options": {"continueOnError": False, "useTransaction": True},
        },
    )

    rpc(
        103,
        "column_operations",
        {
            "operation": "Update",
            "definitions": [
                {"tableName": "SelReportYear", "name": "year", "summarizeBy": "None", "formatString": "0"},
                {"tableName": "SelBaseYear", "name": "year", "summarizeBy": "None", "formatString": "0"},
                {"tableName": "SelMode", "name": "mode_key", "summarizeBy": "None"},
                {"tableName": "SelMode", "name": "mode_label", "summarizeBy": "None"},
                {"tableName": "SelMode", "name": "sort_order", "summarizeBy": "None", "formatString": "0"},
                {"tableName": MEASURE_TABLE, "name": "_placeholder", "isHidden": True, "summarizeBy": "None"},
            ],
            "options": {"continueOnError": False, "useTransaction": True},
        },
    )

    measure_definitions = []
    for measure in MEASURES:
        definition: dict[str, Any] = {
            "tableName": MEASURE_TABLE,
            "name": measure["name"],
            "expression": measure["dax_expression"],
            "description": f'[{measure["measure_id"]}] {measure["description_vi"]}',
            "isHidden": measure["hidden"],
            "lineageTag": _builder.tag("measure", measure["name"]),
        }
        if measure["format_string"]:
            definition["formatString"] = measure["format_string"]
        if measure["display_folder"]:
            definition["displayFolder"] = measure["display_folder"]
        measure_definitions.append(definition)
    # Emit one measure per request. A single request containing the full catalogue
    # is large enough to be truncated by some Windows PTY transports before the
    # MCP server can parse its JSON payload.
    next_request_id = 104
    for definition in measure_definitions:
        rpc(
            next_request_id,
            "measure_operations",
            {
                "operation": "Create",
                "definitions": [definition],
                "options": {"continueOnError": False, "useTransaction": True},
            },
        )
        next_request_id += 1

    relationship_definitions = []
    for dimension, dimension_column, fact, fact_column in K.RELATIONSHIPS:
        relationship_definitions.append(
            {
                "name": f"{fact}_{fact_column}_{dimension}_{dimension_column}",
                "fromTable": fact,
                "fromColumn": fact_column,
                "fromCardinality": "Many",
                "toTable": dimension,
                "toColumn": dimension_column,
                "toCardinality": "One",
                "crossFilteringBehavior": "OneDirection",
                "isActive": True,
            }
        )
    rpc(
        next_request_id,
        "relationship_operations",
        {
            "operation": "Create",
            "definitions": relationship_definitions,
            "options": {"continueOnError": False, "useTransaction": True},
        },
    )
    next_request_id += 1

    rpc(
        next_request_id,
        "model_operations",
        {"operation": "RefreshWithXMLA", "refreshType": "Full"},
    )
    next_request_id += 1
    rpc(next_request_id, "table_operations", {"operation": "List"})
    next_request_id += 1
    rpc(
        next_request_id,
        "measure_operations",
        {"operation": "List", "filter": {"maxResults": 100}},
    )
    next_request_id += 1
    rpc(next_request_id, "relationship_operations", {"operation": "List"})


if __name__ == "__main__":
    main()
