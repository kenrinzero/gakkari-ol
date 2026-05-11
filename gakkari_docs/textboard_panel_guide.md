# Textboard Notice Panel — Implementation Guide

This document specifies the right-column weekly notice panel for Gakkari OL. It is opinionated where the choice is settled and explicit about open questions where it isn't. Iterate freely during implementation; nothing here is precious.

---

## 1. Design intent

The panel commits to the textboard aesthetic — wall of text, post-style metadata lines, `<hr>`-equivalent rules, kaomoji as punctuation — rather than the box-drawn notice cards sketched in the scope doc. Two reasons. First, it gives the right column its own visual identity, distinct from the structured multi-line entry blocks in the center. Second, it earns its place: a generic decorated calendar would be filler, while a recognizable 2ch-flavored thread is a small piece of cultural specificity that costs nothing extra to implement and matches the project's overall retro-anime register.

The functional model stays as the scope doc specifies: a rolling seven-day window starting from today, one notice per day, regenerated when the date rolls over or when subscription data changes. No animation. No sage/age semantics. The textboard look is the entire personality layer the panel needs.

---

## 2. Visual anatomy

### 2.1 Column budget

At ~30% of typical terminal width, the panel's interior content area is roughly 35–45 columns. The spec targets ~40 columns and degrades gracefully below that. Real 2ch assumed 60–80, so the post anatomy here is compressed.

### 2.2 Whole panel

```
┌── (existing amber title bar) ────────┐
│        【週間】更新予定スレ          │
└──────────────────────────────────────┘

1 ：OL ：2026/05/11(月) ID:a4c91b2e
Netflix が3日後に更新
(´・ω・｀)
──────────────────────────────────────

2 ：OL ：2026/05/12(火) ID:7f3d2e10
今日は更新なし
(´_ゝ｀)
──────────────────────────────────────

3 ：OL ：2026/05/13(水) ID:c2b81fa3
Spotify 明日更新
Σ(ﾟДﾟ)
──────────────────────────────────────

... (posts 4 through 7 follow the same shape)
```

The banner at top is the existing right-column title bar — not a separate box-drawn widget. The thread title text just lives inside it. Below the banner, posts stack with no outer container: metadata line, body, kaomoji, separator rule. This is the 2ch "wall of text" anatomy from the reference doc, compressed for column width.

### 2.3 Single post anatomy

Each post is exactly four lines:

```
{post_no} ：OL ：{yyyy/mm/dd}({day}) ID:{hash8}
{body}
{face}
{rule}
```

- `post_no` — 1 through 7, the day's index in the window
- `OL` — fixed handle, untranslated (it's the OL's name)
- `{yyyy/mm/dd}` — ISO-style date
- `{day}` — single-character JA weekday (`月火水木金土日`) regardless of UI language; preserves 2ch flavor and uses one column instead of three
- `ID:{hash8}` — 8-char hex hash derived from the post content (see §4.3)
- `{body}` — one or two lines, language-aware (see §4.2)
- `{face}` — kaomoji chosen by post type (see §4.4)
- `{rule}` — `─` (U+2500) repeated to the column width

Column count for the metadata line: post number (1) + space + `：` (2) + `OL` (2) + space + `：` (2) + date (10) + `(` (1) + day (2) + `)` (1) + space + `ID:` (3) + hash (8) = ~33 columns. Fits cleanly at 40.

### 2.4 Color and markup

The existing palette is amber on near-black. Within that single hue, distinguish parts of the metadata line using Rich modifiers rather than color shifts:

```
[bold]{post_no}[/] ：[bold]OL[/] ：{date}({day}) [dim]ID:{hash}[/]
{body}
[italic]{face}[/]
[dim]{rule}[/]
```

Bold for the post number and the OL handle — the real 2ch convention is bold-green name, and here bold alone suffices because the panel is monochrome. Dim for the ID and the separator. Italic on the kaomoji is optional and worth trying for a small visual lift; drop it if it renders badly in Windows Terminal (see §9). Body text is normal foreground.

The thread title in the banner can be bold and slightly larger if your title-bar styling supports that; otherwise bold alone.

---

## 3. Data model

```python
from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class NoticePost:
    post_no: int          # 1..7
    date: date            # the day this post represents
    day_label: str        # single-char JA weekday: 月火水木金土日
    post_id: str          # 8-char hex hash
    body: str             # already-localized body text
    face: str             # kaomoji
    is_renewal: bool      # true if any subs renew on this day
```

Frozen because each generation produces a fresh list — there is no mutation in place. Bodies are stored already-localized so the renderer stays language-agnostic.

---

## 4. Generation logic

### 4.1 Entry point

```python
def build_notice_posts(
    subs: list[Subscription],
    today: date,
    lang: str,
    *,
    window: int = 7,
) -> list[NoticePost]:
    ...
```

Takes the current (active or paused) subscription list, today's date, and the UI language. Returns exactly `window` posts covering `today` through `today + window - 1`.

Cancelled subs must be filtered out before this is called, matching the established `list_subscriptions(conn, statuses=("active", "paused"))` signature.

### 4.2 Body text rules

For each day in the window, find subscriptions whose `next_renewal_date` equals that day. Cases:

- **Zero renewals on this day.** Use one of 2–3 calm default messages from `strings.py`, picked deterministically (§4.5).
- **One renewal, day is today.** `{name} renews today!` / `{name} 今日更新！`
- **One renewal, day is tomorrow.** `{name} renews tomorrow` / `{name} 明日更新`
- **One renewal, day is 2–6 days out.** `{name} renews in {n} days` / `{name} が{n}日後に更新`
- **Multiple renewals on one day.** First sub's body on line 1, then a second line `+ {n-1} more` / `他{n-1}件`. (See §9 for an alternative two-name layout.)

Names get truncated with ellipsis if the body line would exceed ~38 columns. Truncation lives in the body builder, not the renderer.

### 4.3 Post ID generation

```python
import hashlib

def _post_id(d: date, body: str) -> str:
    raw = f"{d.isoformat()}|{body}".encode("utf-8")
    return hashlib.md5(raw).hexdigest()[:8]
```

Stable per (date, body), so re-rendering the same day gives the same ID. The cosmetic point of the ID is consistency — it should look like a per-poster hash, which means it can't shuffle on every render.

### 4.4 Face selection

Three faces total, matching the scope doc's 2–3 limit:

```python
FACE_SHOBON = "(´・ω・｀)"   # renewal 2+ days out
FACE_CALM   = "(´_ゝ｀)"     # nothing scheduled
FACE_SHOCK  = "Σ(ﾟДﾟ)"      # due today or tomorrow
```

Mapping:

- Day has a renewal today or tomorrow → `FACE_SHOCK`
- Day has a renewal 2+ days out → `FACE_SHOBON`
- Day has no renewals → `FACE_CALM`

If you want more variation later, expand the pools (not the categories) and pick within a category by hash of `(date, body)`.

### 4.5 Deterministic picking for empty-day messages

A small pool of 2–3 messages per language, indexed by `int(post_id, 16) % len(pool)`. Consecutive empty days look visually different without random shuffle on every render.

EN pool:
- `No renewals today`
- `Nothing scheduled`
- `A quiet day`

JA pool:
- `今日は更新なし`
- `予定なし`
- `静かな一日`

---

## 5. Rendering

### 5.1 Per-post render

```python
from rich.text import Text
from rich.console import Group

def render_post(post: NoticePost, width: int) -> Group:
    meta = Text()
    meta.append(f"{post.post_no} ", style="bold")
    meta.append("：")
    meta.append("OL", style="bold")
    meta.append(f" ：{post.date.isoformat()}({post.day_label}) ")
    meta.append(f"ID:{post.post_id}", style="dim")

    body = Text(post.body)
    face = Text(post.face, style="italic")
    rule = Text("─" * width, style="dim")

    return Group(meta, body, face, rule)
```

`width` is the panel's current interior content width, queried from the Textual widget on render.

### 5.2 Panel render

```python
def render_notice_panel(posts: list[NoticePost], width: int) -> Group:
    return Group(*(render_post(p, width) for p in posts))
```

Trivial. The panel widget calls this on every refresh.

### 5.3 Widget choice

A single `Static` widget inside the right column, updated via `static_widget.update(render_notice_panel(...))`. The state is tiny (seven posts), updates are rare (once per day or on subscription change), and re-rendering everything is simpler and faster than incremental update.

`RichLog` is the wrong fit — that's for append-only streams. A `ScrollableContainer` with per-post child widgets is unnecessary mechanism for a fixed-size panel.

If the seven posts ever overflow the visible height at small terminal sizes, wrap the `Static` in a `VerticalScroll` and let Textual handle it. Don't try to match the window count to viewport height.

---

## 6. Widget integration & refresh

### 6.1 Refresh triggers

The panel regenerates when:

1. App startup.
2. After any subscription is added, edited, or status-changed (including soft delete).
3. The system date rolls over while the app is running.

Trigger 3 needs a small bit of plumbing. Cheapest implementation: store `self._last_seen_date: date` on the panel widget (or the app), and on every scheduled tick via Textual's `set_interval` check `date.today()` against it. A 60-second interval is plenty — nothing in this app needs sub-minute reactivity.

### 6.2 Wiring shape

The notice panel widget owns:

- A reference to the DB connection (or a callable that returns the current sub list)
- The current language setting
- The `_last_seen_date` tracker
- The interval task (deferrable, see §8)

Its `refresh_posts()` method does: `list_subscriptions(...)` → `build_notice_posts(...)` → `render_notice_panel(...)` → `self.static.update(...)`. Add/edit/delete flows call `panel.refresh_posts()` after committing.

### 6.3 Banner / thread title

The existing right-column title bar displays `【週間】更新予定スレ` (JA) or `Upcoming renewals` (EN). This is a separate string from the body content and lives in the same `strings.py` namespace as the panel.

---

## 7. i18n hookup

New keys for `strings.py`:

```
notice_thread_title
notice_renews_today
notice_renews_tomorrow
notice_renews_in_n_days
notice_plus_n_more
notice_empty_1
notice_empty_2
notice_empty_3
```

Body templates take `{name}` and (where applicable) `{n}` placeholders. Use `.format(...)`, not f-strings — the templates come from the string table at runtime.

`OL` is not translated. `月火水木金土日` is not translated. Both are part of the look.

---

## 8. MVP vs deferred

**MVP:**

- The dataclass and the build function
- The render functions
- A `NoticePanel` widget (or whatever you name it) inside the right column
- Refresh on app startup and on subscription changes
- The three faces and the localized strings
- Banner text in the title bar

**Deferred (post-MVP, optional polish):**

- Date-rollover detection via `set_interval`. Acceptable to ship without it initially — the panel will refresh on the next subscription change or app restart. Add when it bothers you.
- Multi-renewal display variants beyond "first sub + N more".
- Per-day expansion (selecting a post to see all renewals for that day). Probably not worth doing; the center column is the authoritative renewal list.
- Any kind of post-count growth across days (1, 2, 3 incrementing forever) — keep it 1–7 per generation, no persistence between runs.

---

## 9. Open questions for iteration

Genuine choice points, not pre-settled defaults dressed up as questions.

- **Day labels.** Spec says always-JA single-char (`月`, `火`...). Alternative: per-language (`Mon`, `Tue`... in EN), which is clearer but loses the 2ch flavor and costs ~2 extra columns. Try always-JA first; switch if EN users find it opaque.
- **Multi-renewal body layout.** Spec says first name on line 1, `+{n-1} more` on line 2. Alternatives: two names then `+N more`; a single line `{n} subs renew today`. Try the first; revisit if it reads awkwardly with three or more renewals on the same day.
- **Separator weight.** Spec uses `─` (light). `━` (heavy) is more aggressive and closer to a real `<hr>`. Try light; heavy may make the panel feel claustrophobic in narrow terminals.
- **Italic on kaomoji.** Some terminals render italic poorly. If it looks bad in PowerShell or Windows Terminal, drop the italic — bold-or-nothing is fine and matches the rest of the palette.
- **Banner format.** `【週間】更新予定スレ` is the 2ch-flavored option. Plainer alternatives: `更新予定` or `Upcoming renewals` without the bracket flourish. The flourish costs nothing if you like it.
- **Empty-day pool size.** Three messages is the spec; two is fine and one would feel monotonous. Don't go above four — variation past that starts to feel like the panel is trying too hard.

---

## 10. Implementation order

A reasonable sequencing:

1. Add `strings.py` keys and templates.
2. Write `NoticePost`, `build_notice_posts`, `_post_id`, face constants, face mapping — pure logic, no Textual.
3. Unit-test `build_notice_posts` with a couple of fixture lists. Easy and pays for itself.
4. Write `render_post` and `render_notice_panel`. Render to a plain string in a small script first to confirm the post anatomy looks right at a few widths.
5. Create the `NoticePanel` widget, wire it into the right column, hook refresh into add/edit/delete flows.
6. Add the banner text to the title bar.
7. (Later, when it bothers you.) Add date-rollover detection.
