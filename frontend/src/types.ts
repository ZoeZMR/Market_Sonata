// Shared type definitions mirroring the FastAPI response schema.

export interface MarketSeries {
  symbol: string;
  dates: string[];
  close: number[];
  volume: number[];
  returns: number[];
  volatility: number[];
  source: "yfinance" | "synthetic";
}

export interface PhraseFeatures {
  index: number;
  contour: number[];
  momentum: number;
  volatility: number;
  volume: number;
  brightness: number;
}

export interface MarketFeatures {
  symbol: string;
  start_date: string;
  end_date: string;
  n_days: number;
  trend: number;
  avg_volatility: number;
  avg_volume: number;
  total_return: number;
  max_drawdown: number;
  phrases: PhraseFeatures[];
  is_bull: boolean;
  mode_label: string;
}

export interface Note {
  pitch: number;
  start: number;
  duration: number;
  velocity: number;
  voice: "melody" | "harmony" | "bass";
}

export interface Analysis {
  program_note: string;
  used_llm: boolean;
  facts: Record<string, unknown>;
}

export interface ComposeResponse {
  symbol: string;
  key: string;
  mode: string;
  tempo: number;
  market: MarketSeries;
  features: MarketFeatures;
  analysis: Analysis;
  notes: Note[];
  midi_base64: string;
  midi_source: string;
}
