from datetime import datetime
from datetime import timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.cost_engine import CostEngine


async def generate_executive_summary(
    db: AsyncSession, period_id: int | None = None, branch_id: int | None = None
) -> dict:
    variance = await CostEngine.get_variance_report(
        db, period_id=period_id, branch_id=branch_id
    )
    profitability = await CostEngine.get_branch_profitability(
        db, period_id=period_id, branch_id=branch_id
    )

    total_budget = variance.get("total_budgeted", 0)
    total_actual = variance.get("total_actual", 0)
    total_variance = total_budget - total_actual

    summary = {
        "generated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
        "period_label": variance.get("period_label", "N/A"),
        "financial_health": {
            "total_budgeted": total_budget,
            "total_actual": total_actual,
            "total_variance": total_variance,
            "variance_pct": round(total_variance / total_budget * 100, 2)
            if total_budget
            else 0,
        },
        "variance_rows": variance.get("rows", []),
        "branch_profitability": profitability,
        "alert_count": sum(
            1 for r in variance.get("rows", []) if r.get("flag") == "investigate"
        ),
    }
    return summary


async def render_executive_pdf(summary: dict) -> bytes:
    rows_html = ""
    for r in summary["variance_rows"][:20]:
        flag_class = "investigate" if r.get("flag") == "investigate" else "ok"
        rows_html += f"<tr><td>{r['cost_center_name']}</td><td>{r['coa_account_name']}</td><td>{r['budgeted']:,.2f}</td><td>{r['actual']:,.2f}</td><td class='{flag_class}'>{r['variance_pct']}%</td></tr>"

    branch_html = ""
    for b in summary["branch_profitability"]:
        branch_html += f"<tr><td>{b['branch_name']}</td><td>{b['revenue']:,.2f}</td><td>{b['gross_profit']:,.2f}</td><td>{b['gross_margin_pct']}%</td><td>{b['event_count']}</td></tr>"

    fh = summary["financial_health"]
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
body {{ font-family: 'Noto Sans', sans-serif; padding: 40px; color: #1e293b; }}
h1 {{ color: #1e3a5f; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; }}
h2 {{ color: #334155; margin-top: 24px; }}
table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
th {{ background: #3b82f6; color: white; padding: 8px; text-align: left; }}
td {{ padding: 8px; border-bottom: 1px solid #e2e8f0; }}
.summary-box {{ background: #f0f9ff; border-left: 4px solid #3b82f6; padding: 16px; margin: 16px 0; }}
.investigate {{ color: #dc2626; font-weight: bold; }}
.ok {{ color: #16a34a; }}
.footer {{ margin-top: 32px; color: #94a3b8; font-size: 11px; text-align: center; }}
</style></head><body>
<h1>Executive Summary</h1>
<p>Period: {summary["period_label"]} | Generated: {summary["generated_at"][:10]}</p>
<div class='summary-box'>
<strong>Financial Health:</strong><br>
Budget: EGP {fh["total_budgeted"]:,.2f} | Actual: EGP {fh["total_actual"]:,.2f} | Variance: EGP {fh["total_variance"]:,.2f} ({fh["variance_pct"]}%)<br>
Alerts: {summary["alert_count"]}
</div>
<h2>Variance Report</h2>
<table><thead><tr><th>Cost Center</th><th>Account</th><th>Budget</th><th>Actual</th><th>Var %</th></tr></thead><tbody>{rows_html}</tbody></table>
<h2>Branch Profitability</h2>
<table><thead><tr><th>Branch</th><th>Revenue</th><th>Gross Profit</th><th>Margin</th><th>Events</th></tr></thead><tbody>{branch_html}</tbody></table>
<div class='footer'>BIO-ERP Executive Report | Confidential</div>
</body></html>"""

    from weasyprint import HTML

    pdf = HTML(string=html.encode("utf-8")).write_pdf()
    return pdf
