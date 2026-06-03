// app.jsx — Bellwether (Thesis) shell: topbar, dot-nav, section composition, tweaks.
const { useState, useEffect, useRef } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "accent": "#a4682f",
  "gaugeStyle": "gauge",
  "tableDensity": "regular"
}/*EDITMODE-END*/;

const NAV = [
  { id: "cover", label: "Top" },
  { id: "finding", label: "Finding" },
  { id: "method", label: "Method" },
  { id: "review", label: "Review" },
  { id: "says", label: "Output" },
];

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const { FLEET, ARCHETYPES, SUBSCRIBERS, tierOf } = window.BELLWETHER;
  const [active, setActive] = useState("cover");
  const [solid, setSolid] = useState(false);

  // topbar solid-on-scroll
  useEffect(() => {
    const onScroll = () => setSolid(window.scrollY > 36);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // active-section tracking for the dot nav (scroll-based — robust)
  useEffect(() => {
    const ids = NAV.map((n) => n.id).concat("close");
    const pick = () => {
      const mid = window.innerHeight * 0.42;
      let current = "cover";
      ids.forEach((id) => {
        const el = document.getElementById(id);
        if (el && el.getBoundingClientRect().top <= mid) current = id;
      });
      setActive(current === "close" ? "says" : current);
    };
    pick();
    window.addEventListener("scroll", pick, { passive: true });
    window.addEventListener("resize", pick);
    return () => {
      window.removeEventListener("scroll", pick);
      window.removeEventListener("resize", pick);
    };
  }, []);

  const jump = (id) => {
    const el = document.getElementById(id);
    if (!el) return;
    const top = el.getBoundingClientRect().top + window.scrollY - (id === "cover" ? 0 : 8);
    window.scrollTo({ top, behavior: "smooth" });
  };

  const rootStyle = {
    "--accent": t.accent,
    "--accent-ink": `color-mix(in oklab, ${t.accent}, #000 26%)`,
    "--accent-tint": `color-mix(in oklab, ${t.accent} 12%, #fff)`,
  };

  return (
    <div style={rootStyle}>
      {/* topbar */}
      <header className={`topbar ${solid ? "solid" : ""}`}>
        <div className="tb-brand">
          <span className="tb-mark"><DotMark size={18} color="var(--accent)" /></span>
          <span className="tb-name">Bellwether</span>
          <span className="tb-sep">·</span>
          <span className="tb-for">for Thesis</span>
        </div>
        <div className="tb-stats">
          <span className="tb-stat"><b>{FLEET.scored.toLocaleString()}</b><span>scored</span></span>
          <span className="tb-stat"><b>{FLEET.atRisk.toLocaleString()}</b><span>at risk</span></span>
          <span className="tb-stat"><b>{FLEET.reviewQueue}</b><span>in review</span></span>
          <span className="tb-cycle">{FLEET.cycleLabel}</span>
        </div>
      </header>

      {/* dot nav */}
      <nav className="dotnav" aria-label="Sections">
        {NAV.map((n) => (
          <button key={n.id} data-on={active === n.id ? "1" : "0"} onClick={() => jump(n.id)} aria-label={n.label}>
            <span className="dot-label">{n.label}</span>
            <span className="dot" />
          </button>
        ))}
      </nav>

      {/* sections */}
      <main>
        <Cover fleet={FLEET} />
        <FindingSection fleet={FLEET} archetypes={ARCHETYPES} />
        <MethodSection />
        <DecisionSection fleet={FLEET} subscribers={SUBSCRIBERS} archetypes={ARCHETYPES} tierOf={tierOf} gaugeStyle={t.gaugeStyle} />
        <MessagesSection subscribers={SUBSCRIBERS} tierOf={tierOf} />
        <CloseSection fleet={FLEET} />
      </main>

      {/* tweaks */}
      <TweaksPanel>
        <TweakSection label="Brand" />
        <TweakColor label="Accent" value={t.accent}
          options={["#a4682f", "#4f6147", "#3c6377", "#7c4d22"]}
          onChange={(v) => setTweak("accent", v)} />
        <TweakSection label="Risk display" />
        <TweakRadio label="Risk viz" value={t.gaugeStyle}
          options={["gauge", "bar"]} onChange={(v) => setTweak("gaugeStyle", v)} />
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
