"""
Production Transaction Agent — Incentive House ERP
Wraps the Protocell extraction → mapping → validation → staging pipeline
as a callable agent for batch Excel transaction processing.
"""
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ── Agent Domain Types ──

@dataclass
class ExtractionContext:
    file_path: str
    module: str
    sheet_name: str | None = None
    header_row: int | None = None
    batch_size: int = 500
    dry_run: bool = True

@dataclass
class AgentManifest:
    agent_id: str
    started_at: str
    module: str
    source_file: str
    total_rows: int = 0
    passed: int = 0
    warnings: int = 0
    failed: int = 0
    staged: int = 0
    errors: list = field(default_factory=list)
    summary: str = ""

class ProductionTrxAgent:
    """
    Production Transaction Agent for bulk Excel extraction.
    Reads source Excel → auto-detects columns → maps (Sub_Led_Code, PNR_ID,
    Client_ID, FX) → validates (7 protocell rules) → stages to *__staging tables.
    """

    def __init__(self, db: Session, config_dir: str | Path = None):
        self.db = db
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent / "config"
        self.manifest: AgentManifest | None = None
        self._engine = None
        self._load_config()

    def _load_config(self):
        """Lazy-load Protocell engines from config files."""
        try:
            from app.organs.incentivehouse_organ.mapper import MappingEngine
            self._mapper = MappingEngine(str(self.config_dir))
        except ImportError:
            logger.warning("MappingEngine not available, using inline fallback")
            self._mapper = None

    @property
    def mapper(self):
        if self._mapper is None:
            from app.organs.incentivehouse_organ.mapper import MappingEngine
            self._mapper = MappingEngine(str(self.config_dir))
        return self._mapper

    def execute(self, ctx: ExtractionContext) -> AgentManifest:
        """
        Execute the full extraction pipeline for a single module/file.
        Returns an AgentManifest with results and audit trail.
        """
        agent_id = f"trx_{uuid.uuid4().hex[:12]}"
        started_at = datetime.now().isoformat()
        manifest = AgentManifest(
            agent_id=agent_id,
            started_at=started_at,
            module=ctx.module,
            source_file=ctx.file_path,
        )

        try:
            # Step 1: Extract
            extractor = self._get_extractor(ctx)
            df = extractor.load_excel(ctx.header_row, ctx.sheet_name)
            df = extractor.profile_data()
            manifest.total_rows = len(df)

            # Step 2: Map
            mapped = extractor.apply_mapping(ctx.module)

            # Step 3: Validate
            validator = self._get_validator()
            errors = validator.validate(mapped, ctx.module)

            # Classify errors
            for e in errors:
                if e["severity"] == "WARNING":
                    manifest.warnings += 1
                else:
                    manifest.failed += 1
                manifest.errors.append(e)

            manifest.passed = manifest.total_rows - manifest.warnings - manifest.failed

            # Step 4: Stage (unless dry_run)
            if not ctx.dry_run:
                staged = self._stage_batch(mapped, ctx.module, agent_id, ctx.batch_size)
                manifest.staged = staged
                manifest.summary = (
                    f"{ctx.module}: {staged} rows staged, "
                    f"{manifest.passed} pass / {manifest.warnings} warn / {manifest.failed} fail"
                )
            else:
                manifest.summary = (
                    f"{ctx.module} [DRY-RUN]: "
                    f"{manifest.passed} pass / {manifest.warnings} warn / {manifest.failed} fail"
                )

            # Audit log
            self._write_audit_log(agent_id, ctx, manifest)

        except Exception as exc:
            logger.exception("ProductionTrxAgent execution failed")
            manifest.errors.append({
                "rule": "AGENT_ERROR",
                "severity": "CRITICAL",
                "message": str(exc),
            })
            manifest.summary = f"FAILED: {exc}"

        self.manifest = manifest
        return manifest

    def _get_extractor(self, ctx: ExtractionContext):
        from app.organs.incentivehouse_organ.extractor import TransactionExtractor
        return TransactionExtractor(ctx.file_path, ctx.module, self.mapper)

    def _get_validator(self):
        from app.organs.incentivehouse_organ.validator import ProtocellValidator
        return ProtocellValidator(self.mapper)

    def _stage_batch(self, df: pd.DataFrame, module: str, agent_id: str, batch_size: int) -> int:
        staged = 0
        table = f"{module.lower()}_staging"

        for start in range(0, len(df), batch_size):
            batch = df.iloc[start:start + batch_size]
            for _, row in batch.iterrows():
                try:
                    self.db.execute(
                        text(f"""
                            INSERT INTO {table}
                            (agent_id, transaction_id, transaction_date, account_code,
                             description, debit_amount, credit_amount, currency,
                             exchange_rate, sub_led_code, pnr_id, client_id,
                             cost_center, validation_status, validation_errors,
                             source_file, source_row)
                            VALUES (
                                :agent_id, :tid, :tdate, :acc_code,
                                :desc, :debit, :credit, :curr,
                                :fx_rate, :sub_led, :pnr, :client,
                                :cost_center, :val_status, :val_errors,
                                :src_file, :src_row
                            )
                        """),
                        {
                            "agent_id": agent_id,
                            "tid": str(row.get("TRANSACTION_ID", "")),
                            "tdate": str(row.get("TRANSACTION_DATE", "")),
                            "acc_code": str(row.get("ACCOUNT_CODE", "")),
                            "desc": str(row.get("DESCRIPTION", "")),
                            "debit": float(row.get("DEBIT_AMOUNT", 0)),
                            "credit": float(row.get("CREDIT_AMOUNT", 0)),
                            "curr": str(row.get("CURRENCY", "EGP")),
                            "fx_rate": float(row.get("EXCHANGE_RATE", 1.0)),
                            "sub_led": int(row.get("SUB_LED_CODE", 0)),
                            "pnr": int(row.get("PNR_ID", 0)),
                            "client": int(row.get("CLIENT_ID", 0)),
                            "cost_center": str(row.get("COST_CENTER", "")),
                            "val_status": str(row.get("VALIDATION_STATUS", "PASS")),
                            "val_errors": json.dumps(row.get("VALIDATION_ERRORS", [])),
                            "src_file": Path(self.manifest.source_file).name if self.manifest else "",
                            "src_row": int(row.get("SOURCE_ROW", 0)),
                        },
                    )
                    staged += 1
                except Exception as exc:
                    logger.warning("Row stage failed: %s", exc)
            self.db.commit()

        return staged

    def _write_audit_log(self, agent_id: str, ctx: ExtractionContext, manifest: AgentManifest):
        try:
            self.db.execute(
                text("""
                    INSERT INTO incentivehouse_audit_log
                    (agent_id, module, source_file, total_rows, passed, warnings,
                     failed, staged, dry_run, summary, errors_json, started_at, completed_at)
                    VALUES (
                        :agent_id, :module, :src, :total, :passed, :warn,
                        :fail, :staged, :dry, :summary, :errors, :started, :completed
                    )
                """),
                {
                    "agent_id": agent_id,
                    "module": ctx.module,
                    "src": ctx.file_path,
                    "total": manifest.total_rows,
                    "passed": manifest.passed,
                    "warn": manifest.warnings,
                    "fail": manifest.failed,
                    "staged": manifest.staged,
                    "dry": ctx.dry_run,
                    "summary": manifest.summary,
                    "errors": json.dumps(manifest.errors[:100]),
                    "started": manifest.started_at,
                    "completed": datetime.now().isoformat(),
                },
            )
            self.db.commit()
        except Exception as exc:
            logger.warning("Audit log write failed: %s", exc)
            self.db.rollback()
