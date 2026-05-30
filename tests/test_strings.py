from __future__ import annotations

from gakkari.strings import _STRINGS, t


def test_en_ja_key_parity():
    """Every string must exist in both languages — a missing JA key silently
    falls back to EN, which is easy to ship by accident."""
    en, ja = set(_STRINGS["en"]), set(_STRINGS["ja"])
    assert en == ja, f"only EN: {sorted(en - ja)}; only JA: {sorted(ja - en)}"


def test_t_fallbacks():
    # unknown language falls back to EN; unknown key returns the key itself
    assert t("modal_save", "xx") == _STRINGS["en"]["modal_save"]
    assert t("nonexistent_key", "en") == "nonexistent_key"


def test_new_040_keys_present_both_langs():
    expected = {
        "totals_mode_by_category", "totals_mode_forecast", "forecast_within",
        "history_month_est", "bind_duplicate", "duplicate_suffix",
        "field_payment_method", "budget_over", "rate_stale_warning",
    }
    for lang in ("en", "ja"):
        missing = expected - set(_STRINGS[lang])
        assert not missing, f"{lang} missing: {sorted(missing)}"
