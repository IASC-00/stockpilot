# Project 5: Ops & Inventory Automation

## Live Demo
**[stockpilot-inni.onrender.com](https://stockpilot-inni.onrender.com)**

## Service Demonstrated
**Operations & Inventory Automation** — clients (retail, hospitality, small
manufacturers) get a custom system replacing manual spreadsheet inventory tracking
with a real-time dashboard, low-stock alerts, and reorder automation.

## Goal
Build a polished inventory management demo for a fictional shop ("Harbor Coffee Co.
Supply Room") — showing real-time stock levels, low-stock alerts, reorder workflows,
supplier management, and an AI-powered weekly ops summary.

## Demo Deliverable
- Flask web dashboard: live inventory table with search, filter, sort
- Stock intake: add received shipment → updates quantity instantly
- Stock usage: mark items as used/sold → decrements stock
- Low-stock alerts: configurable threshold per item → badge + email-ready notification
- Reorder workflow: one-click "Create Purchase Order" → printable PO PDF
- AI weekly summary: Claude analyzes stock movements + flags anomalies + recommends reorder quantities
- Supplier directory: contact info, lead times, MOQs

## Tech Stack
- Python 3.12
- Flask (web app + REST API)
- SQLite + SQLAlchemy (inventory, transactions, suppliers, purchase orders)
- Anthropic SDK (Claude Haiku — weekly AI ops summary)
- WeasyPrint (PDF purchase orders)
- Vanilla JS (live search, modal forms, real-time stock level updates)
- CSS (clean ops dashboard, status color coding)

---

## Roadmap

### Phase 1 — Data Model
- [ ] `items(id, sku, name, category, unit, quantity, reorder_threshold, reorder_qty, supplier_id, unit_cost)`
- [ ] `transactions(id, item_id, type[intake|usage|adjustment], quantity, note, ts, user)`
- [ ] `suppliers(id, name, contact_name, email, phone, lead_days, moq)`
- [ ] `purchase_orders(id, supplier_id, status[draft|sent|received], created_at, items_json)`
- [ ] Seed script: 25 sample items across 4 categories (beverages, supplies, equipment, packaging)

### Phase 2 — Core Inventory Routes
- [ ] GET `/api/inventory` — full item list with current quantities, low-stock flag
- [ ] POST `/api/intake` — add received shipment (item_id, qty, note) → `transactions` record
- [ ] POST `/api/usage` — mark used/sold (item_id, qty, note) → `transactions` record
- [ ] POST `/api/adjust` — manual correction with reason
- [ ] GET `/api/transactions?item_id=&days=30` — movement history
- [ ] GET `/api/low-stock` — items below threshold

### Phase 3 — Dashboard UI
- [ ] Inventory table: SKU, name, category, current qty, threshold, status badge (OK/LOW/OUT)
- [ ] Color coding: green (ok), amber (low), red (out)
- [ ] Search: filter by name or SKU (client-side, instant)
- [ ] Category filter tabs
- [ ] Quick-action buttons: "+ Intake" / "- Usage" per row (modal)
- [ ] Modal form: quantity input, optional note, confirm
- [ ] Stock level bar: visual fill indicator (qty / (threshold × 3))

### Phase 4 — Alerts & Notifications
- [ ] Low-stock alert banner: "3 items below threshold" with link to filtered view
- [ ] Alert log: history of when items crossed threshold
- [ ] Email notification draft: template showing what an email alert would look like
  (actual sending optional — use Flask-Mail or just render the template)
- [ ] Per-item threshold editor: click to set/update reorder_threshold inline

### Phase 5 — Purchase Order Workflow
- [ ] "Reorder" button on low-stock items → adds to PO draft for that supplier
- [ ] PO draft page: grouped by supplier, editable quantities, unit costs
- [ ] Confirm PO → saves to DB with status=draft
- [ ] PDF generation: `/po/<id>/pdf` → WeasyPrint renders printable PO
  (PO number, date, supplier contact, line items, total cost)
- [ ] Mark PO as received → auto-intake all line items

### Phase 6 — Supplier Directory
- [ ] `/suppliers` — list all suppliers with contact info + lead days + MOQ
- [ ] Add/edit supplier form
- [ ] Supplier detail: open POs, items sourced from them, avg delivery time
- [ ] Lead time warning: "If reordered today, arrives [date]"

### Phase 7 — AI Weekly Summary
- [ ] GET `/api/ai-summary` — analyzes last 7 days of transactions
- [ ] Claude prompt includes:
  - Items with highest usage velocity
  - Items approaching threshold
  - Unusual usage spikes (> 2× normal daily rate)
  - Recommended reorder quantities based on velocity
- [ ] Output: 200-word plain-English ops summary + bullet action items
- [ ] Shown in dashboard sidebar, refreshes on demand

### Phase 8 — Polish & Demo Packaging
- [ ] Mobile responsive (table becomes card stack on small screens)
- [ ] Demo data reset button (reseed to clean state for demos)
- [ ] Export: download full inventory as CSV
- [ ] Loading states on all async actions
- [ ] Record demo GIF + screenshots for portfolio
- [ ] Deploy to Render.com
- [ ] Add to iswain.dev projects section

---

## Success Criteria
- Intake and usage flows update stock level without page reload
- Low-stock detection fires correctly at threshold boundary
- PO PDF renders with all line items and totals correctly
- AI summary correctly identifies the highest-velocity item from test data
- Demo data reset leaves system in clean, deterministic state

## Key Files
```
05-ops-inventory/
├── app.py                  # Flask routes
├── models.py               # SQLAlchemy models
├── seed.py                 # demo data seeder + reset
├── ai_summary.py           # Claude weekly summary generator
├── po_generator.py         # PDF PO generation via WeasyPrint
├── static/
│   ├── dashboard.js        # live search, modals, stock updates
│   └── style.css
├── templates/
│   ├── index.html          # main inventory dashboard
│   ├── suppliers.html      # supplier directory
│   ├── po_list.html        # purchase orders
│   └── po_print.html       # printable PO layout (PDF target)
├── .env.example
└── requirements.txt
```

## Business Context
This demo mirrors real workflows from my experience managing multi-location retail
operations (Charm City Hemp, Harbor Vapor). The pain points — manual spreadsheets,
missed reorders, no supplier visibility — are real problems I solved operationally.
This tool automates exactly what I used to do by hand.
