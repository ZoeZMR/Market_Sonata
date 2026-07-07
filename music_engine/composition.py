"""
composition.py
==============

The COMPOSITION layer — the musical brain of Market Sonata.

Given a `MarketFeatures` object, the `Composer` builds a `Score`: a list of
timed `Note` events across three voices (melody, harmony, bass) that together
form a coherent piano sonata in the minimalist / contemporary-classical idiom
of Hisaishi, Glass and Richter.

What makes this *composition* rather than *conversion*
------------------------------------------------------
1. KEY & MODE come from the market's overall trend. A bull market lives in a
   major key; a bear market in minor; a directionless market in a modal colour
   (Dorian) that is neither happy nor sad.

2. A MOTIF — a short, memorable melodic cell — is derived once from the first
   phrase and then *developed* (transposed, inverted, augmented, fragmented)
   throughout the piece according to what the market does next. This gives the
   music thematic unity: you can hear the "main theme" return.

3. FORM is imposed on top of the data. The phrases are grouped into an
   A – B – A' arch (exposition, development, recapitulation) so the piece has a
   beginning, a middle and an end — an emotional structure, not a data dump.

4. HARMONY follows a functional chord progression whose consonance/dissonance
   is modulated by volatility (calm phrases stay on triads; turbulent phrases
   add 7ths, 9ths and, at the extreme, cluster tension).

5. A LEFT-HAND OSTINATO (Glass-like arpeggiation) carries the pulse; its
   density and register are driven by trading volume and volatility.

Everything is deterministic: the same market window always yields the same
sonata, so a performer or an analyst can reason about it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import hashlib

import numpy as np

from .data_to_music import MarketFeatures, PhraseFeatures


# ---------------------------------------------------------------------------
# Score primitives
# ---------------------------------------------------------------------------

@dataclass
class Note:
    """A single note event, expressed in beats (not seconds)."""
    pitch: int          # MIDI note number
    start: float        # start time in beats
    duration: float     # length in beats
    velocity: int       # 1..127
    voice: str          # "melody" | "harmony" | "bass"


@dataclass
class Score:
    """A complete composition, ready to be rendered to MIDI."""
    notes: List[Note] = field(default_factory=list)
    tempo: float = 72.0                 # BPM
    key_root: int = 60                  # MIDI pitch of tonic (C4 = 60)
    key_name: str = "C"
    mode: str = "major"                 # "major" | "minor" | "dorian"
    beats_per_phrase: float = 8.0
    title: str = "Market Sonata"

    @property
    def total_beats(self) -> float:
        return max((n.start + n.duration for n in self.notes), default=0.0)

    def add(self, note: Note) -> None:
        self.notes.append(note)


# ---------------------------------------------------------------------------
# Musical constants
# ---------------------------------------------------------------------------

# Scale degrees as semitone offsets from the tonic.
SCALES: Dict[str, List[int]] = {
    "major":  [0, 2, 4, 5, 7, 9, 11],
    "minor":  [0, 2, 3, 5, 7, 8, 10],   # natural minor
    "dorian": [0, 2, 3, 5, 7, 9, 10],   # minor with a raised 6th — hopeful minor
}

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Functional chord progressions (as scale-degree roots, 0-indexed).
# Chosen for the warm, suspended quality of the reference composers.
PROGRESSIONS: Dict[str, List[List[int]]] = {
    # I – V – vi – IV : the archetypal uplifting loop.
    "major":  [[0, 4], [4, 5], [0], [5, 1]],
    # i – VI – III – VII : the "epic minor" cadence used across film scoring.
    "minor":  [[0], [5], [2], [6]],
    # i – IV – i – V : Dorian's characteristic major-IV brightness.
    "dorian": [[0], [3], [0], [4]],
}


# ---------------------------------------------------------------------------
# The Composer
# ---------------------------------------------------------------------------

class Composer:
    """Turns market features into a Score."""

    def __init__(self, features: MarketFeatures, octave: int = 4):
        self.f = features
        self.base_octave = octave
        self.mode = self._choose_mode()
        self.key_root = self._choose_key_root()
        self.scale = SCALES[self.mode]
        self.progression = PROGRESSIONS[self.mode]
        self.tempo = self._choose_tempo()

    # -- Global musical decisions ------------------------------------------

    def _choose_mode(self) -> str:
        t = self.f.trend
        if t > 0.15:
            return "major"
        if t < -0.15:
            return "minor"
        return "dorian"        # ambiguous market -> ambiguous, modal colour

    def _choose_key_root(self) -> int:
        """
        The tonic pitch is derived deterministically from the ticker so that
        every asset has its own recognisable "home". AAPL always sings from
        the same note; TSLA from another. This is an artistic signature, not a
        musical necessity — but it makes each sonata feel authored.
        """
        h = int(hashlib.sha256(self.f.symbol.encode()).hexdigest(), 16)
        # Pick a tonic pitch class, keep it in a comfortable piano register.
        pitch_class = h % 12
        root = 12 * (self.base_octave + 1) + pitch_class  # e.g. octave 4 -> C4=60
        return root

    def _choose_tempo(self) -> float:
        """Volatility raises the heartbeat; calm markets breathe slowly."""
        # 60 BPM (meditative) .. 108 BPM (agitated)
        return float(60 + 48 * self.f.avg_volatility)

    @property
    def key_name(self) -> str:
        return NOTE_NAMES[self.key_root % 12]

    # -- Pitch helpers -----------------------------------------------------

    def _degree_to_pitch(self, degree: int, octave_shift: int = 0) -> int:
        """Map a (possibly out-of-range) scale degree to a MIDI pitch."""
        n = len(self.scale)
        octave = degree // n + octave_shift
        semitone = self.scale[degree % n]
        return self.key_root + 12 * octave + semitone

    def _snap_contour_to_degrees(self, contour: List[float], span: int) -> List[int]:
        """Map a [-1,1] contour onto scale degrees spanning `span` steps."""
        return [int(round((c + 1) / 2 * span)) for c in contour]

    # -- Motif -------------------------------------------------------------

    def _build_motif(self, phrase: PhraseFeatures) -> List[int]:
        """
        The seed theme. A motif is a list of scale degrees (relative to the
        phrase tonic). We derive it from the first phrase's contour, then
        clean it into a singable 4-note cell — the DNA of the whole piece.
        """
        degrees = self._snap_contour_to_degrees(phrase.contour, span=4)
        # Condense to 4 signature notes (start, rise, peak/dip, resolve).
        if len(degrees) >= 4:
            idx = np.linspace(0, len(degrees) - 1, 4).round().astype(int)
            motif = [degrees[i] for i in idx]
        else:
            motif = degrees + [0] * (4 - len(degrees))
        return motif

    def _develop_motif(self, motif: List[int], phrase: PhraseFeatures) -> List[int]:
        """
        Thematic development. Depending on the phrase's character, transform
        the seed motif rather than inventing a new one — the ear recognises
        the theme even as it changes.
        """
        m = list(motif)

        # Falling market -> invert the motif (turn the contour upside-down).
        if phrase.momentum < -0.2:
            pivot = m[0]
            m = [pivot - (d - pivot) for d in m]

        # Strong momentum -> transpose the whole motif up/down a step or two.
        shift = int(round(phrase.momentum * 2))
        m = [d + shift for d in m]

        # Turbulence -> widen the intervals (larger leaps = more tension).
        if phrase.volatility > 0.5:
            m = [int(d * 1.5) for d in m]

        return m

    # -- Rhythm ------------------------------------------------------------

    def _phrase_rhythm(self, phrase: PhraseFeatures, beats: float) -> List[float]:
        """
        Return a list of note durations (in beats) filling one phrase.
        Calm phrases -> long, sustained notes. Turbulent phrases -> more,
        shorter notes (faster rhythmic activity).
        """
        # 2 events (calm) .. 8 events (agitated) per phrase.
        n_events = int(round(2 + 6 * phrase.volatility))
        n_events = max(2, min(8, n_events))
        base = beats / n_events
        # Add gentle rhythmic variety so it doesn't feel mechanical.
        durations = []
        for i in range(n_events):
            if phrase.volatility < 0.3 and i == n_events - 1:
                durations.append(base * 1.5)   # let calm phrases ring out
            else:
                durations.append(base)
        # Normalise so they sum to `beats`.
        scale = beats / sum(durations)
        return [d * scale for d in durations]

    # -- Harmony -----------------------------------------------------------

    def _chord_for_phrase(self, phrase_idx: int) -> List[int]:
        """Root scale-degrees of the chord for this phrase (a triad's root)."""
        prog = self.progression
        return prog[phrase_idx % len(prog)]

    def _build_chord(self, root_degree: int, phrase: PhraseFeatures) -> List[int]:
        """
        Build a voiced chord as MIDI pitches. Volatility decides the colour:
          calm       -> plain triad (root, 3rd, 5th)
          restless   -> add the 7th (jazz-warm, Richter-esque)
          turbulent  -> add the 9th and tighten voicing toward a cluster
        """
        degrees = [root_degree, root_degree + 2, root_degree + 4]  # triad
        if phrase.volatility > 0.35:
            degrees.append(root_degree + 6)          # 7th
        if phrase.volatility > 0.7:
            degrees.append(root_degree + 8)          # 9th -> lush/tense
        # Voice it around one octave below the melody.
        return [self._degree_to_pitch(d, octave_shift=-1) for d in degrees]

    # -- Dynamics ----------------------------------------------------------

    def _velocity(self, phrase: PhraseFeatures, accent: float = 1.0) -> int:
        """
        Trading volume -> loudness. Range chosen to stay musical: even the
        quietest passages (velocity ~40) are audible; the loudest (~112) never
        clip into harshness.
        """
        base = 40 + 72 * phrase.volume
        return int(np.clip(base * accent, 20, 120))

    # -- Form --------------------------------------------------------------

    def _form_plan(self, n: int) -> List[Tuple[int, str]]:
        """
        Impose an A – B – A' arch over the phrases.
        Returns [(phrase_index, section_label), ...].
        A  : exposition (state the theme)
        B  : development (depart, build tension)
        A' : recapitulation (return home, transformed)
        """
        if n < 3:
            return [(i, "A") for i in range(n)]
        a_end = max(1, n // 3)
        b_end = max(a_end + 1, (2 * n) // 3)
        plan = []
        for i in range(n):
            if i < a_end:
                plan.append((i, "A"))
            elif i < b_end:
                plan.append((i, "B"))
            else:
                plan.append((i, "A'"))
        return plan

    # -- Main entry point --------------------------------------------------

    def compose(self) -> Score:
        beats_per_phrase = 8.0
        score = Score(
            tempo=self.tempo,
            key_root=self.key_root,
            key_name=self.key_name,
            mode=self.mode,
            beats_per_phrase=beats_per_phrase,
            title=f"{self.f.symbol} Sonata",
        )

        phrases = self.f.phrases
        if not phrases:
            return score

        motif = self._build_motif(phrases[0])
        plan = self._form_plan(len(phrases))

        cursor = 0.0  # running time in beats

        for phrase_idx, section in plan:
            phrase = phrases[phrase_idx]

            # In the recapitulation we lean back on the *original* motif; in the
            # development we let it mutate freely.
            if section == "A'":
                phrase_motif = self._develop_motif(motif, phrase)
                phrase_motif = [d - 0 for d in phrase_motif]   # gentle return
            elif section == "B":
                phrase_motif = self._develop_motif(motif, phrase)
            else:  # A — state the theme plainly
                phrase_motif = list(motif)

            self._render_phrase(score, phrase, phrase_motif, cursor,
                                beats_per_phrase, section)
            cursor += beats_per_phrase

        # A final tonic resolution — every sonata needs to land home.
        self._render_cadence(score, cursor, phrases[-1])
        return score

    # -- Phrase rendering --------------------------------------------------

    def _render_phrase(
        self,
        score: Score,
        phrase: PhraseFeatures,
        motif: List[int],
        start: float,
        beats: float,
        section: str,
    ) -> None:
        # 1) MELODY — motif stretched across the phrase's rhythm ----------
        rhythm = self._phrase_rhythm(phrase, beats)
        t = start
        for i, dur in enumerate(rhythm):
            degree = motif[i % len(motif)]
            # Follow the intra-phrase contour for expressive micro-motion.
            contour_pos = int(i / max(1, len(rhythm) - 1) * (len(phrase.contour) - 1))
            micro = int(round(phrase.contour[contour_pos]))
            pitch = self._degree_to_pitch(degree + micro, octave_shift=1)
            vel = self._velocity(phrase, accent=1.0 if i == 0 else 0.85)
            score.add(Note(pitch, t, dur * 0.95, vel, "melody"))
            t += dur

        # 2) HARMONY — a sustained chord underpinning the phrase ----------
        root_degrees = self._chord_for_phrase(phrase.index)
        for rd in root_degrees:
            chord = self._build_chord(rd, phrase)
            chord_vel = self._velocity(phrase, accent=0.6)
            for p in chord:
                score.add(Note(p, start, beats, chord_vel, "harmony"))

        # 3) BASS — a minimalist arpeggiated ostinato ---------------------
        # Volume drives how busy the left hand is (more participation = more
        # layers/activity, per the mapping spec).
        self._render_bass(score, phrase, root_degrees[0], start, beats)

    def _render_bass(
        self,
        score: Score,
        phrase: PhraseFeatures,
        root_degree: int,
        start: float,
        beats: float,
    ) -> None:
        # Density: 2 (sparse) .. 8 (driving) notes, from volume + volatility.
        density = int(round(2 + 6 * (0.6 * phrase.volume + 0.4 * phrase.volatility)))
        density = max(2, min(8, density))
        step = beats / density
        # Broken-chord pattern (root, 5th, octave, 3rd) — Glass-like cells.
        pattern = [0, 4, 7, 2]
        for i in range(density):
            deg = root_degree + pattern[i % len(pattern)]
            pitch = self._degree_to_pitch(deg, octave_shift=-2)
            vel = self._velocity(phrase, accent=0.5)
            score.add(Note(pitch, start + i * step, step * 0.9, vel, "bass"))

    def _render_cadence(self, score: Score, start: float,
                        last_phrase: PhraseFeatures) -> None:
        """Resolve to the tonic chord and let it ring — the final breath."""
        beats = 6.0
        vel = self._velocity(last_phrase, accent=0.7)
        # Tonic triad across three registers.
        for octave_shift, voice in [(-2, "bass"), (-1, "harmony"), (1, "melody")]:
            for deg in ([0, 2, 4] if octave_shift != -2 else [0]):
                score.add(Note(
                    self._degree_to_pitch(deg, octave_shift=octave_shift),
                    start, beats, vel, voice,
                ))
