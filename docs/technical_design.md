# Technical Design & Methodology

How does market data become musical structure? This document traces the full
pipeline and justifies each mapping. The guiding rule throughout:

> **Every note must be explainable.** No randomness is used as a shortcut for
> creativity. Where variety is needed it comes from the *data*, not a random
> number generator, so the same market window always yields the same sonata.

---

## 1. Pipeline overview

```
 Yahoo Finance ──▶ market_data.py ──▶ data_to_music.py ──▶ composition.py ──▶ midi_generator.py
   (OHLCV)          clean series        MarketFeatures        Score               .mid file
                                        + PhraseFeatures     (Note events)         + analyst note
```

Four layers, each with one job — analysis, composition, notation, narration —
mirroring how a human composer moves from *understanding* a subject to *scoring*
it.

## 2. From prices to features (`data_to_music.py`)

The most important early decision: **we do not map one day to one note.** A
sonata is built from *phrases*, not samples. The timeline is segmented into
`n_phrases` (default 12) roughly equal chunks. Each chunk becomes one musical
phrase with its own character.

For the **whole piece** we compute:

| Feature | Definition | Musical role |
|---|---|---|
| `trend` | blend of total return and up-day ratio, squashed to [-1, 1] | chooses **key & mode** |
| `avg_volatility` | std. of daily returns → [0, 1] | sets **tempo** and baseline tension |
| `avg_volume` | mean volume vs. its own max | sets overall **dynamic level** |
| `total_return`, `max_drawdown` | raw performance stats | narrative arc, analyst note |

For **each phrase** we compute a `PhraseFeatures`:

| Feature | Meaning | Musical role |
|---|---|---|
| `contour` | normalised shape of price in the phrase, 8 points | the raw **melodic gesture** |
| `momentum` | net change across the phrase | motif **transposition / inversion** |
| `volatility` | local return std vs. the whole piece | **rhythmic density, chord colour, leap size** |
| `volume` | local participation | **velocity (loudness), bass density** |
| `brightness` | local drift biased by global trend | keeps a consistent emotional home key |

All values are normalised with `tanh`/min-max so extreme days never break the
range — the music stays musical.

## 3. From features to a score (`composition.py`)

### 3.1 Key and mode — *Market trend → Harmony*

- `trend > 0.15` → **major** (consonant, hopeful)
- `trend < -0.15` → **minor** (darker, emotional)
- otherwise → **Dorian** (a minor mode with a raised 6th — *ambiguous*, neither
  happy nor sad, right for a directionless market)

The **tonic pitch** is derived deterministically from a hash of the ticker, so
every asset has its own recognisable "home" note — an authorial signature that
makes AAPL and TSLA feel like different works.

### 3.2 Tempo — *Volatility → Pace*

`tempo = 60 + 48 · avg_volatility` BPM. Calm markets breathe at a meditative
~60 BPM; turbulent markets push toward an agitated ~108 BPM.

### 3.3 The motif and its development — *Price movement → Melody*

A single **four-note motif** is derived from the contour of the *first* phrase —
the DNA of the piece. It is then **developed**, never replaced:

- **Falling momentum → inversion** (the contour is flipped upside-down).
- **Strong momentum → transposition** up or down the scale.
- **High volatility → interval widening** (bigger leaps = more tension).

Because later phrases transform the *same* cell, the ear can follow one idea
through the whole work — the difference between *composition* and *noise*.

### 3.4 Harmony and dissonance — *Volatility → Tension*

Each phrase sits on a chord drawn from a functional progression chosen by mode:

- Major: **I – V – vi – IV** (the archetypal uplifting loop)
- Minor: **i – VI – III – VII** (the "epic minor" of film scoring)
- Dorian: **i – IV – i – V** (Dorian's characteristic bright IV)

Volatility then colours the chord:

- calm → plain **triad**
- restless → add the **7th** (warm, Richter-esque)
- turbulent → add the **9th**, tightening toward **cluster tension**

### 3.5 Rhythm — *Volatility → Activity*

Calm phrases use 2–3 long, sustained notes that ring out. Turbulent phrases
subdivide into up to 8 shorter events — faster rhythmic activity, exactly as the
mapping specifies.

### 3.6 The left hand — *Volume → Texture*

A minimalist **broken-chord ostinato** (Glass-like) carries the pulse. Its
density (2–8 notes per phrase) rises with **volume** and volatility: higher
participation literally adds more notes/layers to the texture.

### 3.7 Dynamics — *Volume → Loudness*

MIDI velocity = `40 + 72 · volume`, clamped to a musical 20–120 so quiet
passages stay audible and loud ones never turn harsh.

### 3.8 Form — the emotional structure

Over the phrases we impose an **A – B – A′ arch**:

- **A (exposition):** state the theme plainly.
- **B (development):** depart from it as the market's middle unfolds; tension is
  highest here, and the deepest drawdown is felt as the emotional low point.
- **A′ (recapitulation):** return home, transformed by everything in between.

A final **tonic cadence** across three registers lets the piece land — every
sonata needs to end, not just stop.

## 4. Notation (`midi_generator.py`)

`pretty_midi` writes three piano tracks (melody / harmony / bass) so the work
can be performed, opened in a DAW, or engraved as sheet music. Times are stored
in beats internally and converted to seconds at render time, so tempo changes
never desync the voices.

## 5. The analyst (`backend/analyst.py`)

The analyst extracts only **true facts** from the finished score and the
features, then narrates them. Optionally, if an `ANTHROPIC_API_KEY` is present,
Claude polishes the prose under a strict "use only these facts" system prompt.
Separating *facts* from *prose* is what makes it an analyst and not a chatbot:
every claim is verifiably true of the actual composition.

## 6. Determinism & reproducibility

No `random` calls influence pitches, rhythms or dynamics. Given the same market
window, Market Sonata returns byte-identical MIDI — essential for a work meant
to be studied, performed and defended.
