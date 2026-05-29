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
        "period_half_yearly": "half-yearly",
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
        "bind_advance": "Kept it",
        "bind_quit": "Quit",
        "bind_help": "Help",
        "bind_lang": "Lang",
        "bind_filter": "Filter",
        "bind_gross_net": "Gross/Net",
        "bind_paused": "Paused",
        "bind_archive": "Archive",
        "bind_settings": "Settings",
        "bind_export": "Export",
        "bind_import": "Import",
        "bind_notices": "Notices",
        "bind_sort": "Sort",
        "bind_totals": "Totals",
        "bind_convert": "Convert",
        # Phase 2 UI
        "filter_placeholder": "Filter by name or category…",
        "totals_monthly": "monthly",
        "totals_yearly": "yearly",
        "display_net": "net",
        "display_gross": "gross",
        "paused_shown": "+paused",
        "cancelled_shown": "+archive",
        "rate_fallback_warning": "rate",
        # Sort modes (Phase 6)
        "sort_date": "date",
        "sort_period": "period",
        "sort_name": "name",
        "sort_amount": "amount",
        "indicator_sort": "sort:{mode}",
        # Totals view modes (Phase 6)
        "totals_mode_estimate": "estimate",
        "totals_mode_monthly_strict": "monthly only",
        "totals_mode_yearly_strict": "yearly only",
        "totals_mode_by_period": "by period",
        # Income totals mode (amortized monthly vs income)
        "income_label": "income",
        "income_committed": "committed",
        "income_left": "left",
        "income_over": "over",
        "income_unset": "set monthly income in settings (s)",
        # Conversion column (Phase 6)
        "indicator_conv": "conv→{target}",
        # Auto-advance (Phase 6)
        "advance_notify": "{name}: {old} → {new}",
        # History screen (Phase 6)
        "bind_history": "History",
        "bind_notes": "Notes",
        "history_title": "Renewal history — {count} entries · total {base} {total}",
        "history_title_empty": "Renewal history",
        "history_empty_msg": "No renewals logged yet. Press [k] on a sub to log one.",
        # DB error notifications (Phase 6)
        "settings_load_error": "Could not load settings: {err}",
        "settings_save_error": "Could not save settings: {err}",
        "history_load_error": "Could not load history: {err}",
        # Tutorial panel (Phase 6)
        "tutorial_title": "Keybindings",
        "tutorial_section_editing": "Editing",
        "tutorial_section_views": "Views & filters",
        "tutorial_section_screens": "Screens",
        "tutorial_section_app": "App",
        # Notice panel (Phase 3)
        "notice_thread_title": "Upcoming renewals",
        "notice_renews_today": "{name} renews today!",
        "notice_trial_ends": "{name} trial ends today!",
        "notice_plus_n_more": "+ {n} more",
        "notice_empty_1": "No renewals today",
        "notice_empty_2": "Nothing scheduled",
        "notice_empty_3": "A quiet day",
        # Settings modal
        "settings_title": "Settings",
        "settings_base_currency": "Base currency",
        "settings_convert_currency": "Convert-to currency (blank = base)",
        "settings_display_mode": "Price display",
        "settings_due_soon_days": "Due-soon threshold (days)",
        "settings_monthly_income": "Monthly income (blank = none)",
        "settings_income_currency": "Income currency (blank = base)",
        # Export modal
        "export_title": "Export subscriptions",
        "export_format": "Format",
        "export_path": "Output path",
        # Import modal
        "import_title": "Import subscriptions",
        "import_path": "Input path",
        "import_file_missing": "File does not exist",
        "import_success": "Imported {count} subscription(s)",
        "import_partial": "Imported {count}, skipped {errors} row(s)",
        "export_success": "Exported {count} subscription(s) to {path}",
        # Misc UI
        "title_shortcuts": "Keyboard shortcuts",
        "help_text": "a Add · e Edit · d Delete · k Kept it · h History · / Filter · g Gross/Net · p Paused · v Archive · o Sort · t Totals · c Convert · s Settings · x Export · i Import · L Lang · n Notices · q Quit",
        "no_subs": "No subscriptions. Press [a] to add one.",
        "due_soon": "▲ DUE SOON",
        "no_notes": "no notes",
        "summary_subs": "subs",
        "summary_next": "next",
        "summary_monthly": "mo.est",
        "summary_yearly": "yr.est",
        # Notes view
        "notes_header": "Notes",
        "notes_placeholder": "Type notes here...",
        # Footer (context-aware)
        "footer_notes": "→ Notes",
        "footer_back": "← Back",
        "footer_save": "Ctrl+S Save",
        # Modal labels
        "modal_add_title": "Add Subscription",
        "modal_edit_title": "Edit Subscription",
        "modal_save": "Save",
        "modal_cancel": "Cancel",
        "modal_confirm_delete": "Cancel this subscription?",
        "modal_yes": "Yes",
        "modal_no": "No",
        # Validation errors
        "err_name_required": "Name is required.",
        "err_amount_invalid": "Amount must be a valid number (e.g. 9.99).",
        "err_amount_negative": "Amount must be non-negative.",
        "err_currency_invalid": "Currency must be a 3-letter code (e.g. USD).",
        "err_convert_currency_invalid": "Convert-to currency must be a 3-letter code or blank.",
        "err_income_currency_invalid": "Income currency must be a 3-letter code or blank.",
        "err_date_invalid": "Date must be YYYY-MM-DD format.",
        "err_tax_rate_invalid": "Tax rate must be a valid number.",
        "err_fix_before_save": "Fix before saving",
        # Extra field labels
        "field_notes": "Notes",
        "field_tax_mode": "Tax mode",
        "field_tax_rate": "Tax rate (%)",
        "field_trial_ends": "Trial ends (optional)",
        # Due-soon inline
        "due_days": "days",
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
        "period_half_yearly": "半年",
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
        "bind_advance": "更新済",
        "bind_quit": "終了",
        "bind_help": "ヘルプ",
        "bind_lang": "言語",
        "bind_filter": "絞り込み",
        "bind_gross_net": "税込/税抜",
        "bind_paused": "停止中",
        "bind_archive": "解約済",
        "bind_settings": "設定",
        "bind_export": "書出",
        "bind_import": "読込",
        "bind_notices": "通知",
        "bind_sort": "並替",
        "bind_totals": "合計",
        "bind_convert": "換算",
        # Phase 2 UI
        "filter_placeholder": "名前・種別で絞り込み…",
        "totals_monthly": "月計",
        "totals_yearly": "年計",
        "display_net": "税抜",
        "display_gross": "税込",
        "paused_shown": "+停止中",
        "cancelled_shown": "+解約済",
        "rate_fallback_warning": "為替",
        # Sort modes (Phase 6)
        "sort_date": "日付",
        "sort_period": "周期",
        "sort_name": "名前",
        "sort_amount": "金額",
        "indicator_sort": "順:{mode}",
        # Totals view modes (Phase 6)
        "totals_mode_estimate": "概算",
        "totals_mode_monthly_strict": "月次のみ",
        "totals_mode_yearly_strict": "年次のみ",
        "totals_mode_by_period": "周期別",
        # Income totals mode (amortized monthly vs income)
        "income_label": "収入",
        "income_committed": "支出",
        "income_left": "残り",
        "income_over": "超過",
        "income_unset": "設定で月収を入力してください",
        # Conversion column (Phase 6)
        "indicator_conv": "換算→{target}",
        # Auto-advance (Phase 6)
        "advance_notify": "{name}：{old} → {new}",
        # History screen (Phase 6)
        "bind_history": "履歴",
        "bind_notes": "メモ",
        "history_title": "更新履歴 — {count}件 · 合計 {base} {total}",
        "history_title_empty": "更新履歴",
        "history_empty_msg": "履歴なし。サブスクで [k] を押して記録。",
        # DB error notifications (Phase 6)
        "settings_load_error": "設定の読込に失敗: {err}",
        "settings_save_error": "設定の保存に失敗: {err}",
        "history_load_error": "履歴の読込に失敗: {err}",
        # Tutorial panel (Phase 6)
        "tutorial_title": "操作一覧",
        "tutorial_section_editing": "編集",
        "tutorial_section_views": "表示・絞り込み",
        "tutorial_section_screens": "画面",
        "tutorial_section_app": "アプリ",
        # Notice panel (Phase 3)
        "notice_thread_title": "【週間】更新予定スレ",
        "notice_renews_today": "{name} 今日更新！",
        "notice_trial_ends": "{name} 体験版終了！",
        "notice_plus_n_more": "他{n}件",
        "notice_empty_1": "今日は更新なし",
        "notice_empty_2": "予定なし",
        "notice_empty_3": "静かな一日",
        # Settings modal
        "settings_title": "設定",
        "settings_base_currency": "基準通貨",
        "settings_convert_currency": "換算先通貨（空欄で基準と同じ）",
        "settings_display_mode": "表示モード",
        "settings_due_soon_days": "期限近通知（日数）",
        "settings_monthly_income": "月収（空欄でなし）",
        "settings_income_currency": "収入通貨（空欄で基準）",
        # Export modal
        "export_title": "サブスクを書き出す",
        "export_format": "形式",
        "export_path": "出力先",
        # Import modal
        "import_title": "サブスクを読み込む",
        "import_path": "読込元",
        "import_file_missing": "ファイルが存在しません",
        "import_success": "{count}件のサブスクを読み込みました",
        "import_partial": "{count}件読込、{errors}件スキップ",
        "export_success": "{count}件を {path} に書き出しました",
        # Misc UI
        "title_shortcuts": "キーボードショートカット",
        "help_text": "a 追加 · e 編集 · d 削除 · k 更新済 · h 履歴 · / 絞込 · g 税込/抜 · p 停止中 · v 解約済 · o 並替 · t 合計 · c 換算 · s 設定 · x 書出 · i 読込 · L 言語 · n 通知 · q 終了",
        "no_subs": "サブスクなし。[a] で追加。",
        "due_soon": "▲ 期限近",
        "no_notes": "メモなし",
        "summary_subs": "件",
        "summary_next": "次回",
        "summary_monthly": "月計",
        "summary_yearly": "年計",
        # Notes view
        "notes_header": "メモ",
        "notes_placeholder": "メモを入力...",
        # Footer (context-aware)
        "footer_notes": "→ メモ",
        "footer_back": "← 戻る",
        "footer_save": "Ctrl+S 保存",
        # Modal labels
        "modal_add_title": "サブスク追加",
        "modal_edit_title": "サブスク編集",
        "modal_save": "保存",
        "modal_cancel": "キャンセル",
        "modal_confirm_delete": "このサブスクを解約しますか？",
        "modal_yes": "はい",
        "modal_no": "いいえ",
        # Validation errors
        "err_name_required": "名前は必須です。",
        "err_amount_invalid": "金額は有効な数値で入力してください。",
        "err_amount_negative": "金額は0以上にしてください。",
        "err_currency_invalid": "通貨は3文字のコードで入力してください。",
        "err_convert_currency_invalid": "換算先通貨は3文字のコードか空欄で入力してください。",
        "err_income_currency_invalid": "収入通貨は3文字のコードか空欄で入力してください。",
        "err_date_invalid": "更新日はYYYY-MM-DD形式で入力してください。",
        "err_tax_rate_invalid": "税率は有効な数値で入力してください。",
        "err_fix_before_save": "保存前に修正",
        # Extra field labels
        "field_notes": "メモ",
        "field_tax_mode": "税区分",
        "field_tax_rate": "税率 (%)",
        "field_trial_ends": "体験版終了日（任意）",
        # Due-soon inline
        "due_days": "日",
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
