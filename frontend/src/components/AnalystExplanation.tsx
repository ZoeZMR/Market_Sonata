import type { ComposeResponse } from "../types";

interface Props {
  result: ComposeResponse;
}

export default function AnalystExplanation({ result }: Props) {
  const { analysis, features } = result;
  const note = analysis.program_note;

  const stats: [string, string][] = [
    ["Trend", features.mode_label],
    ["Total return", `${(features.total_return * 100).toFixed(1)}%`],
    ["Avg. volatility", pct(features.avg_volatility)],
    ["Avg. volume", pct(features.avg_volume)],
    ["Max drawdown", `−${(features.max_drawdown * 100).toFixed(1)}%`],
    ["Phrases", String(features.phrases.length)],
  ];

  return (
    <div className="bg-panel/70 border border-white/5 rounded-2xl p-6 backdrop-blur">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-display text-2xl text-gold">The Analyst's Note</h2>
        <span className="text-xs text-mist">
          {analysis.used_llm ? "AI-narrated" : "grounded narration"}
        </span>
      </div>

      <div className="prose-invert max-w-none">
        {note.split("\n\n").map((para, i) => (
          <p
            key={i}
            className="text-mist leading-relaxed mb-4 font-light first-letter:text-gold"
          >
            {para}
          </p>
        ))}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-6">
        {stats.map(([label, value]) => (
          <div
            key={label}
            className="bg-haze/60 border border-white/5 rounded-lg px-3 py-2"
          >
            <p className="text-[10px] uppercase tracking-widest text-mist">
              {label}
            </p>
            <p className="text-gold font-medium">{value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function pct(v: number): string {
  return `${Math.round(v * 100)}%`;
}
