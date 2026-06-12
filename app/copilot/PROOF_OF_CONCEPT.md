# Co-Pilot Smart Modules — Proof of Concept

## Overview
Floating AI panel that appears on every ERP form. Provides contextual
suggestions, auto-fill, budget guardrails, and reconciliation learning.

---

## Mockup 1: Smart Event Builder Form

```
  +------------------------------------------------------------------+
  |  IncentiveHouse ERP  [🧠 Co-Pilot]  User: Admin                  |
  +------------------------------------------------------------------+
  |                                                                   |
  |  CREATE NEW EVENT                                      [AI] 🤖   |
  |  ┌──────────────────────────────────────────────┐  ┌──────────┐ |
  |  │ Event Name: [Annual Gala Dinner           ] │  │ Co-Pilot │ |
  |  │ Client:     [Acme Corp                    ] │  │ Panel ☼  │ |
  |  │ Date:       [2026-09-15]  Budget: [250,000] │  │          │ |
  |  │ Type:       [▼ Corporate Event            ] │  │ ● Suggest│ |
  |  │ Venue:      [Grand Ballroom               ] │  │   Budget │ |
  |  │ ──────────────────────────────────────────  │  │ ● Suggest│ |
  |  │ [Line Items]                                │  │   Vendors│ |
  |  │ + Catering     $45,000  [80 guests]         │  │ ● Suggest│ |
  |  │ + AV Rental    $12,000  [basic pkge]        │  │   Staff  │ |
  |  │ + Decor        $18,000  [premium]           │  │ ● Check  │ |
  |  │ + Security     $8,000   [4 guards]          │  │   Budget │ |
  |  │─────────────────────────────────────────────│  │ ● Auto-  │ |
  |  │ Total: $83,000  //  Budget Remaining: 67%   │  │   Fill   │ |
  |  │                                             │  │          │ |
  |  │ [SAVE DRAFT] [SUBMIT] [CANCEL]              │  │ [ASK AI] │ |
  |  └──────────────────────────────────────────────┘  └──────────┘ |
  |                                                                   |
  |  CO-PILOT SUGGESTIONS:                                            |
  |  ┌──────────────────────────────────────────────────────────────┐ |
  |  │ 💡 Based on similar "Corporate Event" events:               │ |
  |  │   • Avg budget: $220K — yours is $250K (13% above avg)      │ |
  |  │   • Top vendors: Elite Catering (98% score), AV Pro (92%)   │ |
  |  │   • Recommended staff: 2 coordinators, 4 event staff         │ |
  |  │   • Budget alert: Decor is 22% of total (avg is 15%)         │ |
  |  │ [Apply All] [Apply Vendors] [Dismiss]                        │ |
  |  └──────────────────────────────────────────────────────────────┘ |
  +------------------------------------------------------------------+
```

## Mockup 2: PO Generator Panel

```
  +------------------------------------------------------------------+
  |  PURCHASE ORDER #PO-2026-0042                       [🧠 Co-Pilot]|
  +------------------------------------------------------------------+
  |                                                                   |
  |  Event: Annual Gala Dinner  |  Client: Acme Corp                 |
  |  Budget Remaining: $167,000 |  Used: $83,000 / $250,000          |
  |                                                                   |
  |  ┌──────────────────────────────────────────────────────────────┐ |
  |  │ PO DETAILS                                   CO-PILOT       │ |
  |  │ ──────────────────────────                   ─────────       │ |
  |  │ Supplier: [▼ Elite Catering         ]        98% score       │ |
  |  │ Item:     [Catering Services - Premium]      ✓ Budget OK     │ |
  |  │ Qty:      [80]  Unit: [Per Person]           ✓ Supplier     │ |
  |  │ Rate:     [562.50]  Total: $45,000            Active         │ |
  |  │ ──────────────────────────                   ─────────       │ |
  |  │ Delivery: [2026-09-14]                       ● Auto-PO      │ |
  |  │ Payment:  [▼ Net 30]                          Suggested      │ |
  |  │ ──────────────────────────                     Line Items    │ |
  |  │ Notes: [Gala dinner setup incl.]               ● Check       │ |
  |  │                                                  Duplicates  │ |
  |  │ [GENERATE PO] [SAVE DRAFT]                    ● Optimize     │ |
  |  │                                                  Supplier    │ |
  |  └──────────────────────────────────────────────────────────────┘ |
  |                                                                   |
  |  CO-PILOT: ✅ PO lines align with budget. No duplicates found.   |
  |  ⚠️ This supplier has 2 pending deliveries — consider rush fee. |
  |  [Override] [Dismiss]                                            |
  +------------------------------------------------------------------+
```

## Mockup 3: Smart Reconciliation Workbench

```
  +------------------------------------------------------------------+
  |  BANK RECONCILIATION v2                            [🧠 Co-Pilot] |
  +------------------------------------------------------------------+
  |                                                                   |
  |  Account: IH Operations (XXXX-4821)   Period: June 2026          |
  |  ┌──────────────────────────────────────────────────────────────┐ |
  |  │ TRANSACTIONS          Bank $     System $  Match  AI Score   │ |
  |  │ ────────────────────────────────────────────────────────────  │ |
  |  │ ✓ INV-001  Catering    45,000.00  45,000.00  100%   0.99    │ |
  |  │ ✓ INV-002  AV Rental   12,000.00  12,000.00  100%   0.97    │ |
  |  │ ⚠ TRX-003  Decor Dep   18,000.00  18,500.00  97%    0.82    │ |
  |  │ ? TRX-004  Unknown      2,500.00   —           0%     —      │ |
  |  │ ✗ INV-005  Cancelled    5,000.00   —          Void    —      │ |
  |  │ ? TRX-006  Insurance    1,200.00   1,250.00  96%    0.79    │ |
  |  └──────────────────────────────────────────────────────────────┘ |
  |                                                                   |
  |  LEARNING: Pattern "Decor Deposit" → expected 3-5% variance      |
  |  SUGGESTION: 3 auto-matches ready. 2 need review.                |
  |  [Auto-Match All] [Review Suspicious] [Learn Pattern]            |
  |                                                                   |
  |  Co-Pilot has learned 147 patterns from 2,341 reconciliations.   |
  |  Last manual correction: 3 days ago (decreased by 12%)           |
  +------------------------------------------------------------------+
```

## Mockup 4: Financial Cockpit

```
  +------------------------------------------------------------------+
  |  FINANCIAL COCKPIT (Live)                        [🧠 Co-Pilot]   |
  +------------------------------------------------------------------+
  |                                                                   |
  |  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           |
  |  │ P&L This Month│  │ Cash Position│  │ Budget Status│           |
  |  │ Revenue: $1.2M│  │ Current: $487K│ │ Used:  62%   │           |
  |  │ Cost:   $0.8M │  │ Projected:    │ │ Remaining:    │           |
  |  │ Gross:   $0.4M│  │ 30d: $320K    │ │ $1.2M of $3.2M│          |
  |  │ Margin:   33% │  │ 60d: $180K    │ │ ⚠️ 3 events   │          |
  |  └──────────────┘  └──────────────┘  │ at 85%+ usage │          |
  |                                      └──────────────┘           |
  |                                                                   |
  |  TIMELINE: [▬▬▬▬▬▬▬▬▬▬▬▬▬●▬▬▬▬▬▬] June 2026                    |
  |                                                                   |
  |  CO-PILOT INSIGHTS:                                              |
  |  ┌──────────────────────────────────────────────────────────────┐ |
  |  │ 🔴 ALERT: Gala Dinner budget at 85% with 2 months to go     │ |
  |  │ 🟡 WARNING: 3 POs not confirmed for next week's event        │ |
  |  │ 🟢 GOOD: Monthly revenue tracking 8% above forecast          │ |
  |  │ 💡 TIP: Renegotiate AV vendor — avg cost up 12% YoY          │ |
  |  [View Details] [Generate Report] [Dismiss All]                 │ |
  |  └──────────────────────────────────────────────────────────────┘ |
  +------------------------------------------------------------------+
```

## Visual Style Guide

```
  Color Palette:
  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │ Primary  │  │ Accent   │  │ Success  │  │ Warning  │
  │ #667eea  │  │ #764ba2  │  │ #22c55e  │  │ #eab308  │
  │ (Blue)   │  │ (Purple) │  │ (Green)  │  │ (Yellow) │
  └──────────┘  └──────────┘  └──────────┘  └──────────┘

  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │ Danger   │  │ Dark     │  │ Light    │
  │ #ef4444  │  │ #1a1a2e  │  │ #f8fafc  │
  │ (Red)    │  │ (Bg)     │  │ (Text)   │
  └──────────┘  └──────────┘  └──────────┘

  Font: Segoe UI, system-ui, sans-serif
  Border Radius: 8-12px
  Shadows: Subtle (rgba(0,0,0,0.1))
```

## Component Tree

```
  Co-Pilot Panel (floating, bottom-right)
  ├── Header (gradient purple-blue)
  │   ├── Title + AI status dot
  │   └── Close button
  ├── Body
  │   ├── Context Cards (form-specific)
  │   │   ├── Event: budget, vendors, staff suggestions
  │   │   ├── PO: supplier score, duplicate check, budget OK
  │   │   ├── Recon: match score, pattern, suggestion
  │   │   └── Financial: alerts, KPIs, tips
  │   ├── Quick Actions
  │   │   ├── [Apply All] [Apply One] [Dismiss]
  │   │   └── [Learn Pattern] [Override]
  │   └── Chat Input
  │       └── [Ask AI about this form...] [➤]
  └── Footer
      ├── Model status (Local OLMo / Rule-based)
      └── Confidence indicator
```
