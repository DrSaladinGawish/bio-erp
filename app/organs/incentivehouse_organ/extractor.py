import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from app.organs.incentivehouse_organ.mapper import MappingEngine


class TransactionExtractor:
    def __init__(self, file_path: str, module: str, mapper: MappingEngine):
        self.file_path = Path(file_path)
        self.module = module
        self.mapper = mapper
        self.df: Optional[pd.DataFrame] = None
        self.profile: Dict[str, Any] = {}
        self.validation_errors: List[Dict] = []
        self.mapped_df: Optional[pd.DataFrame] = None

    def load_excel(self, header_row: Optional[int] = None, sheet_name: Optional[str] = None) -> pd.DataFrame:
        xl = pd.ExcelFile(self.file_path)
        if sheet_name:
            sheet = sheet_name
        else:
            sheet = self._detect_main_sheet(xl)
        if header_row is None:
            for hr in range(0, 5):
                try:
                    df = pd.read_excel(xl, sheet_name=sheet, header=hr)
                    if len(df.columns) >= 5 and len(df) > 0:
                        self.df = df
                        break
                except Exception:
                    continue
        else:
            self.df = pd.read_excel(xl, sheet_name=sheet, header=header_row)
        if self.df is None:
            raise ValueError(f"Could not load data from {self.file_path}")
        self.df.columns = [str(c).strip().replace(" ", "_").replace(".", "").replace("#", "").upper() for c in self.df.columns]
        return self.df

    def _detect_main_sheet(self, xl: pd.ExcelFile) -> str:
        best_sheet = xl.sheet_names[0]
        best_score = -1
        for s in xl.sheet_names:
            try:
                df = pd.read_excel(xl, sheet_name=s, nrows=1000)
                score = len(df) * len(df.columns)
                if score > best_score and len(df.columns) >= 5:
                    best_score = score
                    best_sheet = s
            except Exception:
                continue
        return best_sheet

    def _find_column(self, df: pd.DataFrame, candidates: List[str], contains: bool = False) -> Optional[str]:
        cols = {c.upper(): c for c in df.columns}
        if not contains:
            for cand in candidates:
                key = cand.upper()
                if key in cols:
                    return cols[key]
        for cand in candidates:
            key = cand.upper()
            for col_name, orig_name in cols.items():
                if key in col_name:
                    return orig_name
        return None

    def _find_multi_column(self, df: pd.DataFrame, candidate_groups: List[List[str]]) -> Optional[str]:
        for group in candidate_groups:
            col = self._find_column(df, group)
            if col:
                return col
        return None

    def profile_data(self) -> Dict[str, Any]:
        if self.df is None:
            raise ValueError("Data not loaded. Call load_excel() first.")
        amt_cols = [
            c for c in self.df.columns
            if any(x in c for x in ["AMOUNT", "AMT", "VALUE", "DEBIT", "CREDIT", "EGP"])
        ]
        date_cols = [c for c in self.df.columns if any(x in c for x in ["DATE", "DT", "TIME"])]
        profile = {
            "file_name": self.file_path.name,
            "module": self.module,
            "row_count": len(self.df),
            "column_count": len(self.df.columns),
            "columns": list(self.df.columns),
            "null_counts": self.df.isnull().sum().to_dict(),
            "data_types": self.df.dtypes.astype(str).to_dict(),
            "amount_columns": amt_cols,
            "date_columns": date_cols,
        }
        if date_cols:
            for dc in date_cols:
                try:
                    self.df[dc] = pd.to_datetime(self.df[dc], errors="coerce")
                    valid_dates = self.df[dc].dropna()
                    if len(valid_dates) > 0:
                        profile["date_range"] = {
                            "column": dc,
                            "min": valid_dates.min().strftime("%Y-%m-%d"),
                            "max": valid_dates.max().strftime("%Y-%m-%d"),
                        }
                        break
                except Exception:
                    continue
        for ac in amt_cols:
            try:
                numeric = pd.to_numeric(self.df[ac], errors="coerce")
                profile[f"sum_{ac.lower()}"] = numeric.sum()
                profile[f"count_{ac.lower()}"] = numeric.notna().sum()
            except Exception:
                pass
        self.profile = profile
        return profile

    def apply_mapping(self) -> pd.DataFrame:
        if self.df is None:
            raise ValueError("Data not loaded.")
        df = self.df.copy()

        # --- Description ---
        desc_col = self._find_column(df, [
            "DESCRIPTION", "DESC", "DETAILS", "NARRATION", "REMARKS", "MEMO",
            "ENTRY_NARRATION", "ACC_NAME", "SUB_LED_NAME", "LINE_ITEM",
        ], contains=True)
        if desc_col:
            df["DESCRIPTION_NORM"] = df[desc_col].fillna("").astype(str).str.strip()
        else:
            remaining = [c for c in df.columns if c not in (
                self._find_column(df, ["TRANSACTION_DATE", "DATE"], contains=True) or "",
                self._find_column(df, ["AMOUNT", "AMT", "VALUE", "EGP"], contains=True) or "",
                self._find_column(df, ["CURRENCY", "CUR"], contains=True) or "",
                self._find_column(df, ["RATE", "RAT", "CON_RAT", "FX"], contains=True) or "",
                self._find_column(df, ["ID", "TRANS_ID", "TRANSACTION_ID", "REF", "VOUCHER", "NUM", "TNX", "TRN"], contains=True) or "",
            )]
            if remaining:
                df["DESCRIPTION_NORM"] = df[remaining[0]].fillna("").astype(str).str.strip()
            else:
                df["DESCRIPTION_NORM"] = ""

        # --- Sub Led Code: try numeric field first, then map from description ---
        sub_led_col = self._find_column(df, ["SUB_LED", "DR_SUB_LED", "CR_SUB_LED"], contains=True)
        if sub_led_col:
            numeric_sub = pd.to_numeric(df[sub_led_col], errors="coerce")
            if numeric_sub.notna().sum() > len(df) * 0.5:
                df["SUB_LED_CODE"] = numeric_sub.fillna(0).astype(int)
            else:
                df["SUB_LED_CODE"] = df["DESCRIPTION_NORM"].apply(
                    lambda d: self.mapper.get_sub_led_code(self.module, d)
                )
        else:
            df["SUB_LED_CODE"] = df["DESCRIPTION_NORM"].apply(
                lambda d: self.mapper.get_sub_led_code(self.module, d)
            )

        df["PNR_ID"] = df["DESCRIPTION_NORM"].apply(lambda d: self.mapper.get_pnr_id(self.module, d))
        df["CLIENT_ID"] = df["DESCRIPTION_NORM"].apply(self.mapper.get_client_id)

        # --- Currency ---
        curr_col = self._find_column(df, ["CURRENCY", "CUR_NMN", "CURR", "CCY", "CUR"], contains=True)
        if curr_col:
            df["CURRENCY"] = df[curr_col].fillna("EGP").astype(str).str.upper().str.strip()
        else:
            df["CURRENCY"] = self._infer_currency(df)

        # --- FX Rate ---
        rate_col = self._find_column(df, ["CON_RAT", "RATE", "FX_RATE", "EXCHANGE", "RAT"], contains=True)
        date_col = self._find_column(df, ["TRANSACTION_DATE", "DATE", "DT"], contains=True)
        if date_col:
            df["TRANSACTION_DATE"] = pd.to_datetime(df[date_col], errors="coerce")
        if rate_col:
            df["FX_RATE"] = pd.to_numeric(df[rate_col], errors="coerce").fillna(1.0)
        elif date_col:
            df["FX_RATE"] = df.apply(
                lambda r: self.mapper.get_fx_rate(
                    r.get("CURRENCY", "EGP"),
                    r["TRANSACTION_DATE"].strftime("%Y-%m-%d") if pd.notna(r.get("TRANSACTION_DATE")) else "2026-01-01",
                ),
                axis=1,
            )
        else:
            df["FX_RATE"] = 1.0

        # --- Amount in EGP ---
        amt_col = self._find_column(df, [
            "ORI_TNX_AMT", "AMOUNT", "VALUE", "EGP_AMOUNT", "LOCAL_AMOUNT",
            "DR_AMT_EGP", "CR_AMT_EGP", "TNX_AMT",
        ], contains=True)
        if amt_col:
            numeric_amt = pd.to_numeric(df[amt_col], errors="coerce")
            # If primary amount col is sparse, try DR_AMT_EGP or DR-CR columns
            if numeric_amt.notna().sum() < len(df) * 0.5:
                dr_egp = self._find_column(df, ["DR_AMT_EGP"], contains=True)
                cr_egp = self._find_column(df, ["CR_AMT_EGP"], contains=True)
                if dr_egp and cr_egp:
                    dr = pd.to_numeric(df[dr_egp], errors="coerce").fillna(0)
                    cr = pd.to_numeric(df[cr_egp], errors="coerce").fillna(0)
                    df["AMOUNT_EGP"] = (dr - cr)
                    df["DEBIT_AMOUNT"] = dr
                    df["CREDIT_AMOUNT"] = cr
                elif dr_egp:
                    df["AMOUNT_EGP"] = pd.to_numeric(df[dr_egp], errors="coerce")
                else:
                    df["AMOUNT_EGP"] = numeric_amt * df["FX_RATE"]
            else:
                df["AMOUNT_EGP"] = numeric_amt * df["FX_RATE"]
        else:
            debit_col = self._find_column(df, ["DEBIT", "DR", "OUT"], contains=True)
            credit_col = self._find_column(df, ["CREDIT", "CR", "IN"], contains=True)
            if debit_col and credit_col:
                df["DEBIT_AMOUNT"] = pd.to_numeric(df[debit_col], errors="coerce").fillna(0)
                df["CREDIT_AMOUNT"] = pd.to_numeric(df[credit_col], errors="coerce").fillna(0)
                df["AMOUNT_EGP"] = (df["DEBIT_AMOUNT"] - df["CREDIT_AMOUNT"]) * df["FX_RATE"]
            else:
                df["AMOUNT_EGP"] = 0.0

        # --- Transaction / Reference ID ---
        tid_col = self._find_column(df, [
            "TRANSACTION_ID", "TRANSACTION_REFERENCE", "REFERENCE", "TNX_NUM",
            "TRN_NUM", "ID", "TRANS_ID", "VOUCHER", "MANUAL_DOC",
        ], contains=True)
        if tid_col:
            df["TRANSACTION_ID"] = df[tid_col].astype(str)
        else:
            df["TRANSACTION_ID"] = [f"{self.module}_{i:08d}" for i in range(len(df))]

        # --- Cost Center (for routing) ---
        cost_col = self._find_column(df, ["COST_CENTER", "COST_CENTRE", "CC"], contains=True)
        if cost_col:
            df["COST_CENTER"] = df[cost_col].astype(str)

        # --- Additional fields for Sal ---
        tax_code_col = self._find_column(df, ["TAX_CODE", "TAX"], contains=True)
        if tax_code_col:
            df["TAX_CODE"] = df[tax_code_col].astype(str)
        tax_amt_col = self._find_column(df, ["TAX_AMOUNT", "TAX_AMT"], contains=True)
        if tax_amt_col:
            df["TAX_AMOUNT"] = pd.to_numeric(df[tax_amt_col], errors="coerce")

        # --- Original raw amount for reference ---
        if amt_col:
            df["ORIGINAL_AMOUNT"] = pd.to_numeric(df[amt_col], errors="coerce")

        # --- Transaction Type ---
        trx_type_col = self._find_column(df, ["TRNX_TYPE", "TXN_TYPE", "TRNX TYPE", "TRX_TYPE", "TRX_SOURCE"], contains=True)
        if trx_type_col:
            df["TRANSACTION_TYPE"] = df[trx_type_col].astype(str).str.strip()
        else:
            df["TRANSACTION_TYPE"] = self.module

        df["MODULE_SOURCE"] = self.module
        self.mapped_df = df
        return df

    def _infer_currency(self, df: pd.DataFrame) -> pd.Series:
        acc_col = self._find_column(df, ["ACCOUNT", "ACC", "BANK", "ACCOUNT_CODE"], contains=True)
        if acc_col:
            s = df[acc_col].astype(str).str.upper()
            return s.apply(lambda x: "USD" if "USD" in x else ("EUR" if "EUR" in x else "EGP"))
        return pd.Series(["EGP"] * len(df))
