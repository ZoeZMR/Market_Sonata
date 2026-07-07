"""
demo.py — run the whole engine from the command line, no server needed.

    python demo.py AAPL 2024-01-01 2024-12-31

Writes  output/<SYMBOL>_sonata.mid  and prints the analyst's program note.
Useful for generating example artefacts for a portfolio without the frontend.
"""

import os
import sys

from backend.market_data import fetch_market_data
from backend.analyst import analyze
from music_engine.data_to_music import extract_features
from music_engine.composition import Composer
from music_engine.midi_generator import score_to_midi


def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    start = sys.argv[2] if len(sys.argv) > 2 else "2024-01-01"
    end = sys.argv[3] if len(sys.argv) > 3 else "2024-12-31"

    print(f"Fetching {symbol}  {start} → {end} …")
    series = fetch_market_data(symbol, start, end)
    print(f"  {len(series.close)} data points  (source: {series.source})")

    features = extract_features(series.dates, series.close, series.volume, symbol)
    score = Composer(features).compose()

    os.makedirs("output", exist_ok=True)
    path = os.path.join("output", f"{symbol}_sonata.mid")
    score_to_midi(score, path)

    analysis = analyze(features, score)

    print(f"\nKey: {score.key_name} {score.mode}   Tempo: {round(score.tempo)} BPM")
    print(f"Notes: {len(score.notes)}   MIDI: {path}\n")
    print("— Analyst's Program Note —\n")
    print(analysis["program_note"])


if __name__ == "__main__":
    # Allow `python demo.py` from the project root.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main()
