import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple


class MappingEngine:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.mappings = self._load_yaml("mappings.yaml")
        self.coa = self._load_json("chart_of_accounts.json")
        self.clients = self._load_json("client_map.json")
        self.router = self._load_yaml("module_router.yaml")
        self.fx = self._load_json("fx_rates.json")
        self.validation = self._load_yaml("validation_rules.yaml")
        self._coa_index = {a["code"]: a for a in self.coa["accounts"]}
        self._client_keywords: List[Tuple[str, int, str]] = []
        for c in self.clients["clients"]:
            for kw in c["keywords"]:
                self._client_keywords.append((kw.upper(), c["id"], c["type"]))

    def _load_yaml(self, filename: str) -> dict:
        with open(self.config_dir / filename, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def _load_json(self, filename: str) -> dict:
        with open(self.config_dir / filename, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_sub_led_code(self, module: str, keyword: str) -> int:
        if not isinstance(keyword, str):
            keyword = str(keyword) if keyword is not None else ""
        mod_cfg = self.mappings["modules"].get(module, {})
        defaults = mod_cfg.get("sub_led_defaults", {})
        key = keyword.strip().replace(" ", "_").replace(".", "")
        if key in defaults:
            return defaults[key]["code"]
        for k, v in defaults.items():
            if k != "default" and k.upper() in keyword.upper():
                return v["code"]
        return defaults.get("default", {}).get("code", 1001)

    def get_pnr_id(self, module: str, keyword: str) -> int:
        if not isinstance(keyword, str):
            keyword = str(keyword) if keyword is not None else ""
        mod_cfg = self.mappings["modules"].get(module, {})
        defaults = mod_cfg.get("pnr_defaults", {})
        key = keyword.strip().replace(" ", "_").replace(".", "")
        if key in defaults:
            return defaults[key]["id"]
        for k, v in defaults.items():
            if k != "default" and k.upper() in keyword.upper():
                return v["id"]
        return defaults.get("default", {}).get("id", 1000)

    def get_client_id(self, description: str) -> int:
        if not isinstance(description, str):
            description = str(description) if description is not None else ""
        desc_upper = description.upper()
        for kw, cid, ctype in self._client_keywords:
            if kw in desc_upper:
                return cid
        return 999

    def get_fx_rate(self, currency: str, date_str: str) -> float:
        if currency == "EGP":
            return 1.0
        rates = self.fx["rates"].get(currency, {})
        if not rates:
            return 1.0
        sorted_dates = sorted(rates.keys())
        applicable_rate = rates[sorted_dates[0]]
        for d in sorted_dates:
            if d <= date_str:
                applicable_rate = rates[d]
            else:
                break
        return applicable_rate

    def validate_coa_code(self, code: int) -> bool:
        account = self._coa_index.get(code)
        if not account:
            return False
        return account.get("status") == "A"

    def route_gl_trnx(self, description: str, account_code: Optional[str] = None) -> str:
        desc_lower = description.lower()
        router = self.router["gl_trnx_router"]
        for kw in router["route_to_evn"]["description_keywords"]:
            if kw.lower() in desc_lower:
                return "Evn"
        if account_code and any(account_code.startswith(p) for p in router["route_to_evn"]["account_code_prefixes"]):
            return "Evn"
        for kw in router["route_to_env"]["description_keywords"]:
            if kw.lower() in desc_lower:
                return "Env"
        if account_code and any(account_code.startswith(p) for p in router["route_to_env"]["account_code_prefixes"]):
            return "Env"
        return router["default_module"]
