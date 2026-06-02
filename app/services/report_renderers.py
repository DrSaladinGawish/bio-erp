from pathlib import Path
from typing import Any

import pandas as pd


class ExcelRenderer:
    @staticmethod
    def generate(report_type: str, data: dict, output_path: str) -> str:
        df = _data_to_dataframe(report_type, data)

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name=report_type[:31], index=False)
            worksheet = writer.sheets[report_type[:31]]
            for col_idx, col in enumerate(df.columns, 1):
                max_len = max(
                    df[col].astype(str).str.len().max() if len(df) else 0,
                    len(str(col)),
                )
                worksheet.column_dimensions[
                    worksheet.cell(1, col_idx).column_letter
                ].width = min(max_len + 2, 60)

        return output_path


class PDFRenderer:
    @staticmethod
    def generate(
        report_type: str, data: dict, output_path: str, template_name: str | None = None
    ) -> str:
        html = _build_html_report(report_type, data, template_name)

        from weasyprint import HTML

        HTML(string=html).write_pdf(output_path)
        return output_path


class CSVRenderer:
    @staticmethod
    def generate(report_type: str, data: dict, output_path: str) -> str:
        df = _data_to_dataframe(report_type, data)
        df.to_csv(output_path, index=False)
        return output_path


def _data_to_dataframe(report_type: str, data: dict) -> pd.DataFrame:
    if "rows" in data and isinstance(data["rows"], list):
        return pd.DataFrame(data["rows"])
    if "data" in data and isinstance(data["data"], list):
        return pd.DataFrame(data["data"])
    flat = _flatten(data)
    if flat:
        return pd.DataFrame([flat])
    return pd.DataFrame()


def _flatten(d: dict, parent_key: str = "", sep: str = "_") -> dict:
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            items.append((new_key, str(v)))
        else:
            items.append((new_key, v))
    return dict(items)


def _build_html_report(
    report_type: str, data: dict, template_name: str | None = None
) -> str:
    df = _data_to_dataframe(report_type, data)
    table_html = df.to_html(index=False, classes="report-table", border=0)

    title = report_type.replace("_", " ").title()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  body {{ font-family: 'Helvetica', 'Arial', sans-serif; margin: 2em; }}
  h1 {{ color: #1a365d; font-size: 1.8em; border-bottom: 2px solid #2b6cb0; padding-bottom: 0.3em; }}
  .report-table {{ border-collapse: collapse; width: 100%; margin-top: 1em; }}
  .report-table th {{ background: #2b6cb0; color: white; padding: 0.5em; text-align: left; font-size: 0.85em; }}
  .report-table td {{ padding: 0.4em; border-bottom: 1px solid #e2e8f0; font-size: 0.85em; }}
  .report-table tr:nth-child(even) {{ background: #f7fafc; }}
  .footer {{ margin-top: 2em; font-size: 0.75em; color: #718096; text-align: center; }}
</style>
</head>
<body>
<h1>{title}</h1>
{table_html}
<div class="footer">BIO-ERP Report · Generated {__import__('datetime').datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</div>
</body>
</html>"""
