// sections.jsx — Bellwether scroll presentation sections. Exported to window.
const { useState: useStateS, useMemo: useMemoS } = React;

function projectedRisk(s) {
  return Math.max(8, Math.round(s.score - s.measure.liftPts * 0.92));
}
function fmt(n) {return n.toLocaleString("en-US");}

// ───────────────────────── Cover ─────────────────────────
function Cover({ fleet }) {
  return (
    <section id="cover" className="cover" data-screen-label="Cover">
      <Reveal className="cover-mark">
        <DotMark size={22} color="var(--accent)" />
        <span className="cm-name">Subscriber retention intelligence · built for Thesis</span>
      </Reveal>
      <Reveal as="h1" className="cover-h1" delay={1}>Bellwether</Reveal>
      <Reveal as="p" className="cover-line" delay={2}>
        They chose Thesis because they own their mind.<br />
        <b>Know when that mind is starting to drift.</b>
      </Reveal>
      <div className="cover-foot">
        <Reveal className="cover-scored" delay={3}>
          <b>{fmt(fleet.scored)}</b>
          <span>subscribers scored · {fleet.cycleLabel}</span>
        </Reveal>
        <div className="scrollcue"><span>The finding</span><i /></div>
      </div>
    </section>);
}

// ───────────────────────── The Finding ─────────────────────────
function FindingSection({ fleet, archetypes }) {
  const maxRate = Math.max(...archetypes.map((a) => a.rate));
  return (
    <section id="finding" className="section" data-screen-label="The Finding">
      <Reveal as="div" className="eyebrow">01 · The finding</Reveal>
      <div className="finding-top">
        <Reveal className="pull" delay={1}>
          <div className="pull-num"><em>{fmt(fleet.atRisk)}</em></div>
          <div className="pull-label"><b>subscribers at risk</b> this month</div>
        </Reveal>
        <Reveal className="pull-side" delay={2}>
          across <b>{fmt(fleet.scored)}</b> active Thesis<br />subscribers scored this cycle
        </Reveal>
      </div>

      <Reveal delay={2}>
        <table className="atable">
          <thead>
            <tr>
              <th>Archetype</th>
              <th className="num">Members</th>
              <th className="num">At risk</th>
            </tr>
          </thead>
          <tbody>
            {archetypes.map((a) => {
              const hot = a.rate >= 20;
              const tone = a.rate >= 50 ? "var(--terracotta)" : a.rate >= 20 ? "var(--gold)" : "var(--accent)";
              return (
                <tr key={a.key} className={hot ? "hot" : ""}>
                  <td>
                    <div className="at-name">{a.name}{a.rate >= 50 && <span className="at-flag">Acute</span>}</div>
                    <div className="at-blurb">{a.blurb}</div>
                  </td>
                  <td className="at-num">{fmt(a.members)}</td>
                  <td>
                    <div className="at-risk">
                      <span className="at-bar"><i style={{ width: `${a.rate / maxRate * 100}%`, background: tone }} /></span>
                      <span className="at-risk-v" style={{ color: a.rate >= 20 ? tone : "var(--ink)" }}>
                        {fmt(a.atRisk)}<small>{a.rate}%</small>
                      </span>
                    </div>
                  </td>
                </tr>);
            })}
          </tbody>
        </table>
      </Reveal>
    </section>);
}

// ───────────────────────── Method (4 questions) ─────────────────────────
const PILLARS = [
  {
    n: "01", q: "Who",
    d: "26,584 subscribers scored each cycle. Behavioral signals — order cadence, billing timing, formula history, email engagement — produce a calibrated churn probability for every one. The top 41 are escalated for human review this cycle."
  },
  {
    n: "02", q: "Why",
    d: "Each score comes with an explanation: the signals driving it, how much each one contributes, and which behavioral archetype they map to. You're not approving a black-box recommendation. You're approving a reasoned one."
  },
  {
    n: "03", q: "What",
    d: "The archetype determines the action. A payment decline gets a frictionless card-update link — not a win-back coupon. Price anxiety gets a cost-per-day reframe. Overstock gets a cadence adjustment. The right fix for the actual cause."
  },
  {
    n: "04", q: "Learn",
    d: "Every approved action creates a natural experiment: 10% held back as a control, a read-out date set. The model's next training run sees real labeled outcomes. Each cycle, the system gets incrementally sharper."
  }
];

function MethodSection() {
  return (
    <section id="method" className="section--tint" data-screen-label="Method">
      <div className="inner">
        <Reveal className="frame-head">
          <span className="eyebrow">02 · The method</span>
          <h2 className="frame-title">A decision system, not a dashboard.</h2>
          <p className="frame-sub">For each at-risk subscriber, Bellwether answers four questions — and closes the loop on whether the answer worked.</p>
        </Reveal>
        <Reveal delay={1}>
          <div className="pillars">
            {PILLARS.map((p) =>
              <div className="pillar" key={p.n}>
                <span className="pillar-n">{p.n}</span>
                <span className="pillar-q">{p.q}</span>
                <span className="pillar-d">{p.d}</span>
              </div>
            )}
          </div>
        </Reveal>
      </div>
    </section>);
}

// ───────────────────────── Decision dashboard ─────────────────────────
function DecisionSection({ fleet, subscribers, tierOf, gaugeStyle }) {
  const ranked = useMemoS(() => [...subscribers].sort((a, b) => b.score - a.score), [subscribers]);
  const [selectedId, setSelectedId] = useStateS(ranked[0].id);
  const [status, setStatus] = useStateS({});
  const sub = subscribers.find((s) => s.id === selectedId);
  const st = status[selectedId];
  const maxWeight = Math.max(...sub.factors.map((f) => Math.abs(f.weight)));
  const decide = (kind) => setStatus((p) => ({ ...p, [selectedId]: kind }));
  const undo = () => setStatus((p) => {const n = { ...p };delete n[selectedId];return n;});

  return (
    <section id="review" className="section section--wide" data-screen-label="Review queue">
      <Reveal className="dec-head">
        <span className="eyebrow">03 · The review queue</span>
        <h2 className="frame-title">Who is at risk, why, what to do, and how we'll know it worked.</h2>
        <p className="frame-sub">Of {fmt(fleet.atRisk)} at-risk, {fleet.reviewQueue} are escalated for human review this cycle. Here are the top five — pick one to see the full picture.</p>
      </Reveal>

      <div className="deckmain">
        {/* roster */}
        <aside className="roster">
          <div className="roster-head"><span>Roster · ranked by risk</span></div>
          {ranked.map((s) => {
            const tier = tierOf(s.score);
            return (
              <button key={s.id} className={`row ${s.id === selectedId ? "row-on" : ""}`} onClick={() => setSelectedId(s.id)}>
                <span className="row-avatar">{s.initials}</span>
                <span className="row-body">
                  <span className="row-name">{s.name}</span>
                  <span className="row-sku">{s.archetype}</span>
                </span>
                <span className="row-meta">
                  <span className="row-score" style={{ color: TIER[tier].color }}>{s.score}</span>
                  <span className="row-pip" style={{ background: TIER[tier].color }} />
                </span>
              </button>);
          })}
          <div className="roster-foot">Showing top <b>5</b> of <b>{fleet.reviewQueue}</b> flagged for review</div>
        </aside>

        {/* detail */}
        <div className="detail" key={selectedId}>
          <div className="detail-main">
            <div className="dos-arch"><span className="tag">{sub.archetype}</span></div>
            <h3 className="dos-name">{sub.name}</h3>
            <div className="dos-loc">{sub.location}</div>
            <p className="dos-headline">{sub.headline}</p>

            {/* 01 who / how risky */}
            <div className="block">
              <div className="b-eyebrow"><span className="n">01</span><span className="t">Who & how risky</span></div>
              <div className="risk-row">
                <RiskGauge score={sub.score} projected={projectedRisk(sub)} showProjected={st === "approved"} variant={gaugeStyle} />
                <div className="risk-side">
                  <Delta now={sub.score} prev={sub.prevScore} />
                  <div className="risk-scale">
                    <span><i style={{ background: "var(--terracotta)" }} />High ≥ 60</span>
                    <span><i style={{ background: "var(--gold)" }} />Elevated 30–59</span>
                    <span><i style={{ background: "var(--sage)" }} />Watch &lt; 30</span>
                  </div>
                  {st === "approved" &&
                    <div className="proj-note">Projected after action: <b>{projectedRisk(sub)}</b>
                      <span> ({TIER[tierOf(projectedRisk(sub))].label.toLowerCase()})</span></div>
                  }
                </div>
              </div>
            </div>

            {/* 02 why */}
            <div className="block">
              <div className="b-eyebrow"><span className="n">02</span><span className="t">Why it's happening</span></div>
              <div className="factors">
                {sub.factors.map((f, i) => <FactorBar key={i} {...f} max={maxWeight} />)}
              </div>
              <div className="factors-key">+ adds to risk · − protective signal</div>
            </div>

            {/* 03 action */}
            <div className="block">
              <div className="b-eyebrow"><span className="n">03</span><span className="t">Recommended action</span></div>
              <div className={`action ${st ? "action-decided" : ""}`}>
                <div className="action-top">
                  <span className="action-kind">{sub.action.kind}</span>
                  {st === "approved" && <span className="action-state on">✓ Scheduled</span>}
                  {st === "held" && <span className="action-state held">○ Holding · monitoring</span>}
                </div>
                <h4 className="action-title">{sub.action.title}</h4>
                <p className="action-detail">{sub.action.detail}</p>
                <div className="action-why"><span className="why-tag">Why this, not a discount</span>{sub.action.why}</div>
                <div className="action-feet">
                  <div><div className="feet-k">Effort</div><div className="feet-v">{sub.action.effort}</div></div>
                  <div><div className="feet-k">Cost</div><div className="feet-v">{sub.action.cost}</div></div>
                </div>
                {!st ?
                  <div className="action-cta">
                    <button className="btn btn-primary" onClick={() => decide("approved")}>Approve action</button>
                    <button className="btn btn-ghost" onClick={() => decide("held")}>Hold &amp; watch</button>
                    <div className="alts">
                      <span className="alts-label">Alternatives</span>
                      {sub.alternatives.map((a, i) => <span key={i} className="alt">{a}</span>)}
                    </div>
                  </div> :
                  <div className="action-cta">
                    <button className="btn btn-undo" onClick={undo}>↺ Undo decision</button>
                  </div>
                }
              </div>
            </div>

            {/* 04 measure */}
            <div className="block">
              <div className="b-eyebrow"><span className="n">04</span><span className="t">How we'll know it worked</span></div>
              <div className={`measure ${st === "approved" ? "measure-live" : ""}`}>
                <div className="m-grid">
                  <div><div className="mstat-k">Expected risk drop</div><div className="mstat-v accent">−{sub.measure.liftPts} pts</div><div className="mstat-sub">±{sub.measure.ci} (90% CI)</div></div>
                  <div><div className="mstat-k">Holdout (control)</div><div className="mstat-v">{sub.measure.holdoutPct ? `${sub.measure.holdoutPct}%` : "—"}</div><div className="mstat-sub">{sub.measure.holdoutPct ? "matched cohort" : "monitor only"}</div></div>
                  <div><div className="mstat-k">Read-out date</div><div className="mstat-v">{sub.measure.checkBack}</div><div className="mstat-sub">auto check-in</div></div>
                </div>
                <div className="m-rows">
                  <div className="m-line"><span className="m-k">Success</span><span className="m-v">{sub.measure.success}</span></div>
                  <div className="m-line"><span className="m-k">Baseline</span><span className="m-v">{sub.measure.baseline}</span></div>
                </div>
                {st === "approved" &&
                  <div className="m-active"><span className="m-dot" /> Experiment live · {100 - sub.measure.holdoutPct}% treated, {sub.measure.holdoutPct}% held back · reads out {sub.measure.checkBack}</div>
                }
                {st === "held" &&
                  <div className="m-active held"><span className="m-dot" /> Monitoring only · no treatment applied · re-scores next cycle</div>
                }
              </div>
            </div>
          </div>

          {/* floating rep glance card */}
          <aside className="repcard">
            <div className="rep-hd"><span className="rep-avatar2">{sub.initials}</span><b>At a glance</b></div>
            <div className="rep-list">
              <div className="rep-row"><span className="rep-k">Product</span><span className="rep-v">{sub.formula}</span></div>
              <div className="rep-row"><span className="rep-k">Cadence</span><span className="rep-v">{sub.cadence}</span></div>
              <div className="rep-row"><span className="rep-k">Tenure</span><span className="rep-v">{sub.tenureLabel}</span></div>
              <div className="rep-row"><span className="rep-k">Lifetime value</span><span className="rep-v accent">${fmt(sub.ltv)}</span></div>
              <div className="rep-row"><span className="rep-k">Next renewal</span><span className="rep-v">{sub.nextRenewal}</span></div>
            </div>
          </aside>
        </div>
      </div>
    </section>);
}

// ───────────────────────── Messages ─────────────────────────
function MessagesSection({ subscribers, tierOf }) {
  return (
    <section id="says" className="section--tint" data-screen-label="What it says">
      <div className="inner">
        <Reveal className="msg-head">
          <span className="eyebrow">04 · What it produces</span>
          <h2 className="frame-title">The Bellwether notes</h2>
          <p className="frame-sub">Each message is drafted from behavioral signals — then scored by an LLM judge before a human ever sees it. No templates. Personalized to the subscriber.</p>
        </Reveal>
        <div className="msg-grid">
          {subscribers.map((s, i) => {
            const tier = tierOf(s.score);
            return (
              <Reveal key={s.id} delay={Math.min(4, i + 1)}>
                <div className="msgcard">
                  <div className="msg-meta">
                    <span className="msg-arch">{s.archetype}</span>
                    <div className="msg-chips">
                      <span className="msg-chip"><span className="k">Formula</span><span className="v">{s.formulaShort}</span></span>
                      <span className="msg-chip"><span className="k">Tenure</span><span className="v">{s.tenureLabel}</span></span>
                      <span className="msg-chip"><span className="k">Risk</span><span className="v risk" style={{ color: TIER[tier].color }}>{s.score}%</span></span>
                    </div>
                  </div>
                  <div className="msg-body">
                    <p className="msg-text">{s.message}</p>
                    <div className="msg-foot">
                      <JudgeDots score={s.judge} />
                      <span className="msg-tag">draft · pending send</span>
                    </div>
                  </div>
                </div>
              </Reveal>);
          })}
        </div>
      </div>
    </section>);
}

// ───────────────────────── Close ─────────────────────────
function CloseSection({ fleet }) {
  return (
    <section id="close" className="close" data-screen-label="Close">
      <Reveal as="div" className="eyebrow muted">The loop</Reveal>
      <Reveal as="div" className="close-loop" delay={1} style={{ marginTop: 22 }}>
        <em>Score</em><span className="arrow">→</span>
        <em>Intervene</em><span className="arrow">→</span>
        <em>Dispatch</em><span className="arrow">→</span>
        <em>Learn</em>
      </Reveal>
      <Reveal as="p" className="close-sub" delay={2}>
        Right now, dispatch is simulated. The only gap between this and live Klaviyo sends is swapping one adapter. When outcomes return — did they churn after the message? — they feed the next model cycle. The system gets sharper every run.
      </Reveal>
      <Reveal as="div" className="close-meta" delay={3}>
        <DotMark size={14} color="var(--ink-3)" />
        Bellwether · {fleet.cycleLabel} · {fleet.modelNote}
      </Reveal>
    </section>);
}

Object.assign(window, {
  Cover, FindingSection, MethodSection, DecisionSection, MessagesSection, CloseSection, projectedRisk
});
