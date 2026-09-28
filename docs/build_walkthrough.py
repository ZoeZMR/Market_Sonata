"""
build_walkthrough.py -- regenerate docs/NVDA_Market_Sonata_Walkthrough.pdf

A step-by-step English walkthrough of the engine on real data (NVDA, 2024).
Every number and chart in the PDF is computed here from the live engine, so
the document stays true to the code.

    pip install reportlab matplotlib
    python docs/build_walkthrough.py
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

from backend.market_data import fetch_market_data
from music_engine import Composer, extract_features

FIG = tempfile.mkdtemp(prefix="sonata_fig_")
OUT = os.path.join(ROOT, "docs", "NVDA_Market_Sonata_Walkthrough.pdf")

# ---------------------------------------------------------------- palette --
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8984"
GRID, SURF, PANEL = "#e4e3df", "#ffffff", "#f5f4f1"
BLUE, ORANGE, AQUA, RED = "#2a78d6", "#eb6834", "#1baf7a", "#e34948"
VOICE = {"melody": BLUE, "harmony": ORANGE, "bass": AQUA}
SECTION_FILL = {"A": "#f3f6fb", "B": "#fbf4ef", "A'": "#f3f6fb"}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.5,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "axes.linewidth": 0.8,
    "xtick.color": INK2, "ytick.color": INK2, "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5, "axes.titlesize": 9, "axes.titlecolor": INK,
    "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False,
    "legend.frameon": False, "legend.fontsize": 7.5,
})

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def pname(p):
    return f"{NOTE_NAMES[p % 12]}{p // 12 - 1}"


def save(fig, name):
    path = os.path.join(FIG, name)
    fig.savefig(path, dpi=220, bbox_inches="tight", facecolor=SURF)
    plt.close(fig)
    return path


# ------------------------------------------------------------------ data ---
SYMBOL, START, END = "NVDA", "2024-01-01", "2024-12-31"
series = fetch_market_data(SYMBOL, START, END)
assert series.source == "yahoo", series.note
dates = np.array(series.dates, dtype="datetime64[D]")
close = np.array(series.close)
vol = np.array(series.volume)
opn = np.array(series.open)

feat = extract_features(series.dates, series.close, series.volume, SYMBOL,
                        open_=series.open)
comp = Composer(feat)
score = comp.compose()
plan = comp._form_plan(len(feat.phrases))
chunks = np.array_split(np.arange(close.size), len(feat.phrases))
motif = comp._build_motif(feat.phrases[0])
BPP = score.beats_per_phrase

rows = []
for (i, sec), p, idx in zip(plan, feat.phrases, chunks):
    m = motif if sec == "A" else comp._develop_motif(motif, p)
    tx = []
    if sec != "A":
        if p.momentum < -0.2:
            tx.append("invert")
        sh = int(round(p.momentum * 2))
        if sh:
            tx.append(f"shift {sh:+d}")
        if p.volatility > 0.5:
            tx.append("widen x1.5")
    colour = "triad"
    if p.volatility > 0.35:
        colour = "+7th"
    if p.volatility > 0.7:
        colour = "+7th +9th"
    gap_day = None
    if p.gap:
        gap_day = series.dates[idx[0] + int(round(p.gap_pos * idx.size))]
    bass_n = int(np.clip(round(2 + 6 * (0.6 * p.volume + 0.4 * p.volatility)), 2, 8))
    rows.append(dict(
        i=i, sec=sec, d0=series.dates[idx[0]], d1=series.dates[idx[-1]],
        idx=idx, p=p, motif=m, tx=", ".join(tx) or "as stated",
        n_mel=len(comp._phrase_rhythm(p, BPP)), bass_n=bass_n,
        colour=colour, vel=comp._velocity(p), gap_day=gap_day,
        chord=comp._chord_for_phrase(i)))

gap_rows = [r for r in rows if r["p"].gap]
dur_s = score.total_beats * 60.0 / score.tempo
ROMAN = ["I", "ii", "iii", "IV", "V", "vi", "vii\u00b0"]

# --------------------------------------------------------------- figures ---
def fig_pipeline():
    fig, ax = plt.subplots(figsize=(7.2, 1.55))
    ax.set_axis_off()
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 22)
    boxes = [
        ("Market data", "close, open,\nvolume (daily)", PANEL),
        ("1  Analysis", "data_to_music.py\n12 phrases of features", "#e6effa"),
        ("2  Composition", "composition.py\nkey, motif, form, voices", "#fbeee6"),
        ("3  Notation", "midi_generator.py\nMIDI file", "#e3f5ee"),
    ]
    w, gap = 21.5, 4.6
    for k, (title, sub, fc) in enumerate(boxes):
        x = k * (w + gap)
        ax.add_patch(FancyBboxPatch((x, 2), w, 18, boxstyle="round,pad=0,rounding_size=1.6",
                                    fc=fc, ec=GRID, lw=0.8))
        ax.text(x + w / 2, 14.2, title, ha="center", va="center", fontsize=9,
                fontweight="bold", color=INK)
        ax.text(x + w / 2, 7.6, sub, ha="center", va="center", fontsize=7.3,
                color=INK2, linespacing=1.35)
        if k < len(boxes) - 1:
            ax.annotate("", xy=(x + w + gap - 0.6, 11), xytext=(x + w + 0.6, 11),
                        arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.1))
    return save(fig, "pipeline.png")


def shade_sections(ax, x_of):
    for r in rows:
        x0, x1 = x_of(r, 0), x_of(r, 1)
        ax.axvspan(x0, x1, color=SECTION_FILL[r["sec"]], lw=0, zorder=0)


GAP_LABEL = {"2024-02-22": (-34, 16), "2024-07-31": (-40, -44), "2024-08-05": (8, -26)}


def fig_price():
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(7.2, 3.9), sharex=True,
                                 gridspec_kw=dict(height_ratios=[3, 1.1], hspace=0.12))
    def xd(r, side):
        idx = r["idx"]
        if side == 0:
            return dates[idx[0]] - np.timedelta64(12, "h")
        if r["i"] + 1 < len(rows):
            return dates[rows[r["i"] + 1]["idx"][0]] - np.timedelta64(12, "h")
        return dates[idx[-1]] + np.timedelta64(12, "h")
    for ax in (a1, a2):
        shade_sections(ax, xd)
        ax.grid(axis="x", visible=False)
    a1.plot(dates, close, color=BLUE, lw=1.6, zorder=3)
    top = close.max() * 1.1
    for r in rows:
        mid = dates[r["idx"][0]] + (dates[r["idx"][-1]] - dates[r["idx"][0]]) / 2
        a1.text(mid, top, f"P{r['i'] + 1}", ha="center", va="top", fontsize=7,
                color=INK2)
        a1.axvline(xd(r, 0), color=GRID, lw=0.7, zorder=1)
    for r in gap_rows:
        d = np.datetime64(r["gap_day"])
        j = series.dates.index(r["gap_day"])
        up = r["p"].gap > 0
        a1.plot([d], [opn[j]], marker="^" if up else "v", ms=8, color=INK,
                mec=SURF, mew=1.2, zorder=4)
        a1.annotate(f"gap {r['p'].gap:+.1%}\n{r['gap_day'][5:]}", (d, opn[j]),
                    xytext=GAP_LABEL.get(r["gap_day"], (8, -26)),
                    textcoords="offset points", fontsize=7, color=INK)
    for sec, x in (("A  exposition", rows[0]), ("B  development", rows[4]),
                   ("A'  recapitulation", rows[8])):
        a1.text(xd(x, 0) + np.timedelta64(3, "D"), close.min() * 0.97, sec,
                fontsize=7, color=MUTED, va="bottom")
    a1.set_ylim(close.min() * 0.9, top * 1.02)
    a1.set_ylabel("Close (USD)")
    a1.set_title("NVDA daily close, 2024, cut into 12 phrases", pad=6)
    a2.bar(dates, vol / 1e6, width=1.0, color="#9ec5f4", lw=0, zorder=2)
    a2.set_ylabel("Volume (M)")
    a2.set_title("Daily volume", pad=4, fontsize=8)
    fig.autofmt_xdate(rotation=0, ha="center")
    return save(fig, "price.png")


def fig_features():
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.3), sharex=True)
    x = np.arange(1, 13)
    mom = [r["p"].momentum for r in rows]
    vol_ = [r["p"].volatility for r in rows]
    vlm = [r["p"].volume for r in rows]
    axes[0].bar(x, mom, color=[BLUE if m >= 0 else RED for m in mom], width=0.62, zorder=2)
    axes[0].axhline(0, color=MUTED, lw=0.8)
    axes[0].set_ylim(-1, 1)
    axes[0].set_title("Momentum  [-1, 1]")
    axes[1].bar(x, vol_, color=BLUE, width=0.62, zorder=2)
    for y, lab in ((0.35, "+7th"), (0.5, "widen")):
        axes[1].axhline(y, color=MUTED, lw=0.8, ls=(0, (3, 2)))
        axes[1].text(12.6, y, lab, fontsize=6.5, color=INK2, va="bottom", ha="right")
    axes[1].set_ylim(0, 1)
    axes[1].set_title("Volatility  [0, 1]")
    axes[2].bar(x, vlm, color=BLUE, width=0.62, zorder=2)
    axes[2].set_ylim(0, 1)
    axes[2].set_title("Volume  [0, 1]")
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels([str(i) for i in x], fontsize=6.5)
        ax.set_xlabel("Phrase", fontsize=7)
        ax.grid(axis="x", visible=False)
    fig.tight_layout(w_pad=1.6)
    return save(fig, "features.png")


def fig_motif():
    p0 = feat.phrases[0]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 2.25),
                                 gridspec_kw=dict(width_ratios=[1.25, 1]))
    xs = np.arange(8)
    a1.plot(xs, p0.contour, color=BLUE, lw=1.6, marker="o", ms=5, mec=SURF, zorder=3)
    snapped = comp._snap_contour_to_degrees(p0.contour, span=4)
    pick = np.linspace(0, 7, 4).round().astype(int)
    for k in pick:
        a1.plot([k], [p0.contour[k]], marker="o", ms=10, mfc="none", mec=INK, mew=1.2, zorder=4)
    a1.set_ylim(-1.15, 1.15)
    a1.set_xticks(xs)
    a1.set_xlabel("Contour point (Phrase 1 resampled to 8 points)", fontsize=7)
    a1.set_title("Phrase 1 price contour, normalised")
    a1.text(0.98, 0.05, "circled = 4 points kept for the motif", transform=a1.transAxes,
            fontsize=7, color=INK2, va="bottom", ha="right")
    names = [pname(comp._degree_to_pitch(d, octave_shift=1)) for d in motif]
    a2.step(np.arange(5), list(motif) + [motif[-1]], where="post", color=GRID, lw=1, zorder=1)
    for k, (d, nm) in enumerate(zip(motif, names)):
        a2.add_patch(Rectangle((k + 0.06, d - 0.18), 0.88, 0.36, fc=BLUE, ec="none", zorder=3))
        a2.text(k + 0.5, d + 0.32, nm, ha="center", fontsize=7.5, color=INK)
    a2.set_xlim(0, 4)
    a2.set_ylim(-0.8, 5)
    a2.set_xticks([0.5, 1.5, 2.5, 3.5])
    a2.set_xticklabels(["1", "2", "3", "4"])
    a2.set_yticks(range(0, 5))
    a2.set_xlabel("Motif note", fontsize=7)
    a2.set_ylabel("Scale degree", fontsize=7)
    a2.set_title(f"Seed motif  {motif}")
    a2.grid(axis="x", visible=False)
    fig.tight_layout(w_pad=2)
    return save(fig, "motif.png")


def fig_pianoroll():
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    def xb(r, side):
        return (r["i"] + side) * BPP
    shade_sections(ax, xb)
    order = {"harmony": 1, "bass": 2, "melody": 3}
    for n in sorted(score.notes, key=lambda n: order[n.voice]):
        loud = n.velocity >= 100
        ax.add_patch(Rectangle((n.start, n.pitch - 0.42), max(n.duration, 0.25), 0.84,
                               fc=VOICE[n.voice], ec=INK if loud else SURF,
                               lw=1.1 if loud else 0.4, zorder=3 + order[n.voice]))
    for r in gap_rows:
        t = r["i"] * BPP + r["p"].gap_pos * BPP
        ax.axvline(t, color=INK, lw=0.7, ls=(0, (2, 2)), zorder=2)
    lo = min(n.pitch for n in score.notes) - 2
    for r in gap_rows:
        t = r["i"] * BPP + r["p"].gap_pos * BPP
        up = r["p"].gap > 0
        ax.text(t - 0.5 if up else t + 0.6, 101 if up else lo + 0.6,
                f"gap {r['p'].gap:+.1%}", fontsize=6.8, color=INK,
                va="top" if up else "bottom", ha="right" if up else "left",
                bbox=dict(fc=SURF, ec="none", pad=1), zorder=9)
    ax.set_ylim(lo, 102)
    ax.set_xlim(0, score.total_beats + 0.5)
    ax.set_xticks([r["i"] * BPP + BPP / 2 for r in rows] + [12 * BPP + 3])
    ax.set_xticklabels([f"P{r['i'] + 1}\n{r['sec']}" for r in rows] + ["end\ncad."], fontsize=6.8)
    ax.tick_params(axis="x", length=0)
    oct_ticks = [p for p in range(lo, 103) if p % 12 == 3]
    ax.set_yticks(oct_ticks)
    ax.set_yticklabels([pname(p) for p in oct_ticks])
    ax.set_ylabel("Pitch")
    ax.grid(axis="x", visible=False)
    ax.set_title(f"The finished score: {len(score.notes)} notes, {score.total_beats:.0f} beats "
                 f"(~{dur_s:.0f} s at {score.tempo:.0f} BPM)", pad=6)
    handles = [Rectangle((0, 0), 1, 1, fc=VOICE[v], ec="none") for v in ("melody", "harmony", "bass")]
    handles.append(Rectangle((0, 0), 1, 1, fc=SURF, ec=INK, lw=1.1))
    ax.legend(handles, ["Melody (right hand)", "Harmony (sustained chord)",
                        "Bass (ostinato)", "Gap accent (velocity 127)"],
              loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=4, fontsize=7)
    return save(fig, "pianoroll.png")


def fig_recipe():
    x = close.copy()
    i_all = np.arange(x.size)
    det = x - np.linspace(x[0], x[-1], x.size)
    w = max(1, x.size // 32)
    sm = np.convolve(det, np.ones(w) / w, mode="same")
    n = 16
    xi = np.linspace(0, x.size - 1, n)
    ds = np.interp(xi, i_all, sm)
    lo, hi = np.percentile(ds, [5, 95])
    nm = np.clip((ds - lo) / (hi - lo), 0, 1)
    deg = np.round(nm * 10).astype(int)
    for k in range(1, deg.size):
        deg[k] = np.clip(deg[k], deg[k - 1] - 4, deg[k - 1] + 4)
    deg[-1] = int(round(deg[-1] / 7)) * 7
    major = [0, 2, 4, 5, 7, 9, 11]
    pitches = [60 + 12 * (d // 7) + major[d % 7] for d in deg]

    fig, axes = plt.subplots(1, 4, figsize=(7.2, 1.95))
    axes[0].plot(i_all, x, color=BLUE, lw=1.2)
    axes[0].set_title("a  Raw close")
    axes[1].plot(i_all, det, color=GRID, lw=0.9)
    axes[1].plot(i_all, sm, color=BLUE, lw=1.4)
    axes[1].set_title("b  Detrend + smooth")
    axes[2].plot(np.arange(n), nm, color=BLUE, lw=1.2, marker="o", ms=4, mec=SURF)
    axes[2].set_ylim(-0.05, 1.05)
    axes[2].set_title("c  16 points, 0-1")
    for k, p in enumerate(pitches):
        axes[3].add_patch(Rectangle((k + 0.05, p - 0.45), 0.9, 0.9, fc=BLUE, ec="none", zorder=3))
    axes[3].set_xlim(0, n)
    axes[3].set_ylim(min(pitches) - 2, max(pitches) + 2)
    yt = sorted(set(pitches))[::2]
    axes[3].set_yticks(yt)
    axes[3].set_yticklabels([pname(p) for p in yt], fontsize=6.5)
    axes[3].set_title("d  Snapped to C major")
    for ax in axes[:3]:
        ax.set_xticks([])
        ax.set_yticks([])
    axes[3].set_xticks([])
    for ax in axes:
        ax.grid(axis="x", visible=False)
    fig.tight_layout(w_pad=1.2)
    return save(fig, "recipe.png"), [pname(p) for p in pitches]


# ------------------------------------------------------------ pdf styles ---
ss = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=ss["Normal"], fontName="Helvetica", fontSize=9.6,
                      leading=14, textColor=colors.HexColor(INK), spaceAfter=7)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8, leading=11,
                       textColor=colors.HexColor(INK2), spaceBefore=5, spaceAfter=4)
CAP = ParagraphStyle("cap", parent=SMALL, fontName="Helvetica-Oblique", spaceBefore=3,
                     spaceAfter=10)
H1 = ParagraphStyle("h1", parent=BODY, fontName="Helvetica-Bold", fontSize=15, leading=19,
                    spaceBefore=16, spaceAfter=8, keepWithNext=1)
H2 = ParagraphStyle("h2", parent=BODY, fontName="Helvetica-Bold", fontSize=11, leading=14,
                    spaceBefore=10, spaceAfter=5, textColor=colors.HexColor(INK),
                    keepWithNext=1)
TITLE = ParagraphStyle("title", parent=BODY, fontName="Helvetica-Bold", fontSize=24,
                       leading=29, spaceAfter=6)
SUB = ParagraphStyle("sub", parent=BODY, fontSize=12, leading=16,
                     textColor=colors.HexColor(INK2), spaceAfter=14)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8, leading=10.2, spaceAfter=0)
CELLB = ParagraphStyle("cellb", parent=CELL, fontName="Helvetica-Bold")
CODE = ParagraphStyle("code", parent=BODY, fontName="Courier", fontSize=8, leading=10.5,
                      backColor=colors.HexColor(PANEL), borderPadding=(6, 7, 6, 7),
                      spaceBefore=4, spaceAfter=12)
CALLOUT = ParagraphStyle("callout", parent=BODY, fontSize=9.2, leading=13.2,
                         backColor=colors.HexColor("#eef4fc"), borderPadding=(7, 9, 7, 9),
                         spaceBefore=14, spaceAfter=18)

FULLW = 7.0 * inch


def figure(path, caption):
    return KeepTogether([img(path), Paragraph(caption, CAP)])


def img(path, width=FULLW):
    from reportlab.lib.utils import ImageReader
    iw, ih = ImageReader(path).getSize()
    return Image(path, width=width, height=width * ih / iw)


def table(data, widths, header=True, zebra=True, align_right=()):
    body = [[c if isinstance(c, Paragraph) else Paragraph(str(c), CELLB if (header and r == 0) else CELL)
             for c in row] for r, row in enumerate(data)]
    t = Table(body, colWidths=widths, repeatRows=1 if header else 0)
    st = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, 0 if header else -1), 0.8, colors.HexColor(INK2)),
        ("LINEBELOW", (0, -1), (-1, -1), 0.6, colors.HexColor(GRID)),
    ]
    if zebra:
        for r in range(1 if header else 0, len(data)):
            if r % 2 == 0:
                st.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor(PANEL)))
    t.setStyle(TableStyle(st))
    return t


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor(MUTED))
    canvas.drawString(0.75 * inch, 0.5 * inch, "Market Sonata  |  Worked example: NVDA 2024")
    canvas.drawRightString(letter[0] - 0.75 * inch, 0.5 * inch, f"{doc.page}")
    canvas.restoreState()


# ---------------------------------------------------------------- story ----
P = lambda t, s=BODY: Paragraph(t, s)
pct = lambda v: f"{v:+.1%}"

story = []
story += [
    Spacer(1, 6),
    P("Market Sonata", TITLE),
    P("How a year of NVIDIA stock becomes a piano sonata: a step-by-step worked example", SUB),
]
story.append(P(
    f"This document follows one real dataset through the whole Market Sonata engine: "
    f"<b>NVIDIA (NVDA) daily prices from {series.dates[0]} to {series.dates[-1]}</b>, "
    f"{close.size} trading sessions from Yahoo Finance. Every number, chart and note "
    f"below was produced by running the project's code on that data, so you can "
    f"reproduce it with <font face='Courier'>python demo.py NVDA 2024-01-01 2024-12-31</font>."))
story.append(P(
    "The engine is split into three layers, mirroring how a human composer works. "
    "The <b>analysis</b> layer listens to the market and describes it in a small vocabulary "
    "(momentum, volatility, volume, trend). The <b>composition</b> layer turns that "
    "description into musical decisions (key, tempo, a theme and its development, harmony, "
    "dynamics). The <b>notation</b> layer writes the result as a MIDI file."))
story.append(figure(fig_pipeline(), "Figure 1. The three-layer pipeline. The composition layer never sees a raw price."))

story.append(P("The key design decision", H2))
story.append(P(
    "The obvious approach is <i>one trading day = one note</i>. It produces 252 notes of "
    "jittery, directionless sound: the ear cannot hear a shape in it. Market Sonata instead "
    "cuts the year into <b>12 phrases</b> (about 21 sessions, roughly one month each) and "
    "summarises each phrase with a handful of features. A sonata is built from phrases, not "
    "from individual samples; this gives the music room to breathe, repeat and develop.",
    CALLOUT))

story.append(P("The result at a glance", H2))
story.append(table([
    ["Market fact", "NVDA 2024", "Musical consequence"],
    ["Total return", pct(feat.total_return), f"Overall trend score {feat.trend:+.2f}: <b>{score.mode} key</b>"],
    ["Daily volatility (score)", f"{feat.avg_volatility:.2f} of 1", f"Tempo <b>{score.tempo:.0f} BPM</b> (range 60-108)"],
    ["Ticker", SYMBOL, f"Home note <b>{score.key_name}</b>, fixed for this ticker"],
    ["Max drawdown", f"-{feat.max_drawdown:.1%}", "Reported by the analyst note"],
    ["Opening gaps detected", f"{len(gap_rows)}", "Sforzando accents at velocity 127"],
    ["Output", f"{len(score.notes)} notes", f"{score.total_beats:.0f} beats, about {dur_s:.0f} seconds"],
], [1.75 * inch, 1.25 * inch, 4.0 * inch]))

# ---- Step 0: the data
story.append(PageBreak())
story.append(P("Step 0. The input data", H1))
story.append(P(
    f"NVDA had an extraordinary 2024: it rose from ${close[0]:.2f} to ${close[-1]:.2f} "
    f"({pct(feat.total_return)}), with a sharp spring rally, a summer sell-off and a choppy "
    f"autumn. The engine reads three daily series: the <b>close</b>, the <b>open</b> and the "
    f"<b>volume</b>. Prices are Yahoo's split-adjusted closes, so the 10-for-1 split in June "
    f"2024 does not show up as a fake crash."))
story.append(figure(fig_price(), "Figure 2. Close and volume, with the 12 phrase windows (P1-P12). Shading shows the "
    "musical form imposed on top: A (exposition), B (development), A' (recapitulation). "
    "Triangles mark the opening gaps the engine turns into accents."))

# ---- Step 1: features
story.append(P("Step 1. Analysis: describe the market in musical terms", H1))
story.append(P(
    "<font face='Courier'>extract_features()</font> in <font face='Courier'>data_to_music.py</font> "
    "computes two kinds of description. <b>Whole-piece</b> features set the global character; "
    "<b>per-phrase</b> features drive what happens moment to moment. Every feature is squashed "
    "into a fixed range (<font face='Courier'>tanh</font> or min-max scaling) so the composer "
    "works with the same numbers whatever the stock or price level."))
story.append(P("Whole-piece features", H2))
story.append(table([
    ["Feature", "How it is computed", "NVDA 2024"],
    ["trend  [-1, 1]", "60% tanh(3 x total return) + 40% share of up days (rescaled)", f"{feat.trend:+.3f}"],
    ["avg_volatility  [0, 1]", "tanh(40 x std of daily returns)", f"{feat.avg_volatility:.3f}"],
    ["avg_volume  [0, 1]", "mean volume / max volume", f"{feat.avg_volume:.3f}"],
    ["max_drawdown  [0, 1]", "worst peak-to-trough fall of the close", f"{feat.max_drawdown:.3f}"],
], [1.6 * inch, 4.2 * inch, 1.2 * inch]))
story.append(Spacer(1, 8))
story.append(P("Per-phrase features", H2))
story.append(P(
    "For each of the 12 windows the engine measures: the <b>contour</b> (the price shape inside "
    "the window, normalised to [-1, 1] and resampled to 8 points); <b>momentum</b> (net change "
    "across the window); <b>volatility</b> (the window's daily-return spread relative to the "
    "whole year); <b>volume</b> (mean volume relative to the year's peak); and <b>gap</b> (the "
    "largest overnight jump, if any)."))
story.append(figure(fig_features(), "Figure 3. The three per-phrase features that drive the composer. Red momentum bars are "
    "falling phrases (P4, P7, P12). Dashed lines are the volatility thresholds used later: "
    "above 0.35 the chord gains a 7th; above 0.5 the motif's intervals are widened."))

# ---- Step 2: global decisions
story.append(P("Step 2. Composition: the global decisions", H1))
story.append(P(
    "The <font face='Courier'>Composer</font> class first fixes three things for the whole "
    "piece. Each is a direct, explainable consequence of a whole-piece feature."))
story.append(table([
    ["Decision", "Rule", "NVDA 2024 result"],
    ["Mode", "trend > 0.15: major.  trend < -0.15: minor.  Otherwise Dorian (neither happy nor sad).",
     f"trend {feat.trend:+.2f} gives <b>major</b>"],
    ["Key (home note)", "SHA-256 hash of the ticker, mod 12. Every ticker always sings from the same note.",
     f"<b>{score.key_name}</b> ({pname(score.key_root)})"],
    ["Tempo", "60 + 48 x avg_volatility. Calm markets breathe slowly; volatile ones race.",
     f"60 + 48 x {feat.avg_volatility:.2f} = <b>{score.tempo:.0f} BPM</b>"],
    ["Chord progression", "Major: I-V, V-vi, I, vi-ii, repeating every 4 phrases.",
     "I+V / V+vi / I / vi+ii"],
], [1.35 * inch, 3.75 * inch, 1.9 * inch]))
story.append(Spacer(1, 10))

story.append(P("Step 3. The motif: one theme for the whole piece", H1))
story.append(P(
    "A random-sounding melody is forgettable. So the engine derives a single four-note "
    "<b>motif</b> from the first phrase, then reuses it everywhere, transformed. The contour "
    "of January's price (P1) is mapped onto scale degrees 0-4, and four evenly spaced points "
    "are kept: start, rise, peak, resolve."))
story.append(figure(fig_motif(), f"Figure 4. January's steady climb becomes a rising four-note motif, scale degrees "
    f"{motif}. Played one octave above the key's home register these are "
    f"{', '.join(pname(comp._degree_to_pitch(d, octave_shift=1)) for d in motif)}."))

# ---- Step 4: form + development
story.append(P("Step 4. Form and thematic development", H1))
story.append(P(
    "The 12 phrases are grouped into an <b>A - B - A'</b> arch, the backbone of classical "
    "sonata form. In <b>A</b> (P1-P4) the motif is stated plainly. In <b>B</b> (P5-P8) and "
    "<b>A'</b> (P9-P12) each phrase transforms the motif according to what the market did:"))
story.append(table([
    ["Market condition", "Transformation", "What the ear hears"],
    ["momentum < -0.2 (falling)", "<b>Inversion</b>: flip the motif upside-down around its first note", "The theme turns downward"],
    ["strong momentum", "<b>Transposition</b> by round(2 x momentum) scale steps", "The theme climbs or sinks"],
    ["volatility > 0.5", "<b>Widening</b>: every interval x 1.5", "Bigger leaps, more strain"],
], [1.7 * inch, 3.2 * inch, 2.1 * inch], zebra=False))
story.append(Spacer(1, 8))
story.append(P(
    "The table below is the full composition plan for NVDA 2024. Read across a row to see how "
    "one month of the market becomes one eight-beat phrase of music."))
hdr = ["#", "Dates", "Market character", "Sec.", "Motif transform", "Motif", "Mel. notes",
       "Bass notes", "Chord", "Vel."]
data = [hdr]
for r in rows:
    p = r["p"]
    data.append([
        f"P{r['i'] + 1}", f"{r['d0'][5:]} to {r['d1'][5:]}",
        f"{p.describe()}<br/><font color='{INK2}'>mom {p.momentum:+.2f}, vol {p.volatility:.2f}</font>",
        r["sec"], r["tx"], str(r["motif"]), str(r["n_mel"]), str(r["bass_n"]),
        f"{'+'.join(ROMAN[d % 7] for d in r['chord'])}<br/><font color='{INK2}'>{r['colour']}</font>",
        str(r["vel"]),
    ])
story.append(table(data, [w * inch for w in (0.42, 0.8, 1.32, 0.42, 1.0, 0.95, 0.47, 0.47, 0.62, 0.38)]))
story.append(P(
    "Dates are month-day in 2024. <b>Mel. notes</b>: more volatile phrases get more, shorter "
    "notes (2 to 8 per phrase). <b>Bass notes</b>: density of the left-hand ostinato, driven "
    "60% by volume and 40% by volatility. <b>Chord</b>: roots from the progression, coloured by "
    "volatility. <b>Vel.</b>: MIDI loudness from volume (40 to 112).", SMALL))
p7 = rows[6]
story.append(P(
    f"<b>Example: P7 ({p7['d0'][5:]} to {p7['d1'][5:]}).</b> NVDA fell hard in July "
    f"(momentum {p7['p'].momentum:+.2f}) and swung widely (volatility {p7['p'].volatility:.2f}). "
    f"All three transformations fire: the motif {motif} is inverted to [0, -2, -3, -4], shifted "
    f"down one step to [-1, -3, -4, -5], then widened to <b>{p7['motif']}</b>. The cheerful "
    f"rising theme from January becomes a steep, falling line, and this is where the "
    f"development section reaches its darkest point.", CALLOUT))

# ---- Step 5: gaps
story.append(P("Step 5. Shocks: opening gaps become accents", H1))
story.append(P(
    "A <b>gap</b> is when a stock opens far from the previous day's close, usually because "
    "news arrived while the market was shut (earnings, a macro shock). No trades happened in "
    "between, so the price literally skips. The engine computes open / previous close - 1 for "
    "every session and keeps only jumps larger than 2.5x the typical daily move (and at "
    "least 1%), so accents stay rare enough to be heard as events."))
gdata = [["Session", "Gap", "What happened", "Musical accent"]]
why = {"2024-02-22": "Blow-out Q4 earnings released the evening before",
       "2024-07-31": "Chip stocks rallied after AMD's strong AI results the evening before",
       "2024-08-05": "Global sell-off as the yen carry trade unwound"}
for r in gap_rows:
    up = r["p"].gap > 0
    gdata.append([r["gap_day"], pct(r["p"].gap), why.get(r["gap_day"], ""),
                  "High tonic + 3rd + 5th, two octaves up" if up else "Low tonic + 5th, three octaves down"])
story.append(table(gdata, [0.95 * inch, 0.65 * inch, 3.0 * inch, 2.4 * inch]))
story.append(P(
    "Each accent lasts half a beat at velocity 100 + 400 x |gap| (capped at 127), placed at "
    "the point inside the phrase where the gap occurred. Upward gaps flash in the melody's "
    "high register; downward gaps thud in the deep bass.", SMALL))

# ---- Step 6: score
story.append(P("Step 6. The finished score", H1))
story.append(P(
    "Each phrase is rendered in three voices, like a pianist's two hands plus sustain: the "
    "<b>melody</b> plays the (transformed) motif on the phrase's rhythm, nudged by the price "
    "contour; the <b>harmony</b> holds the phrase's chord; the <b>bass</b> runs a minimalist "
    "broken-chord ostinato in the style of Philip Glass. After the last phrase, a final "
    "tonic chord across three registers brings the piece home."))
story.append(figure(fig_pianoroll(), "Figure 5. Piano-roll view of the generated MIDI. Time runs left to right in beats "
    "(8 beats per phrase); height is pitch. Note how the melody drops in P7, how bass and "
    "melody thin out in the quieter A' section as volume fades, and the outlined accents "
    "at the three gaps."))
story.append(P("Reading the music against the market", H2))
for t in [
    "<b>A (Jan-Apr):</b> the rising motif is stated four times over a bright major progression. "
    "The Q4-earnings gap in February lands as a high accent in P2.",
    "<b>B (May-Aug):</b> the theme is pushed up during the May-June rally, then inverted and "
    "stretched in July as the stock sold off, with the early-August crash marked by a low thud "
    "at the start of P8.",
    "<b>A' (Sep-Dec):</b> momentum calms and volume fades, so the theme returns closer to its "
    "original form, played more softly (velocity falls from 59 to 52), and the piece resolves "
    "on the tonic.",
]:
    story.append(P("\u2022&nbsp;&nbsp;" + t))

# ---- Appendix
story.append(P("Appendix. A general recipe: any time series to a melody", H1))
story.append(P(
    "Market Sonata's phrase-and-motif design is one answer. If you just need a single melodic "
    "line from any column of numbers, these nine corrections turn raw data into something "
    "singable. Each fixes a specific way raw data sounds wrong."))
recipe_png, recipe_notes = fig_recipe()
story.append(table([
    ["#", "Step", "Problem it fixes", "How"],
    ["1", "Clean", "Missing values", "Linear interpolation"],
    ["2", "Detrend", "A rising series climbs off the keyboard", "Subtract the start-to-end line"],
    ["3", "Smooth", "Day-to-day noise makes the line jitter", "Moving average"],
    ["4", "Downsample", "Too many notes to hear a shape", "Interpolate to N points (here 16)"],
    ["5", "Normalise", "Values must map to a pitch range", "5th-95th percentile to [0, 1], robust to outliers"],
    ["6", "Quantise to a scale", "Out-of-key 'wrong' notes", "Round to scale degrees (major / minor)"],
    ["7", "Limit leaps", "Unsingable jumps", "Clamp each step to at most 4 degrees"],
    ["8", "End on the tonic", "The line never feels finished", "Snap the last note to the home note"],
    ["9", "Merge repeats", "Mechanical repeated notes", "Join equal neighbours into longer notes"],
], [0.3 * inch, 1.25 * inch, 2.45 * inch, 3.0 * inch]))
story.append(Spacer(1, 8))
story.append(figure(recipe_png, "Figure 6. The recipe applied to the same NVDA closes. Resulting 16-note melody in "
    f"C major: {'  '.join(recipe_notes)}."))
story.append(P("Core code", H2))
code = """deg  = np.round(normalised * span).astype(int)                 # 6. quantise
for i in range(1, len(deg)):                                     # 7. limit leaps
    deg[i] = np.clip(deg[i], deg[i-1] - max_leap, deg[i-1] + max_leap)
deg[-1] = round(deg[-1] / 7) * 7                                 # 8. end on tonic
pitch = root + 12 * (d // 7) + MAJOR[d % 7]                      # degree -> MIDI"""
story.append(Paragraph(code.replace(" ", "&nbsp;").replace("\n", "<br/>"), CODE))
story.append(P(
    "<b>Design choice worth making deliberately:</b> detrending removes the long-run direction "
    "from the melody. If that direction matters (a bull versus a bear year), express it "
    "through another musical dimension instead, as Market Sonata does by choosing a major or "
    "minor key from the trend.", SMALL))

doc = SimpleDocTemplate(OUT, pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                        topMargin=0.7 * inch, bottomMargin=0.8 * inch,
                        title="Market Sonata: NVDA 2024 Worked Example",
                        author="Zoe Zhao")
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print(OUT)
