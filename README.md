# Gakkari OL

*The name combines **gakkari** (がっかり, "disappointed / let down") with **OL** (Office Lady) — the small sigh of opening your subscriptions and seeing the monthly total.*

A calm, local-only terminal subscription tracker. Python + Textual TUI, SQLite storage. No accounts, no cloud, no telemetry — the database file lives next to the code.

**[Project site →](https://kenrinzero.github.io/gakkari-ol/)**

```
[Gakkari OL] Upcoming renewals — 2026-05-12 (火)
───────────────────────────────────────────────

!! TODAY (1):
  - Spotify  USD 9.99  (monthly)

Upcoming (next 7 days):
  +2d 2026-05-14 (木)  Netflix  USD 15.49
  +5d 2026-05-17 (日)  Domain   USD 12.00
```

## Install

Requires Python 3.12 or newer.

```bash
pip install git+https://github.com/kenrinzero/gakkari-ol
```

Or clone and install in editable mode for development:

```bash
git clone https://github.com/kenrinzero/gakkari-ol
cd gakkari-ol
pip install -e .
```

## Usage

```bash
gakkari                  # launch the TUI
gakkari --notice         # print today's renewals + 7-day preview, then exit
gakkari --notice --lang en   # force English output (overrides saved setting)
gakkari --notice --lang ja   # force Japanese output
```

The TUI is keyboard-driven. Inside the app, press `?` for the full keybinding list, or `q` to quit.

The SQLite database is created on first launch at `data/gakkari.db` inside the package directory. It is not synced anywhere.

## Features

- Subscription CRUD with soft-delete (`status` = active / paused / cancelled), keyboard-only navigation, notes drill-in.
- **Auto-advance (`k`) + undo (`u`)** — one keystroke advances a sub's renewal date by one billing cycle (with month-end + leap-year clamping) and logs it to a local ledger; `u` reverses the last one if you mis-pressed.
- **History view (`h`)** — renewal ledger grouped by month with per-month subtotals; the current month also shows your amortized estimate so actual spend reads against it. Running total in your base currency.
- **Archive view (`v`) + resume (`r`)** — surface cancelled subs dimmed for reference; press `r` to resume (un-cancel) the highlighted one.
- **Adaptive notice board** — Japanese textboard styling with a rolling 1-to-2-week window that expands as your terminal gets taller. Deterministic kaomoji per day, EN/JA bilingual. Press `n` to flip between notices and a categorized keybindings tutorial.
- **Trial expiry warnings** — optional `trial_ends` per sub; the notice board surfaces an alarmed-kaomoji post on the day a trial converts to paid.
- **Multi-currency totals** — exchange rates fetched daily from [frankfurter.dev](https://frankfurter.dev/) (ECB-derived, no API key) and cached locally. Bad currency codes fall back gracefully with an inline warning.
- **Sort (`o`) and totals (`t`) cycles** — sort by date / period / name / amount; totals as monthly+yearly estimate, strict-monthly, strict-yearly, per-period, **per-category**, a **30/60/90-day cash-out forecast**, or income (amortized spend vs. your monthly income).
- **Conversion column (`c`)** — show each row's amount converted to your base (or any chosen) currency next to its native price, so you stop doing mental currency math.
- **Duplicate (`D`)** a subscription into a prefilled form; tag each with an optional **payment method** ("which card is this on?") that the filter matches.
- **Budget watch** — set a monthly income and the notice board flags when committed spend goes over it.
- **Safe by default** — a rotating daily backup of your local DB plus import validation and a duplicate-guard, so a bad import or a fat-finger can't quietly wreck your data.
- **Gross / net VAT display mode**, per-row tax mode and rate.
- **CSV and JSON import / export.**
- **One-shot `--notice` CLI** for daily routines (Windows Task Scheduler, cron, login scripts).

## Daily notice on login (Windows)

See [docs/scheduler.md](docs/scheduler.md) for the Task Scheduler recipe — register `gakkari --notice` to run at every login and surface what renews today before you open anything else.

## Architecture

- Money is always `Decimal`, never `float`. SQLite stores it as TEXT via a registered adapter.
- Dates are `datetime.date` objects throughout. Same TEXT-with-adapter pattern.
- Subscriptions are never hard-deleted — `status = "cancelled"` is the terminal state.
- Renewal calculation, notice generation, and the renewal ledger all live in the app. External schedulers (Task Scheduler, cron) are only the outer trigger.
- Two-column 60:40 layout (table : notice board) optimised for compact terminals.

Full architectural notes are in [CLAUDE.md](CLAUDE.md).

## Credits

Built collaboratively with several AI models. Each contributed a distinct stage of the work:

- **Mistral Large 2** — original concept
- **Grok Imagine** — mascot character design
- **Claude Sonnet 4.7** — initial scaffold and visual style
- **Claude Opus 4.6** — feature implementation (Phases 1–4: CRUD, totals, import/export, notice board)
- **Claude Opus 4.7** — Phases 5–6: CLI entry point, layout restructure, history screen, auto-advance + ledger, archive view, trial expiry, sort/totals/convert cycles, notice window, tutorial
- **Claude Opus 4.8** — convert-column currency, income totals, 0.4.0: spending insights, undo, backups, import guards, payment-method, test suite + CI
- **Mavis (MiniMax-M3)** — 0.4.2: notice board respects status, test coverage
- **Qwen (Qwen3.8-Max)** — 0.4.3: first full code audit (`AUDIT-2026-08-23.md`) + fix pass — rate-freshness parity, CLI display width, config single-sourcing

## License

MIT. See [LICENSE](LICENSE).
