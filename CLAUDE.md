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
  __main__.py        entry point — argparse for --notice / --lang, default launches TUI
  app.py             GakkariApp (Textual App subclass)
  cli.py             Phase 5 — render today's renewals + 7-day preview for stdout
  db.py              SQLite helpers — schema, CRUD, exchange rate cache
  models.py          Subscription, Settings, _MONTHLY_FACTORS, display helpers
  strings.py         i18n tables (EN + JA), fmt_* helpers
  currency.py        get_rate — frankfurter.app fetch + daily SQLite cache
  io.py              CSV + JSON import/export
  mascot.py          tiered ASCII art loader (4 sizes, threshold-based pick)
  notices.py         Phase 3 — pure logic for the 7-day notice board
  assets/
    mascot_40.txt    smallest tier (36 visible cols)
    mascot_50.txt    baseline tier (45 visible cols)
    mascot_70.txt    large tier (62 visible cols)
    mascot_90.txt    largest tier (79 visible cols)
  ui/
    __init__.py
    main_screen.py        MainScreen — list + filter + totals + CRUD + notes + notice panel
    confirm_modal.py      ConfirmModal — yes/no dialog
    subscription_modal.py SubscriptionModal — add/edit form with validation
    settings_modal.py     SettingsModal — base currency, gross/net, due-soon
    export_modal.py       ExportModal — format select + path
    import_modal.py       ImportModal — path with file-existence check
    notice_panel.py       NoticePanel — right-column textboard widget
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

`billing_period` values: `"monthly"` `"yearly"` `"quarterly"` `"weekly"` `"half_yearly"`.

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
| 1 | Subscription table, add/edit/delete, persistence, due-soon, keyboard nav | **Done** (Session 5) |
| 2 | Totals, multi-currency, VAT mode, CSV/JSON import-export, filters | **Done** (Session 6) |
| 3 | 7-day rolling textboard notice panel | **Done** (Session 7) |
| 4 | ASCII mascot, final three-column layout polish | **Done** (Session 6) |
| 5 | CLI entrypoint, Windows Task Scheduler integration | **Done** (Session 8) |

**Phases 1 and 2 are the finished product.** Phases 3, 4, 5 are all complete. The project is feature-complete per the original spec.

### Current state (after Session 8 — CLI + Task Scheduler)

- Visual identity: PC-9800/CRT aesthetic — amber on black, double-line borders. Unchanged from Session 4.
- `MainScreen` layout: title bar (mode/paused/totals/rate-fallback warning) → filter bar (`Input`) → `ContentSwitcher` between OptionList and notes view. Left panel renders the mascot; right panel renders the textboard notice stack.
- Full CRUD: `SubscriptionModal`, `ConfirmModal` (soft-delete). Notes drill-in (right-arrow open, Esc close+save, Ctrl+S explicit save). Has-notes dot (`●`/`◌`).
- Phase 2 features wired in: multi-currency totals via `currency.get_rate` (frankfurter, daily SQLite cache, fallback rate also cached so bad codes don't burn HTTP timeouts); gross/net display mode (`g`); paused toggle (`p`); text filter (`/`); settings modal (`s`); CSV/JSON export (`x`) and import (`i`).
- Mascot: four locked-size art tiers in `gakkari/assets/` (40, 50, 70, 90 chars wide). `gakkari/mascot.py` picks the largest tier whose `min_panel_width` and `min_panel_height` fit; below the smallest tier the panel stays empty. Bottom-aligned, horizontally centered, no_wrap-cropped to prevent line-garble at narrow widths. `m` key toggles `Settings.mascot_enabled`. Re-renders on resize via `call_after_refresh` using `self.app.size` (not `panel.content_size`, which lags).
- Notice panel (Phase 3): textboard aesthetic — banner + 7 stacked posts (`{n} ：OL ：YYYY-MM-DD(月) ID:hash8`, body, kaomoji, `─` rule). Always-JA single-char weekday labels regardless of UI language; bodies are EN/JA. **Each post is read from its own date's perspective** — a renewal on the day a post represents always reads as "renews today!", never "tomorrow" or "in N days". Two kaomoji pools (5 each) — renewal-day pool (shock / `ｷﾀ━━━` / flushed / sweat-shock / giko grin) and empty-day pool (smug / shobon / disinterest / orz / friendly). Face and empty-day message both picked deterministically by `post_id` hash, so the same day always renders identically across refreshes. Refreshes on mount, resize, language toggle, and any CRUD action. 60-second `set_interval` tick watches for date rollover so the panel and center list both advance to the new "today" when the app is left open past midnight. A dim `〜 終 〜` thread-end marker closes the stack below post 7. `n` key toggles `Settings.notices_enabled`.
- Currency-fallback warning: `· ⚠ rate fallback` appears in the title-bar indicators when any active sub's currency lookup returns `Decimal("1")` for a non-base currency (e.g. user typed `YEN` instead of `JPY`). Detected during the existing `_total_monthly_in_base` rate-fetch pass; set is rebuilt each call, so the warning clears as soon as the offending sub is fixed or removed.
- i18n: full EN+JA bundle covering the Phase 3 surface (banner, body templates, empty-day pool, fallback warning, footer label).
- `billing_period` values: `"monthly"` `"yearly"` `"quarterly"` `"weekly"` `"half_yearly"`.
- CLI (Phase 5): `python -m gakkari --notice` reads the DB and prints today's renewals + a 7-day preview to stdout, then exits. Designed to be called from Windows Task Scheduler on login. `--lang en|ja` overrides the saved UI language. `sys.stdout.reconfigure(encoding="utf-8")` keeps the JA banner and kaomoji from crashing the legacy Console Host. Task Scheduler recipe lives in `gakkari_docs/scheduler.md`.

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
