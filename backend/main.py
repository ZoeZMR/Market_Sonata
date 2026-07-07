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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from market_data import fetch_market_data
from analyst import analyze

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

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "market-sonata"}


@app.get("/api/market")
def market(
    symbol: str = Query(..., description="Ticker, e.g. AAPL"),
    start: str = Query(...),
    end: str = Query(...),
):
    series = fetch_market_data(symbol, start, end)
    if not series.close:
        raise HTTPException(404, "No market data for that symbol/range.")
    return series.to_dict()


@app.post("/api/compose", response_model=ComposeResponse)
def compose(req: ComposeRequest):
    # 1) DATA ----------------------------------------------------------------
    series = fetch_market_data(req.symbol, req.start, req.end)
    if len(series.close) < 4:
        raise HTTPException(400, "Not enough data points to compose.")

    # 2) ANALYSIS ------------------------------------------------------------
    features = extract_features(
        dates=series.dates,
        close=series.close,
        volume=series.volume,
        symbol=req.symbol,
        n_phrases=req.n_phrases,
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
