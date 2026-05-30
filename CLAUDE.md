# Gakkari OL

Terminal subscription tracker. Python + Textual TUI, SQLite storage, local-only.

**Tone:** calm, serious, readable, slightly stylized. No gamification. (A Phase-4 anime office-lady mascot screen was added and later removed — it was presentation polish, not the product.)

---

## Running the app

```powershell
cd path\to\gakkari-ol
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Unix shells:
source .venv/bin/activate
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

### Versioning & updating

The version lives in **three places that must stay in sync** — `pyproject.toml`, `gakkari/__init__.py` (`__version__`), and the landing-page boot line in `docs/index.html` (`ver X.Y.Z`). **Bump all three on every release that changes behavior.**

Why it matters: pip identifies a package by `(name, version)`, so `pip install [--upgrade] git+https://github.com/kenrinzero/gakkari-ol` against an environment that already has that version **no-ops as "Requirement already satisfied"** — the new code never installs. This bit the 0.1.0→0.2.0 update, and again the mascot removal (which shipped without a bump, so installs kept showing the mascot). Keep the version moving and updates resolve cleanly. Escape hatch to force an update regardless of version: `pip install --force-reinstall git+…`.

---

## Project layout

```
gakkari/
  __init__.py
  __main__.py        entry point — argparse for --notice / --lang, default launches TUI
  app.py             GakkariApp (Textual App subclass)
  cli.py             Phase 5 — render today's renewals + 7-day preview for stdout
  db.py              SQLite helpers — schema, CRUD, exchange rate cache, renewal log
  models.py          Subscription, Settings, RenewalLog, _MONTHLY_FACTORS, date helpers
  strings.py         i18n tables (EN + JA), fmt_* helpers
  currency.py        get_rate — frankfurter.dev fetch + daily SQLite cache
  io.py              CSV + JSON import/export
  notices.py         pure logic for the rolling notice board (1–2 week window, trial expiry)
  ui/
    __init__.py
    main_screen.py        MainScreen — list + filter + totals + CRUD + notes + right panel
    history_screen.py     HistoryScreen — renewal ledger with running total (h)
    confirm_modal.py      ConfirmModal — yes/no dialog
    subscription_modal.py SubscriptionModal — add/edit form (incl. optional trial_ends)
    settings_modal.py     SettingsModal — base currency, gross/net, due-soon
    export_modal.py       ExportModal — format select + path
    import_modal.py       ImportModal — path with file-existence check
    notice_panel.py       NoticePanel — right-column textboard + tutorial alt-state
data/
  gakkari.db         created at first run (gitignored)
docs/
  index.html              landing page (live at kenrinzero.github.io/gakkari-ol/)
  scheduler.md            Windows Task Scheduler recipe for --notice
  Glass_TTY_VT220.ttf     bundled font (DEC VT220 bitmap, Latin/symbols)
  DotGothic16-subset.woff2  bundled font (16×16 pixel Japanese, subset to the codepoints used on the page)
  .nojekyll               disables GitHub's Jekyll so files serve as-is
```

---

## Architecture decisions

- **Framework:** Textual. Screens, DataTable, keyboard bindings, CSS-in-Python.
- **Storage:** SQLite via stdlib `sqlite3`. DB file lives at `data/gakkari.db`.
- **Money:** always `Decimal`, never `float`. SQLite stores money as TEXT and converts back via a registered adapter. Do not change this.
- **Dates:** `datetime.date` objects throughout. SQLite stores as ISO TEXT and converts back via a registered adapter. Never parse dates from raw strings in business logic.
- **Currency conversion:** uses `frankfurter.dev` (no API key, ECB-derived, daily). `httpx` is already installed. Conversion logic: convert first, then apply tax.
- **Tax display:** global `price_display_mode` in Settings (`"net"` or `"gross"`). Each subscription row stores `tax_mode` (`none` / `inclusive` / `exclusive`) and `tax_rate`. Net/gross derivation lives on the `Subscription` model (`net_amount()`, `gross_amount()`).
- **Automation boundary:** renewal calculation and notice generation belong in the app. Windows Task Scheduler is an outer trigger only (Phase 5).
- **Scope:** no accounts, no cloud sync, no web rewrite. Local tool only.

---

## Data model

```python
Subscription:
  id, name, amount (Decimal), currency, billing_period, next_renewal_date (date),
  category, notes, tax_mode, tax_rate (Decimal),
  status,            # "active" | "paused" | "cancelled"
  trial_ends         # date | None — optional free-trial expiry

Settings (singleton, id=1):
  base_currency, price_display_mode,           # "net" | "gross"
  due_soon_days (int),
  monthly_income (Decimal),                     # 0 = unset (powers the `income` totals mode)
  monthly_income_currency,                      # income's own currency; blank → follow base_currency
  notices_enabled (bool),
  language,                                     # "en" | "ja"
  convert_column_enabled (bool),                # `c` row-level conversion column
  convert_currency,                             # `c` column target; blank → follow base_currency
  totals_view_mode,                             # estimate | monthly_strict | yearly_strict | by_period
  sort_mode                                     # date | period | name | amount

RenewalLog:
  id, subscription_id, renewed_on (date), amount (Decimal),
  currency, billing_period
  # one row written every time the user presses `k` to acknowledge a renewal

ExchangeRateCache:
  base_currency, quote_currency, rate (Decimal), fetched_at (date)
  PRIMARY KEY (base_currency, quote_currency)
```

`billing_period` values: `"monthly"` `"yearly"` `"quarterly"` `"weekly"` `"half_yearly"`.

Subscriptions are never hard-deleted for historical accuracy — use `status = "cancelled"` instead. `is_active` from the original spec became a three-way `status` field. Cancelled rows are hidden by default; press `v` to surface them dimmed for reference.

`trial_ends` is `None` for most subs. When set and within the notice window, the notice panel emits a louder trial-expiry post (distinct kaomoji pool, "trial ends today!" body) on the expiry date in place of (or alongside) the regular renewal post for that day.

`RenewalLog` powers the history view (`h`) and the running-total-in-base-currency summary. Entries are append-only — the model trusts `k` presses as acknowledgements and never deletes log rows.

---

## DB access pattern

Always use `get_conn()` as a context manager. It commits on clean exit, rolls back on exception.

```python
from gakkari.db import get_conn, list_subscriptions

with get_conn() as conn:
    subs = list_subscriptions(conn)
```

`init_db()` is called once on app mount. It is idempotent: it creates the schema if missing, then runs a tuple of `ALTER TABLE ... ADD COLUMN` statements wrapped individually in `try/except sqlite3.OperationalError` so additive migrations on older DBs are safe to re-run.

DB-write failures at the consumer level (settings load/save, history load) surface as `self.notify(..., severity="warning")` rather than silent swallows — see [gakkari/ui/main_screen.py](gakkari/ui/main_screen.py) `on_mount` / `_persist_settings` and [gakkari/ui/history_screen.py](gakkari/ui/history_screen.py) `on_mount`.

---

## Key conventions

- Due-soon threshold comes from `Settings.due_soon_days` (default 7). Check with `Subscription.is_due_soon(threshold, today)`.
- Totals must always respect the active `price_display_mode` and `base_currency`. Sum in the chosen display mode, not in raw amounts.
- Notice window is adaptive: 7 days minimum (small terminals) up to 14 days when the right column has the vertical room. The window is computed by `NoticePanel._pick_window(height)`; floor stays at 7 so resizing down never *loses* posts.
- Empty notice days still render a calm fallback message — the board must never look broken.
- Each notice post is read from its own date's perspective — never "tomorrow" or "in N days." A renewal on the day a post represents always reads as "renews today!".
- Rate-fetching for table render + totals goes through `MainScreen._build_rate_cache(subs)` — one lookup per unique currency per refresh pass. Sort-by-amount, the conversion column, and the totals computations all read from this shared dict; no per-row HTTP fan-out.
- New features must strengthen clarity, local control, or recurring-use convenience. Style-only features get cut.

---

## Phase plan

| Phase | Goal | Status |
|---|---|---|
| 1 | Subscription table, add/edit/delete, persistence, due-soon, keyboard nav | **Done** (Session 5) |
| 2 | Totals, multi-currency, VAT mode, CSV/JSON import-export, filters | **Done** (Session 6) |
| 3 | Rolling textboard notice panel | **Done** (Session 7) |
| 4 | ASCII mascot, layout polish | Done (Session 6); **mascot later removed** |
| 5 | CLI entrypoint, Windows Task Scheduler integration | **Done** (Session 8) |
| 6 | Compact-terminal restructure + recurring-use features | **Done** (current session) |

### Phase 6 deltas

- Layout went **three-column → two-column 60:40** (table : notice board). (A dedicated `MascotScreen` accessed via `m` was added here and later removed.)
- New keybindings on the main screen: `k` Kept it (auto-advance + ledger), `h` History, `v` Archive (cancelled subs), `c` Convert column, `t` Totals cycle, `o` Sort cycle.
- Notice panel window is now adaptive (7–14 days) and its off-state shows a categorized **keybindings tutorial** instead of going blank.
- New persisted state: `convert_column_enabled`, `convert_currency`, `totals_view_mode`, `sort_mode`, plus the optional `trial_ends` field on `Subscription` and the new `renewal_log` table.
- `SettingsModal._save()` rebuilds the `Settings` object via `dataclasses.replace(self._settings, …)`, editing only the fields the modal exposes. It must never construct a bare `Settings(...)` — the view-state fields (`convert_column_enabled`, `convert_currency`, `totals_view_mode`, `sort_mode`) live only in `self._settings`, and a fresh constructor would silently reset them to defaults on every Save.
- DB-IO failure handling was tightened — bare `except Exception: pass` swallows around settings load/save and history load now surface as `notify(..., severity="warning")`.

### Current state (after Phase 6)

- **Visual identity:** PC-9800/CRT aesthetic — amber on black, double-line borders. Unchanged.
- **`MainScreen` layout:** two-column. Left 60% = `#center-panel` (title bar with mode/paused/sort/conv/cancelled indicators → filter `Input` → `ContentSwitcher` between `OptionList` and notes `TextArea`). Right 40% = `#right-panel` (NoticePanel).
- **Full CRUD:** `SubscriptionModal`, `ConfirmModal` (soft-delete via `status = "cancelled"`). Notes drill-in (right-arrow open, Esc close+save, Ctrl+S explicit save). Has-notes dot (`●`/`◌`).
- **Sort cycle (`o`):** date → period → name → amount. Sort happens in-memory in `_refresh_view` after filtering; sort by amount uses the rate cache so cross-currency comparisons are meaningful. Indicator `· sort:<mode>` shown when not default.
- **Totals cycle (`t`):** estimate (monthly + yearly normalized, default) → monthly_strict (sum only `billing_period == "monthly"`) → yearly_strict (only yearly) → by_period (per-cadence subtotals, in `_PERIOD_ORDER`) → income.
- **Income totals mode:** `income · committed · left (n%)`. "committed" is the **amortized** monthly figure (`_total_monthly_in_base`, same as `estimate` — yearly/quarterly subs folded to their /12 share) so "left" doesn't lurch in months with an annual renewal. Income has its **own currency** (`monthly_income_currency`, blank → base) — e.g. you earn in HUF but track/spend in EUR — and is converted to base for the comparison/%; its rate→base is fetched into `_rate_cache` by `_build_rate_cache` when income mode is active. When the income currency differs from base the line shows the native amount plus the base-equivalent: `HUF 100,000 income (≈ EUR 258) · EUR 200 committed · EUR 58 left (78%)`. Over budget shows `… over (n%)` instead of `left`. With `monthly_income == 0` (unset) it shows committed plus a "set monthly income in settings" nudge. Income amount + currency are set in the Settings modal (blank currency = base). A richer left-press budget panel is a possible later addition.
- **Convert column (`c`):** when on, each row shows `9.99 USD  ≈ 9.20 EUR ●`. The conversion target is **`convert_currency`** if set, else `base_currency` — it is decoupled from the base so totals can stay in one currency (e.g. EUR at the top) while the column converts to another (e.g. JPY). Set the target in the Settings modal (blank = follow base). Rows where the sub currency equals the *target* show `—` in place of the conversion. Toggle indicator `· conv→<target>` in the title bar. Rates to the target are fetched into a second cache (`_conv_rates`) alongside the base cache in `_build_rate_cache`, still one lookup per unique currency per refresh.
- **Auto-advance (`k`):** advances the highlighted sub's `next_renewal_date` by one billing cycle (`Subscription.next_renewal_after`, with month-end clamping via `_add_months` and leap-year safety) AND writes a `renewal_log` row at the *old* date. Toast confirms `name: old → new`.
- **History screen (`h`):** `HistoryScreen` — chronological renewal log (most recent first) with a running total summed in `base_currency`. Esc returns.
- **Archive view (`v`):** cycles cancelled subs in/out of the visible list, dimmed throughout so they read as for-reference. Title-bar indicator `· +archive`.
- **Trial expiry:** optional `trial_ends` field on `Subscription`. Notice panel detects trial endings in its window and emits a distinct trial-flavor post (alarmed kaomoji pool: `(((;ﾟДﾟ)))`, `(´；ω；｀)`, etc.; `"trial ends today!"` body) on the expiry day, taking priority over the regular renewal post if both fall on the same day.
- **Notice panel (`n` cycles):**
  - **Notices state (default):** banner + 7-to-14 stacked posts (`{n} ：OL ：YYYY-MM-DD(月) ID:hash8`, body, kaomoji, `─` rule). Three pools (renewal / trial / empty) picked deterministically by `post_id` hash so the same day always renders identically. Always-JA single-char weekday labels; EN/JA bodies. Adaptive window via `_pick_window(height)`. 60-second `set_interval` tick watches for date rollover.
  - **Tutorial state:** categorized keybindings cheat sheet (Editing / Views & filters / Screens / App) in the same textboard styling. Replaces the textboard rather than blanking the column.
- **Currency-fallback warning:** `· ⚠ rate` in the title bar when any visible sub's lookup returns `Decimal("1")` for a non-base currency. Rebuilt each refresh in `_build_rate_cache`; clears as soon as the offending sub is fixed or removed.
- **i18n:** full EN+JA bundle covering all surfaces. Always-JA weekday labels are intentional flavor (textboard authenticity).
- **CLI (Phase 5):** `python -m gakkari --notice` reads the DB and prints today's renewals + a 7-day preview to stdout, then exits. Designed to be called from Windows Task Scheduler on login. `--lang en|ja` overrides the saved UI language. `sys.stdout.reconfigure(encoding="utf-8")` keeps the JA banner and kaomoji from crashing the legacy Console Host. Task Scheduler recipe lives in [docs/scheduler.md](docs/scheduler.md).

---

## Layout

Two-column 60:40:

```
┌────────────────────────────────────────┬────────────────────────────────┐
│  Subscription table + totals           │  Notice board / Tutorial       │
│  (60% — center of gravity)             │  (40% — adaptive 7–14 day)    │
│                                        │                                │
│  title bar · filter · rows · notes     │  banner · post 1 … post N     │
└────────────────────────────────────────┴────────────────────────────────┘
                          press `h` to view renewal history
                          press `n` to flip notice board ↔ tutorial
```

The table is the functional and visual center. The notice board supports it.
