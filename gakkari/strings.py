from __future__ import annotations

from datetime import date

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # Field labels
        "field_name": "Name",
        "field_amount": "Amount",
        "field_currency": "Currency",
        "field_period": "Period",
        "field_renewal": "Next Renewal",
        "field_category": "Category",
        "field_status": "Status",
        # Renewal shortcuts
        "renewal_today": "Today",
        "renewal_tomorrow": "Tomorrow",
        # Billing periods
        "period_monthly": "monthly",
        "period_yearly": "yearly",
        "period_quarterly": "quarterly",
        "period_weekly": "weekly",
        # Statuses
        "status_active": "active",
        "status_paused": "paused",
        "status_cancelled": "cancelled",
        # Tax modes
        "tax_none": "none",
        "tax_inclusive": "inclusive",
        "tax_exclusive": "exclusive",
        # Bindings / footer labels
        "bind_add": "Add",
        "bind_edit": "Edit",
        "bind_delete": "Delete",
        "bind_quit": "Quit",
        "bind_help": "Help",
        "bind_lang": "Lang",
        # Misc UI
        "title_shortcuts": "Keyboard shortcuts",
        "help_text": "a Add · e Edit · d Delete · q Quit · L Lang",
        "no_subs": "No subscriptions. Press [a] to add one.",
        "due_soon": "▲ DUE SOON",
        "no_notes": "no notes",
        "summary_subs": "subs",
        "summary_next": "next",
        "summary_monthly": "mo.est",
        "summary_yearly": "yr.est",
        # Known categories
        "cat_entertainment": "Entertainment",
        "cat_tools": "Tools",
        "cat_music": "Music",
        "cat_news": "News",
        "cat_productivity": "Productivity",
        "cat_health": "Health",
        "cat_gaming": "Gaming",
        "cat_storage": "Storage",
    },
    "ja": {
        # Field labels
        "field_name": "名前",
        "field_amount": "金額",
        "field_currency": "通貨",
        "field_period": "周期",
        "field_renewal": "更新日",
        "field_category": "種別",
        "field_status": "状態",
        # Renewal shortcuts
        "renewal_today": "今日",
        "renewal_tomorrow": "明日",
        # Billing periods
        "period_monthly": "毎月",
        "period_yearly": "毎年",
        "period_quarterly": "四半期",
        "period_weekly": "毎週",
        # Statuses
        "status_active": "有効",
        "status_paused": "停止中",
        "status_cancelled": "解約済み",
        # Tax modes
        "tax_none": "なし",
        "tax_inclusive": "税込み",
        "tax_exclusive": "税抜き",
        # Bindings / footer labels
        "bind_add": "追加",
        "bind_edit": "編集",
        "bind_delete": "削除",
        "bind_quit": "終了",
        "bind_help": "ヘルプ",
        "bind_lang": "言語",
        # Misc UI
        "title_shortcuts": "キーボードショートカット",
        "help_text": "a 追加 · e 編集 · d 削除 · q 終了 · L 言語",
        "no_subs": "サブスクなし。[a] で追加。",
        "due_soon": "▲ 期限近",
        "no_notes": "メモなし",
        "summary_subs": "件",
        "summary_next": "次回",
        "summary_monthly": "月計",
        "summary_yearly": "年計",
        # Known categories
        "cat_entertainment": "エンタメ",
        "cat_tools": "ツール",
        "cat_music": "音楽",
        "cat_news": "ニュース",
        "cat_productivity": "仕事術",
        "cat_health": "健康",
        "cat_gaming": "ゲーム",
        "cat_storage": "ストレージ",
    },
}


def t(key: str, lang: str) -> str:
    return _STRINGS.get(lang, _STRINGS["en"]).get(key) or _STRINGS["en"].get(key, key)


def fmt_date(d: date, lang: str) -> str:
    if lang == "ja":
        return f"{d.year}年{d.month}月{d.day}日"
    return d.strftime("%Y-%m-%d")


def fmt_period(period: str, lang: str) -> str:
    key = f"period_{period}"
    return t(key, lang)


def fmt_status(status: str, lang: str) -> str:
    key = f"status_{status}"
    return t(key, lang)


def fmt_tax_mode(mode: str, lang: str) -> str:
    key = f"tax_{mode}"
    return t(key, lang)


def fmt_category(category: str, lang: str) -> str:
    if not category:
        return "—"
    key = f"cat_{category.lower().replace(' ', '_')}"
    result = _STRINGS.get(lang, _STRINGS["en"]).get(key)
    return result if result is not None else category
