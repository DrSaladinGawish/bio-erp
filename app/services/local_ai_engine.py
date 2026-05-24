import re
import sqlparse
from typing import Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import Base

_UNSAFE_PATTERN = re.compile(
    r"\b(drop|delete|insert|update|alter|truncate|grant|revoke|create|replace)\s",
    re.IGNORECASE,
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
    parsed = sqlparse.parse(query)
    if not parsed:
        return False, "Could not parse SQL"
    stmt = parsed[0]
    if stmt.get_type() != "SELECT":
        return False, "Only SELECT queries are allowed"
    return True, ""


async def execute_safe_query(
    db: AsyncSession, query: str, timeout: int = 5
) -> list[dict[str, Any]]:
    valid, err = validate_query(query)
    if not valid:
        raise ValueError(err)
    result = await db.execute(text(query))
    rows = result.mappings().all()
    return [dict(row) for row in rows]


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


# Singleton with defaults â€” override via dependency injection
_default_engine: AIEngine | None = None


def get_ai_engine() -> AIEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = AIEngine()
    return _default_engine
