import * as Tone from "tone";
import type { Note } from "./types";

// A small piano-playback engine built on Tone.js. We play the *notes* the
// backend returned (already in beats) rather than re-parsing the MIDI, which
// keeps playback perfectly in sync with the piano-roll visual.

let synth: Tone.PolySynth | null = null;
let scheduledIds: number[] = [];

function getSynth(): Tone.PolySynth {
  if (!synth) {
    // A warm, felt-piano-ish voice: soft attack, gentle release, light reverb.
    const reverb = new Tone.Reverb({ decay: 3.2, wet: 0.25 }).toDestination();
    synth = new Tone.PolySynth(Tone.Synth, {
      oscillator: { type: "triangle" },
      envelope: { attack: 0.02, decay: 0.4, sustain: 0.25, release: 1.6 },
    }).connect(reverb);
    synth.volume.value = -8;
  }
  return synth;
}

const VOICE_GAIN: Record<Note["voice"], number> = {
  melody: 0,
  harmony: -6,
  bass: -3,
};

export interface PlaybackHandle {
  stop: () => void;
  durationSeconds: number;
}

export async function playScore(
  notes: Note[],
  tempo: number,
  onProgress?: (t: number) => void,
  onEnd?: () => void
): Promise<PlaybackHandle> {
  await Tone.start();
  const s = getSynth();

  stopAll();
  Tone.Transport.stop();
  Tone.Transport.cancel();
  Tone.Transport.bpm.value = tempo;

  const secondsPerBeat = 60 / tempo;
  let endBeat = 0;

  for (const n of notes) {
    const startS = n.start * secondsPerBeat;
    const durS = Math.max(0.05, n.duration * secondsPerBeat);
    const freq = Tone.Frequency(n.pitch, "midi").toFrequency();
    const vel = Math.max(0.05, Math.min(1, n.velocity / 127));
    const gainAdj = VOICE_GAIN[n.voice] ?? 0;

    const id = Tone.Transport.schedule((time) => {
      s.triggerAttackRelease(
        freq,
        durS,
        time,
        vel * Math.pow(10, gainAdj / 20)
      );
    }, startS);
    scheduledIds.push(id);
    endBeat = Math.max(endBeat, n.start + n.duration);
  }

  const durationSeconds = endBeat * secondsPerBeat + 0.5;

  // Progress ticker (normalised 0..1).
  const progId = Tone.Transport.scheduleRepeat((time) => {
    const t = Tone.Transport.seconds / durationSeconds;
    Tone.Draw.schedule(() => onProgress?.(Math.min(1, t)), time);
  }, 0.05);
  scheduledIds.push(progId);

  const endId = Tone.Transport.schedule((time) => {
    Tone.Draw.schedule(() => {
      onProgress?.(1);
      onEnd?.();
    }, time);
  }, durationSeconds);
  scheduledIds.push(endId);

  Tone.Transport.start();

  return {
    durationSeconds,
    stop: () => {
      Tone.Transport.stop();
      Tone.Transport.cancel();
      stopAll();
    },
  };
}

function stopAll() {
  scheduledIds.forEach((id) => Tone.Transport.clear(id));
  scheduledIds = [];
  synth?.releaseAll();
}

export function stopPlayback() {
  Tone.Transport.stop();
  Tone.Transport.cancel();
  stopAll();
}
