<div align="center">

# 🎹 Market Sonata

### *A generative music system translating financial markets into musical narratives.*

Choose a financial asset. Hear the shape of its story told as an original
composition — full song form, full band, every note traceable to the data.

*Music composition · Generative systems · Data visualization · AI-assisted creativity*

</div>

---

## ✦ What this is

Market Sonata is not a stock-to-MIDI converter. It is a **musical instrument
whose material is the market.** It treats a price history as a *libretto* — a
source of dramatic structure — and composes an intentional piece from it, with
motifs, development, harmony, and a real song form.

A market and a piece of music are both **time-series of human emotion.** Market
Sonata is a translation instrument between the two:

| The market does… | …the music does |
|---|---|
| Price rises / falls | Melody ascends / descends |
| Volatility increases | Dissonance, wider leaps, denser rhythm, harder drums |
| Trading volume swells | Louder dynamics, fuller texture |
| Bull vs. bear trend | Bright modes vs. dark modes |
| The **ticker symbol** | Key, groove, hook rhythm, bass figure, kit, swing |

Every note is **explainable and deterministic** — the same market window always
produces the same piece, and the analyst can tell you *why* each choice was made.

> The full artistic case is in [`docs/artistic_statement.md`](docs/artistic_statement.md),
> the algorithm in [`docs/technical_design.md`](docs/technical_design.md), and the
> ideas about AI + creativity in [`docs/creative_philosophy.md`](docs/creative_philosophy.md).
> Those documents describe the original solo-piano engine — see
> [Two engines](#-two-engines) for how the shipped version has moved on.

---

## ✦ Features

- **Market selection** — pick a symbol (AAPL, TSLA, SPY, NVDA, BTC-USD…) and a
  date range, or arrive on a **shareable permalink** that restores all of it.
- **Market portrait** — interactive price, volatility and volume charts (Plotly),
  with hover values and drag/scroll zoom.
- **Compose Sonata** — one click runs the full pipeline and returns a real
  composition in song form.
- **Music player** — in-browser playback of the whole band (Tone.js) with an
  animated **piano roll**, section bands and a drum lane.
- **Draggable scrub bar** — drag the bar *or* the piano roll itself to move
  through the piece, playing or stopped, with a running clock. Arrow keys nudge,
  `Home`/`End` jump, **space** plays and stops.
- **Voice mixer** — mute and unmute lead / pad / bass / arpeggio / drums live,
  mid-playback. Muted voices recede in the piano roll instead of disappearing.
- **Light and dark themes** — Auto (follows the OS), Light or Dark. The choice
  is resolved before first paint, persists, and re-skins the charts and the
  canvas piano roll, not just the page chrome.
- **Master volume**, remembered between visits.
- **Export** — **MIDI** (always the complete score) and **WAV** (an offline
  render of exactly what you are hearing, mixer settings included).
- **The Analyst's Note** — a music analyst explains the composition, grounded in
  the actual score, including which decisions came from the market and which
  came from the ticker.
- **Live mode** — optional 60-second auto-refresh that recomposes when the last
  close changes, and never interrupts playback mid-piece.

---

## ✦ Why two tickers don't sound the same

The obvious failure mode for a system like this is that **every symbol comes out
sounding identical**, because most price charts have broadly the same statistics.
Earlier versions had exactly that problem: on an identical market, eleven
different tickers produced **one single rhythm** between them.

Two things fixed it.

**1 · The ticker is hashed into a musical fingerprint.** The symbol runs through
FNV-1a (a char-code *sum* used to collide for anagrams like `AAPL`/`LAPA` and
neighbours like `AAPL`/`AAPM`) and seeds a deterministic RNG that fixes:

| Fingerprint | Choices |
|---|---|
| Home key + register | 12 pitch classes × octaves 3–5 |
| Mode within the family | 4 per family (see below) |
| Chord progression | 3 sets per family |
| Chorus hook rhythm | 8 two-bar rhythmic cells |
| Verse groove | 8 one-bar cells |
| Bass figure | walking · pumping · pushed |
| Drum kit pattern | backbeat · four-on-the-floor · broken |
| Arpeggio pattern | 5 shapes |
| Swing | 0–13% eighth-note lilt |
| Melodic reach | 3–6 scale degrees |
| Tempo | ±6 BPM of personal pulse |

None of it depends on the market, so it is a genuine authorial signature.

**2 · The market re-densifies the ticker's groove.** Rhythm is no longer a run of
equal-length notes. The fingerprint supplies a rhythmic *cell*; volatility then
splits its longest notes or merges its shortest. The ticker sets the character,
the market sets the density, and neither erases the other.

Measured on an identical synthetic market across 11 tickers:

| | distinct melodies | distinct rhythms | distinct modes |
|---|---|---|---|
| Before | 8 / 11 (same tune, transposed) | **1 / 11** | 1 |
| After | **11 / 11** | **11 / 11** | 3 |

Determinism is preserved: the same symbol and window always produce the same
piece, note for note.

---

## ✦ How the music is made

1. The timeline is split into **phrases**, not per-day notes — so the music can
   breathe, repeat and develop.
2. **Trend** picks a modal *family* — bright (major / Lydian / Mixolydian), dark
   (minor / Phrygian / Dorian) or modal — and the **ticker** picks the shade
   inside it. **Volatility** sets tempo, rhythmic density and chord colour
   (triads → 7ths); **volume** sets dynamics and texture.
3. A **four-note motif** from the first phrase is **developed** — transposed,
   inverted, widened — across a fixed, singable **song form**:

   ```
   Intro · Verse 1 · Chorus · Verse 2 · Bridge · Chorus · Outro
     4        8         8        8        4        8        4     bars
   ```

   The verses walk the market chronologically. The **chorus hook is distilled
   from the most energetic stretch of the window**, so the market's loudest
   moment becomes the part you remember. The final chorus lifts an octave; the
   outro brings the opening motif home.
4. Five voices are arranged — **lead, pad, bass, arpeggio** and a
   **kick/snare/hat kit** whose intensity tracks volatility: silent in the intro,
   light in the verses, full in the chorus, with a fill into every section.
5. The score is written to a **type-1 Standard MIDI File** (one track per voice,
   GM drums on channel 10) and rendered to audio by a Tone.js band.
6. The **analyst** narrates only facts that are true of the finished score.

---

## ✦ Market data — and why the numbers now match Yahoo

`backend/market_data.py` had three separate defects that each made the displayed
prices disagree with finance.yahoo.com. All three are fixed:

1. **The pinned `yfinance==0.2.44` was dead.** Every call raised
   `JSONDecodeError` against current Yahoo, and a bare `except Exception`
   silently substituted the synthetic series — so the app was showing invented
   prices while looking like it was live. The **primary path is now Yahoo's
   public chart endpoint called with nothing but the standard library**, which
   removes the fragile dependency from the critical path entirely.
2. **`auto_adjust=True` returned back-adjusted closes.** Those are corrected for
   dividends and splits, so every historical bar of a dividend payer sat *below*
   the `Close` column on the website — about 0.9% for AAPL two years back, and
   growing the further back you look. We now read the **unadjusted close**.
3. **The end date was exclusive**, silently dropping the most recent bar — the
   one a user is most likely to be checking. `end` is now **inclusive**.

The resolution order is **Yahoo chart endpoint → yfinance → synthetic**, and the
response carries `source`, `note` and `currency` so the UI can state exactly what
it is showing. A synthetic fallback is always labelled as such, and the note
explains why the live fetch failed.

> `yfinance` is now only a secondary fallback and its import is optional. It
> requires Python ≥ 3.10, which is what `render.yaml` provisions; on an older
> local interpreter the primary path works regardless.

---

## ✦ Two engines

The repository contains two implementations of the composer, and it is worth
being explicit about which one you are hearing:

| | `standalone.html` (JS) | `music_engine/` (Python) |
|---|---|---|
| **This is what is deployed** | ✅ served at `/` | used by `demo.py` and `/api/compose` |
| Form | Intro–Verse–Chorus–Verse–Bridge–Chorus–Outro | A – B – A′ arch |
| Voices | lead, pad, bass, arpeggio, drum kit | melody, harmony, bass (solo piano) |
| Modes | 6, in three families | 3 |
| Ticker fingerprint | full (key, groove, hook, bass, kit, swing) | key only |

The Python engine is the original solo-piano conception described in `docs/`.
The JavaScript engine in `standalone.html` is the one that ships; it is
self-contained between the `/*ENGINE-START*/` and `/*ENGINE-END*/` markers, has
no DOM dependencies, and exports itself via `module.exports`, so it can be
imported and tested from Node.

---

## ✦ Architecture

```
Market_Sonata/
├── standalone.html             # ← THE DEPLOYED APP: engine + UI in one file
├── render.yaml                 #   Render web-service definition
├── demo.py                     #   run the Python engine from the CLI, no server
│
├── backend/                    # ← FastAPI server
│   ├── main.py                 #   serves standalone.html at /, plus the API
│   ├── market_data.py          #   Yahoo chart endpoint → yfinance → synthetic
│   ├── analyst.py              #   grounded AI program-note writer
│   └── requirements.txt
│
├── music_engine/               # ← the original Python engine (CLI + /api/compose)
│   ├── data_to_music.py        #   ANALYSIS:    market → MarketFeatures
│   ├── composition.py          #   COMPOSITION: features → Score
│   └── midi_generator.py       #   NOTATION:    Score → .mid (pretty_midi)
│
├── frontend/                   # ← React/Vite client (not used by the deployment)
└── docs/
```

The pipeline:

```
Yahoo Finance → market_data → features → fingerprint + composition → MIDI/WAV + analyst note
   (close, volume)   clean series   phrases      song form, 5 voices
```

---

## ✦ Quick start

### Prerequisites
- **Python 3.10+** (3.9 works; you just won't get the `yfinance` fallback)

### Run it

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate      macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
python main.py            # serves http://localhost:8000  (docs at /docs)
```

Open **http://localhost:8000** — the app composes something immediately.

> This used to fail with `Attribute "app" not found in module "main"`.
> `backend/main.py` put the repository root at the *front* of `sys.path` so it
> could import `music_engine`, which let the repo-root `main.py` shadow it. The
> root is now appended instead of inserted, so both imports resolve correctly.

*(Optional)* enable the LLM-polished analyst:

```bash
cp .env.example .env      # then paste your ANTHROPIC_API_KEY
```

Without a key the analyst still works, using grounded rule-based narration.

### Or skip the server entirely

`standalone.html` runs from the filesystem. Open it directly and it will look
for a backend on `localhost:8000`; if there is none it falls back to a
deterministic synthetic market, clearly labelled, so the demo always works.

### Or drive the Python engine from the CLI

```bash
python demo.py AAPL 2024-01-01 2024-12-31
# → writes output/AAPL_sonata.mid and prints the analyst's program note
```

---

## ✦ Deployment

Deployed on **Render** as a single Python web service (`render.yaml`): FastAPI
serves the API *and* returns `standalone.html` at `/`, so there is no separate
frontend build or static host to keep in sync.

```yaml
buildCommand: pip install -r backend/requirements.txt
startCommand: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
healthCheckPath: /api/health
```

Set `ANTHROPIC_API_KEY` in the Render dashboard to enable the LLM analyst.

---

## ✦ API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | the app (`standalone.html`) |
| `GET` | `/api/health` | liveness |
| `GET` | `/api/market?symbol=&start=&end=` | close / volume / volatility, plus `source`, `note`, `currency` |
| `POST` | `/api/compose` | Python-engine pipeline → notes + MIDI (base64) + analyst note |

Both dates are **inclusive**. Interactive docs at `/docs`.

---

## ✦ Testing the engine without a browser

The JS engine is deliberately DOM-free, so it can be exercised in Node:

```js
const fs = require("fs");
const src = fs.readFileSync("standalone.html", "utf8")
  .split("/*ENGINE-START*/")[1].split("/*ENGINE-END*/")[0];
const m = { exports: {} };
new Function("module", "exports", src)(m, m.exports);

const { syntheticSeries, extractFeatures, composer } = m.exports;
const score = composer(extractFeatures(syntheticSeries("AAPL", "2024-01-01"), 12)).compose();
console.log(score.keyName, score.mode, Math.round(score.tempo), score.signature);
```

This is how the variety and determinism figures above were measured.

---

## ✦ Design principles

- **Composition, not conversion.** Motifs, form and development — never random
  MIDI.
- **Determinism.** Same market + same ticker → same piece, so it can be studied
  and performed.
- **Explainability.** Every note traces back to either a market feature or the
  ticker's fingerprint, and the analyst narrates only what is real.
- **Honesty about data.** Synthetic fallbacks are always labelled, with the
  reason attached. The app never passes invented prices off as the market.

---

<div align="center">

*Created as a portfolio work for graduate study in music technology.*

**Market Sonata** — *to hear a market is to be reminded that behind the data are people.*

</div>
