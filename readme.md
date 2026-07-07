<div align="center">

# 🎹 Market Sonata

### *A generative music system translating financial markets into musical narratives.*

Choose a financial asset. Hear the shape of its story told as an original modern
piano composition — in the idiom of **Joe Hisaishi · Philip Glass · Max Richter**.

*Music composition · Generative systems · Data visualization · AI-assisted creativity*

</div>

---

## ✦ What this is

Market Sonata is not a stock-to-MIDI converter. It is a **musical instrument
whose material is the market.** It treats a price history as a *libretto* — a
source of dramatic structure — and composes an intentional piano sonata from it,
with motifs, development, harmony and an A–B–A′ emotional arch.

A market and a piece of music are both **time-series of human emotion.** Market
Sonata is a translation instrument between the two:

| The market does… | …the music does |
|---|---|
| Price rises / falls | Melody ascends / descends |
| Volatility increases | Dissonance, wider leaps, faster rhythm |
| Trading volume swells | Louder dynamics, denser texture |
| Bull vs. bear trend | Major vs. minor (or ambiguous Dorian) |

Every note is **explainable and deterministic** — the same market window always
produces the same sonata, and an AI analyst can tell you *why* each choice was
made.

> Read the full artistic case in [`docs/artistic_statement.md`](docs/artistic_statement.md),
> the algorithm in [`docs/technical_design.md`](docs/technical_design.md), and the
> ideas about AI + creativity in [`docs/creative_philosophy.md`](docs/creative_philosophy.md).

---

## ✦ Features

- **Landing page** — the concept, framed as an instrument.
- **Market selection** — pick a symbol (AAPL, TSLA, SPY, NVDA, BTC-USD…) and a
  date range.
- **Market portrait** — interactive price, volatility and volume charts (Plotly).
- **Compose Sonata** — one click runs the full pipeline and returns a real
  composition.
- **Music player** — in-browser piano playback (Tone.js) with an animated
  **piano-roll** synced to a playhead, plus **MIDI download**.
- **The Analyst's Note** — an AI music analyst explains the composition,
  grounded in the actual score (optionally polished by Claude).

---

## ✦ Architecture

```
Market_Sonata/
├── README.md
├── demo.py                     # run the whole engine from the CLI, no server
│
├── music_engine/               # ← the artistic core (pure, testable)
│   ├── data_to_music.py        #   ANALYSIS:   market → MarketFeatures
│   ├── composition.py          #   COMPOSITION: features → Score (motif, form…)
│   └── midi_generator.py       #   NOTATION:    Score → .mid (pretty_midi)
│
├── backend/                    # ← FastAPI server
│   ├── main.py                 #   /api/market, /api/compose
│   ├── market_data.py          #   Yahoo Finance (yfinance) + synthetic fallback
│   ├── analyst.py              #   grounded AI program-note writer
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                   # ← React + TypeScript + Tailwind + Vite
│   └── src/
│       ├── App.tsx
│       ├── player.ts           #   Tone.js playback engine
│       ├── plotly.ts           #   lightweight Plotly binding
│       └── components/         #   Landing, MarketSelector, MarketCharts,
│                               #   MusicPlayer (piano roll), AnalystExplanation
│
└── docs/
    ├── artistic_statement.md
    ├── technical_design.md
    └── creative_philosophy.md
```

The pipeline:

```
Yahoo Finance → market_data → data_to_music → composition → midi_generator → MIDI + analyst note
   (OHLCV)       clean series   MarketFeatures    Score        .mid file
```

---

## ✦ Quick start

### Prerequisites
- **Python 3.10+**
- **Node 18+**

### 1 · Backend

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate      macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
python main.py            # serves http://localhost:8000  (docs at /docs)
```

*(Optional)* enable the LLM-polished analyst:

```bash
cp .env.example .env      # then paste your ANTHROPIC_API_KEY
```
Without a key, the analyst still works using grounded rule-based narration.

### 2 · Frontend

```bash
cd frontend
npm install
npm run dev               # http://localhost:5173  (proxies /api → :8000)
```

Open **http://localhost:5173**, enter the studio, pick a symbol, and press
**Compose Sonata**.

### 3 · Or skip the UI entirely

```bash
python demo.py AAPL 2024-01-01 2024-12-31
# → writes output/AAPL_sonata.mid and prints the analyst's program note
```

> **No internet / bad symbol?** `market_data.py` falls back to a deterministic
> **synthetic** series (clearly labelled in the UI) so the app always
> demonstrates end-to-end — handy when showing it live.

---

## ✦ How the music is made (in one breath)

1. The timeline is split into **phrases**, not per-day notes — so the music can
   breathe, repeat and develop.
2. **Trend** picks the **key/mode**; **volatility** sets **tempo, rhythmic
   density and dissonance**; **volume** sets **dynamics and left-hand density**;
   the ticker itself picks the **home pitch** (an authorial signature).
3. A **four-note motif** from the first phrase is **developed** — transposed,
   inverted, fragmented — across an **A–B–A′ form** and resolved with a final
   cadence.
4. `pretty_midi` renders three piano voices (melody / harmony / bass).
5. The **analyst** narrates only facts that are true of the finished score.

Full justification for every mapping is in
[`docs/technical_design.md`](docs/technical_design.md).

---

## ✦ Tech stack

| Layer | Tools |
|---|---|
| Frontend | React, TypeScript, Tailwind CSS, Vite, Plotly, Tone.js |
| Backend | Python, FastAPI, Uvicorn, Pydantic |
| Music | pretty_midi, music21, NumPy |
| Data | Yahoo Finance (`yfinance`) + deterministic synthetic fallback |
| AI | Anthropic Claude (optional, for analyst prose) |

---

## ✦ API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | liveness |
| `GET` | `/api/market?symbol=&start=&end=` | price / volume / volatility series |
| `POST` | `/api/compose` | full pipeline → notes + MIDI (base64) + analyst note |

Interactive docs at **http://localhost:8000/docs**.

---

## ✦ Design principles

- **Composition, not conversion.** Motifs, form and development — never random
  MIDI.
- **Determinism.** Same market → same sonata, so it can be studied and
  performed.
- **Explainability.** Every note traces back to a market feature; the AI narrates
  only what is real.
- **Intimacy.** Solo piano keeps a vast, faceless system in a single human voice.

---

<div align="center">

*Created as a portfolio work for graduate study in music technology.*

**Market Sonata** — *to hear a market is to be reminded that behind the data are people.*

</div>
