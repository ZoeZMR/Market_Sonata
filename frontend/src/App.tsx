import { useState } from "react";
import Landing from "./components/Landing";
import MarketSelector from "./components/MarketSelector";
import MarketCharts from "./components/MarketCharts";
import MusicPlayer from "./components/MusicPlayer";
import AnalystExplanation from "./components/AnalystExplanation";
import { composeSonata } from "./api";
import type { ComposeResponse } from "./types";

type Stage = "landing" | "studio";

export default function App() {
  const [stage, setStage] = useState<Stage>("landing");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ComposeResponse | null>(null);

  async function handleCompose(symbol: string, start: string, end: string) {
    setLoading(true);
    setError(null);
    try {
      const res = await composeSonata(symbol, start, end);
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  if (stage === "landing") {
    return <Landing onBegin={() => setStage("studio")} />;
  }

  return (
    <div className="min-h-screen px-5 md:px-10 py-8 max-w-7xl mx-auto">
      <header className="flex items-center justify-between mb-8">
        <h1
          className="font-display text-3xl text-gold cursor-pointer"
          onClick={() => setStage("landing")}
        >
          Market <span className="italic">Sonata</span>
        </h1>
        <p className="text-xs text-mist tracking-widest uppercase hidden md:block">
          financial markets → musical narratives
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-6">
        {/* Left rail */}
        <div className="space-y-6">
          <MarketSelector onCompose={handleCompose} loading={loading} />
          {error && (
            <div className="bg-rose/10 border border-rose/40 text-rose rounded-xl p-4 text-sm">
              {error}
            </div>
          )}
          {result && <MarketCharts market={result.market} />}
        </div>

        {/* Main stage */}
        <div className="space-y-6">
          {!result && !loading && (
            <div className="h-full min-h-[400px] flex items-center justify-center
                            border border-dashed border-white/10 rounded-2xl text-center px-8">
              <div>
                <p className="font-display text-3xl text-mist mb-2">
                  Awaiting the market's voice
                </p>
                <p className="text-mist/70 text-sm max-w-md">
                  Choose a symbol and date range, then press{" "}
                  <span className="text-gold">Compose Sonata</span> to hear the
                  data become music.
                </p>
              </div>
            </div>
          )}

          {loading && (
            <div className="h-full min-h-[400px] flex items-center justify-center">
              <p className="font-display text-3xl text-gold animate-pulse">
                Listening to the market…
              </p>
            </div>
          )}

          {result && !loading && (
            <div className="space-y-6 animate-fadeUp">
              <MusicPlayer result={result} />
              <AnalystExplanation result={result} />
            </div>
          )}
        </div>
      </div>

      <footer className="mt-16 text-center text-xs text-mist/50">
        Market Sonata · a portfolio work in music technology · Hisaishi · Glass · Richter
      </footer>
    </div>
  );
}
