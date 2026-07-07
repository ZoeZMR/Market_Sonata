interface Props {
  onBegin: () => void;
}

export default function Landing({ onBegin }: Props) {
  return (
    <section className="min-h-screen flex flex-col items-center justify-center text-center px-6 animate-fadeUp">
      <p className="uppercase tracking-[0.4em] text-mist text-xs mb-6">
        A generative music instrument
      </p>
      <h1 className="font-display text-6xl md:text-8xl font-semibold leading-none">
        Market <span className="text-gold italic">Sonata</span>
      </h1>
      <p className="mt-8 max-w-xl text-lg text-mist font-light leading-relaxed">
        A generative music system translating financial markets into musical
        narratives. Choose an asset, and hear the shape of its story told as a
        modern piano composition.
      </p>

      <button
        onClick={onBegin}
        className="mt-12 px-8 py-3 rounded-full border border-gold/60 text-gold
                   hover:bg-gold hover:text-ink transition-colors duration-300
                   tracking-widest uppercase text-sm"
      >
        Enter the Studio
      </button>

      <div className="mt-20 grid grid-cols-1 md:grid-cols-3 gap-6 max-w-3xl text-left">
        {[
          ["Price → Melody", "Rising markets ascend; falling markets descend."],
          ["Volatility → Tension", "Turbulence bends harmony toward dissonance."],
          ["Volume → Dynamics", "Participation swells the piano to full voice."],
        ].map(([t, d]) => (
          <div
            key={t}
            className="bg-panel/60 border border-white/5 rounded-xl p-5 backdrop-blur"
          >
            <h3 className="text-gold font-medium mb-1">{t}</h3>
            <p className="text-sm text-mist">{d}</p>
          </div>
        ))}
      </div>

      <p className="mt-16 text-xs text-mist/60">
        Influences — Joe Hisaishi · Philip Glass · Max Richter
      </p>
    </section>
  );
}
