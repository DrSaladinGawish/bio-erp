class MarkupEngine:
    DEFAULT_RULES = {
        "VEN": 0.12,
        "AV": 0.12,
        "CAT": 0.18,
        "DEC": 0.20,
        "TRN": 0.15,
        "STF": 0.10,
        "MRK": 0.25,
        "MISC": 0.12,
    }

    def __init__(self, rules: dict | None = None):
        self.rules = rules or self.DEFAULT_RULES.copy()

    def get_markup(self, category_code: str) -> float:
        return self.rules.get(category_code.upper(), 0.12)

    def calculate_selling_price(self, cost: float, category_code: str) -> float:
        markup = self.get_markup(category_code)
        return round(cost * (1 + markup), 2)

    def calculate_vat(self, amount: float, vat_rate: float = 0.14) -> float:
        return round(amount * vat_rate, 2)

    def extract_vat_from_total(self, total: float, vat_rate: float = 0.14) -> float:
        return round(total * vat_rate / (1 + vat_rate), 2)
