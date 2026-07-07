"""
analyst.py
==========

The AI music analyst.

Given the market features and the finished score, this module writes a
program note — the kind of paragraph you would read beside a piece in a
concert programme. It explains *why* the music sounds the way it does by
tracing each musical decision back to the market that caused it.

Two modes
---------
1. Grounded rule-based narration (default, no API key required). It reads the
   real feature values and the real score and describes them faithfully — it
   never invents facts about the music.

2. Optional LLM polish. If an ANTHROPIC_API_KEY is present, the grounded facts
   are handed to Claude with a strict "music analyst" system prompt to render
   them into more elegant prose. The facts still come from the score, so the
   model narrates rather than hallucinates.

Keeping the facts and the prose separate is what makes this an *analyst* and
not a chatbot: the claims are always true of the actual composition.
"""

from __future__ import annotations

import os
from typing import Dict, Any, List

from music_engine.data_to_music import MarketFeatures
from music_engine.composition import Score


# ---------------------------------------------------------------------------
# Grounded fact extraction
# ---------------------------------------------------------------------------

def _facts(features: MarketFeatures, score: Score) -> Dict[str, Any]:
    """Pull the objective, defensible facts we are allowed to talk about."""
    n_notes = len(score.notes)
    voices = sorted({n.voice for n in score.notes})
    ret_pct = features.total_return * 100.0

    return {
        "symbol": features.symbol,
        "window": f"{features.start_date} to {features.end_date}",
        "n_days": features.n_days,
        "return_pct": ret_pct,
        "direction": "gained" if ret_pct >= 0 else "lost",
        "trend_word": (
            "a confident bull market" if features.trend > 0.4 else
            "a gently rising market" if features.trend > 0.05 else
            "a directionless, sideways market" if features.trend > -0.05 else
            "a declining market" if features.trend > -0.4 else
            "a steep bear market"
        ),
        "key": f"{score.key_name} {score.mode}",
        "tempo": round(score.tempo),
        "tempo_word": (
            "meditative" if score.tempo < 72 else
            "flowing" if score.tempo < 90 else "agitated"
        ),
        "volatility": features.avg_volatility,
        "vol_word": (
            "low volatility, so the harmony stays consonant and the phrases "
            "are long and calm"
            if features.avg_volatility < 0.34 else
            "moderate volatility, colouring the chords with added 7ths and a "
            "more active rhythm"
            if features.avg_volatility < 0.67 else
            "high volatility, pushing the harmony toward dissonant 9ths, wide "
            "melodic leaps and restless rhythm"
        ),
        "volume": features.avg_volume,
        "vol_dyn_word": (
            "quiet, sparse textures" if features.avg_volume < 0.34 else
            "a full-bodied dynamic" if features.avg_volume > 0.66 else
            "a moderate dynamic"
        ),
        "drawdown_pct": features.max_drawdown * 100.0,
        "n_notes": n_notes,
        "voices": voices,
        "n_phrases": len(features.phrases),
    }


# ---------------------------------------------------------------------------
# Rule-based program note
# ---------------------------------------------------------------------------

def _grounded_note(f: Dict[str, Any], features: MarketFeatures) -> str:
    opening = (
        f"The {f['symbol']} Sonata is written in {f['key']}, "
        f"a {f['tempo_word']} {f['tempo']} BPM. That key was not chosen at "
        f"random: over the selected window the asset {f['direction']} "
        f"{abs(f['return_pct']):.1f}% across {f['n_days']} trading days — "
        f"{f['trend_word']} — and Market Sonata maps a rising market to major "
        f"tonality, a falling market to minor, and an undecided market to the "
        f"ambiguous colour of the Dorian mode."
    )

    tension = (
        f"Volatility during the period registered as {f['vol_word']}. "
        f"Trading volume translated into {f['vol_dyn_word']}: the louder the "
        f"market's participation, the fuller the piano writing."
    )

    # Narrate the emotional arc using the first, middle and last phrases.
    phrases = features.phrases
    arc = ""
    if phrases:
        first = phrases[0].describe()
        mid = phrases[len(phrases) // 2].describe()
        last = phrases[-1].describe()
        arc = (
            f"Structurally the work follows an A–B–A′ arch across "
            f"{f['n_phrases']} phrases. The opening theme is drawn from the "
            f"first phrase ({first}); the central development departs from it "
            f"as the market grows {mid}; and the recapitulation returns home "
            f"({last}), transformed by everything in between."
        )

    if f["drawdown_pct"] > 12:
        arc += (
            f" The deepest drawdown of the window (−{f['drawdown_pct']:.1f}%) "
            f"is felt as the emotional low point of the central section, where "
            f"the motif is inverted and the harmony is at its most unstable."
        )

    craft = (
        f"A single four-note motif, derived from the shape of the earliest "
        f"price movement, recurs throughout — transposed, inverted and "
        f"fragmented — so the ear can follow one idea through the whole piece. "
        f"The finished score contains {f['n_notes']} notes across "
        f"{len(f['voices'])} voices ({', '.join(f['voices'])}), rendered as "
        f"solo piano to keep the work in an intimate, human register."
    )

    return "\n\n".join([opening, tension, arc, craft]).strip()


# ---------------------------------------------------------------------------
# Optional LLM polish
# ---------------------------------------------------------------------------

_ANALYST_SYSTEM = (
    "You are a concert-programme music analyst. You will be given a set of "
    "TRUE facts about a generative piano composition and the financial data "
    "that generated it. Write a vivid, elegant program note (3-4 short "
    "paragraphs). You must ONLY use the facts provided — never invent musical "
    "details, key signatures, or events that are not in the facts. Write for "
    "an educated general audience at a graduate music-technology level."
)


def _llm_note(facts: Dict[str, Any], grounded: str) -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=700,
            system=_ANALYST_SYSTEM,
            messages=[{
                "role": "user",
                "content": (
                    "FACTS (JSON):\n" + str(facts) +
                    "\n\nA grounded draft you may improve upon:\n" + grounded +
                    "\n\nWrite the final program note."
                ),
            }],
        )
        return "".join(
            block.text for block in msg.content if getattr(block, "type", "") == "text"
        ).strip()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze(features: MarketFeatures, score: Score) -> Dict[str, Any]:
    """
    Produce the analyst's program note plus the structured facts behind it,
    so the frontend can show both the prose and a "why" breakdown.
    """
    facts = _facts(features, score)
    grounded = _grounded_note(facts, features)
    polished = _llm_note(facts, grounded)

    return {
        "program_note": polished or grounded,
        "used_llm": polished is not None,
        "facts": facts,
    }
