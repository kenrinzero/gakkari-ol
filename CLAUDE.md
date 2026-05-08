# Gakkari OL

Terminal subscription tracker. Python + Textual TUI, SQLite storage, local-only.

**Tone:** calm, serious, readable, slightly stylized. The anime office-lady mascot is presentation polish added in Phase 4 — it is not the product. No gamification.

---

## Running the app

```powershell
cd C:\Users\kenrin\Project\Gakkari_OL
.venv\Scripts\Activate.ps1
python -m gakkari
```

Entry point: `gakkari/__main__.py` → `GakkariApp.run()`.  
The `gakkari` console script (`.venv\Scripts\gakkari.exe`) also works once the venv is active.

Textual devtools (open in a second terminal while the app runs):
```powershell
textual console
# then in the first terminal:
TEXTUAL_LOG=1 python -m gakkari
```

---

## Project layout

```
gakkari/
  __init__.py
  __main__.py        entry point
  app.py             GakkariApp (Textual App subclass)
  db.py              SQLite helpers — schema, CRUD, get_conn() context manager
  models.py          Subscription and Settings dataclasses
  ui/
    __init__.py
    main_screen.py   MainScreen — table, bindings, due-soon highlight
data/
  gakkari.db         created at first run (gitignored)
```

---

## Architecture decisions

- **Framework:** Textual. Screens, DataTable, keyboard bindings, CSS-in-Python.
- **Storage:** SQLite via stdlib `sqlite3`. DB file lives at `data/gakkari.db`.
- **Money:** always `Decimal`, never `float`. SQLite stores money as TEXT and converts back via a registered adapter. Do not change this.
- **Dates:** `datetime.date` objects throughout. SQLite stores as ISO TEXT and converts back via a registered adapter. Never parse dates from raw strings in business logic.
- **Currency conversion:** will use `frankfurter.app` (no API key, ECB-derived, daily). `httpx` is already installed. Conversion logic: convert first, then apply tax.
- **Tax display:** global `price_display_mode` in Settings (`"net"` or `"gross"`). Each subscription row stores `tax_mode` (`none` / `inclusive` / `exclusive`) and `tax_rate`. Net/gross derivation lives on the `Subscription` model (`net_amount()`, `gross_amount()`).
- **Automation boundary:** renewal calculation and notice generation belong in the app. Windows Task Scheduler is an outer trigger only (Phase 5).
- **Scope:** no accounts, no cloud sync, no web rewrite. Local tool only.

---

## Data model

```python
Subscription:
  id, name, amount (Decimal), currency, billing_period, next_renewal_date (date),
  category, notes, tax_mode, tax_rate (Decimal),
  status  # "active" | "paused" | "cancelled"

Settings (singleton, id=1):
  base_currency, price_display_mode,  # "net" | "gross"
  due_soon_days (int),
  mascot_enabled (bool), notices_enabled (bool)

ExchangeRateCache:
  base_currency, quote_currency, rate (Decimal), fetched_at (date)
  PRIMARY KEY (base_currency, quote_currency)
```

`billing_period` values: `"monthly"` `"yearly"` `"quarterly"` `"weekly"`.

Subscriptions are never hard-deleted for historical accuracy — use `status = "cancelled"` instead. `is_active` from the original spec became a three-way `status` field.

---

## DB access pattern

Always use `get_conn()` as a context manager. It commits on clean exit, rolls back on exception.

```python
from gakkari.db import get_conn, list_subscriptions

with get_conn() as conn:
    subs = list_subscriptions(conn)
```

`init_db()` is called once on app mount. It is idempotent.

---

## Key conventions

- Due-soon threshold comes from `Settings.due_soon_days` (default 7). Check with `Subscription.is_due_soon(threshold, today)`.
- Totals must always respect the active `price_display_mode` and `base_currency`. Sum in the chosen display mode, not in raw amounts.
- Weekly notices use a rolling 7-day window from today, not calendar weeks.
- Empty notice days still render a calm fallback message — the board must never look broken.
- New features must strengthen clarity, local control, or recurring-use convenience. Style-only features get cut.

---

## Phase plan

| Phase | Goal | Status |
|---|---|---|
| 1 | Subscription table, add/edit/delete, persistence, due-soon, keyboard nav | Scaffold only — flows are stubs |
| 2 | Totals, multi-currency, VAT mode, CSV/JSON import-export, filters | Not started |
| 3 | 7-day rolling textboard notice panel | Not started |
| 4 | ASCII mascot, final three-column layout polish | Not started |
| 5 | CLI entrypoint, Windows Task Scheduler integration | Not started |

**Phases 1 and 2 are the finished product.** Everything after is optional polish.

### Current state (after Session 4 — aesthetic overhaul)

- Visual identity locked in: PC-9800/CRT aesthetic — black terminal surround, amber DataTable panel, double-line borders.
- `gakkari/strings.py` — full i18n module. EN and JA string tables. Helpers: `t()`, `fmt_date()`, `fmt_period()`, `fmt_status()`, `fmt_tax_mode()`, `fmt_category()`. Language toggle (`L` key) persists to `Settings.language` in SQLite.
- `MainScreen` layout: transposed DataTable (subscriptions as columns, field names as rows), separator columns between subscriptions, detail pane below showing selected subscription's full info, split lower section with summary pane (count + monthly/yearly estimate) and notes pane.
- DataTable: `cursor_type="column"`, cursor skips separator columns automatically, column headers are subscription names, rows are field values.
- **`_SAMPLE_SUBS` is still hardcoded** — real DB reads not yet wired in this design.
- **add/edit/delete are stubs** (show notification only). Modal files from Session 2 (`confirm_modal.py`, `subscription_modal.py`) may exist in the project and can be reused.
- Next session: replace sample data with real DB reads, wire CRUD modals into the new layout. Goal is a fully functional app by end of that session.

---

## Target layout (Phase 4)

Three-column, mascot always visible:

```
┌──────────────┬────────────────────────────────┬──────────────────────┐
│  ASCII       │  Subscription table + totals   │  Weekly notice board │
│  mascot      │  (center of gravity)           │  7-day rolling       │
└──────────────┴────────────────────────────────┴──────────────────────┘
```

The table is always the functional and visual center. Mascot and notice board support it.
