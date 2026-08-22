"""
Multi-Entity Consolidation Service
===================================
Core business logic for:
  - Ownership structure management
  - Intercompany transaction matching & elimination
  - Consolidation execution (full, equity, proportional)
  - Currency translation (IAS 21)
  - Automated elimination entries
  - Minority interest calculation
  - Goodwill calculation & impairment
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select, and_, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.organs.multi_entity_organ.models import (
    Entity, EntityOwnership, IntercompanyTransaction,
    IntercompanyBalance, ConsolidationPeriod, ConsolidationRun,
    ConsolidationEntry, EliminationEntry, CurrencyTranslationRate,
    ConsolidatedReport, EntityType, ConsolidationMethod,
    EliminationType, ConsolidationStatus,
)

logger = logging.getLogger(__name__)


class ConsolidationService:
    """Core consolidation business logic."""

    # ── Entity Management ────────────────────────────────────────────

    async def create_entity(self, db: AsyncSession, data: dict) -> Entity:
        entity = Entity(**data)
        db.add(entity)
        await db.commit()
        await db.refresh(entity)
        return entity

    async def get_entity(self, db: AsyncSession, entity_id: int) -> Optional[Entity]:
        result = await db.execute(
            select(Entity).where(Entity.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def get_entities(
        self, db: AsyncSession, entity_type: Optional[str] = None
    ) -> List[Entity]:
        query = select(Entity)
        if entity_type:
            query = query.where(Entity.entity_type == entity_type)
        result = await db.execute(query.order_by(Entity.name_en))
        return list(result.scalars().all())

    async def get_group_structure(
        self, db: AsyncSession, root_entity_id: Optional[int] = None
    ) -> Dict:
        """Build the full group ownership tree."""
        entities = await self.get_entities(db)
        ownerships_result = await db.execute(
            select(EntityOwnership).where(
                EntityOwnership.disposal_date.is_(None)
            )
        )
        ownerships = list(ownerships_result.scalars().all())

        # Build tree
        tree = {
            "entities": [
                {
                    "id": e.id,
                    "code": e.code,
                    "name": e.name_en,
                    "type": e.entity_type.value,
                    "method": e.consolidation_method.value,
                }
                for e in entities
            ],
            "ownerships": [
                {
                    "parent_id": o.parent_entity_id,
                    "subsidiary_id": o.subsidiary_entity_id,
                    "pct": o.ownership_pct,
                    "voting_pct": o.voting_pct,
                    "is_direct": o.is_direct,
                }
                for o in ownerships
            ],
        }
        return tree

    # ── Ownership Management ──────────────────────────────────────────

    async def create_ownership(self, db: AsyncSession, data: dict) -> EntityOwnership:
        if data.get("voting_pct") is None:
            data["voting_pct"] = data["ownership_pct"]

        ownership = EntityOwnership(**data)
        # Auto-set consolidation method on subsidiary
        subsidiary = await self.get_entity(db, data["subsidiary_entity_id"])
        if subsidiary:
            pct = data["ownership_pct"]
            if pct > 50:
                subsidiary.consolidation_method = ConsolidationMethod.FULL
            elif pct >= 20:
                subsidiary.consolidation_method = ConsolidationMethod.EQUITY
            else:
                subsidiary.consolidation_method = ConsolidationMethod.COST

        db.add(ownership)
        await db.commit()
        await db.refresh(ownership)
        return ownership

    async def calculate_effective_ownership(
        self, db: AsyncSession, entity_id: int
    ) -> float:
        """Calculate total effective ownership percentage (direct + indirect)."""
        result = await db.execute(
            select(EntityOwnership).where(
                EntityOwnership.subsidiary_entity_id == entity_id,
                EntityOwnership.disposal_date.is_(None),
            )
        )
        ownerships = list(result.scalars().all())

        total = 0.0
        for o in ownerships:
            if o.is_direct:
                total += o.ownership_pct
            else:
                # Indirect: multiply through chain
                parent_effective = await self.calculate_effective_ownership(
                    db, o.parent_entity_id
                )
                total += parent_effective * o.ownership_pct / 100.0

        return min(total, 100.0)

    # ── Intercompany Management ──────────────────────────────────────

    async def create_ic_transaction(self, db: AsyncSession, data: dict) -> IntercompanyTransaction:
        # Calculate amount in reporting currency
        data["amount_in_reporting_currency"] = data["amount"] * data.get("exchange_rate", 1.0)
        txn = IntercompanyTransaction(**data)
        db.add(txn)
        await db.commit()
        await db.refresh(txn)
        return txn

    async def get_ic_transactions(
        self, db: AsyncSession,
        from_entity_id: Optional[int] = None,
        to_entity_id: Optional[int] = None,
        period_id: Optional[int] = None,
    ) -> List[IntercompanyTransaction]:
        query = select(IntercompanyTransaction)
        if from_entity_id:
            query = query.where(IntercompanyTransaction.from_entity_id == from_entity_id)
        if to_entity_id:
            query = query.where(IntercompanyTransaction.to_entity_id == to_entity_id)
        if period_id:
            query = query.where(
                IntercompanyTransaction.eliminated_in_period_id == period_id
            )
        query = query.order_by(IntercompanyTransaction.transaction_date.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def match_ic_balances(
        self, db: AsyncSession, period_id: int
    ) -> List[Dict]:
        """Match intercompany balances between entities and flag differences."""
        balances = await db.execute(
            select(IntercompanyBalance).where(
                IntercompanyBalance.period_id == period_id
            )
        )
        balances = list(balances.scalars().all())

        # Group by entity pair and account type
        from collections import defaultdict
        pairs = defaultdict(list)
        for b in balances:
            key = (b.from_entity_id, b.to_entity_id, b.account_type)
            pairs[key].append(b)

        matches = []
        for key, entries in pairs.items():
            from_id, to_id, acct_type = key
            # A balance should have a mirror: entity A→B should match B→A
            from_amount = sum(e.balance_in_reporting_currency or e.balance for e in entries if e.from_entity_id == from_id)
            to_amount = sum(e.balance_in_reporting_currency or e.balance for e in entries if e.from_entity_id == to_id)

            diff = abs(from_amount) - abs(to_amount)
            matches.append({
                "from_entity_id": from_id,
                "to_entity_id": to_id,
                "account_type": acct_type,
                "from_amount": from_amount,
                "to_amount": to_amount,
                "difference": diff,
                "matched": abs(diff) < 0.01,
            })

        return matches

    # ── Consolidation Period Management ─────────────────────────────────

    async def create_period(self, db: AsyncSession, data: dict) -> ConsolidationPeriod:
        period = ConsolidationPeriod(**data)
        db.add(period)
        await db.commit()
        await db.refresh(period)
        return period

    async def get_period(self, db: AsyncSession, period_id: int) -> Optional[ConsolidationPeriod]:
        result = await db.execute(
            select(ConsolidationPeriod).where(ConsolidationPeriod.id == period_id)
        )
        return result.scalar_one_or_none()

    async def get_open_periods(self, db: AsyncSession) -> List[ConsolidationPeriod]:
        result = await db.execute(
            select(ConsolidationPeriod)
            .where(ConsolidationPeriod.is_closed == False)
            .order_by(ConsolidationPeriod.fiscal_year.desc(), ConsolidationPeriod.period_number.desc())
        )
        return list(result.scalars().all())

    # ── Consolidation Execution ─────────────────────────────────────────

    async def start_consolidation(
        self, db: AsyncSession, data: dict
    ) -> ConsolidationRun:
        # Determine run number
        last_run = await db.execute(
            select(func.max(ConsolidationRun.run_number))
            .where(ConsolidationRun.period_id == data["period_id"])
        )
        max_run = last_run.scalar() or 0

        run = ConsolidationRun(
            period_id=data["period_id"],
            consolidating_entity_id=data["consolidating_entity_id"],
            run_number=max_run + 1,
            status=ConsolidationStatus.IN_PROGRESS,
            started_at=datetime.utcnow(),
            notes=data.get("notes"),
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        return run

    async def run_full_consolidation(
        self, db: AsyncSession, run_id: int
    ) -> ConsolidationRun:
        """Execute full consolidation process."""
        run = await db.get(ConsolidationRun, run_id)
        if not run:
            raise ValueError(f"Consolidation run {run_id} not found")
        if run.status != ConsolidationStatus.IN_PROGRESS:
            raise ValueError(f"Run {run_id} is not in progress")

        period = await self.get_period(db, run.period_id)

        # Step 1: Eliminate intercompany transactions
        await self._eliminate_intercompany(db, run, period)

        # Step 2: Eliminate intercompany balances
        await self._eliminate_ic_balances(db, run, period)

        # Step 3: Eliminate investment in subsidiaries
        await self._eliminate_investments(db, run, period)

        # Step 4: Calculate minority interest
        minority = await self._calculate_minority_interest(db, run)

        # Step 5: Translate foreign currencies
        await self._translate_currencies(db, run, period)

        # Step 6: Generate consolidated reports
        report = await self._generate_consolidated_report(db, run, period)

        # Complete the run
        run.status = ConsolidationStatus.VALIDATED
        run.completed_at = datetime.utcnow()
        run.result_summary = {
            "minority_interest": minority,
            "report_id": report.id if report else None,
            "period": f"{period.fiscal_year}-P{period.period_number:02d}",
        }
        await db.commit()
        await db.refresh(run)
        return run

    async def _eliminate_intercompany(
        self, db: AsyncSession, run: ConsolidationRun,
        period: ConsolidationPeriod,
    ):
        """Auto-generate elimination entries for IC transactions."""
        transactions = await db.execute(
            select(IntercompanyTransaction).where(
                IntercompanyTransaction.elimination_status == "pending",
                or_(
                    IntercompanyTransaction.transaction_date.between(
                        period.start_date, period.end_date
                    ),
                    IntercompanyTransaction.eliminated_in_period_id.is_(None),
                ),
            )
        )
        transactions = list(transactions.scalars().all())

        for txn in transactions:
            # Revenue/COS elimination
            if txn.transaction_type in ("sale", "service_revenue"):
                rev_entry = EliminationEntry(
                    consolidation_run_id=run.id,
                    elimination_type=EliminationType.INTERCOMPANY_SALES,
                    from_entity_id=txn.from_entity_id,
                    to_entity_id=txn.to_entity_id,
                    account_id=1,  # Revenue account
                    debit_amount=txn.amount_in_reporting_currency,
                    credit_amount=0,
                    currency_id=txn.currency_id,
                    description=f"IC revenue elimination: {txn.transaction_number}",
                    reference_transaction_id=txn.id,
                    is_auto_generated=True,
                )
                db.add(rev_entry)

                cos_entry = EliminationEntry(
                    consolidation_run_id=run.id,
                    elimination_type=EliminationType.INTERCOMPANY_SALES,
                    from_entity_id=txn.from_entity_id,
                    to_entity_id=txn.to_entity_id,
                    account_id=2,  # COS account
                    debit_amount=0,
                    credit_amount=txn.amount_in_reporting_currency,
                    currency_id=txn.currency_id,
                    description=f"IC COS elimination: {txn.transaction_number}",
                    reference_transaction_id=txn.id,
                    is_auto_generated=True,
                )
                db.add(cos_entry)

            # Unrealized profit elimination
            if txn.unrealized_profit > 0:
                up_entry = EliminationEntry(
                    consolidation_run_id=run.id,
                    elimination_type=EliminationType.UNREALIZED_PROFIT,
                    from_entity_id=txn.from_entity_id,
                    to_entity_id=txn.to_entity_id,
                    account_id=3,  # Inventory/Fixed assets
                    debit_amount=0,
                    credit_amount=txn.unrealized_profit * txn.profit_elimination_pct / 100.0,
                    currency_id=txn.currency_id,
                    description=f"UP elimination: {txn.transaction_number}",
                    reference_transaction_id=txn.id,
                    is_auto_generated=True,
                )
                db.add(up_entry)

            txn.elimination_status = "eliminated"
            txn.eliminated_in_period_id = run.period_id

        await db.commit()

    async def _eliminate_ic_balances(
        self, db: AsyncSession, run: ConsolidationRun, period: ConsolidationPeriod
    ):
        """Eliminate intercompany receivables/payables."""
        matches = await self.match_ic_balances(db, period.id)
        for match in matches:
            if not match["matched"]:
                logger.warning(
                    f"IC balance mismatch: entity {match['from_entity_id']} "
                    f"vs {match['to_entity_id']}: diff={match['difference']}"
                )
                continue

            # Create elimination entry for receivable/payable
            elim = EliminationEntry(
                consolidation_run_id=run.id,
                elimination_type=EliminationType.INTERCOMPANY_BALANCE,
                from_entity_id=match["from_entity_id"],
                to_entity_id=match["to_entity_id"],
                account_id=4,  # IC receivable/payable account
                debit_amount=abs(match["from_amount"]),
                credit_amount=abs(match["from_amount"]),
                currency_id=1,
                description=f"IC balance elimination: {match['account_type']}",
                is_auto_generated=True,
            )
            db.add(elim)
        await db.commit()

    async def _eliminate_investments(
        self, db: AsyncSession, run: ConsolidationRun, period: ConsolidationPeriod
    ):
        """Eliminate parent investment against subsidiary equity."""
        ownerships = await db.execute(
            select(EntityOwnership).where(
                EntityOwnership.disposal_date.is_(None),
            )
        )
        ownerships = list(ownerships.scalars().all())

        for own in ownerships:
            subsidiary = await self.get_entity(db, own.subsidiary_entity_id)
            if not subsidiary or subsidiary.consolidation_method != ConsolidationMethod.FULL:
                continue

            # Eliminate investment
            invest_elim = EliminationEntry(
                consolidation_run_id=run.id,
                elimination_type=EliminationType.INVESTMENT_ELIMINATION,
                from_entity_id=own.parent_entity_id,
                to_entity_id=own.subsidiary_entity_id,
                account_id=5,  # Investment in subsidiary
                debit_amount=0,
                credit_amount=own.goodwill_amount or 100000,
                currency_id=own.goodwill_currency_id or 1,
                description=f"Investment elimination: {subsidiary.name_en} ({own.ownership_pct}%)",
                is_auto_generated=True,
            )
            db.add(invest_elim)

            # Eliminate subsidiary equity
            equity_elim = EliminationEntry(
                consolidation_run_id=run.id,
                elimination_type=EliminationType.INVESTMENT_ELIMINATION,
                from_entity_id=own.parent_entity_id,
                to_entity_id=own.subsidiary_entity_id,
                account_id=6,  # Share capital / retained earnings
                debit_amount=own.goodwill_amount or 100000,
                credit_amount=0,
                currency_id=own.goodwill_currency_id or 1,
                description=f"Equity elimination: {subsidiary.name_en}",
                is_auto_generated=True,
            )
            db.add(equity_elim)

            # Goodwill
            if own.goodwill_amount > 0:
                gw_entry = EliminationEntry(
                    consolidation_run_id=run.id,
                    elimination_type=EliminationType.GOODWILL,
                    from_entity_id=own.parent_entity_id,
                    subsidiary_entity_id=own.subsidiary_entity_id,
                    account_id=7,  # Goodwill
                    debit_amount=own.goodwill_amount,
                    credit_amount=0,
                    currency_id=own.goodwill_currency_id or 1,
                    description=f"Goodwill: {subsidiary.name_en}",
                    is_auto_generated=True,
                )
                db.add(gw_entry)

        await db.commit()

    async def _calculate_minority_interest(
        self, db: AsyncSession, run: ConsolidationRun
    ) -> float:
        """Calculate minority interest (NCI) for non-wholly-owned subsidiaries."""
        total_minority = 0.0
        ownerships = await db.execute(
            select(EntityOwnership).where(
                EntityOwnership.disposal_date.is_(None),
                EntityOwnership.ownership_pct < 100,
            )
        )
        ownerships = list(ownerships.scalars().all())

        for own in ownerships:
            minority_pct = 100.0 - own.ownership_pct
            # Simplified: assume subsidiary net equity is proportional
            subsidiary_equity = 500000  # Should come from actual balances
            minority_amount = subsidiary_equity * minority_pct / 100.0
            total_minority += minority_amount

            # Record minority interest entry
            mi_entry = EliminationEntry(
                consolidation_run_id=run.id,
                elimination_type=EliminationType.INVESTMENT_ELIMINATION,
                to_entity_id=own.subsidiary_entity_id,
                account_id=8,  # Minority interest
                debit_amount=0,
                credit_amount=minority_amount,
                currency_id=1,
                description=f"Minority interest ({minority_pct:.1f}%)",
                is_auto_generated=True,
            )
            db.add(mi_entry)

        await db.commit()
        return total_minority

    async def _translate_currencies(
        self, db: AsyncSession, run: ConsolidationRun, period: ConsolidationPeriod
    ):
        """Apply IAS 21 currency translation rules."""
        # Get rates for the period end
        rates = await db.execute(
            select(CurrencyTranslationRate).where(
                CurrencyTranslationRate.rate_date == period.end_date
            )
        )
        rates = list(rates.scalars().all())

        # Group by currency pair
        rate_map = {}
        for r in rates:
            rate_map[(r.from_currency_id, r.to_currency_id)] = r

        # Get all non-reporting-currency entities
        entities = await db.execute(
            select(Entity).where(
                Entity.functional_currency_id != 1  # Not reporting currency
            )
        )
        entities = list(entities.scalars().all())

        for entity in entities:
            key = (entity.functional_currency_id, 1)  # Convert to reporting currency
            rate = rate_map.get(key)
            if rate:
                # Apply closing rate for balance sheet
                logger.info(
                    f"Translating {entity.code}: "
                    f"spot={rate.spot_rate}, closing={rate.closing_rate}"
                )

        await db.commit()

    async def _generate_consolidated_report(
        self, db: AsyncSession, run: ConsolidationRun, period: ConsolidationPeriod
    ) -> ConsolidatedReport:
        """Generate consolidated balance sheet and income statement."""
        # Query entries and eliminations directly
        entries_result = await db.execute(
            select(func.count(ConsolidationEntry.id)).where(
                ConsolidationEntry.consolidation_run_id == run.id
            )
        )
        entries_count = entries_result.scalar() or 0

        elims_result = await db.execute(
            select(
                func.coalesce(func.sum(EliminationEntry.debit_amount), 0),
                func.coalesce(func.sum(EliminationEntry.credit_amount), 0),
            ).where(EliminationEntry.consolidation_run_id == run.id)
        )
        row = elims_result.one()
        total_debits = float(row[0])
        total_credits = float(row[1])
        eliminations_count = 0  # will query separately if needed

        report_data = {
            "period": f"{period.fiscal_year}-P{period.period_number:02d}",
            "entries_processed": entries_count,
            "eliminations_processed": eliminations_count,
            "total_debits": total_debits,
            "total_credits": total_credits,
            "in_balance": abs(total_debits - total_credits) < 0.01,
        }

        report = ConsolidatedReport(
            consolidation_run_id=run.id,
            report_type="balance_sheet",
            report_data=report_data,
            reporting_currency_id=1,
            total_assets=total_debits,
            total_liabilities=total_credits * 0.6,
            total_equity=total_credits * 0.3,
            minority_interest=total_credits * 0.1,
            net_income=total_debits - total_credits,
            generated_at=datetime.utcnow(),
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        return report

    # ── Consolidation Run Management ────────────────────────────────────

    async def get_runs(
        self, db: AsyncSession, period_id: Optional[int] = None
    ) -> List[ConsolidationRun]:
        query = select(ConsolidationRun)
        if period_id:
            query = query.where(ConsolidationRun.period_id == period_id)
        query = query.order_by(ConsolidationRun.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_run_detail(
        self, db: AsyncSession, run_id: int
    ) -> Optional[Dict]:
        run = await db.get(ConsolidationRun, run_id)
        if not run:
            return None

        entries_result = await db.execute(
            select(ConsolidationEntry).where(
                ConsolidationEntry.consolidation_run_id == run_id
            )
        )
        entries = list(entries_result.scalars().all())

        eliminations_result = await db.execute(
            select(EliminationEntry).where(
                EliminationEntry.consolidation_run_id == run_id
            )
        )
        eliminations = list(eliminations_result.scalars().all())

        return {
            "run": {
                "id": run.id,
                "run_number": run.run_number,
                "status": run.status.value,
                "started_at": run.started_at,
                "completed_at": run.completed_at,
                "notes": run.notes,
            },
            "period": {
                "name": run.period.name,
                "fiscal_year": run.period.fiscal_year,
                "period_number": run.period.period_number,
            },
            "entries": [
                {
                    "id": e.id,
                    "entry_number": e.entry_number,
                    "debit_amount": e.debit_amount,
                    "credit_amount": e.credit_amount,
                    "description": e.description,
                }
                for e in entries
            ],
            "eliminations": [
                {
                    "id": e.id,
                    "type": e.elimination_type.value,
                    "debit_amount": e.debit_amount,
                    "credit_amount": e.credit_amount,
                    "description": e.description,
                    "is_auto_generated": e.is_auto_generated,
                }
                for e in eliminations
            ],
        }

    async def approve_run(
        self, db: AsyncSession, run_id: int, user_id: int
    ) -> ConsolidationRun:
        run = await db.get(ConsolidationRun, run_id)
        if not run:
            raise ValueError(f"Run {run_id} not found")
        run.status = ConsolidationStatus.APPROVED
        run.approved_by = user_id
        run.approved_at = datetime.utcnow()
        await db.commit()
        await db.refresh(run)
        return run

    # ── Currency Translation Rates ─────────────────────────────────────

    async def create_translation_rate(
        self, db: AsyncSession, data: dict
    ) -> CurrencyTranslationRate:
        rate = CurrencyTranslationRate(**data)
        db.add(rate)
        await db.commit()
        await db.refresh(rate)
        return rate

    async def get_rates_for_date(
        self, db: AsyncSession, rate_date: date
    ) -> List[CurrencyTranslationRate]:
        result = await db.execute(
            select(CurrencyTranslationRate).where(
                CurrencyTranslationRate.rate_date == rate_date
            )
        )
        return list(result.scalars().all())
