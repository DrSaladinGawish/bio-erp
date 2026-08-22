"""
FAR-GL Chart of Accounts Templates — 9 industry-specific COA templates.
Each template defines accounts with: code, name_en, name_ar, type,
normal_balance, category, is_control.
"""

from typing import Dict, List, Any, Optional
import re

COA_TEMPLATES: Dict[str, List[Dict[str, Any]]] = {

    "generic": [
        {"code": "1000", "name_en": "Current Assets", "type": "asset", "normal_balance": "debit", "category": "current_asset", "is_control": True},
        {"code": "1010", "name_en": "Cash on Hand", "type": "asset", "normal_balance": "debit", "category": "current_asset"},
        {"code": "1020", "name_en": "Cash at Bank", "type": "asset", "normal_balance": "debit", "category": "current_asset"},
        {"code": "1100", "name_en": "Accounts Receivable", "type": "asset", "normal_balance": "debit", "category": "current_asset", "is_control": True},
        {"code": "1101", "name_en": "Trade Receivables", "type": "asset", "normal_balance": "debit", "category": "current_asset"},
        {"code": "1150", "name_en": "Prepaid Expenses", "type": "asset", "normal_balance": "debit", "category": "current_asset"},
        {"code": "1200", "name_en": "Inventory", "type": "asset", "normal_balance": "debit", "category": "current_asset", "is_control": True},
        {"code": "1400", "name_en": "Fixed Assets", "type": "asset", "normal_balance": "debit", "category": "non_current_asset", "is_control": True},
        {"code": "1499", "name_en": "Accumulated Depreciation", "type": "asset", "normal_balance": "credit", "category": "non_current_asset"},
        {"code": "2000", "name_en": "Current Liabilities", "type": "liability", "normal_balance": "credit", "category": "current_liability", "is_control": True},
        {"code": "2100", "name_en": "Accounts Payable", "type": "liability", "normal_balance": "credit", "category": "current_liability", "is_control": True},
        {"code": "2200", "name_en": "VAT Payable", "type": "liability", "normal_balance": "credit", "category": "current_liability"},
        {"code": "2300", "name_en": "Accrued Expenses", "type": "liability", "normal_balance": "credit", "category": "current_liability"},
        {"code": "2400", "name_en": "Short-term Loans", "type": "liability", "normal_balance": "credit", "category": "current_liability"},
        {"code": "2500", "name_en": "Long-term Liabilities", "type": "liability", "normal_balance": "credit", "category": "non_current_liability", "is_control": True},
        {"code": "3000", "name_en": "Equity", "type": "equity", "normal_balance": "credit", "category": "equity", "is_control": True},
        {"code": "3010", "name_en": "Share Capital", "type": "equity", "normal_balance": "credit", "category": "equity"},
        {"code": "3020", "name_en": "Retained Earnings", "type": "equity", "normal_balance": "credit", "category": "equity"},
        {"code": "3030", "name_en": "Current Year Profit/Loss", "type": "equity", "normal_balance": "credit", "category": "equity"},
        {"code": "4000", "name_en": "Revenue", "type": "revenue", "normal_balance": "credit", "category": "revenue", "is_control": True},
        {"code": "4100", "name_en": "Sales Revenue", "type": "revenue", "normal_balance": "credit", "category": "revenue"},
        {"code": "4110", "name_en": "Service Revenue", "type": "revenue", "normal_balance": "credit", "category": "revenue"},
        {"code": "5000", "name_en": "Cost of Sales", "type": "expense", "normal_balance": "debit", "category": "cogs", "is_control": True},
        {"code": "5100", "name_en": "Cost of Goods Sold", "type": "expense", "normal_balance": "debit", "category": "cogs"},
        {"code": "6000", "name_en": "Operating Expenses", "type": "expense", "normal_balance": "debit", "category": "opex", "is_control": True},
        {"code": "6100", "name_en": "Salaries & Wages", "type": "expense", "normal_balance": "debit", "category": "opex"},
        {"code": "6200", "name_en": "Rent Expense", "type": "expense", "normal_balance": "debit", "category": "opex"},
        {"code": "6300", "name_en": "Office Supplies", "type": "expense", "normal_balance": "debit", "category": "opex"},
        {"code": "6400", "name_en": "Marketing & Advertising", "type": "expense", "normal_balance": "debit", "category": "opex"},
        {"code": "6500", "name_en": "Professional Fees", "type": "expense", "normal_balance": "debit", "category": "opex"},
        {"code": "7000", "name_en": "Depreciation & Amortization", "type": "expense", "normal_balance": "debit", "category": "opex"},
        {"code": "8000", "name_en": "Non-Operating Items", "type": "expense", "normal_balance": "debit", "category": "other", "is_control": True},
    ],

    "manufacturing": [
        {"code": "1205", "name_en": "Raw Materials", "type": "asset", "normal_balance": "debit", "category": "current_asset"},
        {"code": "1210", "name_en": "Work in Process", "type": "asset", "normal_balance": "debit", "category": "current_asset"},
        {"code": "1215", "name_en": "Finished Goods", "type": "asset", "normal_balance": "debit", "category": "current_asset"},
        {"code": "8100", "name_en": "Direct Materials Consumed", "type": "expense", "normal_balance": "debit", "category": "cogs"},
        {"code": "8110", "name_en": "Direct Labor", "type": "expense", "normal_balance": "debit", "category": "cogs"},
        {"code": "8120", "name_en": "Manufacturing Overhead", "type": "expense", "normal_balance": "debit", "category": "cogs"},
        {"code": "8130", "name_en": "Quality Control Costs", "type": "expense", "normal_balance": "debit", "category": "cogs"},
        {"code": "8140", "name_en": "Production Variance", "type": "expense", "normal_balance": "debit", "category": "cogs"},
    ],

    "pharma": [
        {"code": "1220", "name_en": "Quarantine Inventory", "type": "asset", "normal_balance": "debit", "category": "current_asset"},
        {"code": "1225", "name_en": "Batch Testing Inventory", "type": "asset", "normal_balance": "debit", "category": "current_asset"},
        {"code": "8200", "name_en": "R&D Expenses", "type": "expense", "normal_balance": "debit", "category": "opex"},
        {"code": "8210", "name_en": "FDA Compliance Costs", "type": "expense", "normal_balance": "debit", "category": "opex"},
        {"code": "8220", "name_en": "GMP Validation Costs", "type": "expense", "normal_balance": "debit", "category": "opex"},
        {"code": "8230", "name_en": "Clinical Trial Costs", "type": "expense", "normal_balance": "debit", "category": "opex"},
        {"code": "8240", "name_en": "Quality Assurance - Pharma", "type": "expense", "normal_balance": "debit", "category": "opex"},
        {"code": "8250", "name_en": "Regulatory Affairs", "type": "expense", "normal_balance": "debit", "category": "opex"},
        {"code": "2260", "name_en": "Rebate & Discount Payable", "type": "liability", "normal_balance": "credit", "category": "current_liability"},
    ],

    "construction": [
        {"code": "1230", "name_en": "Construction Materials", "type": "asset", "normal_balance": "debit", "category": "current_asset"},
        {"code": "1410", "name_en": "Construction Equipment", "type": "asset", "normal_balance": "debit", "category": "non_current_asset"},
        {"code": "1420", "name_en": "Heavy Machinery", "type": "asset", "normal_balance": "debit", "category": "non_current_asset"},
        {"code": "4200", "name_en": "Contract Revenue", "type": "revenue", "normal_balance": "credit", "category": "revenue"},
        {"code": "4210", "name_en": "Progress Billings", "type": "liability", "normal_balance": "credit", "category": "current_liability"},
        {"code": "8300", "name_en": "Contract Costs", "type": "expense", "normal_balance": "debit", "category": "cogs"},
        {"code": "8310", "name_en": "Site Labor Costs", "type": "expense", "normal_balance": "debit", "category": "cogs"},
        {"code": "8320", "name_en": "Equipment Operating Costs", "type": "expense", "normal_balance": "debit", "category": "cogs"},
        {"code": "8330", "name_en": "Subcontractor Costs", "type": "expense", "normal_balance": "debit", "category": "cogs"},
        {"code": "8340", "name_en": "Retention Receivable", "type": "asset", "normal_balance": "debit", "category": "current_asset"},
        {"code": "2350", "name_en": "Retention Payable", "type": "liability", "normal_balance": "credit", "category": "current_liability"},
    ],

    "hospitality": [
        {"code": "1240", "name_en": "F&B Inventory", "type": "asset", "normal_balance": "debit", "category": "current_asset"},
        {"code": "1245", "name_en": "Linens & Uniforms", "type": "asset", "normal_balance": "debit", "category": "current_asset"},
        {"code": "4300", "name_en": "Room Revenue", "type": "revenue", "normal_balance": "credit", "category": "revenue"},
        {"code": "4310", "name_en": "F&B Revenue", "type": "revenue", "normal_balance": "credit", "category": "revenue"},
        {"code": "4320", "name_en": "Banquet Revenue", "type": "revenue", "normal_balance": "credit", "category": "revenue"},
        {"code": "8400", "name_en": "Housekeeping Expenses", "type": "expense", "normal_balance": "debit", "category": "cogs"},
        {"code": "8410", "name_en": "Guest Amenities", "type": "expense", "normal_balance": "debit", "category": "cogs"},
        {"code": "8420", "name_en": "Property Maintenance", "type": "expense", "normal_balance": "debit", "category": "opex"},
        {"code": "8430", "name_en": "Reservation Commission", "type": "expense", "normal_balance": "debit", "category": "selling"},
    ],

    "education": [
        {"code": "4400", "name_en": "Tuition Revenue", "type": "revenue", "normal_balance": "credit", "category": "revenue"},
        {"code": "4410", "name_en": "Registration Fees", "type": "revenue", "normal_balance": "credit", "category": "revenue"},
        {"code": "4420", "name_en": "Research Grant Revenue", "type": "revenue", "normal_balance": "credit", "category": "revenue"},
        {"code": "8500", "name_en": "Faculty Salaries", "type": "expense", "normal_balance": "debit", "category": "opex"},
        {"code": "8510", "name_en": "Campus Operations", "type": "expense", "normal_balance": "debit", "category": "opex"},
        {"code": "8520", "name_en": "Scholarships & Aid", "type": "expense", "normal_balance": "debit", "category": "opex"},
        {"code": "8530", "name_en": "Research Expenses", "type": "expense", "normal_balance": "debit", "category": "opex"},
        {"code": "8540", "name_en": "Library & Learning Resources", "type": "expense", "normal_balance": "debit", "category": "opex"},
    ],

    "nonprofit": [
        {"code": "4500", "name_en": "Donation Revenue - Unrestricted", "type": "revenue", "normal_balance": "credit", "category": "revenue"},
        {"code": "4510", "name_en": "Donation Revenue - Restricted", "type": "revenue", "normal_balance": "credit", "category": "revenue"},
        {"code": "4520", "name_en": "Grant Revenue", "type": "revenue", "normal_balance": "credit", "category": "revenue"},
        {"code": "3040", "name_en": "Net Assets - Unrestricted", "type": "equity", "normal_balance": "credit", "category": "equity"},
        {"code": "3050", "name_en": "Net Assets - Restricted", "type": "equity", "normal_balance": "credit", "category": "equity"},
        {"code": "3060", "name_en": "Net Assets - Permanently Restricted", "type": "equity", "normal_balance": "credit", "category": "equity"},
        {"code": "8600", "name_en": "Program Expenses", "type": "expense", "normal_balance": "debit", "category": "opex"},
        {"code": "8610", "name_en": "Grant Disbursements", "type": "expense", "normal_balance": "debit", "category": "opex"},
        {"code": "8620", "name_en": "Fundraising Costs", "type": "expense", "normal_balance": "debit", "category": "selling"},
        {"code": "8630", "name_en": "Administrative Overhead", "type": "expense", "normal_balance": "debit", "category": "opex"},
    ],

    "agriculture": [
        {"code": "1250", "name_en": "Seeds & Planting Materials", "type": "asset", "normal_balance": "debit", "category": "current_asset"},
        {"code": "1255", "name_en": "Fertilizers & Chemicals", "type": "asset", "normal_balance": "debit", "category": "current_asset"},
        {"code": "1260", "name_en": "Livestock Inventory", "type": "asset", "normal_balance": "debit", "category": "current_asset"},
        {"code": "1265", "name_en": "Harvested Crops", "type": "asset", "normal_balance": "debit", "category": "current_asset"},
        {"code": "1430", "name_en": "Agricultural Land", "type": "asset", "normal_balance": "debit", "category": "non_current_asset"},
        {"code": "1440", "name_en": "Farm Machinery", "type": "asset", "normal_balance": "debit", "category": "non_current_asset"},
        {"code": "1450", "name_en": "Irrigation Systems", "type": "asset", "normal_balance": "debit", "category": "non_current_asset"},
        {"code": "4600", "name_en": "Crop Sales Revenue", "type": "revenue", "normal_balance": "credit", "category": "revenue"},
        {"code": "8700", "name_en": "Planting & Cultivation", "type": "expense", "normal_balance": "debit", "category": "cogs"},
        {"code": "8710", "name_en": "Irrigation & Water", "type": "expense", "normal_balance": "debit", "category": "cogs"},
        {"code": "8720", "name_en": "Seasonal Labor", "type": "expense", "normal_balance": "debit", "category": "cogs"},
        {"code": "8730", "name_en": "Crop Protection", "type": "expense", "normal_balance": "debit", "category": "cogs"},
        {"code": "8740", "name_en": "Harvesting Costs", "type": "expense", "normal_balance": "debit", "category": "cogs"},
    ],

    "services": [
        {"code": "4150", "name_en": "Consulting Revenue", "type": "revenue", "normal_balance": "credit", "category": "revenue"},
        {"code": "4160", "name_en": "Retainer Revenue", "type": "revenue", "normal_balance": "credit", "category": "revenue"},
        {"code": "4170", "name_en": "Project Revenue", "type": "revenue", "normal_balance": "credit", "category": "revenue"},
        {"code": "8800", "name_en": "Consultant Costs", "type": "expense", "normal_balance": "debit", "category": "cogs"},
        {"code": "8810", "name_en": "Subcontractor Professional", "type": "expense", "normal_balance": "debit", "category": "cogs"},
        {"code": "8820", "name_en": "Travel & Expense - Billable", "type": "expense", "normal_balance": "debit", "category": "cogs"},
    ],
}


# Account type configs: which range maps to which type
ACCOUNT_TYPE_RANGES = {
    (1000, 1999): ("asset", "debit"),
    (2000, 2999): ("liability", "credit"),
    (3000, 3999): ("equity", "credit"),
    (4000, 4999): ("revenue", "credit"),
    (5000, 5999): ("expense", "debit"),
    (6000, 9999): ("expense", "debit"),
}


def detect_template_from_text(text: str) -> str:
    """Auto-detect industry COA template from document text."""
    text_lower = text.lower()
    scores = {}
    for industry in COA_TEMPLATES:
        keywords = INDUSTRY_KEYWORDS.get(industry, [industry])
        score = sum(2 if f" {kw} " in f" {text_lower} " else (1 if kw in text_lower else 0) for kw in keywords)
        if score > 0:
            scores[industry] = score
    if scores:
        return max(scores, key=scores.get)
    return "generic"


INDUSTRY_KEYWORDS = {
    "manufacturing": ["manufacturing", "factory", "production", "bom", "work order", "mrp", "shop floor"],
    "pharma": ["pharma", "pharmaceutical", "fda", "gmp", "clinical", "batch", "drug", "medicine"],
    "construction": ["construction", "contractor", "subcontractor", "project", "building", "civil", "retention"],
    "hospitality": ["hotel", "resort", "restaurant", "hospitality", "catering", "banquet", "lodging"],
    "education": ["school", "university", "education", "college", "academy", "tuition", "student"],
    "nonprofit": ["nonprofit", "ngo", "charity", "foundation", "donation", "grant", "volunteer"],
    "agriculture": ["agriculture", "farm", "crop", "livestock", "irrigation", "harvest", "poultry"],
    "services": ["consulting", "services", "professional", "retainer", "project-based", "timesheet"],
}


def merge_templates(base_industry: str, additional_industries: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Merge multiple industry templates into a single COA."""
    accounts: Dict[str, Dict[str, Any]] = {}
    base = COA_TEMPLATES.get(base_industry, COA_TEMPLATES["generic"])
    for a in base:
        accounts[a["code"]] = dict(a)

    if additional_industries:
        for ind in additional_industries:
            extra = COA_TEMPLATES.get(ind, [])
            for a in extra:
                if a["code"] not in accounts:
                    accounts[a["code"]] = dict(a)

    return sorted(accounts.values(), key=lambda x: x["code"])


def get_default_accounts(industry: str = "generic") -> List[Dict[str, Any]]:
    """Get the full merged COA for an industry (generic base + industry-specific)."""
    return merge_templates(industry)


def get_account_normal_balance(code: str) -> str:
    """Determine normal balance from account code range."""
    code_int = int(code)
    for (lo, hi), (_, normal) in ACCOUNT_TYPE_RANGES.items():
        if lo <= code_int <= hi:
            return normal
    return "debit"


def get_account_type(code: str) -> str:
    """Determine account type from code range."""
    code_int = int(code)
    for (lo, hi), (atype, _) in ACCOUNT_TYPE_RANGES.items():
        if lo <= code_int <= hi:
            return atype
    return "expense"
