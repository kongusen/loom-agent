from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List


PLACEHOLDER_PATTERN = re.compile(r"{{\s*(?P<name>[\w\-]+)\s*:\s*(?P<desc>[^}]+)\s*}}")


@dataclass(frozen=True)
class Placeholder:
    """Represents a placeholder extracted from a context template."""

    name: str
    description: str


@dataclass
class SQLPlaceholderPlan:
    """Plan describing how to populate placeholders using a single SQL result row."""

    context_template: str
    sql: str
    placeholder_columns: Dict[str, str]
    data_source: Dict[str, str]
    schedule: str
    window_start: str
    window_end: str


def parse_placeholders(template: str) -> List[Placeholder]:
    """Extract placeholders of the form {{name: description}} from a template."""
    matches = PLACEHOLDER_PATTERN.findall(template)
    return [Placeholder(name=m[0].strip(), description=m[1].strip()) for m in matches]


def _infer_column_alias(placeholder: Placeholder, index: int) -> str:
    """Infer a sensible column alias for a placeholder."""
    desc = placeholder.description.lower()
    if placeholder.name == "top_product":
        return "top_product_name"
    if "销量" in desc:
        return "total_quantity"
    if "收入" in desc or "revenue" in desc or "gmv" in desc:
        return "total_revenue"
    return f"{placeholder.name}_{index}"


def _build_top_product_query(window_start: str, window_end: str, database: str) -> str:
    """Create SQL that returns the top-selling product for the window."""
    # Doris uses MySQL-compatible syntax for DATE_ADD.
    return (
        "SELECT\n"
        "    p.product_name AS top_product_name,\n"
        "    SUM(oi.order_item_quantity) AS total_quantity,\n"
        "    SUM(oi.order_item_subtotal) AS total_revenue\n"
        f"FROM {database}.orders AS o\n"
        f"JOIN {database}.order_items AS oi\n"
        "  ON o.order_id = oi.order_item_order_id\n"
        f"JOIN {database}.products AS p\n"
        "  ON p.product_id = oi.order_item_product_id\n"
        f"WHERE o.order_date >= '{window_start}'\n"
        f"  AND o.order_date < DATE_ADD('{window_end}', INTERVAL 1 DAY)\n"
        "GROUP BY p.product_name\n"
        "ORDER BY total_quantity DESC\n"
        "LIMIT 1;"
    )


def generate_placeholder_sql_plan(
    *,
    context_template: str,
    schedule: str,
    window_start: str,
    window_end: str,
    data_source: Dict[str, str],
) -> SQLPlaceholderPlan:
    """Generate an execution plan that maps template placeholders to SQL columns."""
    placeholders = parse_placeholders(context_template)
    placeholder_columns: Dict[str, str] = {}
    for idx, placeholder in enumerate(placeholders, start=1):
        key = f"{placeholder.name}:{placeholder.description}"
        placeholder_columns[key] = _infer_column_alias(placeholder, idx)

    sql = _build_top_product_query(
        window_start=window_start,
        window_end=window_end,
        database=data_source.get("database", "retail_db"),
    )

    return SQLPlaceholderPlan(
        context_template=context_template,
        sql=sql,
        placeholder_columns=placeholder_columns,
        data_source=data_source,
        schedule=schedule,
        window_start=window_start,
        window_end=window_end,
    )
