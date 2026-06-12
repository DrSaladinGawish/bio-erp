# Co-Pilot Smart Supportive ERP — Proof of Concept Mockups

> **All designs are 100% local AI — no cloud APIs required**

---

## 🎨 MOCKUP 1: Smart Event Builder Form

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🏢 IncentiveHouse ERP                                      🤖 Co-Pilot ▼ │
│  ══════════════════════════════════════════════════════════════════════════ │
│                                                                             │
│  📅 NEW EVENT                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ Client:        [ CISCO ▼ ]                                          │   │
│  │                💡 "84 past events, avg budget 670K EGP"              │   │
│  │                [✓ Use last template] [✓ Auto-populate]              │   │
│  │                                                                     │   │
│  │ Event Type:    [ Corporate Meeting ▼ ]                              │   │
│  │                📊 Historical: 84 events | Avg: 670K | Range: 400K-1.2M│   │
│  │                                                                     │   │
│  │ Budget:        [ 750,000 ] 💰                                       │   │
│  │                ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 112% of avg        │   │
│  │                ⚠️  15% above historical average                     │   │
│  │                ⚠️  Client has 2 unpaid invoices (180K total)          │   │
│  │                                                                     │   │
│  │ Venue:         [ Four Seasons ▼ ]                                   │   │
│  │                ⭐ 4.8★ (used 12x by CISCO, 98% on-time)            │   │
│  │                🏷️  Alternative: Nile Ritz (cheaper, 4.5★)            │   │
│  │                                                                     │   │
│  │ Staff:         [ 8 ] 👥                                             │   │
│  │                🤖 Suggested: Ahmed (Lead), Sara, Mohamed...           │   │
│  │                [Accept All] [Modify]                                │   │
│  │                                                                     │   │
│  │ 📋 AUTO-GENERATED LINE ITEMS:                                       │   │
│  │  ┌─────────────┬────────┬────────┬────────┬─────────────────────┐    │   │
│  │  │ Item        │ Qty    │ Rate   │ Amount │ Source              │    │   │
│  │  ├─────────────┼────────┼────────┼────────┼─────────────────────┤    │   │
│  │  │ AV Setup    │ 1      │ 45,000 │ 45,000 │ ✓ CISCO history    │    │   │
│  │  │ Catering    │ 80     │ 850    │ 68,000 │ ✓ CISCO history    │    │   │
│  │  │ Transport   │ 2      │ 5,000  │ 10,000 │ ✓ CISCO history    │    │   │
│  │  │ ...         │ ...    │ ...    │ ...    │                    │    │   │
│  │  └─────────────┴────────┴────────┴────────┴─────────────────────┘    │   │
│  │                                                                     │   │
│  │ 💡 NEXT ACTIONS:                                                    │   │
│  │    [Create POs] [Book Venue] [Notify Team] [Schedule Rehearsal]    │   │
│  │                                                                     │   │
│  │  [💾 Save & Continue]  [📝 Save Draft]  [❌ Cancel]                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 🤖 CO-PILOT PANEL (Floating)                                        │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  ⚡ Quick Actions                                                   │   │
│  │    → Create POs from Line Items                    [Run]            │   │
│  │    → Optimize Supplier Selection                     [Run]            │   │
│  │    → Generate Event Timeline                        [Run]            │   │
│  │                                                                     │   │
│  │  💡 Tips                                                            │   │
│  │    • Budget 15% contingency typical for CISCO events                 │   │
│  │    • Book venue 30 days ahead for June events                      │   │
│  │                                                                     │   │
│  │  📊 Insights                                                        │   │
│  │    • Similar events avg 12% profit margin                          │   │
│  │    • Recommended deposit: 50% upfront                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎨 MOCKUP 2: Intelligent PO Generator

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🏢 IncentiveHouse ERP                                      🤖 Co-Pilot ▼ │
│  ══════════════════════════════════════════════════════════════════════════ │
│                                                                             │
│  📦 GENERATE PURCHASE ORDERS — Event #1: CISCO Annual Meet                │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │ 📋 EVENT LINE ITEMS → PO RECOMMENDATIONS                            │   │
│  │                                                                     │   │
│  │ ┌─────────────────────────────────────────────────────────────────┐ │   │
│  │ │ PO #1 — AudioVis Pro (Score: 0.88 ⭐⭐⭐⭐)                        │ │   │
│  │ │ Confidence: HIGH  │  Delivery: 3 days  │  On-time: 95%          │ │   │
│  │ ├─────────────────────────────────────────────────────────────────┤ │   │
│  │ │ Item        Qty    Unit    Total    Supplier Score              │ │   │
│  │ │ AV Setup    1      45,000  45,000   ████████░░ 0.88            │ │   │
│  │ │ Sound Sys   2      8,500   17,000   ███████░░░ 0.82            │ │   │
│  │ │ Lighting    1      12,000  12,000   ████████░░ 0.85            │ │   │
│  │ │                                          Subtotal:   74,000     │ │   │
│  │ │                                          VAT (14%):  10,360     │ │   │
│  │ │                                          TOTAL:      84,360     │ │   │
│  │ │                                          Budget Used: 11.2%     │ │   │
│  │ │ [✓ Approve] [✏️ Edit] [🔄 Find Alternative]                     │ │   │
│  │ └─────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                     │   │
│  │ ┌─────────────────────────────────────────────────────────────────┐ │   │
│  │ │ PO #2 — Nile Ritz F&B (Score: 0.87 ⭐⭐⭐⭐)                     │ │   │
│  │ │ Confidence: HIGH  │  Delivery: 5 days  │  On-time: 92%          │ │   │
│  │ ├─────────────────────────────────────────────────────────────────┤ │   │
│  │ │ Catering    80     850     68,000   ████████░░ 0.87            │ │   │
│  │ │ Beverages   80     150     12,000   ███████░░░ 0.79            │ │   │
│  │ │                                          Subtotal:   80,000     │ │   │
│  │ │                                          VAT (14%):  11,200     │ │   │
│  │ │                                          TOTAL:      91,200     │ │   │
│  │ │                                          Budget Used: 12.2%     │ │   │
│  │ │ [✓ Approve] [✏️ Edit] [🔄 Find Alternative]                     │ │   │
│  │ └─────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                     │   │
│  │ 💰 BUDGET GUARDRAILS                                                │   │
│  │    Total PO Impact: 175,560 EGP  │  Budget Remaining: 574,440    │   │
│  │    Status: ✅ WITHIN BUDGET (23.4% utilized)                       │   │
│  │                                                                     │   │
│  │ [📤 Approve All POs]  [📊 View Budget]  [⚙️ Optimize Suppliers]    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎨 MOCKUP 3: Smart Reconciliation v2

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🏢 IncentiveHouse ERP                                      🤖 Co-Pilot ▼ │
│  ══════════════════════════════════════════════════════════════════════════ │
│                                                                             │
│  🏦 BANK RECONCILIATION — Bnk_Cur Account                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │ 📊 SUMMARY CARDS                                                    │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │   │
│  │  │ 2,501      │  │ 1,947      │  │ 412        │  │ 142      │ │   │
│  │  │ Total TXNs │  │ Auto-Match │  │ Suggested │  │ Exception│ │   │
│  │  │            │  │ 77.8%      │  │ 16.5%     │  │ 5.7%     │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘ │   │
│  │                                                                     │   │
│  │ 🔄 RECONCILIATION GRID                                              │   │
│  │  ┌──────┬─────────────────────┬─────────┬─────────┬────────┬────────┐│   │
│  │  │ #    │ Narration           │ Amount  │ Match   │ Status │ Action ││   │
│  │  ├──────┼─────────────────────┼─────────┼─────────┼────────┼────────┤│   │
│  │  │ 0001 │ CISCO INV-001       │ 45,000  │ INV-001 │ ✅ Auto│ [View] ││   │
│  │  │ 0002 │ SALARY TRANSFER     │ 125,000 │ SL-245  │ ✅ Auto│ [View] ││   │
│  │  │ 0003 │ MR MAGED ATM        │ 5,000   │ SL-428  │ ✅ Auto│ [View] ││   │
│  │  │ 0004 │ NILE RITZ CATERING  │ 68,000  │ PO-002  │ 💡 Sug │ [Conf] ││   │
│  │  │ 0005 │ UNKNOWN VENDOR XYZ  │ 12,500  │ —       │ ⚠️ Exc │ [Fix]  ││   │
│  │  │ 0006 │ PETTY CASH REPLENISH│ 3,000   │ SL-178  │ 💡 Sug │ [Conf] ││   │
│  │  │ ...  │ ...                 │ ...     │ ...     │ ...    │ ...    ││   │
│  │  └──────┴─────────────────────┴─────────┴─────────┴────────┴────────┘│   │
│  │                                                                     │   │
│  │ 🔧 EXCEPTION QUEUE (142 items)                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │   │
│  │  │ TXN #0005 — UNKNOWN VENDOR XYZ (12,500 EGP)                     │ │   │
│  │  │ 🤖 Suggested: Category="Supplies", Sub-Ledger="1009"            │ │   │
│  │  │     Confidence: 62%  │  Reason: Keyword "vendor" detected       │ │   │
│  │  │ [✓ Confirm] [✏️ Edit] [🔍 Search] [🚫 Skip]                       │ │   │
│  │  │                                                                  │ │   │
│  │  │ TXN #0042 — INTERNATIONAL WIRE (150,000 USD)                    │ │   │
│  │  │ 🤖 Suggested: Category="Client Payment", Sub-Ledger="1439"      │ │   │
│  │  │     Confidence: 71%  │  Reason: Large amount + "wire" pattern   │ │   │
│  │  │ [✓ Confirm] [✏️ Edit] [🔍 Search] [🚫 Skip]                       │ │   │
│  │  └─────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                     │   │
│  │ [🤖 Smart Recon All] [📤 Export Excel] [📤 Export CSV] [Promote]   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎨 MOCKUP 4: Live Financial Cockpit

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🏢 IncentiveHouse ERP                                      🤖 Co-Pilot ▼ │
│  ══════════════════════════════════════════════════════════════════════════ │
│                                                                             │
│  📊 LIVE FINANCIAL COCKPIT                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │ 💰 COMPANY SUMMARY                                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │   │
│  │  │ 1.6M       │  │ 1.1M       │  │ 900K       │  │ 200K     │ │   │
│  │  │ Gross Sales│  │ Invoiced   │  │ Collected  │  │ Outstanding│ │   │
│  │  │            │  │            │  │            │  │           │ │   │
│  │  │ Margin:    │  │ Collection:│  │            │  │           │ │   │
│  │  │ 18.5% GP   │  │ 81.8% rate │  │            │  │           │ │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └───────────┘ │   │
│  │                                                                     │   │
│  │ 📈 CASH FLOW PROJECTION (Next 30 Days)                              │   │
│  │                                                                     │   │
│  │  Balance (EGP)                                                      │   │
│  │  1.5M ┤    ╭─╮                                                      │   │
│  │  1.0M ┤   ╭╯ ╰╮    ╭──╮                                             │   │
│  │  500K ┤  ╭╯   ╰────╯  ╰──╮                                          │   │
│  │    0K ┤──╯                 ╰────── ⚠️ Negative projected Jun 19    │   │
│  │ -500K ┤                                                            │   │
│  │       └────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬    │   │
│  │           W1   W2   W3   W4   W5   W6   W7   W8   W9  W10  W11    │   │
│  │                                                                     │   │
│  │  Inflows:  450K  →  300K  →  200K  →  150K  →  100K               │   │
│  │  Outflows: 200K  →  350K  →  400K  →  250K  →  200K               │   │
│  │                                                                     │   │
│  │  ⚠️ ALERT: Negative cash projected on June 19, 2026              │   │
│  │     Action: Accelerate CISCO collection (300K due) or defer PO payments│   │
│  │                                                                     │   │
│  │ 📋 EVENT FINANCIALS                                                 │   │
│  │  ┌────┬────────────────────┬─────────┬─────────┬────────┬─────────┐│   │
│  │  │ #  │ Event              │ Budget  │ Actual  │ Margin │ Status  ││   │
│  │  ├────┼────────────────────┼─────────┼─────────┼────────┼─────────┤│   │
│  │  │ 1  │ CISCO Annual Meet  │ 700K    │ 680K    │ 9.3%   │ 🟢 OK   ││   │
│  │  │ 2  │ Microsoft Launch   │ 450K    │ 480K    │ -6.7%  │ 🔴 CRIT ││   │
│  │  │ 3  │ Noventiq Conf      │ 300K    │ 290K    │ 17.1%  │ 🟢 OK   ││   │
│  │  └────┴────────────────────┴─────────┴─────────┴────────┴─────────┘│   │
│  │                                                                     │   │
│  │  🔴 CRITICAL EVENTS: 1  │  🟡 WARNING: 0  │  🟢 ON TRACK: 2          │   │
│  │                                                                     │   │
│  │ [📊 Full Report] [💰 Cash Flow Details] [📧 Email to Finance]     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎨 MOCKUP 5: Co-Pilot Floating Panel (All Forms)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 🤖 Co-Pilot                                              [_] [✕]   │   │
│  │  ═════════════════════════════════════════════════════════════════  │   │
│  │                                                                     │   │
│  │  ⚡ QUICK ACTIONS                                                   │   │
│  │    → Create POs from Line Items              [Run →]               │   │
│  │    → Optimize Supplier Selection               [Run →]               │   │
│  │    → Run Smart Reconciliation                [Run →]               │   │
│  │                                                                     │   │
│  │  ⚠️ ALERTS (2)                                                      │   │
│  │    🔴 Budget exceeded on Event #2 (Microsoft)                      │   │
│  │    🟡 Supplier AudioVis Pro delayed 3x this month                  │   │
│  │                                                                     │   │
│  │  💡 INSIGHTS                                                        │   │
│  │    • CISCO events avg 15% contingency — add 112K buffer           │   │
│  │    • Best booking window: 30 days ahead for June events             │   │
│  │                                                                     │   │
│  │  ✅ TIPS                                                            │   │
│  │    • Use template from last CISCO event (saves 45 min)            │   │
│  │    • Auto-match rate: 78% — review exceptions daily               │   │
│  │                                                                     │   │
│  │  🔗 SHORTCUTS                                                       │   │
│  │    [Events] [POs] [Recon] [Finance] [Staff] [Reports]             │   │
│  │                                                                     │   │
│  │  ────────────────────────────────────────────────────────────────  │   │
│  │  Local AI • 45ms • v1.0.0                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  [This panel floats on every form — bottom-right corner]                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎨 MOCKUP 6: Ask OLMo — Local LLM Chat

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🏢 IncentiveHouse ERP                                      🤖 Co-Pilot ▼ │
│  ══════════════════════════════════════════════════════════════════════════ │
│                                                                             │
│  💬 ASK CO-PILOT (OLMo Local LLM)                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  🤖 Co-Pilot: Hello! I can help you with:                          │   │
│  │     • Event planning and budgeting                                  │   │
│  │     • Supplier selection and PO optimization                        │   │
│  │     • Bank reconciliation and categorization                        │   │
│  │     • Financial analysis and cash flow projections                  │   │
│  │                                                                     │   │
│  │  👤 You: What should I budget for a CISCO event with 100 attendees?  │   │
│  │                                                                     │   │
│  │  🤖 Co-Pilot: Based on 84 historical CISCO events:                 │   │
│  │     • Average budget: 670,000 EGP                                    │   │
│  │     • For 100 attendees: estimate 750,000 - 850,000 EGP              │   │
│  │     • Typical breakdown:                                           │   │
│  │       - AV/Production: 35% (245K - 280K)                            │   │
│  │       - Catering: 30% (210K - 240K)                                │   │
│  │       - Venue: 20% (140K - 160K)                                    │   │
│  │       - Transport/Logistics: 10% (70K - 80K)                        │   │
│  │       - Contingency: 5% (35K - 40K)                                  │   │
│  │     • Recommended: 800,000 EGP with 15% contingency (920K total)   │   │
│  │                                                                     │   │
│  │  [💬 Ask follow-up...]  [📋 Copy]  [📊 View Details]                 │   │
│  │                                                                     │   │
│  │  ⚡ Powered by OLMo-1B (local) • Response time: 2.3s               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎨 MOCKUP 7: Mobile Responsive View

```
┌─────────────────────────────┐
│  IncentiveHouse ERP    ☰  │
│  ═══════════════════════════ │
│                             │
│  📊 Dashboard               │
│                             │
│  ┌───────────────────────┐  │
│  │ 💰 Cash: 900K EGP     │  │
│  │ ⚠️  Alert: -500K Jun19│  │
│  └───────────────────────┘  │
│                             │
│  ┌───────────────────────┐  │
│  │ 📅 Active Events: 3   │  │
│  │ 🔴 1 Critical         │  │
│  └───────────────────────┘  │
│                             │
│  ┌───────────────────────┐  │
│  │ 🏦 Recon: 78% Auto    │  │
│  │ 142 exceptions pending│  │
│  └───────────────────────┘  │
│                             │
│  [+] New Event              │
│                             │
│  ┌───────────────────────┐  │
│  │ 🤖 Co-Pilot           │  │
│  │ ⚡ 3 actions pending  │  │
│  │ ⚠️  2 alerts          │  │
│  │ [Tap to expand →]     │  │
│  └───────────────────────┘  │
│                             │
│  [Home] [Events] [Finance]  │
└─────────────────────────────┘
```

---

## 📐 Design System

### Colors
| Token | Dark | Light |
|-------|------|-------|
| Primary | `#667eea` → `#764ba2` | Same |
| Background | `#1a1a2e` | `#ffffff` |
| Surface | `rgba(255,255,255,0.05)` | `#f8fafc` |
| Text Primary | `#e0e0e0` | `#1e293b` |
| Text Secondary | `#8892b0` | `#64748b` |
| Success | `#22c55e` | `#16a34a` |
| Warning | `#eab308` | `#ca8a04` |
| Error | `#ef4444` | `#dc2626` |

### Typography
| Element | Size | Weight |
|---------|------|--------|
| Header Title | 14px | 600 |
| Section Title | 10px | 600 |
| Body | 12-13px | 400 |
| Badge | 10px | 600 |

### Spacing
- Panel width: 380px desktop, 100vw mobile
- Section padding: 12px 14px
- Card border-radius: 8px
- Panel border-radius: 12px

---

**All mockups are implemented in the actual code files above.**
