# charmoji

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-d97757)](https://claude.com/claude-code)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![Deps: Pillow only](https://img.shields.io/badge/Deps-Pillow%20only-2ea44f)](https://python-pillow.org/)
[![Static + animated](https://img.shields.io/badge/static+%20animated-supported-2ea44f)](references/animated.md)
[![Spec synced](https://img.shields.io/badge/Spec%20synced-2026--08--27-orange)](https://sticker.weixin.qq.com/cgi-bin/mmemoticon-bin/readtemplate?t=guide/index.html#/makingSpecifications)
[![Stars](https://img.shields.io/github/stars/webkubor/charmoji?style=flat&color=yellow)](https://github.com/webkubor/charmoji/stargazers)
[![Promo video: reel-kit](https://img.shields.io/badge/promo%20video-reel--kit-8b5cf6)](https://github.com/webkubor/reel-kit)
[![Version](https://img.shields.io/badge/version-1.3.0-blue)](CHANGELOG.md)

**One frontal IP photo → a complete WeChat sticker submission set ready to upload.**

[中文](./README.md)

**`charmoji` is an installable Claude Code skill** — the `name` in `SKILL.md` frontmatter is
`charmoji`, same as the repo name. Clone it into `~/.claude/skills/` and Claude Code picks it up;
say "help me make a set of WeChat stickers" to trigger. Commands and deps: see [Install](#install).

The name is `char` (character IP) + `moji` (what it says for you): stickers speak for the character — [source](CHANGELOG.md).

WeChat sticker open platform's submission bar isn't about art — it's about specs: 240×240 sticker images, 750×400 banner, transparent-background cover and icon, ≤4-char meaning words with no duplicates …

And the platform **does NOT reject or error on out-of-spec assets — it silently compresses and crops** — by the time you spot your subject got cropped off, the work is lost.

This is a [Claude Code](https://claude.com/claude-code) skill: character management, generation, cropping, machine-check, copy validation, and submission checklist — all scripted, no art background needed. After upload, one command stitches the whole set into a 1080×1920 vertical promo video for Moments / Video Account — compositing delegated to [reel-kit](https://github.com/webkubor/reel-kit). This skill only reads `album.yml` and assembles parameters; it doesn't rebuild video output or layout.

**The specs and rejection reasons are field-measured, not copied from docs**: official spec text archived in full, real post-login URLs and submission form fields recorded field-by-field, plus a real rejection note (writing "WeChat" in the artwork gets it classified as promoting an app you don't own the rights to) — none of that lives in the official docs.

## Demo outputs

A real full run — only one frontal photo as input, one command outputs stickers + cover + icon + banner, machine-check FAIL 0:

![8 stickers](https://img.webkubor.online/skills/wechat-sticker-demo-stickers.jpg)

Filenames carry the meaning word (`01-happy.png`, `02-wronged.png` …) — the number is the upload order, no need to cross-reference a mapping table.

![Cover, chat icon, detail-page banner](https://img.webkubor.online/skills/wechat-sticker-demo-assets.jpg)

The three pieces have contradictory requirements, so the pipeline splits them: cover uses frontal half-body + transparent background; icon uses head close-up + transparent background; banner must be opaque, with a scene, and no text in-frame.

### Photo-style sticker → transparent sticker

An opaque white-background photo posted to WeChat is just a white square; in dark mode the edges look harsh. After cutout + redrawing text:

![Before/after photo → sticker](https://img.webkubor.online/skills/wechat-sticker-demo-restyle.jpg)

The key is **order: erase text first, then cutout**. The other way around, text sitting on top of the subject stays with the subject, layered over the redrawn text — cutout is binary "subject / background", and text's home depends on what's underneath, which is uncontrollable.

### Promo video (1080×1920 vertical)

One command stitches the whole sticker set into a vertical video for Moments / Video Account, layout aligned with the official SuiJian templates:

```bash
scripts/make_promo.py <series-dir>                    # BGM defaults to "儿童轻快"
scripts/make_promo.py <series-dir> --sec 1.8          # shorten per-sticker dwell when count is high
scripts/make_promo.py <series-dir> --voice narrator   # add voice, shot length driven by voice
```

The copy source of truth is the `captions` block in `album.yml` — write "when to send this one", not repeat the artwork text; it's more shareable. BGM goes through the manifest alias (`reel bgm` lists them); license prints at render time.

Video rendering lives in **[reel-kit](https://github.com/webkubor/reel-kit) (`reel` command)**; this script only reads `album.yml` and assembles parameters. To change a layout, edit `templates/*.html` in reel-kit — drop in an HTML and you have a new layout, no code changes.

> Prerequisite: `cd ~/dev/github/devtool/reel-kit && pnpm install && npm link` (needs ffmpeg + Chrome)
>
> **`museav slideshow` is gone.** It briefly lived in museav-cli on 2026-08-28, until we realized reel-kit already does the same thing better (HTML/CSS layout handles line wrap, voice-driven shot length, free local TTS), so it was consolidated.

### Animated stickers (transparent GIF)

240×240 / 20 frames / ≤465 KB / looping, no white edge on light or dark backgrounds:

![GIF keyframes](https://img.webkubor.online/skills/wechat-sticker-demo-gif.jpg)

GIF only supports 1-bit transparency (each pixel is fully transparent or fully opaque); semi-transparent pixels must be binarized. Approach: threshold 128 + 1px subject erosion, idea from [hackerb9/mktrans](https://github.com/hackerb9/mktrans). **Don't follow the Photoshop tutorial's "set matte color to white"** — clean on light mode, but every sticker gets a white border on dark mode. See [`references/animated.md`](references/animated.md).

## What it saves you from

| Pitfall you'll hit | How the skill catches it |
|---|---|
| Out-of-spec assets get silently cropped | Crop pipeline normalizes to spec dimensions + caps file size |
| Cover / icon forgotten to be transparent | Machine-check FAILs cover/icon, WARNs stickers, reverses for banner |
| "Transparent corners" mistaken for cutout | The few-pixel transparent border from cropping fools corner detection → instead check whether the subject's bounding box is a "solid rectangle" |
| Subject has a white halo | Compare outline-vs-subject-interior brightness — white cats won't get false-positive flagged |
| Whole set too similar (the #1 rejection) | After cropping to subject, compute dHash pairwise; too similar → FAIL |
| Different albums sharing a cover / icon | Cross-album dHash comparison (explicitly forbidden by the platform) |
| Stage directions used as meaning words ("555… I'm fine") | Validate ≤4 chars, no punctuation, no duplicates within a set, one-to-one with sticker count |
| Icon cropped square, hard corners | Auto-crop frontal head with 12% padding |
| Vertical-composition assets cropped off-center by middle | `--anchor top/center/bottom`; tip-jar image MUST be top (bottom half overlays amount UI) |
| Occasional generation failure causing short count | Per-image retry; upstream rate-limit detection + 3-tier backoff; rerun fills only the missing ones |
| Multiple IPs in progress, profile/avatar gets mixed | IP library hierarchical; duplicate character names, same avatar across characters all get rejected |
| Wrong character attached to a work | `ip_name` in `album.yml` not matching `--ip` is blocked outright (only 1 chance to change attribution) |
| Master character file only on local disk, lose it = lose collection | `ip.py sync` pushes to private repo with versioning; clone on a new machine restores |
| **Writing "WeChat" in the artwork** | Machine-check can't catch this — only human eyes can; logged into the redline list |

## Install

```bash
git clone https://github.com/webkubor/charmoji.git \
  ~/.claude/skills/charmoji
```

After install, say "help me make a set of WeChat stickers" in Claude Code to trigger; can also be used purely as a CLI tool.

> ⚠️ Must clone into a **real directory** under `~/.claude/skills/`. Claude Code **does not follow symlinks for skill loading** — putting the real directory elsewhere and symlinking here makes the skill disappear.

## Data model: one character, many sets

WeChat's side has two independent configs, and it's one-to-many:

```
Sticker character (unique)        Sticker series / album (multiple sets)
Name · Bio · Avatar · Icon   ──┬── Series A: 8~24 stickers + cover + banner + meaning words
                              ├── Series B: another set, reusing the same character
                              └── Series C: …
```

Local layout mirrors this, **with version-control decided by "can it be regenerated"**:

```
~/.wechat-stickers/                        ← data root (private git repo)
├── ips/<character>/                       irretrievable → versioned
│   ├── ip.yml · ip.png · ip-reverse.txt
│   ├── 形象头像-<name>.png · 形象图标-<name>.png
│   └── source/                            original art pool, multiple sets pick from here
├── albums/<character>/<NN-series-name>/  output, regenerable → gitignored
│   ├── 表情图/ · 封面 · 图标 · 横幅
│   └── album.yml · submit.md · raw/
└── outbox/                                pending upload staging → gitignored
```

Backing up only outputs would lose the truly precious things (originals you can't redraw).
`STICKER_HOME` / `STICKER_ALBUMS` can override locations.

## IP library

```bash
S=~/.claude/skills/charmoji/scripts

python3 $S/ip.py add Tuanzi frontal-photo.png --desc "Bio, ≤80 chars" --source art-pool/
python3 $S/ip.py list                    # all characters + series + completion progress
python3 $S/ip.py show Tuanzi             # item-by-item check + todos + attached series
python3 $S/ip.py page                    # generate HTML progress dashboard and open
python3 $S/ip.py rename Tuanzi Tuantuan  # rename (syncs dir/filenames/album.yml)
python3 $S/ip.py update Tuanzi --photo new-frontal.png   # swap master and redo avatar/icon
python3 $S/ip.py sync                   # back up to private repo (auto-init on first run)
```

`show` checks each item against the official "character" requirements, explaining why anything is non-compliant:

```console
🎭 Mei-jiu    completion 4/7
  ✅ Character name          Mei-jiu (2 chars)
  ✅ Bio                     40 chars
  ✅ Master frontal photo    351×460
  ✅ Image-reading prompt    generated, reused across sets
  ✅ Original art pool       source/ 33 originals (irretrievable, follows git)
  ⚠️  Character avatar 240×240   subject is solid rectangle → just scaled-on photo, no contour cut
  ⚠️  Character icon 50×50       subject is solid rectangle → just scaled-on photo, no contour cut
```

Three official cross-character constraints auto-enforced: **character names must be unique**, **different characters must not share the same avatar** (dHash comparison), **one work set can only attach to one character and you only get 1 chance to change attribution**.

## Create a series

```bash
$S/new_album.sh --ip Tuanzi --series daily      # → albums/Tuanzi/01-daily/
$S/new_album.sh --ip Tuanzi --series office     # → albums/Tuanzi/02-office (auto-incremented)
```

Idempotent. If it stalls, fix what's flagged and rerun the same command:

1. First run → generates `album.yml` and stops for you to fill in copy (the only place you actually think)
2. Fill in, rerun → generate → crop → machine-check → generate `submit.md`
3. Machine-check FAIL → prints "how to fix this one"; fix and rerun

You can also use your own pre-drawn images — drop into `<series-dir>/raw/`, run without `--ip`, takes over from the cropping step.

## Machine-check output

Three-tier judgment — `FAIL` must fix, `WARN` human confirm, `OK` passes. Exit code = FAIL count:

```console
$ python3 scripts/check_assets.py <series-dir> --copy <series-dir>/album.yml
✅ 01-wronged.png: PNG 240×240 55KB
✅ 封面-Mei-jiu.png: PNG 240×240 67KB
✅ Detail-banner-Mei-jiu-daily.jpg: JPEG 750×400 37KB
✅ copy: all wording compliant (9 meaning words)

Ready to submit — FAIL 0 / WARN 0
```

When non-compliant, here's the exact wording (each one was triggered during real development):

```console
❌ Chat-icon-Mei-jiu.png: corners not transparent (66%) — white background or square border; official "must set transparent background"
❌ 06.png vs 08.png: artwork nearly identical (dHash distance 0/64) — too-similar is the highest-frequency rejection
❌ 01.png: subject outline 100% near-white, interior only 53% — white halo, must remove
❌ copy: 9 meaning words ≠ 8 stickers, must be one-to-one
⚠️  10-hungry.png: subject is solid rectangle — just scaled-on photo, no contour cut
```

**Machine-check can't catch what's written in the artwork** — one set was killed by this (the banner printed "WeChat sticker album" and got classified as promoting an app you don't own the rights to), and those images were all machine-check ✅. Externally-shown artwork needs a human eye pass too.

## Pitfall records

[`references/pitfalls.md`](references/pitfalls.md) has 15 entries, each with **symptom → root cause → fix**. The first four are general Chinese shell-script traps, not sticker-specific:

- Variable followed by fullwidth punctuation (`"concurrency $JOBS，"`) → the punctuation byte joins the variable name; `set -u` reports unbound variable
- `(( i++ ))` standalone under `set -e` returns 1 when `i=0` → script silently exits 0, loop doesn't run once, no error
- Two siblings: a single command in command substitution with non-zero exit, `grep` no match under `pipefail` — the latter **only blows up on the failure path**; normal flow can be tested a hundred times and miss it
- Don't parse CLI output by what your terminal shows (often goes to stderr); don't `2>/dev/null` to swallow the error text

Domain-specific: mean-hash fails on same-background-color image groups, white-halo detection flags white cats as violating, PIL mode `P` conversion drops alpha, `sharp` single-channel resize returns 3 channels causing misaligned sampling, the "edit-then-rerun" validation cadence doesn't work under upstream rate-limiting.

One of them became an executable gate — [`scripts/lint.sh`](scripts/lint.sh):

```console
$ ./scripts/lint.sh
✅ Variable and fullwidth punctuation boundaries
✅ Arithmetic increment idiom
✅ Concurrency wait compatibility
✅ Command substitution failure fallbacks
✅ grep pipes under pipefail
✅ External command error visibility
✅ All script syntax
Gate passed.
```

The reason for this gate is practical: I tripped the fullwidth-punctuation one again after writing the docs — **docs can't catch a repeat, checks can**.

## Dependencies

- **Machine-check / cropping / GIF compositing**: Python 3 + [Pillow](https://python-pillow.org/), no other deps, no ImageMagick needed
- **Image generation / cutout / text erase**: [museav](https://www.npmjs.com/package/museav-cli) CLI
  (`--ref` reference image, `--transparent` transparent output, `remove-bg` cutout defaults to BiRefNet, `remove-watermark` LaMa inpaint).
  You can skip it and supply your own images — the rest of the pipeline works without it.

## Directory

| File | Purpose |
|---|---|
| `SKILL.md` | Main flow (Claude Code reads this) |
| `scripts/ip.py` | **IP library**: register / completion progress / cross-character constraints / rename / HTML dashboard / backup |
| `scripts/new_album.sh` | **One-shot entry** (idempotent): copy → generate → crop → machine-check → submission checklist |
| `scripts/gen_album.sh` | One frontal photo → full original image set (with retry, rate-limit backoff, diff-set filling) |
| `scripts/restyle.py` | Photo-style sticker → transparent sticker (erase text first then cutout, unify redrawn text) |
| `scripts/make_gif.py` | Transparent PNG sequence → 240×240 transparent GIF, adaptive compression to 500KB |
| `scripts/make_promo.py` | Full sticker set → 1080×1920 vertical promo video (read `album.yml` → invoke `reel make`) |
| `scripts/fit_assets.py` | Source image → spec-compliant assets (cut white margin / trim padding / center / compress / `--anchor`) |
| `scripts/check_assets.py` | Asset + copy machine-check, exit code = FAIL count |
| `scripts/make_submit.py` | Generate `submit.md`: platform form fields → value/file mapping table |
| `scripts/page_tpl.py` | Progress dashboard styling and rendering |
| `scripts/lint.sh` | Script gate: turns pitfalls into runnable checks |
| `references/specs.md` | Official production specs in full (sticker / character / effects / artist / tip / paid) — numeric truth |
| `references/audit.md` | Official audit standards in full + **field rejection reasons** + top-frequency rejections |
| `references/platform.md` | **Platform map**: real URLs, login method, complete submission form fields, account prerequisites |
| `references/animated.md` | **Animated stickers**: 1-bit transparency constraints, four-step pipeline, IP fit assessment |
| `references/ip-design.md` | IP naming / bio / emotion topic selection / meaning word writing |
| `references/pitfalls.md` | 15 pitfall records (symptom → root cause → fix) |
| `templates/album.yml` | Copy template machine-check can parse |
| `CHANGELOG.md` | Version history |
| `examples/` | Real `submit.md` and `album.yml` outputs |

## Disclaimer

Spec content scraped from [WeChat Sticker Open Platform official docs](https://sticker.weixin.qq.com/cgi-bin/mmemoticon-bin/readtemplate?t=guide/index.html#/makingSpecifications) (2026-08-27); the platform declares it as dynamic docs. **If conflicting with current platform pages, the platform pages win.**
This project is not affiliated with Tencent, and does not guarantee approval — machine-check only catches spec issues; creative and rights issues are yours.

Submission material must be your original work or you must hold the rights. Use your own originals as reference images, don't reference others' work or well-known IPs.

## License

MIT