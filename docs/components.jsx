// components.jsx — presentational pieces for Bellwether (Thesis). Exported to window.
const { useState, useEffect, useRef } = React;

// ---- brand six-dot mark (the glyph on the Thesis jar label) ------------
function DotMark({ size = 18, color = "currentColor" }) {
  const r = size * 0.085;
  const cols = [size * 0.34, size * 0.5, size * 0.66];
  const rows = [size * 0.28, size * 0.5, size * 0.72];
  const dots = [];
  cols.forEach((cx) => rows.forEach((cy) => dots.push([cx, cy])));
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
      {dots.map(([cx, cy], i) => (
        <circle key={i} cx={cx} cy={cy} r={r} fill={color} />
      ))}
    </svg>
  );
}

// ---- reveal-on-scroll wrapper (scroll/viewport check — robust, no IO quirks) ----
function Reveal({ children, as = "div", delay = 0, className = "", ...rest }) {
  const ref = useRef(null);
  const [shown, setShown] = useState(false);
  useEffect(() => {
    if (shown) return;
    const el = ref.current;
    if (!el) return;
    const check = () => {
      const r = el.getBoundingClientRect();
      const vh = window.innerHeight || document.documentElement.clientHeight;
      if (r.top < vh * 0.92 && r.bottom > 0) { setShown(true); return true; }
      return false;
    };
    if (check()) return;
    const onScroll = () => { if (check()) cleanup(); };
    const cleanup = () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return cleanup;
  }, [shown]);
  const Tag = as;
  return (
    <Tag ref={ref} className={`reveal ${shown ? "in" : ""} ${className}`} data-d={delay || undefined} {...rest}>
      {children}
    </Tag>
  );
}

// ---- angle helpers (0deg = top, clockwise) ----------------------------
function polar(cx, cy, r, deg) {
  const rad = (deg * Math.PI) / 180;
  return [cx + r * Math.sin(rad), cy - r * Math.cos(rad)];
}
function arcPath(cx, cy, r, startDeg, endDeg) {
  const [x1, y1] = polar(cx, cy, r, startDeg);
  const [x2, y2] = polar(cx, cy, r, endDeg);
  const large = endDeg - startDeg > 180 ? 1 : 0;
  return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
}

// ---- tween hook --------------------------------------------------------
function useTween(target, ms = 900) {
  const [val, setVal] = useState(target);
  const from = useRef(target);
  const raf = useRef(0);
  useEffect(() => {
    const start = performance.now();
    const a = from.current;
    const b = target;
    if (a === b) return;
    cancelAnimationFrame(raf.current);
    const tick = (now) => {
      const p = Math.min(1, (now - start) / ms);
      const e = 1 - Math.pow(1 - p, 3); // easeOutCubic
      setVal(a + (b - a) * e);
      if (p < 1) raf.current = requestAnimationFrame(tick);
      else from.current = b;
    };
    raf.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf.current);
  }, [target, ms]);
  return val;
}

const TIER = {
  high:     { color: "var(--terracotta)", label: "High risk" },
  elevated: { color: "var(--gold)",       label: "Elevated" },
  watch:    { color: "var(--sage)",       label: "Watch" },
};

// ---- radial risk gauge (270° sweep) — PRESERVED, the user likes this ---
function RiskGauge({ score, projected = null, size = 168, stroke = 11, showProjected = false, variant = "gauge" }) {
  const target = showProjected && projected != null ? projected : score;
  const v = useTween(target, 950);
  const display = Math.round(v);
  const tier = window.BELLWETHER.tierOf(display);
  const color = TIER[tier].color;

  if (variant === "bar") {
    const tierNow = window.BELLWETHER.tierOf(display);
    return (
      <div className="riskbar">
        <div className="riskbar-num" style={{ color: TIER[tierNow].color }}>{display}</div>
        <div className="riskbar-track">
          <div className="riskbar-fill" style={{ width: `${display}%`, background: TIER[tierNow].color }} />
          {showProjected && projected != null && (
            <div className="riskbar-ghost" style={{ left: `${projected}%` }} />
          )}
        </div>
        <div className="riskbar-tier" style={{ color: TIER[tierNow].color }}>{TIER[tierNow].label}</div>
      </div>
    );
  }

  const cx = size / 2, cy = size / 2, r = (size - stroke) / 2 - 2;
  const START = -135, SWEEP = 270;
  const end = START + (display / 100) * SWEEP;
  const projEnd = projected != null ? START + (projected / 100) * SWEEP : null;
  return (
    <div className="gauge" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <path d={arcPath(cx, cy, r, START, START + SWEEP)} fill="none"
          style={{ stroke: "var(--hairline)" }} strokeWidth={stroke} strokeLinecap="round" />
        {showProjected && projEnd != null && projEnd < end && (
          <path d={arcPath(cx, cy, r, projEnd, end)} fill="none"
            style={{ stroke: "var(--ink-3)", opacity: 0.35 }} strokeWidth={stroke}
            strokeLinecap="round" strokeDasharray="1 7" />
        )}
        {display > 0 && (
          <path d={arcPath(cx, cy, r, START, end)} fill="none"
            style={{ stroke: color, transition: "stroke .5s ease" }} strokeWidth={stroke} strokeLinecap="round" />
        )}
      </svg>
      <div className="gauge-center">
        <div className="gauge-num" style={{ color }}>{display}</div>
        <div className="gauge-tier" style={{ color }}>{TIER[tier].label}</div>
      </div>
    </div>
  );
}

// ---- delta chip (trend vs last cycle) ---------------------------------
function Delta({ now, prev }) {
  const d = now - prev;
  if (d === 0) return <span className="delta delta-flat">— no change vs. last cycle</span>;
  const up = d > 0;
  return (
    <span className={`delta ${up ? "delta-up" : "delta-down"}`}>
      {up ? "▲" : "▼"} {Math.abs(d)} pts vs. last cycle
    </span>
  );
}

// ---- factor bar (positive = risk-driver, negative = protective) -------
function FactorBar({ label, weight, note, max }) {
  const protective = weight < 0;
  const pct = Math.min(100, (Math.abs(weight) / max) * 100);
  return (
    <div className="factor">
      <div className="factor-head">
        <span className="factor-label">{label}</span>
        <span className={`factor-weight ${protective ? "protective" : ""}`}>
          {protective ? "−" : "+"}{Math.abs(weight)}
        </span>
      </div>
      <div className="factor-track">
        <div className="factor-fill" style={{
          width: `${pct}%`,
          background: protective ? "var(--sage)" : "var(--accent)",
          opacity: protective ? 0.85 : Math.max(0.34, pct / 100),
        }} />
      </div>
      {note && <div className="factor-note">{note}</div>}
    </div>
  );
}

// ---- judge score (LLM-as-judge rating of the drafted message) ---------
function JudgeDots({ score, max = 5 }) {
  const dots = [];
  for (let i = 1; i <= max; i++) {
    const cls = score >= i ? "on" : score >= i - 0.5 ? "half" : "";
    dots.push(<i key={i} className={cls} />);
  }
  return (
    <div className="judge">
      <span className="judge-label">Judge</span>
      <span className="judge-dots">{dots}</span>
      <span className="judge-score">{score.toFixed(1)}<span> / {max.toFixed(1)}</span></span>
    </div>
  );
}

Object.assign(window, { DotMark, Reveal, RiskGauge, Delta, FactorBar, JudgeDots, TIER });
