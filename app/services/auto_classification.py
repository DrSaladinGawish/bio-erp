from difflib import SequenceMatcher


class AutoClassificationEngine:
    KEYWORD_RULES = {
        "venue": {"category_code": "VEN", "confidence": 0.9},
        "hall": {"category_code": "VEN", "confidence": 0.8},
        "conference room": {"category_code": "VEN", "confidence": 0.85},
        "hotel": {"category_code": "VEN", "confidence": 0.7},
        "audio": {"category_code": "AV", "confidence": 0.9},
        "visual": {"category_code": "AV", "confidence": 0.9},
        "sound": {"category_code": "AV", "confidence": 0.85},
        "speaker": {"category_code": "AV", "confidence": 0.8},
        "microphone": {"category_code": "AV", "confidence": 0.9},
        "projector": {"category_code": "AV", "confidence": 0.9},
        "screen": {"category_code": "AV", "confidence": 0.8},
        "lighting": {"category_code": "AV", "confidence": 0.85},
        "catering": {"category_code": "CAT", "confidence": 0.95},
        "food": {"category_code": "CAT", "confidence": 0.9},
        "beverage": {"category_code": "CAT", "confidence": 0.9},
        "meal": {"category_code": "CAT", "confidence": 0.85},
        "buffet": {"category_code": "CAT", "confidence": 0.9},
        "decoration": {"category_code": "DEC", "confidence": 0.95},
        "decor": {"category_code": "DEC", "confidence": 0.9},
        "furniture": {"category_code": "DEC", "confidence": 0.8},
        "flowers": {"category_code": "DEC", "confidence": 0.85},
        "transport": {"category_code": "TRN", "confidence": 0.9},
        "transportation": {"category_code": "TRN", "confidence": 0.9},
        "bus": {"category_code": "TRN", "confidence": 0.85},
        "car rental": {"category_code": "TRN", "confidence": 0.85},
        "staff": {"category_code": "STF", "confidence": 0.9},
        "personnel": {"category_code": "STF", "confidence": 0.85},
        "labor": {"category_code": "STF", "confidence": 0.8},
        "hostess": {"category_code": "STF", "confidence": 0.85},
        "marketing": {"category_code": "MRK", "confidence": 0.9},
        "advertising": {"category_code": "MRK", "confidence": 0.85},
        "printing": {"category_code": "MRK", "confidence": 0.85},
        "banner": {"category_code": "MRK", "confidence": 0.9},
        "signage": {"category_code": "MRK", "confidence": 0.85},
        "giveaway": {"category_code": "MRK", "confidence": 0.8},
        "gift": {"category_code": "MRK", "confidence": 0.75},
    }

    SUBCATEGORY_KEYWORDS = {
        "VEN": {
            "exhibition": "exhibition_hall",
            "conference": "conference_room",
            "hotel": "hotel_ballroom",
            "outdoor": "outdoor_space",
        },
        "AV": {
            "sound": "sound_system",
            "lighting": "stage_lighting",
            "projection": "projection",
            "video": "video_production",
        },
        "CAT": {
            "breakfast": "breakfast",
            "lunch": "lunch",
            "dinner": "dinner",
            "refreshment": "refreshment",
        },
        "DEC": {
            "stage": "stage_design",
            "entrance": "entrance_decor",
            "table": "table_decor",
            "backdrop": "backdrop",
        },
        "TRN": {
            "sedan": "sedan",
            "bus": "bus",
            "van": "van",
            "limousine": "limousine",
        },
    }

    BOOTH_TEMPLATES = {
        "BASIC": {
            "name": "Basic Booth",
            "markup_multiplier": 1.0,
            "line_items": ["Booth Structure", "Basic Lighting", "1 Table", "2 Chairs"],
        },
        "PREMIUM": {
            "name": "Premium Booth",
            "markup_multiplier": 1.15,
            "line_items": [
                "Premium Structure",
                "LED Lighting",
                "Reception Desk",
                "4 Chairs",
                "Carpet",
                "Branding Panel",
            ],
        },
        "VIP": {
            "name": "VIP Booth",
            "markup_multiplier": 1.25,
            "line_items": [
                "VIP Structure",
                "Smart Lighting",
                "Reception Desk",
                "Lounge Seating",
                "Premium Carpet",
                "Digital Signage",
                "Custom Branding",
                "Hospitality Station",
            ],
        },
    }

    def classify(self, description: str) -> dict:
        desc_lower = description.lower()
        best_match = {
            "category_code": "MISC",
            "confidence": 0.0,
            "matched_keyword": None,
        }

        for keyword, rule in self.KEYWORD_RULES.items():
            SequenceMatcher(None, keyword, desc_lower).ratio()
            if keyword in desc_lower:
                rule["confidence"]

            if keyword in desc_lower and rule["confidence"] > best_match["confidence"]:
                best_match = {
                    "category_code": rule["category_code"],
                    "confidence": rule["confidence"],
                    "matched_keyword": keyword,
                }

        return best_match

    def classify_subcategory(self, category_code: str, description: str) -> str | None:
        if category_code not in self.SUBCATEGORY_KEYWORDS:
            return None
        desc_lower = description.lower()
        for keyword, subcat in self.SUBCATEGORY_KEYWORDS[category_code].items():
            if keyword in desc_lower:
                return subcat
        return None

    def get_booth_template(self, tier: str) -> dict | None:
        return self.BOOTH_TEMPLATES.get(tier.upper())

    def get_suggestions(self, partial: str, limit: int = 5) -> list[dict]:
        partial_lower = partial.lower()
        suggestions = []
        for keyword, rule in self.KEYWORD_RULES.items():
            if keyword.startswith(partial_lower) or partial_lower in keyword:
                suggestions.append(
                    {
                        "keyword": keyword,
                        "category": rule["category_code"],
                        "confidence": rule["confidence"],
                    }
                )
        return sorted(suggestions, key=lambda x: x["confidence"], reverse=True)[:limit]
