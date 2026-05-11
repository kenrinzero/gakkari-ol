# Windows Task Scheduler recipe

Goal: have Windows print today's Gakkari OL renewal summary in a console window every time you log in, so you see what's renewing before opening anything else.

The CLI is `python -m gakkari --notice` — one-shot, reads the DB, prints to stdout, exits. Task Scheduler is just the outer trigger.

---

## TL;DR — one-line PowerShell

Run this once in an admin PowerShell from anywhere:

```powershell
$exe = "C:\Users\kenrin\Project\Gakkari_OL\.venv\Scripts\pythonw.exe"
$arg = "-m gakkari --notice"
# Actually: use the regular python.exe (not pythonw) so a console window appears.
$exe = "C:\Users\kenrin\Project\Gakkari_OL\.venv\Scripts\python.exe"
$task = New-ScheduledTaskAction -Execute $exe -Argument $arg `
    -WorkingDirectory "C:\Users\kenrin\Project\Gakkari_OL"
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable
Register-ScheduledTask -TaskName "Gakkari OL — daily notice" `
    -Action $task -Trigger $trigger -Settings $settings -Force
```

Log out and back in — a console window pops, the notice prints, and the window stays until you press a key. To inspect the task afterwards: `Get-ScheduledTask -TaskName "Gakkari OL — daily notice"`.

To delete: `Unregister-ScheduledTask -TaskName "Gakkari OL — daily notice" -Confirm:$false`.

---

## Keeping the window open

By default the console closes the instant `python` exits. Three options, pick one:

**A. Wrap in a `cmd /K` call.** Re-register the action so the window stays open until you close it:

```powershell
$exe = "C:\Windows\System32\cmd.exe"
$arg = '/K "C:\Users\kenrin\Project\Gakkari_OL\.venv\Scripts\python.exe -m gakkari --notice"'
```

**B. Append a pause.** Have python print, then wait for keypress before exiting. Easiest if you want minimal scheduler config — just write a `notice.bat` next to the project root:

```bat
@echo off
cd /d "C:\Users\kenrin\Project\Gakkari_OL"
.venv\Scripts\python.exe -m gakkari --notice
pause
```

…and point Task Scheduler at the `.bat` file.

**C. Redirect to a log file you tail later.** Useful if you want history rather than a live popup:

```powershell
$arg = "-m gakkari --notice >> C:\Users\kenrin\gakkari-notice.log 2>&1"
```

(Wrap the whole thing in `cmd /c` so the redirect works — `python.exe` doesn't process `>>` itself.)

---

## UTF-8 and Japanese output

The CLI calls `sys.stdout.reconfigure(encoding="utf-8")` so the JA banner (`【週間】更新予定スレ`) and kaomoji render correctly in modern Windows Terminal. If you see mojibake in the legacy Console Host (`conhost.exe`), set the codepage to 65001 before running:

```powershell
$arg = '/K "chcp 65001 >nul && C:\Users\kenrin\Project\Gakkari_OL\.venv\Scripts\python.exe -m gakkari --notice"'
```

`Windows Terminal` (the default on Win11) does this transparently and you don't need the chcp dance.

---

## Forcing English output

Add `--lang en` to the argument. Overrides whatever `Settings.language` is in the DB:

```powershell
$arg = "-m gakkari --notice --lang en"
```

---

## Other triggers

`-AtLogOn -User $env:USERNAME` is the login trigger. Alternatives:

- Fixed time every day:
  ```powershell
  $trigger = New-ScheduledTaskTrigger -Daily -At "08:00"
  ```
- After waking from sleep: requires combining `-AtLogOn` with `-StartWhenAvailable` plus the registry tweak `HKLM\System\CurrentControlSet\Services\WSearch` — not worth it for this use case. Daily-at-time covers it.

---

## What the output looks like

```
[Gakkari OL] Upcoming renewals — 2026-05-11 (月)
───────────────────────────────────────────────

!! TODAY (1):
  - test 2  HUF 3,000.00  (weekly)

Upcoming (next 7 days):
  +1d 2026-05-12 (火)  test  YEN 2,700.00
  +4d 2026-05-15 (金)  test 3  USD 90,000.00
```

Empty-day fallback (when nothing renews today):

```
[Gakkari OL] Upcoming renewals — 2026-05-11 (月)
───────────────────────────────────────────────

TODAY: nothing scheduled  (´_ゝ｀)

Upcoming (next 7 days):
  +2d 2026-05-13 (水)  Spotify  USD 9.99
```

---

## Troubleshooting

- **Task fires but no window appears**: the action is using `pythonw.exe` instead of `python.exe`. `pythonw` is the "GUI" variant that suppresses console output. Switch to `python.exe`.
- **`ModuleNotFoundError: No module named 'gakkari'`**: working directory is wrong. The action needs `-WorkingDirectory "C:\Users\kenrin\Project\Gakkari_OL"`, OR install the package globally (`pip install -e .` already done in the venv, but the venv's `python.exe` only sees `gakkari` when invoked via the venv).
- **`UnicodeEncodeError`**: the console is in cp1252. Either upgrade to Windows Terminal, or do the `chcp 65001` dance shown above.
- **Task runs but prints nothing**: DB doesn't exist yet. Launch the TUI once (`python -m gakkari`) to create `data/gakkari.db` and add at least one subscription.
