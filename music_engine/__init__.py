"""
Market Sonata — Music Engine
============================

A generative composition system that translates financial market behavior
into intentional musical structure.

The engine is deliberately split into three layers, mirroring how a human
composer works:

    data_to_music.py  ->  ANALYSIS    (What is the market *saying*?)
    composition.py    ->  COMPOSITION (What musical form expresses that?)
    midi_generator.py ->  NOTATION    (Render the score as MIDI)

Nothing here produces random notes. Every pitch, rhythm and dynamic is a
consequence of a musical decision that is, in turn, a consequence of the
market data. The chain of causality is preserved so it can be *explained*.
"""

from .data_to_music import MarketFeatures, PhraseFeatures, extract_features
from .composition import Composer, Score, Note

# The MIDI/notation layer depends on `pretty_midi`. Import it lazily so the pure
# analysis + composition layers remain usable (and testable) even if the audio
# dependency isn't installed yet.
try:
    from .midi_generator import score_to_midi, score_to_midi_bytes
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    def score_to_midi(*_args, **_kwargs):  # type: ignore
        raise ModuleNotFoundError(
            "pretty_midi is required for MIDI export. Install it with "
            "`pip install pretty_midi`."
        )

    score_to_midi_bytes = score_to_midi  # type: ignore

__all__ = [
    "MarketFeatures",
    "PhraseFeatures",
    "extract_features",
    "Composer",
    "Score",
    "Note",
    "score_to_midi",
    "score_to_midi_bytes",
]

__version__ = "1.0.0"
