import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
from app.organs.incentivehouse_organ.mapper import MappingEngine


class ProtocellValidator:
    def __init__(self, mapper: MappingEngine):
        self.mapper = mapper
        self.rules = mapper.validation["protocell"]
        self.errors: List[Dict[str, Any]] = []

    def validate(self, df: pd.DataFrame, module: str) -> List[Dict[str, Any]]:
        self.errors = []
        self._rule_1_mandatory_fields(df, module)
        self._rule_2_sub_led_validation(df, module)
        self._rule_3_pnr_validation(df, module)
        self._rule_4_dual_entry_balance(df, module)
        self._rule_5_date_validation(df, module)
        self._rule_6_amount_validation(df, module)
        self._rule_7_duplicate_detection(df, module)
        return self.errors

    def _rule_1_mandatory_fields(self, df: pd.DataFrame, module: str):
        req = self.rules["rule_1_mandatory_fields"]["required"]
        min_desc = self.rules["rule_1_mandatory_fields"]["min_description_length"]
        for idx, row in df.iterrows():
            for field in req:
                val = row.get(field)
                if pd.isna(val) or str(val).strip() == "":
                    self.errors.append({
                        "row_index": int(idx),
                        "rule": "RULE_1_MANDATORY_FIELDS",
                        "field": field,
                        "message": f"Mandatory field '{field}' is missing or empty.",
                        "severity": "ERROR",
                    })
            desc = str(row.get("DESCRIPTION_NORM", "")).strip()
            if len(desc) < min_desc:
                self.errors.append({
                    "row_index": int(idx),
                    "rule": "RULE_1_MANDATORY_FIELDS",
                    "field": "description",
                    "message": f"Description too short ({len(desc)} chars, min {min_desc}).",
                    "severity": "WARNING",
                })

    def _rule_2_sub_led_validation(self, df: pd.DataFrame, module: str):
        for idx, row in df.iterrows():
            code = row.get("SUB_LED_CODE")
            if pd.isna(code):
                continue
            if not self.mapper.validate_coa_code(int(code)):
                self.errors.append({
                    "row_index": int(idx),
                    "rule": "RULE_2_SUB_LED_VALIDATION",
                    "field": "SUB_LED_CODE",
                    "message": f"Sub_Led_Code {code} not found in Chart of Accounts or inactive.",
                    "severity": "ERROR",
                })

    def _rule_3_pnr_validation(self, df: pd.DataFrame, module: str):
        for idx, row in df.iterrows():
            pnr = row.get("PNR_ID")
            if pd.isna(pnr) or int(pnr) == 1000:
                self.errors.append({
                    "row_index": int(idx),
                    "rule": "RULE_3_PNR_VALIDATION",
                    "field": "PNR_ID",
                    "message": f"PNR_ID {pnr} is unclassified (default). Review mapping.",
                    "severity": "WARNING",
                })

    def _rule_4_dual_entry_balance(self, df: pd.DataFrame, module: str):
        if "DEBIT_AMOUNT" in df.columns and "CREDIT_AMOUNT" in df.columns:
            for idx, row in df.iterrows():
                dr = float(row.get("DEBIT_AMOUNT", 0) or 0)
                cr = float(row.get("CREDIT_AMOUNT", 0) or 0)
                computed_net = dr - cr
                actual_amt = float(row.get("AMOUNT_EGP", 0) or 0)
                if abs(computed_net - actual_amt) > 0.01:
                    self.errors.append({
                        "row_index": int(idx),
                        "rule": "RULE_4_DUAL_ENTRY_BALANCE",
                        "field": "amount",
                        "message": f"Dual-entry imbalance: DR={dr}, CR={cr}, Net={computed_net}, Amount_EGP={actual_amt}",
                        "severity": "ERROR",
                    })

    def _rule_5_date_validation(self, df: pd.DataFrame, module: str):
        min_date = datetime.strptime(self.rules["rule_5_date_validation"]["min_date"], "%Y-%m-%d")
        max_date = datetime.now()
        for idx, row in df.iterrows():
            dt = row.get("TRANSACTION_DATE")
            if pd.isna(dt):
                continue
            if isinstance(dt, str):
                try:
                    dt = datetime.strptime(dt, "%Y-%m-%d")
                except ValueError:
                    self.errors.append({
                        "row_index": int(idx),
                        "rule": "RULE_5_DATE_VALIDATION",
                        "field": "TRANSACTION_DATE",
                        "message": f"Invalid date format: {dt}",
                        "severity": "ERROR",
                    })
                    continue
            if dt > max_date:
                self.errors.append({
                    "row_index": int(idx),
                    "rule": "RULE_5_DATE_VALIDATION",
                    "field": "TRANSACTION_DATE",
                    "message": f"Future date: {dt.strftime('%Y-%m-%d')}",
                    "severity": "ERROR",
                })
            if dt < min_date:
                self.errors.append({
                    "row_index": int(idx),
                    "rule": "RULE_5_DATE_VALIDATION",
                    "field": "TRANSACTION_DATE",
                    "message": f"Date before company inception: {dt.strftime('%Y-%m-%d')}",
                    "severity": "ERROR",
                })

    def _rule_6_amount_validation(self, df: pd.DataFrame, module: str):
        max_amt = self.rules["rule_6_amount_validation"]["max_without_approval_egp"]
        for idx, row in df.iterrows():
            amt = row.get("AMOUNT_EGP")
            if pd.isna(amt):
                continue
            amt = float(amt)
            if amt == 0:
                self.errors.append({
                    "row_index": int(idx),
                    "rule": "RULE_6_AMOUNT_VALIDATION",
                    "field": "AMOUNT_EGP",
                    "message": "Zero-amount transaction.",
                    "severity": "ERROR",
                })
            if abs(amt) > max_amt:
                self.errors.append({
                    "row_index": int(idx),
                    "rule": "RULE_6_AMOUNT_VALIDATION",
                    "field": "AMOUNT_EGP",
                    "message": f"Amount {abs(amt):,.2f} EGP exceeds {max_amt:,.0f} threshold. Manager approval required.",
                    "severity": "WARNING",
                })

    def _rule_7_duplicate_detection(self, df: pd.DataFrame, module: str):
        key_fields = self.rules["rule_7_duplicate_detection"]["composite_key"]
        subset = [f for f in key_fields if f in df.columns]
        if not subset:
            return
        dups = df[df.duplicated(subset=subset, keep=False)]
        for idx in dups.index:
            row_data = dups.loc[idx, subset].to_dict()
            self.errors.append({
                "row_index": int(idx),
                "rule": "RULE_7_DUPLICATE_DETECTION",
                "field": "composite_key",
                "message": f"Potential duplicate on {subset}: {row_data}",
                "severity": "WARNING",
            })
