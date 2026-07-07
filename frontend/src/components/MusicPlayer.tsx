import { useEffect, useMemo, useRef, useState } from "react";
import type { ComposeResponse, Note } from "../types";
import { playScore, stopPlayback } from "../player";
import { midiBlobUrl } from "../api";

interface Props {
  result: ComposeResponse;
}

const VOICE_COLOR: Record<Note["voice"], string> = {
  melody: "#d9b26a",
  harmony: "#7aa2d1",
  bass: "#c97b84",
};

export default function MusicPlayer({ result }: Props) {
  const { notes, tempo, key, symbol, midi_base64 } = result;
  const [playing, setPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const handleRef = useRef<{ stop: () => void } | null>(null);

  const midiUrl = useMemo(() => midiBlobUrl(midi_base64), [midi_base64]);

  useEffect(() => {
    return () => {
      stopPlayback();
      URL.revokeObjectURL(midiUrl);
    };
  }, [midiUrl]);

  // Reset when a new composition arrives.
  useEffect(() => {
    stopPlayback();
    setPlaying(false);
    setProgress(0);
  }, [midi_base64]);

  async function toggle() {
    if (playing) {
      handleRef.current?.stop();
      setPlaying(false);
      return;
    }
    setPlaying(true);
    handleRef.current = await playScore(
      notes,
      tempo,
      (t) => setProgress(t),
      () => {
        setPlaying(false);
        setProgress(0);
      }
    );
  }

  const bounds = useMemo(() => {
    const pitches = notes.map((n) => n.pitch);
    const lo = Math.min(...pitches);
    const hi = Math.max(...pitches);
    const end = Math.max(...notes.map((n) => n.start + n.duration), 1);
    return { lo, hi, end };
  }, [notes]);

  return (
    <div className="bg-panel/70 border border-white/5 rounded-2xl p-6 backdrop-blur">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="font-display text-2xl text-gold">{symbol} Sonata</h2>
          <p className="text-xs text-mist tracking-widest uppercase">
            {key} · {Math.round(tempo)} BPM · {notes.length} notes
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={toggle}
            className="px-5 py-2 rounded-full bg-gold text-ink text-sm font-medium
                       tracking-widest uppercase hover:brightness-110 transition"
          >
            {playing ? "◼ Stop" : "▶ Play"}
          </button>
          <a
            href={midiUrl}
            download={`${symbol}_sonata.mid`}
            className="px-5 py-2 rounded-full border border-gold/60 text-gold text-sm
                       tracking-widest uppercase hover:bg-gold hover:text-ink transition"
          >
            ↓ MIDI
          </a>
        </div>
      </div>

      {/* Piano roll */}
      <PianoRoll notes={notes} bounds={bounds} progress={progress} />

      <div className="flex gap-4 mt-3 text-xs text-mist">
        {(["melody", "harmony", "bass"] as const).map((v) => (
          <span key={v} className="flex items-center gap-1">
            <span
              className="inline-block w-3 h-3 rounded-sm"
              style={{ background: VOICE_COLOR[v] }}
            />
            {v}
          </span>
        ))}
      </div>
    </div>
  );
}

function PianoRoll({
  notes,
  bounds,
  progress,
}: {
  notes: Note[];
  bounds: { lo: number; hi: number; end: number };
  progress: number;
}) {
  const H = 220;
  const range = Math.max(1, bounds.hi - bounds.lo);
  const rowH = H / (range + 2);

  return (
    <div
      className="relative w-full rounded-xl overflow-hidden bg-ink/60 border border-white/5"
      style={{ height: H }}
    >
      {notes.map((n, i) => {
        const x = (n.start / bounds.end) * 100;
        const w = Math.max(0.4, (n.duration / bounds.end) * 100);
        const y = H - (n.pitch - bounds.lo + 1) * rowH;
        return (
          <div
            key={i}
            className="absolute rounded-[2px]"
            style={{
              left: `${x}%`,
              width: `${w}%`,
              top: y,
              height: Math.max(2, rowH - 1),
              background: VOICE_COLOR[n.voice],
              opacity: 0.35 + (n.velocity / 127) * 0.6,
            }}
          />
        );
      })}
      {/* Playhead */}
      <div
        className="absolute top-0 bottom-0 w-[2px] bg-white/70"
        style={{ left: `${progress * 100}%` }}
      />
    </div>
  );
}
