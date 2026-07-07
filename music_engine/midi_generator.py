"""
midi_generator.py
=================

The NOTATION layer.

Renders a `Score` (times expressed in beats) into a Standard MIDI File using
`pretty_midi`. Three voices are written to three instrument tracks so the piece
can be performed, edited in a DAW, or engraved as sheet music:

    melody   -> Acoustic Grand Piano (right hand)
    harmony  -> Acoustic Grand Piano (sustained chords)
    bass     -> Acoustic Grand Piano (left-hand ostinato)

Using a single timbre (solo piano) is a deliberate artistic choice: it keeps
the work in the intimate, human world of the reference composers rather than
letting it drift into generic synth-generative territory.
"""

from __future__ import annotations

import io
from typing import Dict

import pretty_midi

from .composition import Score


# General MIDI program numbers (0-indexed).
PIANO_PROGRAM = 0  # Acoustic Grand Piano


def _beats_to_seconds(beats: float, tempo: float) -> float:
    return beats * 60.0 / tempo


def score_to_pretty_midi(score: Score) -> pretty_midi.PrettyMIDI:
    """Build a PrettyMIDI object from a Score."""
    pm = pretty_midi.PrettyMIDI(initial_tempo=score.tempo)

    # One instrument per voice keeps the hands legible in a DAW / notation app.
    instruments: Dict[str, pretty_midi.Instrument] = {
        "melody": pretty_midi.Instrument(program=PIANO_PROGRAM, name="Melody (RH)"),
        "harmony": pretty_midi.Instrument(program=PIANO_PROGRAM, name="Harmony"),
        "bass": pretty_midi.Instrument(program=PIANO_PROGRAM, name="Bass (LH)"),
    }

    for note in score.notes:
        inst = instruments.get(note.voice, instruments["melody"])
        start_s = _beats_to_seconds(note.start, score.tempo)
        end_s = _beats_to_seconds(note.start + note.duration, score.tempo)
        pitch = int(max(0, min(127, note.pitch)))
        velocity = int(max(1, min(127, note.velocity)))
        inst.notes.append(
            pretty_midi.Note(velocity=velocity, pitch=pitch,
                             start=start_s, end=end_s)
        )

    for inst in instruments.values():
        if inst.notes:
            pm.instruments.append(inst)

    return pm


def score_to_midi(score: Score, path: str) -> str:
    """Write the score to a .mid file on disk. Returns the path."""
    pm = score_to_pretty_midi(score)
    pm.write(path)
    return path


def score_to_midi_bytes(score: Score) -> bytes:
    """Return the MIDI file as raw bytes (for streaming over HTTP)."""
    pm = score_to_pretty_midi(score)
    buf = io.BytesIO()
    pm.write(buf)
    return buf.getvalue()
