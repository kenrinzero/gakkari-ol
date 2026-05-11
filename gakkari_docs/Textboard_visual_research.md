# The Visual Anatomy of Late‑90s/Early‑2000s Textboards: A Reconstruction Guide

## TL;DR
- Late‑90s/early‑2000s Japanese textboards (Ayashii World → Amezou → 2channel) and their Western descendants (world2ch, 4‑ch, Kareha/Wakaba/Shiichan boards) were almost entirely **HTML 3.2/4.0 Transitional**, table‑based, flat‑file CGI/Perl pages with minimal or no CSS; their look is defined by a near‑white or pale‑cream background, dark serif‑less text, blue/purple/red link colors, and aggressive horizontal `<hr>` rules separating every post in a long vertical "wall of text" with no avatars, no images, and no decoration beyond simple bold name labels and `>>1` style backlinks.
- Typography on the Japanese originals is the **MS PGothic** proportional gothic at roughly 12 px / ~16 px line‑height, full‑width punctuation, mixed half/full‑width Latin characters, and pervasive Shift_JIS art ("AA") that depends specifically on PGothic's column widths — Western clones either reused this stack or substituted **Mona/IPA Mona PGothic** to keep AA aligned; non‑AA posts tend to be short one‑liners or 2–4 lines, while AA posts span 10–40 lines of fixed‑column glyphs.
- The post form is a compact `<table>` with a small one‑line `Name:` field, an `E‑mail:` field (where typing `sage` suppresses bumping), an optional `Subject:` field, a `<textarea>` of roughly **rows=10–14, cols=60–80**, and a single grey submit button labelled "書き込む" / "Submit" — buttons and inputs use the unstyled OS‑native chrome of Windows 98/2000 era IE, which is itself a defining part of the look.

---

## Key Findings

**1. The defining color palette.** Period‑authentic Japanese textboards (2ch‑style/0ch‑style/Pseud0ch CSS) used near‑white or off‑white backgrounds (#FFFFFF, #EFEFEF white‑smoke, or the lightly warm #FFFFEE), dark text (#000000 or maroon #800000 in the Futaba lineage), blue links (#0000EE / #0000FF, visited #551A8B purple, hover/active #DD0000 red), and a thin `<hr>` ruled in maroon or dark grey between posts. The Futaba/Yotsuba branch (used as the *imageboard* counterpart and emulated by Wakaba and 4chan's stock styles) is the warmer cream #FFFFEE body with #F0E0D6 reply blocks, #800000 maroon subject text, and #117743 greentext — these exact values (#FFFFEE / #F0E0D6 / #800000 / #0000EE / #DD0000) are encoded in Futaba's original `futaba.css` and copied verbatim into Wakaba/Kareha/Futallaby. 2channel itself in 1999–2003 was even plainer: a body bgcolor of white or `#EFEFEF`, no reply boxes at all, just `<hr>` separators between flat post blocks.

**2. Page chrome and layout.** A 2ch thread page (read.cgi output, c. 2000–2003) was a single `<html>` doc, served as Shift_JIS, with structure roughly:
- `<title>` showing thread title and post count
- A header line: board name, link back to subject list (`subback.html`), and "最新50" / "全部" / "1‑100" navigation
- A bold thread title (often `<font size="+1">` or `<b>` rather than `<h1>`)
- A vertical run of post blocks, each:
  - `<dt>` line: `1 名前：名無しさん ：YYYY/MM/DD(曜) HH:MM:SS ID:xxxxx`
  - `<dd>` block: the post body, with `<br>` for line breaks, no `<p>` wrapping
- `<hr>` between posts (or no rule, with just whitespace) — the look is a relentless stack of left‑aligned text
- Footer with a posting form, then board nav.

The board top page (subject.txt rendered) was a numbered list of threads with reply counts in parentheses: `1: 雑談スレ (321)` — pure links, no thumbnails.

**3. HTML/CSS technology.** Japanese boards generally avoided CSS until the late 2000s — pages relied on `<font color="">`, `bgcolor="" `, `<table border="0" cellpadding="2" cellspacing="0">` and `<hr>`. Western textboard scripts went the other way: Kareha (Perl, by !WAHa.06x36), Wakaba (Perl, image‑mode), and Shiichan (PHP, by Shii) explicitly used XHTML 1.0 Strict + external CSS. Kareha shipped multiple alternate stylesheets selected via `<link rel="alternate stylesheet">`: `futaba.css`, `burichan.css`, `headline.css` (the default for text mode), `pseud0ch.css` (the canonical 2channel imitator — Shii actually modelled it on the 0ch script's appearance), plus community themes (`amber.css`, `buun.css`, `tanasinn.css`, `mittens.css`). The default `mode_message` style is `Headline`; the default `mode_image` style is `Futaba`. Pseud0ch is the closest match to the "real" 2ch look.

**4. Post‑form anatomy.** The classic 2ch form, embedded at top and bottom of every page, is a tiny table:

```
名前: [____________________]   E-mail: [____________________]
件名: [______________________________________________]
[                                                              ]
[                  textarea, rows=10, cols=60                  ]
[                                                              ]
[ 書き込む ]
```

- All inputs are unstyled `<input type="text" size="28">`.
- The textarea is typically `rows="10" cols="60"` on 2ch (Wakaba/Kareha defaults: `rows="6" cols="48"` for image mode, `rows="8"–"10"` `cols="65"–"70"` for text mode).
- The "E‑mail" field is the secret control: leave blank → bump; type `sage` (lowercase Latin) → post does not bump the thread; type a real address → name becomes a `mailto:` link.
- Some boards add a small `Link:` / `URL:` field and a single `Subject:` field above the body; checkboxes are rare (occasionally "Don't bump"); dropdowns essentially never appear.
- The submit button is the OS default grey 3D‑bevelled button; no styling, no rounded corners, no hover state — the bevel and Win9x/2000 chrome is itself signature.

**5. Per‑post display details.** A post block in the 2ch era shows, on one line, the post number (often inside square brackets or with a colon), the name field (`名無しさん` "Nameless‑san" by default; tripcode appended as `◆xxxxxxx` after a `#` separator in the input), the timestamp (`2002/04/01(月) 23:45:01`), and in later years an `ID:xxxxxxxx` derived from a hash of IP+date. The name is rendered bold and dark green in many 2ch boards (`color="green"` inline), or maroon in Futaba‑style boards; the rest of the metadata line is plain text. The body follows on the next line, indented or not. Quote/back‑references use the literal string `>>1`, `>>1-9`, `>>7,11` rendered as a blue link to the referenced post — this is the canonical "anchor" syntax that survived to 4chan unchanged. Greentext (Western "ASCII art quoting") is the line‑prefix `>` rendered in #789922 olive‑green — this convention itself came out of the Futaba/Wakaba lineage and was already standard by 2003.

**6. Typography in detail.** The fonts in the cascade on a real 1999–2003 Japanese textboard, served from a CGI on Shift_JIS, would have rendered through the browser's default Japanese font: **MS PGothic** (proportional gothic; PostScript name `MS-PGothic`) at the browser's default size (typically 16px in IE 5/6 but reduced via `<font size="2">` or `<font size="-1">` to roughly 12–13px). MS PGothic is proportional for Latin but every CJK glyph is exactly the same width — this dual property is what makes Shift_JIS art possible. ASCII art / AA on 2ch is *designed for* PGothic's specific metrics; viewing it in any other font (including MS Gothic, the monospace version) breaks alignment. The community‑developed **Mona Font** and later **IPAMonaPGothic** replicate PGothic's metrics for Linux/Mac users. Line‑height in the rendered output is the browser default (roughly 1.0–1.2× of font size; no explicit `line-height` is set). Character spacing is browser default (no `letter-spacing`). Half‑width katakana (ｷﾀ━━━), full‑width punctuation (．，！？), full‑width tildes (～), Greek letters (ω, Σ, Д), and box‑drawing characters (━, ┃, ╋) are mixed freely — a hallmark visual texture.

**7. Posting style / textual texture.** Posts on 2ch in 1999–2003 fall into roughly four shapes:
- **One‑liners** (the majority): `そうだね` / `禿同` / `ｷﾀ━━━(ﾟ∀ﾟ)━━━!!` / `>>5 乙` — often just a kaomoji, a quote backreference, or a single short reaction.
- **Short paragraphs**: 2–6 lines of prose, no formatting, `<br>` line breaks.
- **Kaomoji‑heavy posts** using the period‑specific repertoire: `(´・ω・｀)` (shobon), `(ﾟДﾟ)` (gikoneko stare), `(゜∀゜)` (giko grin), `( ´∀｀)` (Mona), `(((( ;゜Д゜)))` (shivering), `_| ̄|○` (orz), `ｷﾀ━━━(ﾟ∀ﾟ)━━━!!`, `(*´Д｀)ハァハァ`, `工エエェェ(´д｀)ェェエエ工`.
- **AA blocks**: full Shift_JIS art such as the Giko‑neko (1999), Monā (2000), Hattoushin Monā, Shii — these occupy 8–30 lines of carefully aligned PGothic glyphs and assume a wide enough viewport (~600–800px) to not wrap. Wrapping kills the art, which is why early scripts did not enforce word‑wrap on `<dd>`.

Western conventions adopted into Western Kareha boards: `w` / `wwwww` for laughter (Japanese 笑 → "w"), `>` prefix for quoted text (greentext), `>>n` for backrefs, `sage` in the email field, and the explicit "name‑tripcode" form `Anonymous#secret`.

**8. Sage/age visualization.** "Age" (the default — empty email) bumps the thread to the top of `subback.html` and visually moves it; no marker appears on the post itself. "Sage" (typing `sage` in email) does not bump; on most scripts the email field literally becomes `mailto:sage` on hover, which is the only visual cue. Some Kareha themes (Pseud0ch in particular) add a faint background tint or a small `[sage]` label, but classical 2ch shows nothing — the post looks identical to an age post.

**9. Specific boards side‑by‑side.**
- **Ayashii World / Amezou (1996–1999):** Pre‑bumping, reverse chronological flat list, very plain Shift_JIS HTML, no per‑post coloring, large `<hr>` rules; visually closer to a guestbook script of the era than to later 2ch.
- **2channel 1999–2003:** White or very pale background, default Times‑like serif overridden to PGothic via the user's IE default for Shift_JIS pages, post metadata bold + dark green name, `<hr noshade size="1">` between posts, no boxes, no avatars, no signatures; very narrow header strip (board name + a few text links).
- **Futaba Channel (since 2001):** Same script lineage but cream `#FFFFEE` body, `#F0E0D6` reply blocks (a faint warm beige), maroon (#800000) subject and "Reply mode" banner, greentext quoting, image thumbnails inline — this is what Western imageboards (4chan, Wakaba) copied wholesale.
- **world2ch (2003–2006):** Eng2ch (Japanese script translated awkwardly into English), very 2ch‑plain visual layout, partial English/Japanese fields, broken or eccentric form labels after RIR6's late "fixes."
- **4‑ch.net (since 2004):** Kareha with its own customizations; default Headline CSS — narrow text column, white background, simple sans‑serif, very 2ch‑flavored but XHTML/CSS based. Multiple alternate stylesheets selectable from a sidebar (`tanasinn`, `amber`, `buun`, `mittens`, `pseud0ch`, `headline`).
- **Wakaba/Kareha boards (iichan, 4‑ch, sageru, world4ch, etc.):** Stock `futaba.css` and `burichan.css` shipped in the package, plus `headline.css` for text mode; the package also includes a Pseud0ch (fake 2ch) skin.
- **Shiichan boards (world4ch, early 4chan text boards):** PHP, ported by Shii from 0ch's Perl script; visually a 2ch clone with the cream background of the 0ch theme rather than the pure white of bare 2ch.

---

## Details

### Page structure (a reconstructable skeleton)

A faithful early‑2000s 2ch thread page is essentially:

```html
<html><head>
<meta http-equiv="Content-Type" content="text/html; charset=Shift_JIS">
<title>【スレ】タイトル【総合】</title></head>
<body bgcolor="#EFEFEF" text="#000000" link="#0000FF" vlink="#660099" alink="#FF0000">
<font size="2">
<a href="../">板に戻る</a> <a href="subback.html">全部</a> <a href="#bottom">最新50</a>
<hr>
<b><font size="+1">【スレ】タイトル【総合】</font></b>
<hr>
1 ：<font color="green"><b>名無しさん</b></font>：2002/04/01(月) 23:45:01 ID:xxxxxxxx<br>
これはテスト投稿です。<br>
(´・ω・｀)<br>
<br>
2 ：<font color="green"><b>名無しさん</b></font>：2002/04/01(月) 23:46:12 ID:yyyyyyyy<br>
&gt;&gt;1 乙<br>
...
<hr>
<form method=POST action="../test/bbs.cgi">
<table>
<tr><td>名前:</td><td><input name="FROM" size="28"></td>
    <td>E-mail:</td><td><input name="mail" size="28"></td></tr>
<tr><td colspan=4><textarea name="MESSAGE" rows="10" cols="60"></textarea></td></tr>
<tr><td colspan=4><input type=submit value="書き込む"></td></tr>
</table>
</form>
</font></body></html>
```

The presence of an outer `<font size="2">` wrapping the entire body is a signature trick of the era (and of the bbs.cgi templates) used to shrink the default 16px IE rendering down to the dense ~12px look without CSS.

### Form sizing and labels

- 2ch / 0ch / Pseud0ch text mode: `name` size 28, `mail` size 28, `subject` size 35 (text mode only), textarea **rows=10 cols=60** (some boards: rows=8 cols=80).
- Kareha (text mode, default templates): name size 28, link size 28, textarea **rows=8 cols=70** with `wrap="soft"`.
- Wakaba (image mode): name size 28, email size 28, subject size 35, textarea **rows=5 cols=48**, plus a `[file]` input.
- Buttons: bare `<input type="submit">`, OS chrome only; no class names, no inline style.

### Typography stack (concrete)

A faithful CSS stack for recreation:

```css
body {
  font-family: "MS PGothic", "ＭＳ Ｐゴシック", "Mona", "IPAMonaPGothic",
               "submona", "Hiragino Kaku Gothic Pro", Osaka, sans-serif;
  font-size: 12px;
  line-height: 1.2;
  background: #EFEFEF;     /* 2ch */
  /* background: #FFFFEE; */  /* Futaba/Yotsuba */
  color: #000;
}
a:link    { color: #0000FF; }
a:visited { color: #660099; }
a:hover   { color: #FF0000; }
hr { border: 0; border-top: 1px solid #800000; height: 0; }
```

For an authentic *Western* Kareha look, the cascade also commonly resolves to **"MS PGothic", "Mona", monospace** with sizes 10–11px, and the AA segments are wrapped in `<span class="aa">` with `font-family: "Mona","IPAMonaPGothic","MS PGothic",monospace; white-space: pre;`.

### Futaba/Yotsuba palette (exact)

From `futaba.css` (the file Wakaba/Kareha ship):

- Body background: `#FFFFEE`
- Foreground text: `#800000` (maroon)
- Reply block background: `#F0E0D6`
- Link: `#0000EE`
- Link hover: `#DD0000`
- Reply‑mode banner: `#E04000` background, `#FFFFFF` text
- Catalog‑mode banner: `#0040E0`
- Greentext (quoted lines beginning with `>`): `#789922`
- Admin/management banner: `#00B930`
- A faint horizontal rule rendered with a 3‑stop linear gradient from `rgba(255,255,238,1)` → `rgba(128,0,0,0.75)` → `rgba(255,255,238,1)`.

The Burichan variant simply swaps the body for a blueish `#EEF2FF` with reply blocks at `#D6DAF0` and dark navy text `#0F0C5D`; greentext `#789922` is unchanged.

### Post‑number / timestamp formatting

- 2ch: `1 ：名無しさん：2002/04/01(月) 23:45:01 ID:abc12345`
- Kareha (text mode): `1 Name: Anonymous 2010-01-01 12:00 [No.1]`
- Futaba/Wakaba (image mode): `Name: Anonymous  2010-01-01 12:00  No.12345  [Reply]`

In all cases, the post number is a hyperlink/anchor: `<a href="#1" name="1">1</a>`, used for `>>1` back‑references. Backrefs themselves are produced by the script's text filter that scans for `>>\d+` patterns and rewrites them to `<a href="#1" class="reflink">>>1</a>` (Kareha's `.reflink` class).

### Visual density and "wall of text"

The signature look comes from:
- **No avatars, no signatures, no per‑user color, no rep counters, no badges, no sidebar widgets** — every horizontal pixel of the content area is text or rule.
- **Posts stacked vertically with `<hr>` between them**, no boxes, no rounded corners, no shadows.
- **A narrow effective content width** (~600–800 px in 2003 IE rendering), with text running edge to edge and AA blocks dictating the de facto minimum width.
- **Mixed half/full‑width Latin glyphs** within Japanese sentences, which produces uneven inter‑character spacing characteristic of PGothic; this is the *intended* look, not a bug.
- **Dense kaomoji and inline AA** breaking up otherwise plain prose.

### Differences between Japanese and Western boards

- **Encoding:** Japanese boards used Shift_JIS until very late (well into the 2010s on 2ch); Western Kareha/Wakaba boards used UTF‑8 from inception.
- **Font fallback:** Japanese boards relied on the Windows default Japanese font (PGothic) without specifying it. Western Kareha sites *had to* specify a font stack including Mona/IPAMonaPGothic to render AA at all on non‑Japanese systems.
- **Markup quality:** Japanese 2ch‑lineage scripts were Shift_JIS‑aware Perl CGIs emitting HTML 3.2‑style tables and `<font>` tags. Western Kareha/Wakaba emitted XHTML 1.0 Strict with external CSS — visually similar but technically a generation newer.
- **Color culture:** Japanese boards leaned toward neutral, almost monochrome palettes (white/grey/black/blue links). Western imageboard‑descended skins (Futaba/Burichan/Yotsuba) introduced the cream + maroon + greentext combination that became *the* "*chan look" outside Japan.
- **Form ergonomics:** Western boards tended to add larger textareas and richer field sets (Subject, Link/URL, Password for self‑deletion, optional file upload); Japanese boards stayed minimal (Name / E‑mail / body).

### Kaomoji repertoire (period‑accurate, c. 1999–2003)

- `(´・ω・｀)` — shobon (sad/resigned), late‑2002+
- `(ﾟДﾟ)` — gikoneko stare
- `( ´∀｀)` — Mona / friendly grin (Monā established 2000)
- `(゜∀゜)` — giko grin
- `(*´Д｀)` — flushed
- `Σ(ﾟДﾟ)` — shock
- `_| ̄|○` / `orz` — kneeling in despair (2003)
- `ｷﾀ━━━(ﾟ∀ﾟ)━━━!!` — "it's here!" excitement
- `工エエェェ(´д｀)ェェエエ工` — disbelief
- `(´_ゝ｀)` — smug
- `(゚∀゚ ) ｱﾋｬﾋｬ` — laughing maniacally
- `( ´_ゝ`)フーン` — disinterest

These are not decorations; they are *the punctuation* of the medium.

---

## Caveats

- The Wayback Machine's stored 2ch pages from 1999–2001 are sparse, and direct fetching is currently blocked from many automated agents, so several specific details above (exact `bgcolor` hex on 2ch in 1999 vs 2001, exact textarea dimensions per board) are reconstructed from open‑source clones (0ch, 0ch Plus, Pseud0ch, Shiichan, Kareha) and the Bibliotheca Anonoma / Nameless Rumia documentation rather than from primary 2ch source — the 0ch Perl script and Pseud0ch CSS were designed *as* faithful copies of 2ch's appearance, but minor numeric details may differ from the live 1999–2003 site.
- "MS PGothic" is a Microsoft proprietary font and cannot be redistributed; for a public modern reconstruction, use **IPAMonaPGothic** or the **submona** web‑font subset, which is purpose‑built to render Shift_JIS AA correctly at small file size.
- The Futaba/Yotsuba palette quoted is the one shipped in Wakaba/Kareha c. 2005–2010; the original Futaba Channel CSS in 2001 was slightly cruder (more inline `bgcolor="#F0E0D6"` attributes on `<td>` cells, fewer CSS classes), but the colors are the same.
- "Greentext" as a Western convention is sometimes attributed to early 4chan; it actually originates in the Futaba script's quote‑line handling (lines beginning with `>`), and is therefore present in *imageboard* lineage software (Futaba/Wakaba) more than in 2ch text mode, where quoting is done with `>>n` backrefs instead.
- Some sources (e.g. the "textboards.json" thread on 4‑ch's /iaa/) argue, with merit, that the strong Western distinction between "textboard" and "forum" is a retrospective Shii‑era construction — visually, Japanese textboards from 1996–2003 looked very much like contemporary Japanese guestbook/BBS scripts (YY‑BBS, KENT‑WEB scripts), which is itself useful context for anyone trying to faithfully recreate the period: the look you want is not a specially designed UI, it is a *generic late‑90s Japanese CGI guestbook* with thread bumping bolted on.