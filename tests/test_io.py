from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from gakkari import io as gio
from gakkari.models import Subscription


def make(**kw) -> Subscription:
    base = dict(
        name="Netflix", amount=Decimal("9.99"), currency="USD",
        billing_period="monthly", next_renewal_date=date(2026, 6, 1),
        category="entertainment", notes="note", tax_mode="inclusive",
        tax_rate=Decimal("10"), status="active",
        trial_ends=date(2026, 7, 1), payment_method="Visa 1234",
    )
    base.update(kw)
    return Subscription(**base)


def _same(a: Subscription, b: Subscription) -> bool:
    fields = ("name", "amount", "currency", "billing_period", "next_renewal_date",
              "category", "notes", "tax_mode", "tax_rate", "status",
              "trial_ends", "payment_method")
    return all(getattr(a, f) == getattr(b, f) for f in fields)


def test_csv_roundtrip(tmp_path):
    s = make()
    p = tmp_path / "x.csv"
    gio.export_csv(p, [s])
    out, errs = gio.import_csv(p)
    assert not errs and len(out) == 1 and _same(out[0], s)


def test_json_roundtrip_optional_fields_empty(tmp_path):
    s = make(trial_ends=None, payment_method="")
    p = tmp_path / "x.json"
    gio.export_json(p, [s])
    out, errs = gio.import_json(p)
    assert not errs and out[0].trial_ends is None and out[0].payment_method == ""


@pytest.mark.parametrize("bad", [
    {"billing_period": "montly"},
    {"status": "activ"},
    {"tax_mode": "vat"},
    {"currency": "US"},
    {"currency": "US1"},
    {"amount": "-1"},
    {"tax_rate": "-5"},
    {"name": "   "},
])
def test_validation_rejects(bad):
    row = dict(name="A", amount="1.00", currency="EUR",
               billing_period="monthly", next_renewal_date="2026-06-01")
    row.update(bad)
    with pytest.raises(ValueError):
        gio._row_to_sub(row)


def test_currency_uppercased():
    s = gio._row_to_sub(dict(name="A", amount="1", currency="eur",
                             billing_period="monthly", next_renewal_date="2026-06-01"))
    assert s.currency == "EUR"


def test_import_collects_per_row_errors(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text(
        "name,amount,currency,billing_period,next_renewal_date\n"
        "Good,1,EUR,monthly,2026-06-01\n"
        "Bad,2,EUR,bogus,2026-06-01\n",
        encoding="utf-8",
    )
    out, errs = gio.import_csv(p)
    assert len(out) == 1 and out[0].name == "Good"
    assert len(errs) == 1 and "billing_period" in errs[0]


def test_import_json_root_must_be_list(tmp_path):
    p = tmp_path / "x.json"
    p.write_text('{"not": "a list"}', encoding="utf-8")
    out, errs = gio.import_json(p)
    assert out == [] and errs
