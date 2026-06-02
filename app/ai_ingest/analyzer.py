import logging
import re
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

INVOICE_PATTERNS = [
    (r"(?i)(?:invoice|فاتورة)\s+(?:no|#|nummer|number)\s*[:\-]?\s*(\S+)", "invoice_number"),
    (r"(?i)(date|تاريخ)\s*[:\-]?\s*(\d{1,4}[/\-\.]\d{1,2}[/\-\.]\d{1,4})", "document_date"),
    (r"(?i)(total|due|المجموع|الإجمالي)\s*[:\-]?\s*([\d,]+\.?\d*)", "total_amount"),
    (r"(?i)(vat|tax|ضريبة|قيمة مضافة)\s*[:\-]?\s*([\d,]+\.?\d*)", "tax_amount"),
    (r"(?i)(supplier|vendor|مورد|بائع)\s*[:\-]?\s*(.+?)(?:\n|$)", "supplier_name"),
    (r"(?i)(customer|client|عميل)\s*[:\-]?\s*(.+?)(?:\n|$)", "customer_name"),
]

ACCOUNT_PATTERNS = [
    (r"(?i)(GL|حساب|account)\s*(no|#|code|رقم)?\s*[:\-]?\s*(\d{3,})", "gl_account"),
    (r"(?i)(cost center|مركز تكلفة)\s*[:\-]?\s*(.+?)(?:\n|$)", "cost_center"),
]

AMOUNT_LINE_PATTERN = re.compile(
    r"(?i)([\w\s/]+?)\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)"
)


def extract_entities(text: str) -> dict[str, Any]:
    entities: dict[str, Any] = {
        "invoice_number": None,
        "document_date": None,
        "total_amount": None,
        "tax_amount": None,
        "supplier_name": None,
        "customer_name": None,
        "gl_accounts": [],
        "cost_centers": [],
        "line_items": [],
    }

    for pattern, key in INVOICE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            last = match.lastindex or 1
            if key in ("total_amount", "tax_amount"):
                val_str = match.group(last).replace(",", "")
                try:
                    entities[key] = float(val_str)
                except ValueError:
                    entities[key] = val_str
            else:
                entities[key] = match.group(last).strip().rstrip(".,;")

    for pattern, key in ACCOUNT_PATTERNS:
        for match in re.finditer(pattern, text):
            val = match.group(3) if match.lastindex >= 3 else match.group(2)
            if key == "gl_account":
                entities["gl_accounts"].append(val.strip())
            elif key == "cost_center":
                entities["cost_centers"].append(val.strip().rstrip(".,;"))

    return entities


def extract_patterns(text: str) -> list[dict[str, Any]]:
    patterns = []
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        m = AMOUNT_LINE_PATTERN.search(line)
        if m:
            desc = m.group(1).strip()
            try:
                qty = float(m.group(2).replace(",", ""))
                amt = float(m.group(3).replace(",", ""))
            except ValueError:
                continue
            patterns.append({
                "type": "line_item",
                "description": desc,
                "quantity": qty,
                "amount": amt,
            })

    for entry in INVOICE_PATTERNS:
        pattern = entry[0] if isinstance(entry, tuple) else entry
        for match in re.finditer(pattern, text):
            patterns.append({
                "type": "keyword_match",
                "pattern": str(pattern)[:100],
                "matched": match.group(0).strip(),
            })

    return patterns


def match_neural_nodes(
    entities: dict[str, Any],
    existing_nodes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    matched = []
    if not existing_nodes:
        return matched
    for node in existing_nodes:
        label = node.get("label", "").lower()
        for key, val in entities.items():
            if val is None:
                continue
            str_val = str(val).lower()
            if label in str_val or str_val in label:
                matched.append({
                    "node_id": node.get("id"),
                    "label": node.get("label"),
                    "matched_on": key,
                    "confidence": 0.8,
                })
                break
    return matched


def analyze_document(
    text: str,
    existing_nodes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    start = datetime.utcnow()
    entities = extract_entities(text)
    patterns = extract_patterns(text)
    neural_nodes_matched = match_neural_nodes(entities, existing_nodes or [])

    line_items = entities.pop("line_items", [])
    pattern_line_items = [p for p in patterns if p["type"] == "line_item"]
    if not line_items and pattern_line_items:
        entities["line_items"] = pattern_line_items

    processing_ms = int((datetime.utcnow() - start).total_seconds() * 1000)

    return {
        "raw_text": text[:50000],
        "extracted_entities": entities,
        "extracted_patterns": patterns[:200],
        "neural_nodes": neural_nodes_matched,
        "neural_links": [],
        "summary": _generate_summary(entities, patterns),
        "confidence_score": _calculate_confidence(entities, patterns),
        "processing_time_ms": processing_ms,
    }


def _generate_summary(entities: dict[str, Any], patterns: list[dict[str, Any]]) -> str:
    parts = []
    inv = entities.get("invoice_number")
    if inv:
        parts.append(f"Invoice #{inv}")
    supp = entities.get("supplier_name")
    if supp:
        parts.append(f"from {supp}")
    cust = entities.get("customer_name")
    if cust:
        parts.append(f"to {cust}")
    total = entities.get("total_amount")
    if total:
        parts.append(f"total {total}")
    li_count = len([p for p in patterns if p["type"] == "line_item"])
    if li_count:
        parts.append(f"({li_count} line items)")
    return " ".join(parts) if parts else "Document analyzed, no key entities found."


def _calculate_confidence(entities: dict[str, Any], patterns: list[dict[str, Any]]) -> float:
    score = 0.0
    if entities.get("invoice_number"):
        score += 0.25
    if entities.get("total_amount"):
        score += 0.25
    if entities.get("supplier_name") or entities.get("customer_name"):
        score += 0.2
    if entities.get("document_date"):
        score += 0.15
    line_items = [p for p in patterns if p["type"] == "line_item"]
    if line_items:
        score += min(0.15, len(line_items) * 0.03)
    return min(1.0, score)
