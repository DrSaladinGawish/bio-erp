from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.auth import User
from app.services.local_ai_engine import (
    get_ai_engine,
    validate_query,
    execute_safe_query,
    format_results,
)
from app.services.cost_engine import CostEngine

router = APIRouter(prefix="/api/v1/ai", tags=["AI Bridge"])


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    answer: str
    sql: str | None = None
    source: str = "ai"


_KEYWORD_ROUTES = {
    "profitability": "branch_profitability",
    "variance": "variance_report",
    "budget vs actual": "variance_report",
    "branch comparison": "branch_profitability",
    "pnl": "branch_profitability",
    "p&l": "branch_profitability",
    "profit and loss": "branch_profitability",
}


def _route_question(question: str) -> str | None:
    q = question.lower()
    for keyword, route in _KEYWORD_ROUTES.items():
        if keyword in q:
            return route
    return None


@router.post("/query", response_model=QueryResponse)
async def ai_query(
    req: QueryRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    route = _route_question(req.question)

    if route == "branch_profitability":
        data = await CostEngine.get_branch_profitability(db)
        lines = ["Branch Profitability:", "---"]
        for row in data:
            lines.append(
                f"  {row['branch_name']}: "
                f"Revenue {row['revenue']:,.2f} | "
                f"Gross Profit {row['gross_profit']:,.2f} ({row['gross_margin_pct']}%) | "
                f"Net {row['net_profit']:,.2f} ({row['net_margin_pct']}%) | "
                f"{row['event_count']} events"
            )
        return QueryResponse(answer="\n".join(lines), sql=None, source="service")

    if route == "variance_report":
        data = await CostEngine.get_variance_report(db)
        lines = [f"Variance Report â€” {data['period_label']}", "---"]
        for row in data["rows"]:
            lines.append(
                f"  {row['cost_center_name']}/{row['coa_account_name']}: "
                f"Budget {row['budgeted']:,.2f} | "
                f"Actual {row['actual']:,.2f} | "
                f"Variance {row['variance']:,.2f} ({row['variance_pct']}%) [{row['flag']}]"
            )
        lines.append(
            f"---\nTotal: Budget {data['total_budgeted']:,.2f} | Actual {data['total_actual']:,.2f}"
        )
        return QueryResponse(answer="\n".join(lines), sql=None, source="service")

    engine = get_ai_engine()
    try:
        sql = await engine.generate_sql(req.question)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI engine unavailable: {e}")

    valid, err = validate_query(sql)
    if not valid:
        return QueryResponse(
            answer=f"The AI generated an invalid query: {err}\n\nGenerated SQL:\n```sql\n{sql}\n```",
            sql=sql,
            source="ai",
        )

    try:
        rows = await execute_safe_query(db, sql)
    except Exception as e:
        return QueryResponse(
            answer=f"Query execution failed: {e}\n\nGenerated SQL:\n```sql\n{sql}\n```",
            sql=sql,
            source="ai",
        )

    answer = format_results(rows)
    return QueryResponse(answer=answer, sql=sql, source="ai")
