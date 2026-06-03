"""Seed 2,501 bank transactions and a reconciliation session for testing."""
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from app.database import get_sync_session, init_db
from app.models import (
    BankAccount,
    BankImportSession,
    BankReconciliation,
    BankStaging,
    COAAccount,
    COACategory,
)

DESCRIPTIONS = [
    "Client payment - Event #{}",
    "Supplier invoice #INV-{}",
    "Transfer to savings",
    "ATM withdrawal",
    "Online payment - Ref #{}",
    "Salary disbursement",
    "Utility bill payment",
    "Vendor settlement",
    "Service fee",
    "Bank charges",
    "Interest credit",
    "Refund - Transaction #{}",
    "Purchase order #PO-{}",
    "Petty cash top-up",
    "Loan installment",
]


def _ensure_bank_account(session) -> BankAccount:
    ba = session.query(BankAccount).first()
    if ba:
        return ba

    # Create a COA category + account first
    cat = session.query(COACategory).first()
    if not cat:
        cat = COACategory(
            code="BANK-CAT",
            name_en="Bank Accounts",
            name_ar="الحسابات البنكية",
            report_type="Balance Sheet",
        )
        session.add(cat)
        session.flush()

    acct = session.query(COAAccount).filter(COAAccount.code == "BANK-001").first()
    if not acct:
        acct = COAAccount(
            code="BANK-001",
            name_en="Main Operating Account",
            name_ar="الحساب التشغيلي الرئيسي",
            category_id=cat.id,
            account_type="Asset",
        )
        session.add(acct)
        session.flush()

    ba = BankAccount(
        account_name="Main Operating Account",
        bank_name="National Bank of Egypt",
        account_number="100-123456-78",
        swift_code="NBEGEGCX",
        currency="EGP",
        coa_account_id=acct.id,
        current_balance=0.0,
    )
    session.add(ba)
    session.flush()
    return ba


def main():
    init_db()
    session = get_sync_session()

    bank_account = _ensure_bank_account(session)

    import_sess = BankImportSession(
        bank_account_id=bank_account.id,
        file_name="bank_statement_2026_05.csv",
        total_transactions=2501,
        matched_count=0,
        unmatched_count=2501,
        status="IMPORTED",
    )
    session.add(import_sess)
    session.flush()

    base_date = datetime(2026, 5, 1, tzinfo=timezone.utc)
    for i in range(2501):
        days_offset = random.randint(0, 30)
        txn_date = base_date + timedelta(
            days=days_offset,
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        is_debit = random.choice([True, False])
        amount = round(random.uniform(100, 50000), 2)
        ref_num = random.randint(10000, 99999)
        description = random.choice(DESCRIPTIONS).format(ref_num)

        staging = BankStaging(
            session_id=import_sess.id,
            transaction_date=txn_date.replace(tzinfo=None),
            description=description,
            debit_amount=amount if is_debit else 0.0,
            credit_amount=0.0 if is_debit else amount,
            reference=f"REF-{ref_num}",
            is_matched=False,
        )
        session.add(staging)

    session.commit()

    total_debit = (
        session.query(func.sum(BankStaging.debit_amount))
        .filter(BankStaging.session_id == import_sess.id)
        .scalar()
        or 0
    )
    total_credit = (
        session.query(func.sum(BankStaging.credit_amount))
        .filter(BankStaging.session_id == import_sess.id)
        .scalar()
        or 0
    )
    net_balance = round(total_credit - total_debit, 2)

    recon = BankReconciliation(
        bank_account_id=bank_account.id,
        statement_balance=net_balance,
        system_balance=0.0,
        difference=net_balance,
        status="IN_PROGRESS",
    )
    session.add(recon)
    session.commit()

    print(f"Imported  {import_sess.total_transactions}  transactions  ->  session  #{import_sess.id}")
    print(f"Reconciliation  #{recon.id}  created  (difference  EGP  {recon.difference:,.2f})")
    session.close()


if __name__ == "__main__":
    main()
