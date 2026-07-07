import type { ComposeResponse, MarketSeries } from "./types";

// In dev, Vite proxies /api to the FastAPI server. In production, set
// VITE_API_BASE to the deployed backend URL.
const BASE = import.meta.env.VITE_API_BASE ?? "";

export async function fetchMarket(
  symbol: string,
  start: string,
  end: string
): Promise<MarketSeries> {
  const url = `${BASE}/api/market?symbol=${encodeURIComponent(
    symbol
  )}&start=${start}&end=${end}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Market fetch failed (${res.status})`);
  return res.json();
}

export async function composeSonata(
  symbol: string,
  start: string,
  end: string,
  nPhrases = 12
): Promise<ComposeResponse> {
  const res = await fetch(`${BASE}/api/compose`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, start, end, n_phrases: nPhrases }),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Compose failed (${res.status}): ${detail}`);
  }
  return res.json();
}

/** Decode a base64 MIDI payload into a downloadable Blob URL. */
export function midiBlobUrl(midiBase64: string): string {
  const binary = atob(midiBase64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const blob = new Blob([bytes], { type: "audio/midi" });
  return URL.createObjectURL(blob);
}
