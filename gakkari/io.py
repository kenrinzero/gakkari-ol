from __future__ import annotations

import csv
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from gakkari.models import Subscription

_FIELDS = (
    "name", "amount", "currency", "billing_period", "next_renewal_date",
    "category", "notes", "tax_mode", "tax_rate", "status",
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
    }


def _row_to_sub(row: dict) -> Subscription:
    return Subscription(
        id=None,
        name=str(row["name"]),
        amount=Decimal(str(row["amount"])),
        currency=str(row["currency"]),
        billing_period=str(row["billing_period"]),
        next_renewal_date=date.fromisoformat(str(row["next_renewal_date"])),
        category=str(row.get("category") or ""),
        notes=str(row.get("notes") or ""),
        tax_mode=str(row.get("tax_mode") or "none"),
        tax_rate=Decimal(str(row.get("tax_rate") or "0")),
        status=str(row.get("status") or "active"),
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
