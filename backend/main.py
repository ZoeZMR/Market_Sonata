"""
main.py
=======

FastAPI server for Market Sonata.

Endpoints
---------
GET  /api/health                 -> liveness check
GET  /api/market                 -> fetch price/volume/volatility series
POST /api/compose                -> full pipeline: data -> features -> score
                                    -> MIDI (base64) + analyst program note
GET  /api/midi/{token}           -> download a previously composed MIDI file

The compose endpoint returns the MIDI inline (base64) so the frontend can both
play it (via a JS synth) and offer a download without a second round-trip.
"""

from __future__ import annotations

import base64
import sys
import os
from typing import List, Optional

# Make the sibling music_engine package importable when run from /backend.
# APPEND rather than insert(0): the repository root contains its own main.py,
# and putting the root first made `import main` resolve to that script instead
# of this module — which broke `python main.py` with "Attribute 'app' not found".
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load backend/.env if present, so ANTHROPIC_API_KEY set there (per the
# Quick start in README) actually reaches os.environ. On Render, the
# dashboard sets real env vars directly and there is no .env file — this is a
# no-op there, but without it locally the documented ".env" setup never did
# anything and the analyst silently stayed rule-based.
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from market_data import (fetch_market_data, search_symbols, fetch_screener,
                         fetch_trending, fetch_spark, fetch_universe,
                         SCREENERS, REGIONS, SECTORS)
from catalog import catalog as market_catalog
from analyst import analyze, analyze_facts, stream_program_note, NoteUnavailable

from music_engine.data_to_music import extract_features
from music_engine.composition import Composer
from music_engine.midi_generator import score_to_midi_bytes


app = FastAPI(
    title="Market Sonata API",
    description="Translating financial markets into musical narratives.",
    version="1.0.0",
)

# Allow the Vite dev server (and any local frontend) to call us.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ComposeRequest(BaseModel):
    symbol: str = Field(..., examples=["AAPL"])
    start: str = Field(..., examples=["2024-01-01"])
    end: str = Field(..., examples=["2024-12-31"])
    n_phrases: int = Field(12, ge=4, le=32)
    interval: str = Field("1d", examples=["1d", "1wk", "1h"])


class AnalystNoteRequest(BaseModel):
    # Deliberately untyped: the deployed JS engine (standalone.html) computes
    # its own grounded facts client-side, in its own shape. This endpoint's
    # only job is the optional Claude polish (see analyst.analyze_facts) —
    # it never invents facts, only rephrases the ones it is handed.
    facts: dict = Field(..., examples=[{"symbol": "AAPL"}])
    grounded: str = Field(..., description="The rule-based draft note.")


class AnalystNoteResponse(BaseModel):
    program_note: str
    used_llm: bool


class NoteOut(BaseModel):
    pitch: int
    start: float
    duration: float
    velocity: int
    voice: str


class ComposeResponse(BaseModel):
    symbol: str
    key: str
    mode: str
    tempo: float
    market: dict
    features: dict
    analysis: dict
    notes: List[NoteOut]        # for the in-browser player / piano roll
    midi_base64: str
    midi_source: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

_STANDALONE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "standalone.html",
)


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(_STANDALONE, media_type="text/html")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "market-sonata"}


@app.get("/api/market")
def market(
    symbol: str = Query(..., description="Ticker, e.g. AAPL"),
    start: str = Query(...),
    end: str = Query(...),
    interval: str = Query("1d", description="1d | 1wk | 1mo | 1h | 30m | 15m | 5m"),
):
    series = fetch_market_data(symbol, start, end, interval)
    if not series.close:
        raise HTTPException(404, "No market data for that symbol/range.")
    return series.to_dict()


@app.get("/api/catalog")
def catalog():
    """The market explorer's curated groups, plus the live screener ids."""
    return {
        "groups": market_catalog(),
        "screeners": [{"id": k, "label": v} for k, v in SCREENERS.items()],
    }


@app.get("/api/screener/{scr_id}")
def screener(scr_id: str, count: int = Query(50, ge=1, le=250)):
    """A live Yahoo screen: gainers, losers, most active, crypto, funds, ..."""
    if scr_id not in SCREENERS:
        raise HTTPException(404, "Unknown screener.")
    try:
        return fetch_screener(scr_id, count)
    except Exception as exc:                                  # noqa: BLE001
        raise HTTPException(502, f"Screener unavailable: {exc}")


@app.get("/api/universe")
def universe(
    region: str = Query("us"),
    sector: str = Query(""),
    type: str = Query("EQUITY", description="EQUITY | ETF"),
    sort: str = Query("size", description="size | percentchange | dayvolume | intradayprice"),
    order: str = Query("desc"),
    offset: int = Query(0, ge=0),
    size: int = Query(100, ge=1, le=250),
    main_only: bool = Query(False),
):
    """Every instrument Yahoo lists for a region, one sorted page at a time."""
    try:
        return fetch_universe(region, sector, type, sort, order != "asc",
                              offset, size, main_only)
    except Exception as exc:                                  # noqa: BLE001
        raise HTTPException(502, f"Universe screener unavailable: {exc}")


@app.get("/api/universe/meta")
def universe_meta():
    return {"regions": [{"code": k, "label": v} for k, v in REGIONS.items()],
            "sectors": SECTORS}


@app.get("/api/trending")
def trending(region: str = Query("US"), count: int = Query(25, ge=1, le=50)):
    try:
        return {"region": region.upper(), "symbols": fetch_trending(region, count)}
    except Exception:                                         # noqa: BLE001
        return {"region": region.upper(), "symbols": []}


@app.get("/api/spark")
def spark(
    symbols: str = Query(..., description="Comma-separated tickers (max 300)"),
    range: str = Query("1mo"),
    interval: str = Query("1d"),
):
    """Last price, change % and a mini close series for many symbols at once."""
    return {"quotes": fetch_spark(symbols.split(","), range, interval)}


@app.get("/api/search")
def search(q: str = Query(..., min_length=1, description="Company name or ticker fragment")):
    """
    Ticker discovery for the symbol box: resolves a free-text query to real
    tickers via Yahoo's search endpoint, so a user does not need to already
    know a symbol. `/api/market` and `/api/compose` already accept any ticker
    Yahoo resolves — this only makes those tickers findable.
    """
    try:
        return {"results": search_symbols(q)}
    except Exception:
        # Best-effort discovery aid; a failure here should never block typing
        # a symbol directly into the box.
        return {"results": []}


@app.post("/api/analyst-note", response_model=AnalystNoteResponse)
def analyst_note(req: AnalystNoteRequest):
    """
    Optional Claude polish for the deployed JS engine's analyst note.

    The frontend always has a grounded, rule-based note ready to show
    immediately; this endpoint tries to improve its prose with Claude and
    falls back to that same grounded text (used_llm=False) if no API key is
    configured or the call fails for any reason.
    """
    return AnalystNoteResponse(**analyze_facts(req.facts, req.grounded))


class ProgramNoteRequest(BaseModel):
    # Built by the frontend from the series and the finished score; see
    # buildDossier() in standalone.html.
    dossier: dict
    style: str = "concert"
    language: str = "en"
    request: str = ""


@app.post("/api/program-note")
def program_note(req: ProgramNoteRequest):
    """
    Stream an AI-written programme note (plain text / Markdown chunks).
    503 when no Anthropic credentials are configured, so the page can keep
    showing its grounded rule-based note instead.
    """
    try:
        gen = stream_program_note(req.dossier, req.style, req.language, req.request)
        first = next(gen)              # surface config/auth errors before streaming
    except NoteUnavailable as exc:
        raise HTTPException(503, str(exc))
    except StopIteration:
        first = ""
    except Exception as exc:                                  # noqa: BLE001
        print(f"[program-note] failed: {exc!r}")
        raise HTTPException(502, f"The analyst is unavailable right now ({type(exc).__name__}).")

    def body():
        yield first
        try:
            yield from gen
        except Exception as exc:                              # noqa: BLE001
            print(f"[program-note] stream broke: {exc!r}")
            yield "\n\n*(The note was cut short — try regenerating.)*"

    return StreamingResponse(body(), media_type="text/plain; charset=utf-8",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/compose", response_model=ComposeResponse)
def compose(req: ComposeRequest):
    # 1) DATA ----------------------------------------------------------------
    series = fetch_market_data(req.symbol, req.start, req.end, req.interval)
    if len(series.close) < 4:
        raise HTTPException(400, "Not enough data points to compose.")

    # 2) ANALYSIS ------------------------------------------------------------
    features = extract_features(
        dates=series.dates,
        close=series.close,
        volume=series.volume,
        symbol=req.symbol,
        n_phrases=req.n_phrases,
        open_=series.open,
    )

    # 3) COMPOSITION ---------------------------------------------------------
    composer = Composer(features)
    score = composer.compose()

    # 4) NOTATION ------------------------------------------------------------
    midi_bytes = score_to_midi_bytes(score)
    midi_b64 = base64.b64encode(midi_bytes).decode("ascii")

    # 5) ANALYST -------------------------------------------------------------
    analysis = analyze(features, score)

    notes_out = [
        NoteOut(pitch=n.pitch, start=n.start, duration=n.duration,
                velocity=n.velocity, voice=n.voice)
        for n in score.notes
    ]

    return ComposeResponse(
        symbol=features.symbol,
        key=f"{score.key_name} {score.mode}",
        mode=score.mode,
        tempo=score.tempo,
        market=series.to_dict(),
        features=features.to_dict(),
        analysis=analysis,
        notes=notes_out,
        midi_base64=midi_b64,
        midi_source=series.source,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
