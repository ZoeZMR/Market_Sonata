import type { ReactNode } from "react";
import Plot from "../plotly";
import type { MarketSeries } from "../types";

interface Props {
  market: MarketSeries;
}

const AXIS = {
  gridcolor: "rgba(255,255,255,0.06)",
  zerolinecolor: "rgba(255,255,255,0.1)",
  color: "#a7adc4",
};

const LAYOUT_BASE = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { color: "#a7adc4", family: "Inter, sans-serif", size: 11 },
  margin: { l: 48, r: 16, t: 32, b: 32 },
  showlegend: false,
  height: 220,
};

export default function MarketCharts({ market }: Props) {
  const { dates, close, volume, volatility, symbol, source } = market;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-2xl text-gold">{symbol} — Market Portrait</h2>
        {source === "synthetic" && (
          <span className="text-xs text-rose/80 border border-rose/30 rounded-full px-3 py-1">
            synthetic demo data
          </span>
        )}
      </div>

      <ChartCard title="Price">
        <Plot
          data={[
            {
              x: dates,
              y: close,
              type: "scatter",
              mode: "lines",
              line: { color: "#d9b26a", width: 2 },
              fill: "tozeroy",
              fillcolor: "rgba(217,178,106,0.08)",
            },
          ]}
          layout={{ ...LAYOUT_BASE, xaxis: AXIS, yaxis: { ...AXIS } }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: "100%" }}
        />
      </ChartCard>

      <ChartCard title="Volatility (rolling)">
        <Plot
          data={[
            {
              x: dates,
              y: volatility,
              type: "scatter",
              mode: "lines",
              line: { color: "#c97b84", width: 2 },
              fill: "tozeroy",
              fillcolor: "rgba(201,123,132,0.08)",
            },
          ]}
          layout={{ ...LAYOUT_BASE, xaxis: AXIS, yaxis: { ...AXIS } }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: "100%" }}
        />
      </ChartCard>

      <ChartCard title="Volume">
        <Plot
          data={[
            {
              x: dates,
              y: volume,
              type: "bar",
              marker: { color: "rgba(122,162,209,0.5)" },
            },
          ]}
          layout={{ ...LAYOUT_BASE, xaxis: AXIS, yaxis: { ...AXIS } }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: "100%" }}
        />
      </ChartCard>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="bg-panel/70 border border-white/5 rounded-2xl p-4 backdrop-blur">
      <p className="text-xs uppercase tracking-widest text-mist mb-1">{title}</p>
      {children}
    </div>
  );
}
