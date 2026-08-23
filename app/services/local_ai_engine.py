import re
import logging
from typing import Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlglot import parse as sqlglot_parse, exp
from sqlglot.errors import SqlglotError
from app.database import Base

logger = logging.getLogger(__name__)

_UNSAFE_PATTERN = re.compile(
    r"\b(drop|delete|insert|update|alter|truncate|grant|revoke|create|replace|exec|execute|executescript)\s",
    re.IGNORECASE,
)

_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(union\s+all|into\s+outfile|into\s+dumpfile|load_file|sleep|benchmark|waitfor|pg_sleep)\b",
    re.IGNORECASE,
)

_TABLE_ALLOWLIST: set[str] = set()
_COLUMN_ALLOWLIST: dict[str, set[str]] = {}


def _build_allowlists() -> None:
    global _TABLE_ALLOWLIST, _COLUMN_ALLOWLIST
    if _TABLE_ALLOWLIST:
        return
    _TABLE_ALLOWLIST = {name.lower() for name in Base.metadata.tables.keys()}
    _COLUMN_ALLOWLIST = {}
    for table_name, table in Base.metadata.tables.items():
        _COLUMN_ALLOWLIST[table_name.lower()] = {
            col.name.lower() for col in table.columns
        }


def _get_allowed_tables() -> set[str]:
    _build_allowlists()
    return _TABLE_ALLOWLIST


def _get_allowed_columns(table_name: str) -> set[str]:
    _build_allowlists()
    return _COLUMN_ALLOWLIST.get(table_name.lower(), set())


def _extract_references(sql: str) -> tuple[set[str], set[tuple[str, str]]]:
    try:
        statements = sqlglot_parse(sql, read="postgres")
    except SqlglotError:
        raise ValueError("Failed to parse SQL — query rejected")

    if not statements:
        raise ValueError("Empty SQL statement — query rejected")

    stmt = statements[0]
    if len(statements) > 1:
        raise ValueError("Multiple statements not allowed")

    tables: set[str] = set()
    column_refs: set[tuple[str, str]] = set()

    for node in stmt.walk():
        if isinstance(node, exp.Table):
            catalog = node.args.get("catalog")
            db = node.args.get("db")
            if catalog or db:
                ref = catalog.name if catalog else db.name
                raise ValueError(
                    f"Cross-database reference not allowed: {ref}"
                )
            name = node.name
            if name:
                tables.add(name.lower())

        if isinstance(node, exp.Column):
            col_table = node.table.lower() if node.table else None
            col_name = node.name.lower() if node.name else None
            if col_name:
                column_refs.add((col_table, col_name))

    return tables, column_refs


def _check_select_only(stmt) -> None:
    if not isinstance(stmt, exp.Select):
        raise ValueError(
            f"Only SELECT queries are allowed (got {type(stmt).__name__})"
        )


def _check_tables(tables: set[str]) -> None:
    allowed = _get_allowed_tables()
    unknown = tables - allowed
    if unknown:
        raise ValueError(
            f"Query references unknown table(s): {', '.join(sorted(unknown))}"
        )


def _check_columns(column_refs: set[tuple[str, str]], tables: set[str]) -> None:
    allowed_all = _get_allowed_tables()
    table_for_col: dict[str | None, set[str]] = {}
    for col_table, col_name in column_refs:
        table_for_col.setdefault(col_table, set()).add(col_name)

    for col_table, col_names in table_for_col.items():
        if col_table and col_table not in allowed_all:
            continue
        if col_table:
            allowed_cols = _get_allowed_columns(col_table)
            if not allowed_cols:
                continue
            unknown = col_names - allowed_cols - {
                "count", "sum", "avg", "min", "max", "abs", "round",
                "cast", "coalesce", "now", "extract", "date_part",
                "length", "trim", "upper", "lower", "substring", "replace",
            }
            if unknown:
                raise ValueError(
                    f"Table '{col_table}' — unknown column(s): "
                    f"{', '.join(sorted(unknown))}"
                )


_FEW_SHOT_EXAMPLES = """
-- Example 1: Total revenue by branch
SELECT b.name_en, SUM(e.total_revenue) AS total_revenue
FROM events e JOIN branches b ON e.branch_id = b.id
GROUP BY b.name_en ORDER BY total_revenue DESC;

-- Example 2: Top 5 clients by event count
SELECT c.name_en, COUNT(e.id) AS event_count, SUM(e.total_revenue) AS total_revenue
FROM clients c JOIN events e ON c.id = e.client_id
GROUP BY c.id ORDER BY event_count DESC LIMIT 5;

-- Example 3: Budget variance over 10%
SELECT cc.name_en, bl.budgeted_amount, bl.actual_amount,
       (bl.actual_amount - bl.budgeted_amount) AS variance,
       ((bl.actual_amount - bl.budgeted_amount) / bl.budgeted_amount * 100) AS variance_pct
FROM budget_lines bl JOIN cost_centers cc ON bl.cost_center_id = cc.id
WHERE bl.budgeted_amount > 0
  AND abs((bl.actual_amount - bl.budgeted_amount) / bl.budgeted_amount * 100) > 10
ORDER BY variance_pct DESC;

-- Example 4: Active events with client names
SELECT e.event_code, e.name_en, c.name_en AS client_name,
       e.status, e.total_budget, e.start_date
FROM events e JOIN clients c ON e.client_id = c.id
WHERE e.status IN ('APPROVED', 'IN_PROGRESS')
ORDER BY e.start_date;

-- Example 5: Supplier performance
SELECT s.name_en, COUNT(po.id) AS po_count, AVG(s.rating) AS avg_rating
FROM suppliers s LEFT JOIN purchase_orders po ON s.id = po.supplier_id
GROUP BY s.id ORDER BY avg_rating DESC;
"""


def extract_schema_context() -> str:
    _build_allowlists()
    lines = []
    for name, table in Base.metadata.tables.items():
        cols = [f"  {c.name} {c.type}" for c in table.columns]
        newline = "\n"
        lines.append(f"CREATE TABLE {name} ({', '.join(cols).replace('', newline)}\n);")
    return "\n\n".join(lines)


def get_system_prompt() -> str:
    schema = extract_schema_context()
    return f"""You are a SQL expert for the BIO-ERP system. Generate ONLY SELECT queries.

Rules:
- Return ONLY the SQL query, no explanation
- Use SQLite-compatible syntax
- Add LIMIT 50 unless specified otherwise
- Use table names exactly as shown

Schema:
{schema}

Few-shot examples:
{_FEW_SHOT_EXAMPLES}
"""


def validate_query(query: str) -> tuple[bool, str]:
    if _UNSAFE_PATTERN.search(query):
        return False, "Unsafe SQL operation blocked"
    if _FORBIDDEN_KEYWORDS.search(query):
        return False, "Forbidden SQL pattern detected"
    if ";" in query.strip().rstrip(";").strip():
        return False, "Multiple statements not allowed"

    try:
        tables, column_refs = _extract_references(query)
    except ValueError as e:
        return False, str(e)

    try:
        statements = sqlglot_parse(query, read="postgres")
        if statements:
            _check_select_only(statements[0])
    except (SqlglotError, ValueError) as e:
        return False, str(e)

    try:
        _check_tables(tables)
    except ValueError as e:
        return False, str(e)

    try:
        _check_columns(column_refs, tables)
    except ValueError as e:
        return False, str(e)

    return True, ""


async def execute_safe_query(
    db: AsyncSession, query: str, timeout: int = 5
) -> list[dict[str, Any]]:
    valid, err = validate_query(query)
    if not valid:
        raise ValueError(err)

    from app.database import get_readonly_session_factory

    readonly_factory = get_readonly_session_factory()
    readonly_session = readonly_factory()
    try:
        result = await readonly_session.execute(text(query))
        rows = result.mappings().all()
        return [dict(row) for row in rows]
    finally:
        await readonly_session.close()


def format_results(rows: list[dict[str, Any]], max_rows: int = 20) -> str:
    if not rows:
        return "No results found."
    truncated = rows[:max_rows]
    header = " | ".join(str(k) for k in truncated[0].keys())
    separator = "-" * len(header)
    lines = [header, separator]
    for row in truncated:
        lines.append(
            " | ".join(str(v) if v is not None else "NULL" for v in row.values())
        )
    if len(rows) > max_rows:
        lines.append(f"... and {len(rows) - max_rows} more rows")
    return "\n".join(lines)


class AIEngine:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = base_url or "http://localhost:11434/v1"
        self.model = model or "qwen2.5-coder:7b"
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(base_url=self.base_url, api_key="ollama")
        return self._client

    async def generate_sql(self, question: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": get_system_prompt()},
                {"role": "user", "content": question},
            ],
            temperature=0.05,
            max_tokens=500,
        )
        sql = response.choices[0].message.content.strip()
        sql = re.sub(r"^```(?:sql)?\s*", "", sql, flags=re.IGNORECASE)
        sql = re.sub(r"\s*```$", "", sql)
        return sql


_default_engine: AIEngine | None = None


def get_ai_engine() -> AIEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = AIEngine()
    return _default_engine
