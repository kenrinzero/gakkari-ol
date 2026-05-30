from __future__ import annotations

import csv
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from gakkari.models import BILLING_PERIODS, STATUSES, TAX_MODES, Subscription

_FIELDS = (
    "name", "amount", "currency", "billing_period", "next_renewal_date",
    "category", "notes", "tax_mode", "tax_rate", "status", "trial_ends",
)


def _sub_to_row(sub: Subscription) -> dict[str, str]:
    return {
        "name": sub.name,
        "amount": str(sub.amount),
        "currency": sub.currency,
        "billing_period": sub.billing_period,
        "next_renewal_date": sub.next_renewal_date.isoformat(),
        "category": sub.category,
        "notes": sub.notes,
        "tax_mode": sub.tax_mode,
        "tax_rate": str(sub.tax_rate),
        "status": sub.status,
        "trial_ends": sub.trial_ends.isoformat() if sub.trial_ends else "",
    }


def _row_to_sub(row: dict) -> Subscription:
    raw_trial = (row.get("trial_ends") or "").strip() if row.get("trial_ends") else ""
    trial_ends = date.fromisoformat(raw_trial) if raw_trial else None

    # Validate enum/domain fields up front — Decimal/date parse errors are
    # caught by the callers, but a typo'd status/period/tax_mode would
    # otherwise import silently and (e.g.) make a row permanently invisible.
    name = str(row["name"]).strip()
    if not name:
        raise ValueError("name: must not be empty")
    currency = str(row["currency"]).strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError(f"currency: {currency!r} must be a 3-letter code")
    billing_period = str(row["billing_period"]).strip()
    if billing_period not in BILLING_PERIODS:
        raise ValueError(
            f"billing_period: {billing_period!r} not one of {', '.join(BILLING_PERIODS)}"
        )
    tax_mode = str(row.get("tax_mode") or "none").strip()
    if tax_mode not in TAX_MODES:
        raise ValueError(f"tax_mode: {tax_mode!r} not one of {', '.join(TAX_MODES)}")
    status = str(row.get("status") or "active").strip()
    if status not in STATUSES:
        raise ValueError(f"status: {status!r} not one of {', '.join(STATUSES)}")
    amount = Decimal(str(row["amount"]))
    if amount < 0:
        raise ValueError("amount: must be non-negative")
    tax_rate = Decimal(str(row.get("tax_rate") or "0"))
    if tax_rate < 0:
        raise ValueError("tax_rate: must be non-negative")

    return Subscription(
        id=None,
        name=name,
        amount=amount,
        currency=currency,
        billing_period=billing_period,
        next_renewal_date=date.fromisoformat(str(row["next_renewal_date"])),
        category=str(row.get("category") or ""),
        notes=str(row.get("notes") or ""),
        tax_mode=tax_mode,
        tax_rate=tax_rate,
        status=status,
        trial_ends=trial_ends,
    )


def export_csv(path: Path, subs: list[Subscription]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDS)
        writer.writeheader()
        for sub in subs:
            writer.writerow(_sub_to_row(sub))


def export_json(path: Path, subs: list[Subscription]) -> None:
    payload = [_sub_to_row(sub) for sub in subs]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def import_csv(path: Path) -> tuple[list[Subscription], list[str]]:
    out: list[Subscription] = []
    errs: list[str] = []
    with path.open(encoding="utf-8", newline="") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            try:
                out.append(_row_to_sub(row))
            except (KeyError, InvalidOperation, ValueError) as e:
                errs.append(f"row {i}: {e}")
    return out, errs


def import_json(path: Path) -> tuple[list[Subscription], list[str]]:
    out: list[Subscription] = []
    errs: list[str] = []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return out, ["JSON root must be a list of subscriptions"]
    for i, row in enumerate(payload, start=1):
        try:
            out.append(_row_to_sub(row))
        except (KeyError, InvalidOperation, ValueError, TypeError) as e:
            errs.append(f"item {i}: {e}")
    return out, errs


def import_auto(path: Path) -> tuple[list[Subscription], list[str]]:
    if path.suffix.lower() == ".json":
        return import_json(path)
    return import_csv(path)
