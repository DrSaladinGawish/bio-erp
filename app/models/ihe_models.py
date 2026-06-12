from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Date, Numeric, BigInteger, ForeignKey, Identity
from sqlalchemy.orm import declarative_base, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Dimension Tables ──────────────────────────────────────────

class Currency(Base):
    __tablename__ = "Currency"
    __table_args__ = {"schema": "dbo"}
    CurrencyCode = Column(String(3), primary_key=True)
    CurrencyName = Column(String(50), nullable=False)
    Symbol = Column(String(5), nullable=True)
    IsBaseCurrency = Column(Boolean, default=False)


class Client(Base):
    __tablename__ = "Client"
    __table_args__ = {"schema": "dbo"}
    ClientCode = Column(String(10), primary_key=True)
    ClientName = Column(String(200), nullable=False)
    TaxID = Column(String(50), nullable=True)
    TaxRegisterNo = Column(String(50), nullable=True)
    Address = Column(String(500), nullable=True)
    Telephone = Column(String(50), nullable=True)
    Email = Column(String(200), nullable=True)
    ContactPerson = Column(String(200), nullable=True)
    PostingAccount = Column(String(20), nullable=True)
    ExpenseAccount = Column(String(20), nullable=True)
    PaymentTerms = Column(String(100), nullable=True)
    IsActive = Column(Boolean, default=True)

    pnrs = relationship("PNRMaster", back_populates="client")
    sales_invoices = relationship("SalesInvoice", back_populates="client")
    employees = relationship("ClientEmployee", back_populates="client")


class Vendor(Base):
    __tablename__ = "Vendor"
    __table_args__ = {"schema": "dbo"}
    VendorCode = Column(String(10), primary_key=True)
    VendorName = Column(String(200), nullable=False)
    TaxID = Column(String(50), nullable=True)
    TaxRegisterNo = Column(String(50), nullable=True)
    Address = Column(String(500), nullable=True)
    Telephone = Column(String(50), nullable=True)
    Email = Column(String(200), nullable=True)
    Branch = Column(String(100), nullable=True)
    BankName = Column(String(100), nullable=True)
    IBAN = Column(String(50), nullable=True)
    EGPAccountNo = Column(String(50), nullable=True)
    USDAccountNo = Column(String(50), nullable=True)
    VendorType = Column(String(50), nullable=True)
    PostingAccount = Column(String(20), nullable=True)
    ExpenseAccount = Column(String(20), nullable=True)
    PaymentTerms = Column(String(100), nullable=True)
    IsActive = Column(Boolean, default=True)


class Employee(Base):
    __tablename__ = "Employee"
    __table_args__ = {"schema": "dbo"}
    EmployeeCode = Column(String(10), primary_key=True)
    EmployeeName = Column(String(200), nullable=False)
    EmployeeType = Column(String(20), nullable=False)
    PostingAccount = Column(String(20), nullable=True)
    ExpenseAccount = Column(String(20), nullable=True)
    IsActive = Column(Boolean, default=True)


class Bank(Base):
    __tablename__ = "Bank"
    __table_args__ = {"schema": "dbo"}
    BankCode = Column(String(10), primary_key=True)
    BankName = Column(String(200), nullable=False)
    GLAccount = Column(String(20), nullable=True)
    IsActive = Column(Boolean, default=True)

    transactions = relationship("BankTransaction", back_populates="bank")


class ServiceMainCategory(Base):
    __tablename__ = "ServiceMainCategory"
    __table_args__ = {"schema": "dbo"}
    MainCategoryCode = Column(String(10), primary_key=True)
    MainCategoryName = Column(String(100), nullable=False)
    DisplayOrder = Column(Integer, nullable=True)

    sub_categories = relationship("ServiceSubCategory", back_populates="main_category")


class ServiceSubCategory(Base):
    __tablename__ = "ServiceSubCategory"
    __table_args__ = {"schema": "dbo"}
    SubCategoryCode = Column(String(20), primary_key=True)
    MainCategoryCode = Column(String(10), ForeignKey("dbo.ServiceMainCategory.MainCategoryCode"), nullable=False)
    SubCategoryName = Column(String(200), nullable=False)
    DefaultVendorCode = Column(String(10), nullable=True)
    GLAccount = Column(String(20), nullable=True)

    main_category = relationship("ServiceMainCategory", back_populates="sub_categories")
    service_types = relationship("ServiceType", back_populates="sub_category")


class ServiceType(Base):
    __tablename__ = "ServiceType"
    __table_args__ = {"schema": "dbo"}
    ServiceTypeCode = Column(String(10), primary_key=True)
    ServiceName = Column(String(200), nullable=False)
    CostAccount = Column(String(20), nullable=True)
    SubCategoryCode = Column(String(20), ForeignKey("dbo.ServiceSubCategory.SubCategoryCode"), nullable=True)

    sub_category = relationship("ServiceSubCategory", back_populates="service_types")


class ChartOfAccounts(Base):
    __tablename__ = "ChartOfAccounts"
    __table_args__ = {"schema": "dbo"}
    AccountCode = Column(String(20), primary_key=True)
    AccountName = Column(String(200), nullable=False)
    AccountType = Column(String(50), nullable=False)
    ParentAccount = Column(String(20), nullable=True)
    IsControlAccount = Column(Boolean, default=False)
    CurrencyCode = Column(String(3), nullable=True)


class PNRMaster(Base):
    __tablename__ = "PNRMaster"
    __table_args__ = {"schema": "dbo"}
    PNRNumber = Column(String(50), primary_key=True)
    ClientCode = Column(String(10), ForeignKey("dbo.Client.ClientCode"), nullable=True)
    EventName = Column(String(500), nullable=True)
    EventStartDate = Column(Date, nullable=True)
    EventEndDate = Column(Date, nullable=True)
    JobFolder = Column(String(200), nullable=True)
    Year = Column(Integer, nullable=True)
    Status = Column(String(20), nullable=True)
    CurrencyCode = Column(String(3), nullable=True)

    client = relationship("Client", back_populates="pnrs")
    sales_invoices = relationship("SalesInvoice", back_populates="pnr")
    purchase_vouchers = relationship("PurchaseVoucher", back_populates="pnr")


class ClientEmployee(Base):
    __tablename__ = "ClientEmployee"
    __table_args__ = {"schema": "dbo"}
    EmployeeID = Column(Integer, primary_key=True, autoincrement=True)
    ClientCode = Column(String(10), ForeignKey("dbo.Client.ClientCode"), nullable=False)
    EmployeeName = Column(String(200), nullable=False)
    Position = Column(String(100), nullable=True)
    Email = Column(String(200), nullable=True)
    Phone = Column(String(50), nullable=True)

    client = relationship("Client", back_populates="employees")


# ── Transaction Tables ────────────────────────────────────────

class PNRBudgetLineItem(Base):
    __tablename__ = "PNRBudgetLineItem"
    __table_args__ = {"schema": "dbo"}
    LineItemID = Column(BigInteger, primary_key=True, autoincrement=True)
    Year = Column(Integer, nullable=True)
    JobFolder = Column(String(500), nullable=True)
    FileName = Column(String(500), nullable=True)
    SheetName = Column(String(200), nullable=True)
    RowNumber = Column(Integer, nullable=True)
    MainCategoryCode = Column(String(10), nullable=True)
    SubCategoryCode = Column(String(20), nullable=True)
    ClientCode = Column(String(10), nullable=True)
    Description = Column(Text, nullable=True)
    Quantity = Column(Numeric(18,2), nullable=True)
    UnitPrice = Column(Numeric(18,2), nullable=True)
    Amount = Column(Numeric(18,2), nullable=True)
    CurrencyCode = Column(String(3), nullable=True)
    C1 = Column(String(500), nullable=True)
    C2 = Column(String(500), nullable=True)
    C3 = Column(String(500), nullable=True)
    C4 = Column(String(500), nullable=True)
    C5 = Column(String(500), nullable=True)
    C6 = Column(String(500), nullable=True)
    C7 = Column(String(500), nullable=True)
    C8 = Column(String(500), nullable=True)
    C9 = Column(String(500), nullable=True)
    C10 = Column(String(500), nullable=True)
    C11 = Column(String(500), nullable=True)
    C12 = Column(String(500), nullable=True)
    C13 = Column(String(500), nullable=True)
    C14 = Column(String(500), nullable=True)
    C15 = Column(String(500), nullable=True)
    C16 = Column(String(500), nullable=True)
    C17 = Column(String(500), nullable=True)
    C18 = Column(String(500), nullable=True)
    C19 = Column(String(500), nullable=True)
    C20 = Column(String(500), nullable=True)
    IsHeaderRow = Column(Boolean, default=False)


class SalesInvoice(Base):
    __tablename__ = "SalesInvoice"
    __table_args__ = {"schema": "dbo"}
    InvoiceID = Column(Integer, primary_key=True, autoincrement=True)
    InvoiceNumber = Column(String(50), nullable=True)
    PNRNumber = Column(String(50), ForeignKey("dbo.PNRMaster.PNRNumber"), nullable=True)
    ClientCode = Column(String(10), ForeignKey("dbo.Client.ClientCode"), nullable=True)
    EventName = Column(String(500), nullable=True)
    InvoiceDate = Column(Date, nullable=True)
    DueDate = Column(Date, nullable=True)
    TotalValue = Column(Numeric(18,2), nullable=True)
    CollectedAmount = Column(Numeric(18,2), nullable=True)
    PaymentStatus = Column(String(20), nullable=True)
    CurrencyCode = Column(String(3), nullable=True)

    pnr = relationship("PNRMaster", back_populates="sales_invoices")
    client = relationship("Client", back_populates="sales_invoices")
    lines = relationship("SalesInvoiceLine", back_populates="invoice")


class SalesInvoiceLine(Base):
    __tablename__ = "SalesInvoiceLine"
    __table_args__ = {"schema": "dbo"}
    InvoiceLineID = Column(Integer, primary_key=True, autoincrement=True)
    InvoiceID = Column(Integer, ForeignKey("dbo.SalesInvoice.InvoiceID"), nullable=False)
    ServiceTypeCode = Column(String(10), ForeignKey("dbo.ServiceType.ServiceTypeCode"), nullable=True)
    LineAmount = Column(Numeric(18,2), nullable=True)

    invoice = relationship("SalesInvoice", back_populates="lines")


class PurchaseVoucher(Base):
    __tablename__ = "PurchaseVoucher"
    __table_args__ = {"schema": "dbo"}
    VoucherID = Column(Integer, primary_key=True, autoincrement=True)
    VoucherNumber = Column(String(50), nullable=True)
    DocumentNumber = Column(String(50), nullable=True)
    PNRNumber = Column(String(50), ForeignKey("dbo.PNRMaster.PNRNumber"), nullable=True)
    EventName = Column(String(500), nullable=True)
    InvoiceDate = Column(Date, nullable=True)
    TotalValue = Column(Numeric(18,2), nullable=True)
    CurrencyCode = Column(String(3), nullable=True)

    pnr = relationship("PNRMaster", back_populates="purchase_vouchers")
    lines = relationship("PurchaseVoucherLine", back_populates="voucher")


class PurchaseVoucherLine(Base):
    __tablename__ = "PurchaseVoucherLine"
    __table_args__ = {"schema": "dbo"}
    VoucherLineID = Column(Integer, primary_key=True, autoincrement=True)
    VoucherID = Column(Integer, ForeignKey("dbo.PurchaseVoucher.VoucherID"), nullable=False)
    ServiceTypeCode = Column(String(10), ForeignKey("dbo.ServiceType.ServiceTypeCode"), nullable=True)
    VendorCode = Column(String(10), ForeignKey("dbo.Vendor.VendorCode"), nullable=True)
    ItemNarration = Column(Text, nullable=True)
    Quantity = Column(Numeric(18,2), nullable=True)
    NoOfNights = Column(Integer, nullable=True)
    UnitPrice = Column(Numeric(18,2), nullable=True)
    SubTotal = Column(Numeric(18,2), nullable=True)
    VATAmount = Column(Numeric(18,2), nullable=True)

    voucher = relationship("PurchaseVoucher", back_populates="lines")


class BankTransaction(Base):
    __tablename__ = "BankTransaction"
    __table_args__ = {"schema": "dbo"}
    TransactionID = Column(Integer, primary_key=True, autoincrement=True)
    TransactionDate = Column(Date, nullable=False)
    Payee = Column(String(200), nullable=True)
    DocumentType = Column(String(100), nullable=True)
    DocumentNumber = Column(String(50), nullable=True)
    Withdrawal = Column(Numeric(18,2), nullable=True)
    Deposit = Column(Numeric(18,2), nullable=True)
    RunningBalance = Column(Numeric(18,2), nullable=True)
    TransactionType = Column(String(50), nullable=True)
    JVNumber = Column(String(50), nullable=True)
    Narration = Column(Text, nullable=True)
    DrAccount = Column(String(20), nullable=True)
    CrAccount = Column(String(20), nullable=True)
    FromSubCategory = Column(String(200), nullable=True)
    ToSubCategory = Column(String(200), nullable=True)
    BankCode = Column(String(10), ForeignKey("dbo.Bank.BankCode"), nullable=True)
    CurrencyCode = Column(String(3), default="EGP")

    bank = relationship("Bank", back_populates="transactions")


class JournalVoucher(Base):
    __tablename__ = "JournalVoucher"
    __table_args__ = {"schema": "dbo"}
    JVNumber = Column(String(50), primary_key=True)
    JVDate = Column(Date, nullable=True)
    Narration = Column(Text, nullable=True)
    TotalDebit = Column(Numeric(18,2), nullable=True)
    TotalCredit = Column(Numeric(18,2), nullable=True)

    lines = relationship("JournalVoucherLine", back_populates="jv")


class JournalVoucherLine(Base):
    __tablename__ = "JournalVoucherLine"
    __table_args__ = {"schema": "dbo"}
    JVLineID = Column(Integer, primary_key=True, autoincrement=True)
    JVNumber = Column(String(50), ForeignKey("dbo.JournalVoucher.JVNumber"), nullable=False)
    AccountCode = Column(String(20), nullable=True)
    DebitAmount = Column(Numeric(18,2), nullable=True)
    CreditAmount = Column(Numeric(18,2), nullable=True)
    Narration = Column(Text, nullable=True)
    PNRNumber = Column(String(50), ForeignKey("dbo.PNRMaster.PNRNumber"), nullable=True)

    jv = relationship("JournalVoucher", back_populates="lines")
