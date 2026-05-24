from datetime import datetime
from sqlalchemy import Integer, String, Float, ForeignKey, DateTime, Boolean, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.base import BaseMixin, BranchAwareMixin, CurrencyAwareMixin


class VendorInvoice(Base, BaseMixin, BranchAwareMixin, CurrencyAwareMixin):
    __tablename__ = "vendor_invoices"

    invoice_number: Mapped[str] = mapped_column(String(50), nullable=False)
    vendor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=False
    )
    po_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_orders.id"), nullable=True
    )
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=True
    )
    invoice_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    due_date: Mapped[datetime] = mapped_column(Date, nullable=True)
    received_date: Mapped[datetime] = mapped_column(Date, nullable=True)
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    amount_due: Mapped[float] = mapped_column(Float, default=0.0)
    amount_paid: Mapped[float] = mapped_column(Float, default=0.0)
    match_status: Mapped[str] = mapped_column(String(20), default="Pending")
    variance_amount: Mapped[float] = mapped_column(Float, default=0.0)
    variance_pct: Mapped[float] = mapped_column(Float, default=0.0)
    variance_reason: Mapped[str] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Unpaid")
    gl_posted: Mapped[bool] = mapped_column(Boolean, default=False)
    gl_posted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    gl_posted_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    notes: Mapped[str] = mapped_column(String(500), nullable=True)

    vendor = relationship("Supplier")
    po = relationship("PurchaseOrder")
    lines = relationship("VendorInvoiceLine", back_populates="invoice")
    allocations = relationship("PMTAllocation", back_populates="vendor_invoice")


class VendorInvoiceLine(Base, BaseMixin):
    __tablename__ = "vendor_invoice_lines"

    invoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vendor_invoices.id"), nullable=False
    )
    po_line_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_orders.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(200), nullable=True)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    uom: Mapped[str] = mapped_column(String(20), nullable=True)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    line_total: Mapped[float] = mapped_column(Float, default=0.0)
    qty_invoiced: Mapped[float] = mapped_column(Float, default=0.0)
    qty_received: Mapped[float] = mapped_column(Float, default=0.0)
    qty_variance: Mapped[float] = mapped_column(Float, default=0.0)
    gl_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_accounts.id"), nullable=True
    )

    invoice = relationship("VendorInvoice", back_populates="lines")


class CustomerInvoice(Base, BaseMixin, BranchAwareMixin, CurrencyAwareMixin):
    __tablename__ = "customer_invoices"

    invoice_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=False
    )
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id"), nullable=False
    )
    final_budget_version_id: Mapped[int] = mapped_column(Integer, nullable=True)
    invoice_type: Mapped[str] = mapped_column(String(20), default="Standard")
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    invoice_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    due_date: Mapped[datetime] = mapped_column(Date, nullable=True)
    sent_date: Mapped[datetime] = mapped_column(Date, nullable=True)
    paid_date: Mapped[datetime] = mapped_column(Date, nullable=True)
    subtotal: Mapped[float] = mapped_column(Float, default=0.0)
    tax_amount: Mapped[float] = mapped_column(Float, default=0.0)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    amount_due: Mapped[float] = mapped_column(Float, default=0.0)
    amount_paid: Mapped[float] = mapped_column(Float, default=0.0)
    gl_posted: Mapped[bool] = mapped_column(Boolean, default=False)
    gl_posted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    gl_posted_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    notes: Mapped[str] = mapped_column(String(500), nullable=True)

    event = relationship("Event", foreign_keys=[event_id])
    customer = relationship("Client")
    lines = relationship("CustomerInvoiceLine", back_populates="invoice")
    allocations = relationship("RCTAllocation", back_populates="invoice")


class CustomerInvoiceLine(Base, BaseMixin):
    __tablename__ = "customer_invoice_lines"

    invoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_invoices.id"), nullable=False
    )
    budget_line_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("event_budget_lines.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    description_ar: Mapped[str] = mapped_column(String(200), nullable=True)
    quantity: Mapped[float] = mapped_column(Float, default=1.0)
    uom: Mapped[str] = mapped_column(String(20), nullable=True)
    unit_cost: Mapped[float] = mapped_column(Float, default=0.0)
    markup_pct: Mapped[float] = mapped_column(Float, default=0.0)
    markup_amount: Mapped[float] = mapped_column(Float, default=0.0)
    unit_price: Mapped[float] = mapped_column(Float, default=0.0)
    line_total: Mapped[float] = mapped_column(Float, default=0.0)
    budget_category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_categories.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    invoice = relationship("CustomerInvoice", back_populates="lines")


class RCTHeader(Base, BaseMixin, BranchAwareMixin, CurrencyAwareMixin):
    __tablename__ = "rct_headers"

    receipt_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id"), nullable=True
    )
    received_from: Mapped[str] = mapped_column(String(100), nullable=True)
    receipt_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    receipt_type: Mapped[str] = mapped_column(String(20), default="Cash")
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    bank_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_accounts.id"), nullable=True
    )
    check_number: Mapped[str] = mapped_column(String(50), nullable=True)
    check_date: Mapped[datetime] = mapped_column(Date, nullable=True)
    bank_reference: Mapped[str] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Open")
    gl_posted: Mapped[bool] = mapped_column(Boolean, default=False)
    gl_posted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    notes: Mapped[str] = mapped_column(String(500), nullable=True)

    allocations = relationship("RCTAllocation", back_populates="receipt")


class RCTAllocation(Base, BaseMixin):
    __tablename__ = "rct_allocations"

    receipt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("rct_headers.id"), nullable=False
    )
    invoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_invoices.id"), nullable=False
    )
    amount_allocated: Mapped[float] = mapped_column(Float, nullable=False)
    discount_taken: Mapped[float] = mapped_column(Float, default=0.0)
    invoice_balance_before: Mapped[float] = mapped_column(Float, nullable=True)
    invoice_balance_after: Mapped[float] = mapped_column(Float, nullable=True)
    allocated_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    receipt = relationship("RCTHeader", back_populates="allocations")
    invoice = relationship("CustomerInvoice", back_populates="allocations")


class PMTHeader(Base, BaseMixin, BranchAwareMixin, CurrencyAwareMixin):
    __tablename__ = "pmt_headers"

    payment_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    vendor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=True
    )
    paid_to: Mapped[str] = mapped_column(String(100), nullable=True)
    payment_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    payment_type: Mapped[str] = mapped_column(String(20), default="BankTransfer")
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    bank_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_accounts.id"), nullable=True
    )
    check_number: Mapped[str] = mapped_column(String(50), nullable=True)
    check_date: Mapped[datetime] = mapped_column(Date, nullable=True)
    bank_reference: Mapped[str] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="Pending")
    approved_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    gl_posted: Mapped[bool] = mapped_column(Boolean, default=False)
    gl_posted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    notes: Mapped[str] = mapped_column(String(500), nullable=True)

    allocations = relationship("PMTAllocation", back_populates="payment")


class PMTAllocation(Base, BaseMixin):
    __tablename__ = "pmt_allocations"

    payment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("pmt_headers.id"), nullable=False
    )
    invoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vendor_invoices.id"), nullable=False
    )
    amount_allocated: Mapped[float] = mapped_column(Float, nullable=False)
    discount_taken: Mapped[float] = mapped_column(Float, default=0.0)
    invoice_balance_before: Mapped[float] = mapped_column(Float, nullable=True)
    invoice_balance_after: Mapped[float] = mapped_column(Float, nullable=True)
    allocated_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    payment = relationship("PMTHeader", back_populates="allocations")
    vendor_invoice = relationship("VendorInvoice", back_populates="allocations")


class JVHeader(Base, BaseMixin, BranchAwareMixin):
    __tablename__ = "jv_headers"

    jv_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    jv_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    reference: Mapped[str] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(String(200), nullable=True)
    description_ar: Mapped[str] = mapped_column(String(200), nullable=True)
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=True
    )
    total_debit: Mapped[float] = mapped_column(Float, default=0.0)
    total_credit: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="Draft")
    approved_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    gl_posted: Mapped[bool] = mapped_column(Boolean, default=False)
    gl_posted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    gl_period: Mapped[str] = mapped_column(String(7), nullable=True)
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    notes: Mapped[str] = mapped_column(String(500), nullable=True)

    lines = relationship("JVLine", back_populates="jv")


class JVLine(Base, BaseMixin):
    __tablename__ = "jv_lines"

    jv_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jv_headers.id"), nullable=False
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    gl_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_accounts.id"), nullable=False
    )
    debit_amount: Mapped[float] = mapped_column(Float, default=0.0)
    credit_amount: Mapped[float] = mapped_column(Float, default=0.0)
    description: Mapped[str] = mapped_column(String(200), nullable=True)
    description_ar: Mapped[str] = mapped_column(String(200), nullable=True)
    event_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("events.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    jv = relationship("JVHeader", back_populates="lines")
    gl_account = relationship("COAAccount")


class JVTemplate(Base, BaseMixin):
    __tablename__ = "jv_templates"

    template_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    template_name: Mapped[str] = mapped_column(String(100), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[datetime] = mapped_column(Date, nullable=True)
    end_date: Mapped[datetime] = mapped_column(Date, nullable=True)
    next_run_date: Mapped[datetime] = mapped_column(Date, nullable=True)
    last_run_date: Mapped[datetime] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    lines = relationship("JVTemplateLine", back_populates="template")


class JVTemplateLine(Base, BaseMixin):
    __tablename__ = "jv_template_lines"

    template_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jv_templates.id"), nullable=False
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    gl_account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("coa_accounts.id"), nullable=False
    )
    debit_amount: Mapped[float] = mapped_column(Float, default=0.0)
    credit_amount: Mapped[float] = mapped_column(Float, default=0.0)
    description: Mapped[str] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    template = relationship("JVTemplate", back_populates="lines")
    gl_account = relationship("COAAccount")
