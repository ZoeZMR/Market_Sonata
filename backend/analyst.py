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
    "TRUE facts about a generative composition — for solo piano or a full "
    "band, whichever the facts describe — and the financial data that "
    "generated it. Write a vivid, elegant program note (3-4 short "
    "paragraphs). You must ONLY use the facts provided — never invent musical "
    "details, instruments, key signatures, or events that are not in the "
    "facts. Write for an educated general audience at a graduate "
    "music-technology level."
)


def _llm_note(facts: Dict[str, Any], grounded: str) -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-sonnet-5",
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
    except Exception as exc:                                  # noqa: BLE001
        # Never let a broken/expired key or model-id change break the note —
        # the caller always has the grounded text to fall back to. Do log it,
        # though: an LLM key that silently never fires looks identical to one
        # that was never set, and that gap is easy to miss.
        print(f"[analyst] LLM polish failed, using grounded note: {exc!r}")
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


def analyze_facts(facts: Dict[str, Any], grounded: str) -> Dict[str, Any]:
    """
    Same LLM-polish step as `analyze()`, but for a caller that already has its
    own grounded facts and draft note — used by the deployed JS engine
    (`standalone.html`), which computes its own facts client-side and only
    needs this module for the optional Claude polish.
    """
    polished = _llm_note(facts, grounded)
    return {
        "program_note": polished or grounded,
        "used_llm": polished is not None,
    }


# ---------------------------------------------------------------------------
# AI-written program note (streamed)
#
# Unlike the polish step above, this does not rephrase a template: Claude
# writes the note from scratch, from a rich, structured account of the market
# window and of the finished score that the frontend assembles. The prompt
# keeps every claim anchored to those facts.
# ---------------------------------------------------------------------------

PROGRAM_NOTE_MODEL = os.environ.get("MARKET_SONATA_MODEL", "claude-opus-5")

_PROGRAM_NOTE_SYSTEM = """\
You are the resident writer of Market Sonata, a generative instrument that \
turns a financial market's price history into an original piece of music. \
For every piece it composes, you write the programme note a listener reads \
while the music plays — the way a great concert-hall annotator or a music \
critic would, not the way a template fills blanks.

You will receive a JSON dossier with three parts:
- "asset" and "market": what was traded, over which window, and what happened \
(returns, drawdown and when it bottomed, the biggest single moves with dates, \
and a chronological list of chapters with their mood).
- "composition": the finished score — key, mode, tempo, length, instruments, \
the song form with each section's start time, what each section musically \
does and which dates of the market it reads, and the "ticker fingerprint" \
(musical traits fixed by the symbol itself, independent of the market).
- "mapping": the rules that connect the two (e.g. trend picks the modal \
family, volatility sets tempo, rhythmic density and chord colour, volume sets \
loudness, the chorus hook comes from the most energetic chapter).

How to write it:
- Tell the story of THIS window. Pick the two or three moments that matter \
most — a turning point, the deepest fall, the most frenzied stretch — name \
their dates, and say exactly what the listener hears there and why. Causality \
is the point: market event → musical decision → what it feels like.
- Write with a point of view and sensory, specific language; vary sentence \
rhythm; avoid clichés ("rollercoaster", "tale of two halves", "buckle up") \
and avoid restating the same number twice.
- Be accurate. Use only facts in the dossier. Quote numbers as given (you may \
round sensibly). Never invent events, news, causes, instruments, chords or \
timings that are not in the dossier; if you don't know why the market moved, \
describe the movement, not a reason for it.
- This is art, not advice: no predictions, recommendations or opinions on \
whether to buy or sell.

Shape (Markdown, no preamble, no sign-off):
1. A short, evocative title as a level-3 heading (###).
2. Three or four paragraphs of prose (about 250–400 words in total).
3. A "Listening guide" level-4 heading (####), then 4–6 bullets, each \
starting with a timestamp in **m:ss** bold taken from the section start \
times, telling the listener what to listen for at that moment and what \
market moment it carries.
"""

_STYLES = {
    "concert": "Voice: an elegant concert-programme annotator — warm, erudite, precise.",
    "poetic": "Voice: lyrical and imagistic, closer to a prose poem, while staying factually exact.",
    "critic": "Voice: a sharp, witty music critic reviewing the piece — opinionated about the music, never about the investment.",
    "desk": "Voice: a markets-desk storyteller who also knows music — brisk, concrete, with the market narrative up front and each musical choice explained in plain terms.",
    "simple": "Voice: friendly and plain for a curious listener with no finance or music background; explain every term you use in a few words.",
}
_LANGS = {
    "en": "Write in English.",
    "zh": "用简体中文写作。标题、正文和聆听指南全部使用中文；股票代码、调名（如 C# major）和数字保持原样。",
}


class NoteUnavailable(RuntimeError):
    """Raised when no Anthropic credentials are configured."""


def stream_program_note(dossier: Dict[str, Any], style: str = "concert",
                        language: str = "en", request: str = ""):
    """
    Yield the programme note as text chunks while Claude writes it.
    Raises NoteUnavailable if no API key is configured.
    """
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        raise NoteUnavailable("Set ANTHROPIC_API_KEY in backend/.env to enable AI-written notes.")
    import json as _json
    import anthropic

    brief = [_STYLES.get(style, _STYLES["concert"]), _LANGS.get(language, _LANGS["en"])]
    request = (request or "").strip()[:500]
    if request:
        brief.append("The listener also asked for this (honour it if it doesn't "
                     "conflict with the rules above): " + request)

    client = anthropic.Anthropic()
    with client.beta.messages.stream(
        model=PROGRAM_NOTE_MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        # Server-side fallback: if the primary model declines, the same request
        # is re-run on the fallback inside this one call.
        betas=["server-side-fallback-2026-06-01"],
        fallbacks=[{"model": "claude-opus-4-8"}],
        system=_PROGRAM_NOTE_SYSTEM,
        messages=[{
            "role": "user",
            "content": ("<dossier>\n" + _json.dumps(dossier, ensure_ascii=False, indent=1)
                        + "\n</dossier>\n\n" + "\n".join(brief)
                        + "\n\nWrite the programme note."),
        }],
    ) as stream:
        for text in stream.text_stream:
            yield text
        final = stream.get_final_message()
        if final.stop_reason == "refusal":
            yield "\n\n*(The analyst declined to write a note for this piece.)*"
