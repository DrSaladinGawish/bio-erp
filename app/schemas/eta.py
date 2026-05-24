from pydantic import BaseModel
from datetime import datetime
from typing import Literal
from decimal import Decimal


class ETAAddress(BaseModel):
    branchID: str | None = None
    country: str = "EG"
    governate: str | None = None
    regionCity: str | None = None
    street: str | None = None
    buildingNumber: str | None = None
    postalCode: str | None = None
    floor: str | None = None
    room: str | None = None
    landmark: str | None = None
    additionalInformation: str | None = None


class ETAIssuer(BaseModel):
    type: Literal["B", "P", "F"] = "B"
    id: str
    name: str
    address: ETAAddress
    registrationNumber: str | None = None


class ETAParty(BaseModel):
    type: Literal["B", "P", "F"] | None = "B"
    id: str | None = None
    name: str | None = None
    address: ETAAddress | None = None


class ETAValue(BaseModel):
    currencySold: str = "EGP"
    amountEGP: Decimal = Decimal("0.00")
    amountSold: Decimal | None = None
    currencyExchangeRate: Decimal | None = None


class ETATaxableItem(BaseModel):
    taxType: Literal[
        "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11", "T12"
    ]
    amount: Decimal
    subType: str | None = None
    rate: Decimal = Decimal("14.00")


class ETAInvoiceLine(BaseModel):
    description: str
    itemType: Literal["GS1", "EGS", "HS"]
    itemCode: str
    unitType: str
    quantity: Decimal
    internalCode: str | None = None
    salesTotal: Decimal
    total: Decimal
    valueDiscount: Decimal = Decimal("0.00")
    discount: ETAValue = ETAValue()
    taxableItems: list[ETATaxableItem]
    netTotal: Decimal
    itemsDiscount: Decimal | None = Decimal("0.00")


class ETADocument(BaseModel):
    issuer: ETAIssuer
    receiver: ETAParty | None = None
    documentType: Literal["I", "C", "D", "S"] = "I"
    documentTypeVersion: Literal["1.0", "0.9"] = "1.0"
    dateTimeIssued: datetime
    taxpayerActivityCode: str = "6201"
    internalID: str
    purchaseOrderReference: str | None = None
    purchaseOrderDescription: str | None = None
    salesOrderReference: str | None = None
    salesOrderDescription: str | None = None
    proformaInvoiceNumber: str | None = None
    payment: dict | None = None
    delivery: dict | None = None
    totalDiscountAmount: Decimal | None = Decimal("0.00")
    totalSalesAmount: Decimal
    netAmount: Decimal
    taxTotals: list[ETATaxableItem]
    totalAmount: Decimal
    extraDiscountAmount: Decimal | None = Decimal("0.00")
    totalItemsDiscountAmount: Decimal | None = Decimal("0.00")
    invoiceLines: list[ETAInvoiceLine]


class ETASubmissionResponse(BaseModel):
    submissionId: str
    acceptedDocuments: list | None = None
    rejectedDocuments: list | None = None
    documentCount: int


class ETAStatusResponse(BaseModel):
    uuid: str
    longId: str | None = None
    internalId: str
    status: Literal["Pending", "Valid", "Invalid", "Submitted", "Rejected", "Cancelled"]
    rejectionReason: str | None = None
