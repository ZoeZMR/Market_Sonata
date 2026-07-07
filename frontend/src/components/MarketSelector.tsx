import { useState } from "react";

interface Props {
  onCompose: (symbol: string, start: string, end: string) => void;
  loading: boolean;
}

const PRESETS = ["AAPL", "TSLA", "SPY", "NVDA", "BTC-USD", "MSFT"];

export default function MarketSelector({ onCompose, loading }: Props) {
  const [symbol, setSymbol] = useState("AAPL");
  const [start, setStart] = useState("2024-01-01");
  const [end, setEnd] = useState("2024-12-31");

  return (
    <div className="bg-panel/70 border border-white/5 rounded-2xl p-6 backdrop-blur">
      <h2 className="font-display text-2xl mb-4 text-gold">Select a Market</h2>

      <label className="block text-xs uppercase tracking-widest text-mist mb-1">
        Symbol
      </label>
      <input
        value={symbol}
        onChange={(e) => setSymbol(e.target.value.toUpperCase())}
        className="w-full bg-haze border border-white/10 rounded-lg px-3 py-2 mb-3
                   focus:outline-none focus:border-gold/60 text-lg tracking-wide"
      />

      <div className="flex flex-wrap gap-2 mb-5">
        {PRESETS.map((p) => (
          <button
            key={p}
            onClick={() => setSymbol(p)}
            className={`text-xs px-3 py-1 rounded-full border transition-colors ${
              symbol === p
                ? "bg-gold text-ink border-gold"
                : "border-white/10 text-mist hover:border-gold/50"
            }`}
          >
            {p}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-3 mb-6">
        <div>
          <label className="block text-xs uppercase tracking-widest text-mist mb-1">
            From
          </label>
          <input
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            className="w-full bg-haze border border-white/10 rounded-lg px-3 py-2
                       focus:outline-none focus:border-gold/60"
          />
        </div>
        <div>
          <label className="block text-xs uppercase tracking-widest text-mist mb-1">
            To
          </label>
          <input
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            className="w-full bg-haze border border-white/10 rounded-lg px-3 py-2
                       focus:outline-none focus:border-gold/60"
          />
        </div>
      </div>

      <button
        disabled={loading}
        onClick={() => onCompose(symbol, start, end)}
        className="w-full py-3 rounded-xl bg-gold text-ink font-medium tracking-widest
                   uppercase text-sm hover:brightness-110 transition disabled:opacity-50
                   disabled:cursor-wait"
      >
        {loading ? "Composing…" : "Compose Sonata"}
      </button>
    </div>
  );
}
